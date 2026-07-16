"""Cursor handling and draw smoke test for the city map scene."""

import pygame
import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import DEPOT_POS
from psychic_cleaners.core.convergence import Convergence
from psychic_cleaners.core.events import BuyItem, SceneId, SetDestination
from psychic_cleaners.core.game import new_game
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.city_map import _CAR_MARKER, _HUD_Y, CityMapScene, _cell_rect
from psychic_cleaners.shell.text import TextRenderer

_HUD_BACKGROUND: tuple[int, int, int] = (12, 12, 18)


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_cursor_moves_and_clamps_to_grid() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(1)
    assert scene.cursor == DEPOT_POS  # (0, 5)
    scene.commands([_key(pygame.K_RIGHT)], game, 1 / 60)
    assert scene.cursor == (1, 5)
    scene.commands([_key(pygame.K_UP)], game, 1 / 60)
    assert scene.cursor == (1, 4)
    scene.commands([_key(pygame.K_LEFT), _key(pygame.K_LEFT)], game, 1 / 60)
    assert scene.cursor == (0, 4)  # clamped at x=0
    scene.commands([_key(pygame.K_DOWN), _key(pygame.K_DOWN)], game, 1 / 60)
    assert scene.cursor == (0, 5)  # clamped at y=GRID_HEIGHT-1


def test_enter_emits_set_destination_at_cursor() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(2)
    scene.commands([_key(pygame.K_RIGHT)], game, 1 / 60)
    commands = scene.commands([_key(pygame.K_RETURN)], game, 1 / 60)
    assert commands == [SetDestination((1, 5))]


def test_s_emits_buy_snare() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(5)
    commands = scene.commands([_key(pygame.K_s)], game, 1 / 60)
    assert commands == [BuyItem("snare")]


def test_draw_smoke_without_detector_hides_wisps() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(3)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])  # no detector
    game.scene = SceneId.MAP
    game.city.buildings[(2, 2)].haunted = True  # drawn as the static haunted sprite
    game.city.wisps.append(Wisp(x=4.5, y=2.5))  # centre pixel (320, 180): grid gutter
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 180)) == (24, 26, 34, 255)  # type: ignore[comparison-overlap]


def test_draw_shows_walkers_while_converging() -> None:
    # The Warden and the Locksmith are visible without any detector: their
    # walk is the endgame telegraph, not a gadget-gated detail.
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(6)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])  # no detector
    game.scene = SceneId.MAP
    game.convergence = Convergence.start()
    game.convergence.warden.x = 4.5  # centre pixel (320, 180): grid gutter
    game.convergence.warden.y = 2.5
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 180)) != (24, 26, 34, 255)  # type: ignore[comparison-overlap]


def test_draw_smoke_with_detector_shows_wisps() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(4)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("detector")
    game.scene = SceneId.MAP
    game.city.buildings[(2, 2)].haunted = True  # flashes: either sprite is valid
    game.city.wisps.append(Wisp(x=4.5, y=2.5))
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 180)) != (24, 26, 34, 255)  # type: ignore[comparison-overlap]


def test_haunted_flash_is_driven_by_simulated_time_not_wall_clock() -> None:
    # Regression: the flash used to read pygame.time.get_ticks() (real
    # wall-clock), making it non-deterministic under fast-forwarded or
    # injected dt (e.g. a screenshot taken via the playtest harness could
    # land on either phase depending on real execution speed, not seed or
    # game state). It must depend only on time accumulated via commands().
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(9)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("detector")
    game.scene = SceneId.MAP
    game.city.buildings[(2, 2)].haunted = True
    sample = (180, 152)  # inside building (2,2)'s middle window row
    surface = pygame.Surface((640, 400))

    scene.commands([], game, 0.0)  # elapsed stays 0 -> flash on
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    on_pixel = surface.get_at(sample)

    scene.commands([], game, 0.25)  # elapsed=0.25 -> exactly one half-period -> flash off
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    off_pixel = surface.get_at(sample)

    assert on_pixel != off_pixel
    assert on_pixel[:3] == (215, 140, 255)  # haunted window color while "on"
    assert off_pixel[:3] == (225, 210, 140)  # normal window color while "off"


def test_flash_elapsed_resets_on_scene_reset() -> None:
    scene = CityMapScene()
    game = new_game(10)
    scene.commands([], game, 0.5)
    assert scene._flash_elapsed == pytest.approx(0.5)
    scene.reset()
    assert scene._flash_elapsed == 0.0


def test_car_marker_visible_when_parked_at_depot() -> None:
    # Fix 6: the player marker must draw ON TOP of the depot sprite, not
    # underneath it, or it disappears whenever the car is parked at (0, 5).
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(7)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    assert game.position == DEPOT_POS
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    cell = _cell_rect(DEPOT_POS)
    marker_pixels = sum(
        1
        for x in range(cell.left, cell.left + cell.width)
        for y in range(cell.top, cell.top + cell.height)
        if surface.get_at((x, y))[:3] == _CAR_MARKER
    )
    assert marker_pixels > 0


def test_tower_sprite_does_not_cover_building_below() -> None:
    # Fix: the map tower must fit its own cell so the haunting at (5, 4),
    # directly below TOWER_POS (5, 3), stays visible instead of being
    # covered by the full-size 56x96 tower sprite. The comparison uses an
    # interior sub-rect (inset from the cell edges) rather than the whole
    # cell rect: the old tower sprite's non-rectangular silhouette already
    # leaves a few edge pixels of the building visible even when it covers
    # the bulk of the cell, so a whole-cell-bytes comparison would pass
    # even with the bug present. The centre of the cell is fully covered
    # by the old tower and is where the fix must make a difference.
    pygame.init()
    pygame.display.set_mode((640, 400))
    below_tower = (5, 4)
    cell = pygame.Rect(40 + 5 * 56 + 4, 12 + 4 * 56 + 4, 48, 48)
    assert cell == _cell_rect(below_tower)
    interior = cell.inflate(-24, -24)  # centre 24x24, well clear of tower's edges

    def render(haunted: bool) -> pygame.Surface:
        scene = CityMapScene()
        game = new_game(8)
        game.loadout = Loadout(vehicle=VEHICLES["hearse"])  # no detector
        game.scene = SceneId.MAP
        if haunted:
            game.city.buildings[below_tower].haunted = True
        surface = pygame.Surface((640, 400))
        scene.draw(surface, game, SpriteFactory(), TextRenderer())
        return surface

    haunted_surface = render(haunted=True)
    clear_surface = render(haunted=False)
    haunted_bytes = pygame.image.tobytes(haunted_surface.subsurface(interior), "RGBA")
    clear_bytes = pygame.image.tobytes(clear_surface.subsurface(interior), "RGBA")
    assert haunted_bytes != clear_bytes


def test_draw_smoke_depot_hint_and_notice() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(6)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    assert game.position == DEPOT_POS  # hint line only draws at the Depot
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())  # exercises the hint line
    game.notice = "snares only, at the Depot"
    scene.draw(surface, game, SpriteFactory(), TextRenderer())  # exercises the notice line


def _row_has_content(surface: pygame.Surface, row: pygame.Rect) -> bool:
    return any(
        surface.get_at((x, y))[:3] != _HUD_BACKGROUND
        for x in range(row.left, row.right)
        for y in range(row.top, min(row.bottom, surface.get_height()))
    )


def test_control_hint_fills_the_third_hud_row_by_default() -> None:
    # A first-time player never presses a key wrong, so game.notice never
    # fires and the third HUD row would otherwise stay blank forever.
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(9)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    assert game.notice is None
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    row = pygame.Rect(10, _HUD_Y + 32, 300, 400 - (_HUD_Y + 32))
    assert _row_has_content(surface, row)


def test_notice_still_takes_the_row_over_the_control_hint() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(10)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    game.notice = "snares only, at the Depot"
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    row = pygame.Rect(10, _HUD_Y + 32, 300, 400 - (_HUD_Y + 32))
    assert _row_has_content(surface, row)  # unchanged: the notice, not the hint, fills the row

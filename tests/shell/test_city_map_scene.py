"""Cursor handling and draw smoke test for the city map scene."""

import pygame

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import DEPOT_POS
from psychic_cleaners.core.events import BuyItem, SceneId, SetDestination
from psychic_cleaners.core.game import new_game
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.text import TextRenderer


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_cursor_moves_and_clamps_to_grid() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(1)
    assert scene.cursor == DEPOT_POS  # (0, 5)
    scene.commands([_key(pygame.K_RIGHT)], game)
    assert scene.cursor == (1, 5)
    scene.commands([_key(pygame.K_UP)], game)
    assert scene.cursor == (1, 4)
    scene.commands([_key(pygame.K_LEFT), _key(pygame.K_LEFT)], game)
    assert scene.cursor == (0, 4)  # clamped at x=0
    scene.commands([_key(pygame.K_DOWN), _key(pygame.K_DOWN)], game)
    assert scene.cursor == (0, 5)  # clamped at y=GRID_HEIGHT-1


def test_enter_emits_set_destination_at_cursor() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(2)
    scene.commands([_key(pygame.K_RIGHT)], game)
    commands = scene.commands([_key(pygame.K_RETURN)], game)
    assert commands == [SetDestination((1, 5))]


def test_s_emits_buy_snare() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(5)
    commands = scene.commands([_key(pygame.K_s)], game)
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

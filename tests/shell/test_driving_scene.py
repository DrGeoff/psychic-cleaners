"""Key-mapping, sprite, and draw-smoke tests for the driving scene."""

from collections.abc import Iterator

import pygame
import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.drive import DriveSim, RoadWisp
from psychic_cleaners.core.events import SceneId, Steer
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.driving import DrivingScene
from psychic_cleaners.shell.text import TextRenderer


@pytest.fixture(autouse=True)
def _pygame() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.mark.parametrize("vehicle_id", ["compact", "hearse", "wagon", "performance"])
def test_car_sprites_are_48_by_24(vehicle_id: str) -> None:
    sprite = SpriteFactory().get(f"car.{vehicle_id}")
    assert sprite.get_size() == (48, 24)


def test_car_sprites_have_distinct_body_colours() -> None:
    factory = SpriteFactory()
    bodies = {
        tuple(factory.get(f"car.{vid}").get_at((24, 14)))
        for vid in ("compact", "hearse", "wagon", "performance")
    }
    assert len(bodies) == 4


def test_faint_wisp_sprite_is_translucent() -> None:
    sprite = SpriteFactory().get("wisp.faint")
    assert sprite.get_flags() & pygame.SRCALPHA
    alphas = {
        sprite.get_at((x, y)).a
        for x in range(sprite.get_width())
        for y in range(sprite.get_height())
    }
    assert 90 in alphas  # drawn pixels use the contract-pinned alpha 90
    assert 255 not in alphas  # nothing fully opaque


def _driving_game() -> Game:
    game = new_game(1)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.DRIVE
    drive = DriveSim(distance_total=1200.0, speed=140.0, has_vacuum=True, has_lens=False)
    drive.distance_done = 480.0
    drive.wisps.append(RoadWisp(x=320.0, lane=0, faint=False))
    drive.wisps.append(RoadWisp(x=400.0, lane=2, faint=True))
    game.drive = drive
    return game


def test_up_key_steers_toward_lane_zero() -> None:
    scene = DrivingScene()
    events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)]
    assert scene.commands(events, _driving_game()) == [Steer(delta=-1)]


def test_down_key_steers_toward_last_lane() -> None:
    scene = DrivingScene()
    events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)]
    assert scene.commands(events, _driving_game()) == [Steer(delta=1)]


def test_other_events_produce_no_commands() -> None:
    scene = DrivingScene()
    events = [
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE),
        pygame.event.Event(pygame.KEYUP, key=pygame.K_UP),
    ]
    assert scene.commands(events, _driving_game()) == []


def test_draw_renders_an_active_drive_without_error() -> None:
    surface = pygame.Surface((640, 400))
    DrivingScene().draw(surface, _driving_game(), SpriteFactory(), TextRenderer())


def test_draw_with_lens_owned_renders_faint_wisps_without_error() -> None:
    game = _driving_game()
    assert game.loadout is not None
    game.loadout.add("lens")
    surface = pygame.Surface((640, 400))
    DrivingScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_draw_without_an_active_drive_does_not_crash() -> None:
    game = _driving_game()
    game.drive = None
    surface = pygame.Surface((640, 400))
    DrivingScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_scene_registry_uses_driving_scene() -> None:
    from psychic_cleaners.shell.app import SCENES

    assert isinstance(SCENES[SceneId.DRIVE], DrivingScene)

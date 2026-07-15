"""World-scene mascot overlay: flashing banner and B-key bait mapping in MAP, DRIVE, BUST."""

from collections.abc import Callable, Iterator

import pygame
import pytest

from psychic_cleaners.core.bust import BustSim
from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.drive import DriveSim
from psychic_cleaners.core.events import DeployBait
from psychic_cleaners.core.game import Game, SceneId, new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import Scene, _draw_mascot_banner
from psychic_cleaners.shell.scenes.busting import BustingScene
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.scenes.driving import DrivingScene
from psychic_cleaners.shell.text import TextRenderer


@pytest.fixture(autouse=True)
def _pygame() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((640, 400))
    yield
    pygame.quit()


WORLD_SCENES: list[tuple[SceneId, Callable[[], Scene]]] = [
    (SceneId.MAP, CityMapScene),
    (SceneId.DRIVE, DrivingScene),
    (SceneId.BUST, BustingScene),
]


def _world_game(scene_id: SceneId) -> Game:
    """A Game dropped into the given world scene with the state its scene draws from."""
    game = new_game(301)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("bait")
    game.scene = scene_id
    if scene_id is SceneId.DRIVE:
        game.drive = DriveSim(distance_total=800.0, speed=140.0, has_vacuum=False, has_lens=False)
    elif scene_id is SceneId.BUST:
        game.bust = BustSim()
    return game


@pytest.mark.parametrize(("scene_id", "make_scene"), WORLD_SCENES)
def test_b_key_maps_to_deploy_bait(scene_id: SceneId, make_scene: Callable[[], Scene]) -> None:
    scene = make_scene()
    key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
    commands = scene.commands([key_event], _world_game(scene_id), 1 / 60)
    assert any(isinstance(c, DeployBait) for c in commands)


@pytest.mark.parametrize(("scene_id", "make_scene"), WORLD_SCENES)
def test_alert_overlay_full_scene_draw_smoke(
    scene_id: SceneId, make_scene: Callable[[], Scene]
) -> None:
    scene = make_scene()
    game = _world_game(scene_id)
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = 10.0
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())  # must not raise


def test_banner_visible_only_in_alert_and_flash_on_phase() -> None:
    text = TextRenderer()
    game = _world_game(SceneId.MAP)

    def banner_bytes() -> bytes:
        surface = pygame.Surface((640, 400))
        surface.fill((0, 0, 0))
        _draw_mascot_banner(surface, game, text)
        return pygame.image.tobytes(surface, "RGB")

    blank = banner_bytes()  # CALM: helper draws nothing
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = 10.0  # elapsed 0.0 -> int(0.0) % 2 == 0 -> visible phase
    visible = banner_bytes()
    game.mascot.alert_remaining = 9.5  # elapsed 0.5 -> int(1.0) % 2 == 1 -> hidden phase
    hidden = banner_bytes()
    assert visible != blank
    assert hidden == blank


def test_banner_visible_at_alert_start_bug_case() -> None:
    """The very start of an alert (remaining just under the window) must flash ON.

    Before the fix, the flash phase was computed from alert_remaining directly
    (counting DOWN from MASCOT_ALERT_WINDOW), so the first ~0.5s of an alert
    landed in the "off" phase -- the banner was invisible exactly when the
    player most needed to see it.
    """
    text = TextRenderer()
    game = _world_game(SceneId.MAP)
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = 9.9  # elapsed 0.1 -> must be visible

    surface = pygame.Surface((640, 400))
    surface.fill((0, 0, 0))
    _draw_mascot_banner(surface, game, text)
    drawn = pygame.image.tobytes(surface, "RGB")

    blank_surface = pygame.Surface((640, 400))
    blank_surface.fill((0, 0, 0))
    blank = pygame.image.tobytes(blank_surface, "RGB")

    assert drawn != blank

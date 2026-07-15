"""Shell foundation smoke tests: text, sprites, App.step."""

import pygame
import pytest

from psychic_cleaners.core.events import SceneId
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer


def test_sprite_factory_caches_surfaces() -> None:
    pygame.init()
    factory = SpriteFactory()
    first = factory.get("cleaner")
    second = factory.get("cleaner")
    assert first is second
    assert first.get_size() == (24, 40)


def test_sprite_factory_builds_logo() -> None:
    pygame.init()
    factory = SpriteFactory()
    logo = factory.get("logo")
    assert logo.get_width() > 0
    assert logo.get_height() > 0


def test_sprite_factory_unknown_name_raises_key_error() -> None:
    pygame.init()
    factory = SpriteFactory()
    with pytest.raises(KeyError):
        factory.get("does-not-exist")


def test_text_renderer_draws_without_error() -> None:
    pygame.init()
    surface = pygame.Surface((640, 400))
    text = TextRenderer()
    text.draw(surface, "hello", (10, 10))
    text.draw(surface, "big", (10, 40), size=32, color=(255, 0, 0))


def test_app_step_runs_for_every_scene_id() -> None:
    from psychic_cleaners.shell.app import App

    app = App(seed=1)
    for scene_id in SceneId:
        app.game.scene = scene_id
        app.step(1 / 60)


def test_app_registry_covers_every_scene_id() -> None:
    from psychic_cleaners.shell.app import SCENES

    assert set(SCENES) == set(SceneId)

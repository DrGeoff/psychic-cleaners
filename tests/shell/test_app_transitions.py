"""App.step transition behaviour: singleton scene resets and post-tick draws."""

from collections.abc import Callable

import pygame
import pytest

from psychic_cleaners.core.constants import DEPOT_POS
from psychic_cleaners.core.events import SceneId
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.app import SCENES, App
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.scenes.shop import ShopScene
from psychic_cleaners.shell.scenes.title import TitleScene
from psychic_cleaners.shell.text import TextRenderer


def _step_game_over_continue(app: App) -> None:
    """Drive App.step through the GAME_OVER -> Continue -> TITLE transition.

    Mirrors test_app_clears_title_fields_on_game_over_continue in
    tests/shell/test_title_scene.py.
    """
    app.game.scene = SceneId.GAME_OVER
    app.game.result = "lost"
    app._prev_scene = SceneId.GAME_OVER  # keep the tracked prev scene in sync
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    app.step(1 / 60)
    assert app.game.scene is SceneId.TITLE


def test_app_resets_shop_and_map_cursors_on_title_transition() -> None:
    """GAME_OVER -> Continue -> TITLE must reset the shared shop/map cursors."""
    app = App(seed=1)
    try:
        shop_scene = SCENES[SceneId.SHOP]
        map_scene = SCENES[SceneId.MAP]
        assert isinstance(shop_scene, ShopScene)
        assert isinstance(map_scene, CityMapScene)
        shop_scene.cursor = 10  # last row the "previous game" used
        map_scene.cursor = (3, 1)
        assert map_scene.cursor != DEPOT_POS
        _step_game_over_continue(app)
        assert shop_scene.cursor == 0
        assert map_scene.cursor == DEPOT_POS
    finally:
        pygame.quit()


def test_fresh_app_starts_with_reset_scene_state() -> None:
    """A new App must not inherit scene state left by a previous App.

    SCENES is a module-level singleton dict, so without a reset in
    App.__init__ a second App in the same process (tests, scripted
    playtests) opens with the previous game's cursors and title fields.
    """
    app = App(seed=1)
    try:
        shop_scene = SCENES[SceneId.SHOP]
        map_scene = SCENES[SceneId.MAP]
        title_scene = SCENES[SceneId.TITLE]
        assert isinstance(shop_scene, ShopScene)
        assert isinstance(map_scene, CityMapScene)
        assert isinstance(title_scene, TitleScene)
        shop_scene.cursor = 9  # state the "previous game" left behind
        map_scene.cursor = (7, 2)
        title_scene._name = "LEFTOVER"
        title_scene._code = "AAAAAAA"
        App(seed=2)
        assert shop_scene.cursor == 0
        assert map_scene.cursor == DEPOT_POS
        assert title_scene._name == ""
        assert title_scene._code == ""
        assert app is not None  # keep the first App alive through the checks
    finally:
        pygame.quit()


def test_transition_frame_draws_the_post_tick_scene(monkeypatch: pytest.MonkeyPatch) -> None:
    """A step whose tick changes game.scene must draw the NEW scene, not the old."""
    app = App(seed=1)
    try:
        drawn: list[SceneId] = []

        def _recorder(
            scene_id: SceneId,
        ) -> Callable[[pygame.Surface, Game, SpriteFactory, TextRenderer], None]:
            def _draw(
                surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
            ) -> None:
                drawn.append(scene_id)

            return _draw

        for scene_id in (SceneId.GAME_OVER, SceneId.TITLE):
            monkeypatch.setattr(SCENES[scene_id], "draw", _recorder(scene_id))
        _step_game_over_continue(app)
        assert drawn == [SceneId.TITLE]
    finally:
        pygame.quit()

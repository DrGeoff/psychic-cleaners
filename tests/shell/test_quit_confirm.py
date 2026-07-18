"""Escape-to-quit confirmation overlay: App.step intercepts input while it's open."""

import pygame
import pytest

from psychic_cleaners.core.events import Command, NewGame, SceneId
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.app import SCENES, App


def _open_quit_confirm(app: App) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app.step(1 / 60)
    assert app._quit_confirm is True


def test_escape_opens_quit_confirm_and_pauses_tick() -> None:
    app = App(seed=1)
    try:
        app.game.tick([NewGame("Ada")], 0.0)  # TITLE -> SHOP, so a tick would be visible
        scene_before = app.game.scene
        assert app._quit_confirm is False
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        app.step(1 / 60)
        assert app._quit_confirm is True
        assert app.game.scene is scene_before  # tick was skipped, not just a no-op transition
    finally:
        pygame.quit()


def test_quit_overlay_draws_prompt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(seed=1)
    try:
        drawn: list[str] = []
        original_draw = app.text.draw

        def _recording_draw(
            surface: pygame.Surface,
            message: str,
            pos: tuple[int, int],
            size: int = 16,
            color: tuple[int, int, int] = (230, 230, 230),
        ) -> None:
            drawn.append(message)
            original_draw(surface, message, pos, size=size, color=color)

        monkeypatch.setattr(app.text, "draw", _recording_draw)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        app.step(1 / 60)
        assert any("Quit" in message for message in drawn)
    finally:
        pygame.quit()


def test_y_confirms_quit() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()


def test_return_confirms_quit() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()


def test_n_cancels_and_resumes_scene_input() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
        app.step(1 / 60)
        assert app._quit_confirm is False
        assert app.running is True
        assert app.game.scene is SceneId.TITLE
    finally:
        pygame.quit()


def test_escape_again_cancels() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        app.step(1 / 60)
        assert app._quit_confirm is False
        assert app.running is True
    finally:
        pygame.quit()


def test_other_key_is_swallowed_while_confirming() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        app.step(1 / 60)
        assert app._quit_confirm is True
        assert app.running is True
    finally:
        pygame.quit()


def test_scene_commands_not_called_while_confirming(monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(seed=1)
    try:
        title_scene = SCENES[SceneId.TITLE]
        calls: list[object] = []
        original_commands = title_scene.commands

        def _recording_commands(
            events: list[pygame.event.Event], game: Game, dt: float
        ) -> list[Command]:
            calls.append(1)
            return original_commands(events, game, dt)

        monkeypatch.setattr(title_scene, "commands", _recording_commands)
        _open_quit_confirm(app)
        assert calls == []  # the Escape keydown itself must not reach scene.commands
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        app.step(1 / 60)
        assert calls == []  # still swallowed on the following frame
    finally:
        pygame.quit()


def test_window_close_still_works_while_confirming() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()

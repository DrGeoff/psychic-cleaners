"""TitleScene: text entry, focus handling, command emission, draw smoke test."""

import pygame

from psychic_cleaners.core.events import EnterAccount, NewGame, SceneId
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.shell.app import LOGICAL_SIZE, SCENES
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.title import TitleScene, _Field
from psychic_cleaners.shell.text import TextRenderer


def _text(text: str) -> pygame.event.Event:
    return pygame.event.Event(pygame.TEXTINPUT, text=text)


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def _game() -> Game:
    return new_game(1)


def test_textinput_appends_to_name_field() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _text("t")], _game())
    assert scene._name == "Pat"
    assert scene._code == ""


def test_tab_moves_focus_and_code_is_uppercased() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _key(pygame.K_TAB), _text("a"), _text("b"), _text("7")], _game())
    assert scene._name == "P"
    assert scene._code == "AB7"


def test_tab_toggles_back_to_name() -> None:
    scene = TitleScene()
    scene.commands([_key(pygame.K_TAB), _key(pygame.K_TAB), _text("x")], _game())
    assert scene._name == "x"
    assert scene._code == ""


def test_backspace_edits_the_focused_field() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _key(pygame.K_BACKSPACE)], _game())
    assert scene._name == "P"
    scene.commands([_key(pygame.K_TAB), _text("x"), _key(pygame.K_BACKSPACE)], _game())
    assert scene._code == ""
    # Backspace on an already-empty field is a no-op, not an error.
    scene.commands([_key(pygame.K_BACKSPACE)], _game())
    assert scene._code == ""


def test_field_length_limits() -> None:
    scene = TitleScene()
    scene.commands([_text("a")] * 25, _game())
    assert scene._name == "a" * 20
    scene.commands([_key(pygame.K_TAB)], _game())
    scene.commands([_text("b")] * 10, _game())
    assert scene._code == "B" * 7


def test_enter_with_empty_code_emits_new_game() -> None:
    scene = TitleScene()
    out = scene.commands([_text("P"), _text("a"), _text("t"), _key(pygame.K_RETURN)], _game())
    assert out == [NewGame("Pat")]
    # Enter no longer clears the buffers itself: only an explicit reset()
    # (driven by the shell on a TITLE transition) does that. Otherwise a
    # REJECTED code would wipe a name the player just typed.
    assert scene._name == "Pat"
    assert scene._code == ""


def test_enter_with_code_emits_enter_account() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _text("t"), _key(pygame.K_TAB)], _game())
    out = scene.commands([_text(ch) for ch in "cpdg8jx"] + [_key(pygame.K_RETURN)], _game())
    assert out == [EnterAccount("Pat", "CPDG8JX")]
    # A REJECTED code must keep BOTH fields so the player can fix a typo.
    assert scene._name == "Pat"
    assert scene._code == "CPDG8JX"


def test_reset_clears_both_fields_and_refocuses_name() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _text("t"), _key(pygame.K_TAB), _text("x")], _game())
    assert scene._name == "Pat"
    assert scene._code == "X"
    assert scene._focus is _Field.CODE
    scene.reset()
    assert scene._name == ""
    assert scene._code == ""
    # mypy false positive: narrows scene._focus from the prior assert and
    # doesn't invalidate it across the reset() call above, even though
    # reset() does mutate it (same quirk noted in test_bust.py/test_game_fsm.py).
    assert scene._focus is _Field.NAME  # type: ignore[comparison-overlap]


def test_enter_ignored_while_name_empty() -> None:
    scene = TitleScene()
    assert scene.commands([_key(pygame.K_RETURN)], _game()) == []
    scene.commands([_text(" ")], _game())  # whitespace-only name still counts as empty
    assert scene.commands([_key(pygame.K_RETURN)], _game()) == []


def test_draw_smoke() -> None:
    pygame.init()  # dummy video/audio drivers via tests/conftest.py
    surface = pygame.Surface(LOGICAL_SIZE)
    scene = TitleScene()
    scene.commands([_text("P"), _key(pygame.K_TAB), _text("x")], _game())
    scene.draw(surface, _game(), SpriteFactory(), TextRenderer())
    rejected = _game()
    rejected.notice = "invalid account code"
    scene.draw(surface, rejected, SpriteFactory(), TextRenderer())  # exercises the error line


def test_registry_uses_title_scene() -> None:
    assert isinstance(SCENES[SceneId.TITLE], TitleScene)


def test_app_clears_title_fields_on_game_over_continue() -> None:
    """GAME_OVER -> Continue -> TITLE must reset the shared TitleScene.

    Mirrors the music-transition check in tests/shell/test_theme.py
    (test_app_starts_title_music): drive App.step and inspect the
    side effect the scene transition is responsible for.
    """
    from psychic_cleaners.shell.app import App

    app = App(seed=1)
    title_scene = SCENES[SceneId.TITLE]
    assert isinstance(title_scene, TitleScene)
    title_scene._name = "Leftover"
    title_scene._code = "STALE"
    title_scene._focus = _Field.CODE
    app.game.scene = SceneId.GAME_OVER
    app.game.result = "lost"
    app._prev_scene = SceneId.GAME_OVER  # keep the tracked prev scene in sync
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    app.step(1 / 60)
    assert app.game.scene is SceneId.TITLE
    assert title_scene._name == ""
    assert title_scene._code == ""
    assert title_scene._focus is _Field.NAME

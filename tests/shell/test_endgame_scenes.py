"""Key-mapping and draw-smoke tests for the finale and game-over scenes."""

from __future__ import annotations

from collections.abc import Iterator

import pygame
import pytest

from psychic_cleaners.core.events import Continue, SceneId, StartRun
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.finale import FinaleScene
from psychic_cleaners.shell.scenes.gameover import GameOverScene
from psychic_cleaners.shell.text import TextRenderer


@pytest.fixture(autouse=True)
def _display() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((640, 400))
    yield
    pygame.quit()


@pytest.fixture
def surface() -> pygame.Surface:
    return pygame.Surface((640, 400))


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_mascot_sprite_is_72_by_96() -> None:
    assert SpriteFactory().get("mascot").get_size() == (72, 96)


def test_finale_space_sends_start_run() -> None:
    game = new_game(1)
    assert FinaleScene().commands([_key(pygame.K_SPACE)], game, 1 / 60) == [StartRun()]


def test_finale_ignores_other_keys() -> None:
    game = new_game(1)
    events = [_key(pygame.K_RETURN), pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE)]
    assert FinaleScene().commands(events, game, 1 / 60) == []


def _finale_game() -> Game:
    game = new_game(1)
    game.scene = SceneId.FINALE
    game.finale = FinaleSim(able_cleaners=3)
    game.finale.start_run()
    return game


def test_finale_draw_smoke_with_active_runner(surface: pygame.Surface) -> None:
    FinaleScene().draw(surface, _finale_game(), SpriteFactory(), TextRenderer())


def test_finale_draw_smoke_without_runner(surface: pygame.Surface) -> None:
    game = _finale_game()
    assert game.finale is not None
    game.finale.runner_x = None
    FinaleScene().draw(surface, game, SpriteFactory(), TextRenderer())


class _RecordingText(TextRenderer):
    """TextRenderer that records every message it draws."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def draw(
        self,
        surface: pygame.Surface,
        message: str,
        pos: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = (230, 230, 230),
    ) -> None:
        self.messages.append(message)
        super().draw(surface, message, pos, size, color)


_PROMPT = "SPACE: send cleaner"


def test_finale_prompt_shown_when_a_runner_can_be_sent(surface: pygame.Surface) -> None:
    game = _finale_game()
    assert game.finale is not None
    game.finale.runner_x = None
    text = _RecordingText()
    FinaleScene().draw(surface, game, SpriteFactory(), text)
    assert _PROMPT in text.messages


def test_finale_prompt_hidden_while_a_runner_is_mid_run(surface: pygame.Surface) -> None:
    game = _finale_game()  # start_run() already sent a runner
    assert game.finale is not None and game.finale.runner_x is not None
    text = _RecordingText()
    FinaleScene().draw(surface, game, SpriteFactory(), text)
    assert _PROMPT not in text.messages


def test_finale_prompt_hidden_when_nobody_remains_outside(surface: pygame.Surface) -> None:
    game = _finale_game()
    sim = game.finale
    assert sim is not None
    sim.runner_x = None
    sim.inside = 1
    sim.squashed = 2  # 3 able cleaners all accounted for
    assert sim.remaining_outside == 0
    text = _RecordingText()
    FinaleScene().draw(surface, game, SpriteFactory(), text)
    assert _PROMPT not in text.messages


def test_gameover_return_sends_continue() -> None:
    game = new_game(1)
    assert GameOverScene().commands([_key(pygame.K_RETURN)], game, 1 / 60) == [Continue()]


def test_gameover_ignores_other_keys() -> None:
    game = new_game(1)
    assert GameOverScene().commands([_key(pygame.K_SPACE)], game, 1 / 60) == []


def test_gameover_draw_smoke_won_with_code(surface: pygame.Surface) -> None:
    game = new_game(1)
    game.scene = SceneId.GAME_OVER
    game.result = "won"
    game.last_account_code = "ABCDEFG"
    GameOverScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_gameover_draw_smoke_lost_with_reason(surface: pygame.Surface) -> None:
    game = new_game(1)
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    game.lose_reason = "the Tower claimed the city"
    GameOverScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_scene_registry_uses_endgame_scenes() -> None:
    from psychic_cleaners.shell.app import SCENES

    assert isinstance(SCENES[SceneId.FINALE], FinaleScene)
    assert isinstance(SCENES[SceneId.GAME_OVER], GameOverScene)

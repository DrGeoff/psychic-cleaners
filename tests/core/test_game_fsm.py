"""The Game FSM skeleton: scene transitions and world-time gating."""

import pytest

from psychic_cleaners.core.constants import GAME_MINUTES_PER_REAL_SECOND
from psychic_cleaners.core.events import CommandRejected, Continue, NewGame, SceneChanged
from psychic_cleaners.core.game import SceneId, new_game


def test_new_game_moves_title_to_shop() -> None:
    game = new_game(1)
    assert game.scene is SceneId.TITLE
    events = game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    # mypy false positive: narrows game.scene from the dataclass default and
    # doesn't invalidate it across the tick() call above, even though tick()
    # does mutate it (verified with a minimal repro outside this codebase).
    assert game.scene is SceneId.SHOP  # type: ignore[comparison-overlap]
    assert game.player_name == "Ada"
    assert SceneChanged(SceneId.SHOP) in events


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_new_game_blank_name_rejected(name: str) -> None:
    # A name that normalizes to empty must be rejected at the door: accepting
    # it makes the win-time encode_account() call raise AccountCodeError.
    game = new_game(1)
    events = game.tick([NewGame(name=name)], dt_seconds=0.0)
    assert game.scene is SceneId.TITLE
    assert game.player_name == ""
    assert any(isinstance(e, CommandRejected) for e in events)
    assert not any(isinstance(e, SceneChanged) for e in events)


def test_new_game_ignored_outside_title() -> None:
    game = new_game(1)
    game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    events = game.tick([NewGame(name="Bee")], dt_seconds=0.0)
    assert events == []
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Ada"


def test_clock_frozen_outside_world_scenes() -> None:
    game = new_game(1)
    game.tick([], dt_seconds=5.0)  # TITLE: time must not pass
    assert game.clock.minutes == 0.0
    game.scene = SceneId.SHOP
    game.tick([], dt_seconds=5.0)  # SHOP: still frozen
    assert game.clock.minutes == 0.0


def test_clock_advances_in_world_scenes() -> None:
    game = new_game(1)
    game.scene = SceneId.MAP
    game.tick([], dt_seconds=5.0)
    assert game.clock.minutes == pytest.approx(5.0 * GAME_MINUTES_PER_REAL_SECOND)
    game.scene = SceneId.DRIVE
    game.tick([], dt_seconds=1.0)
    game.scene = SceneId.BUST
    game.tick([], dt_seconds=1.0)
    assert game.clock.minutes == pytest.approx(7.0 * GAME_MINUTES_PER_REAL_SECOND)


def test_continue_resets_to_fresh_title_preserving_rng() -> None:
    game = new_game(1)
    game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    game.clock.advance(10.0)
    rng_before = game.rng
    events = game.tick([Continue()], dt_seconds=0.0)
    assert game.scene is SceneId.TITLE
    assert game.player_name == ""
    assert game.result is None
    assert game.clock.minutes == 0.0
    assert game.rng is rng_before
    assert SceneChanged(SceneId.TITLE) in events


def test_continue_ignored_outside_game_over() -> None:
    game = new_game(1)
    game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    events = game.tick([Continue()], dt_seconds=0.0)
    assert events == []
    assert game.scene is SceneId.SHOP

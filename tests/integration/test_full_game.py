"""Scripted full-game playthroughs of core.game: one win, one loss. No pygame."""

from __future__ import annotations

import pytest

from psychic_cleaners.core.codec import decode_account
from psychic_cleaners.core.constants import (
    GIANT_MAX_X,
    GIANT_MIN_X,
    GIANT_SPEED,
    PSI_MAX,
    STARTING_BANKROLL,
    TOWER_POS,
)
from psychic_cleaners.core.events import (
    BuyItem,
    Continue,
    Event,
    FinaleUnlocked,
    FinishShopping,
    GameLost,
    GameWon,
    NewGame,
    RunnerEntered,
    RunnerSquashed,
    SceneId,
    SelectVehicle,
    SetDestination,
    StartRun,
)
from psychic_cleaners.core.game import Game, new_game


def _assert_scene(game: Game, expected: SceneId) -> None:
    """Assert the current scene, re-reading through a widened ``SceneId``.

    A plain ``assert game.scene is SceneId.X`` narrows ``game.scene`` to that
    literal, and mypy keeps the narrowing across the intervening ``tick`` calls
    (method calls do not invalidate attribute narrowing). Two differing literal
    checks in one scope would then trip ``comparison-overlap``; funnelling every
    check through this helper keeps each comparison over the full ``SceneId``.
    """
    assert game.scene is expected


def _drive_until_arrival(game: Game, max_ticks: int = 1000) -> None:
    for _ in range(max_ticks):
        game.tick([], 0.1)
        if game.scene is not SceneId.DRIVE:
            return
    raise AssertionError("drive never arrived")


def _align_giant(game: Game) -> None:
    """One closed-form tick that parks the giant exactly on GIANT_MIN_X.

    It lands heading left, which the reflection turns into 'rising from the
    min bound' on the next tick — a reproducible phase for the run schedule.
    """
    sim = game.finale
    assert sim is not None
    if sim.giant_dir == -1:
        t = (sim.giant_x - GIANT_MIN_X) / GIANT_SPEED
    else:
        t = ((GIANT_MAX_X - sim.giant_x) + (GIANT_MAX_X - GIANT_MIN_X)) / GIANT_SPEED
    if t > 0:
        game.tick([], t)
    assert sim.giant_x == pytest.approx(GIANT_MIN_X)


def _run_one_cleaner_through(game: Game) -> list[Event]:
    """Verified dodge: from the aligned phase, launch at once and step 0.4 s.

    Sampled gaps stay >= 68 px (never inside SQUASH_RANGE, so the giant's
    hop phase is irrelevant); the 5th tick crosses DOOR_X.
    """
    _align_giant(game)
    events = list(game.tick([StartRun()], 0.0))
    for _ in range(9):
        evs = game.tick([], 0.4)
        events.extend(evs)
        if any(isinstance(e, RunnerEntered | RunnerSquashed) for e in evs):
            break
    assert not any(isinstance(e, RunnerSquashed) for e in events)
    assert any(isinstance(e, RunnerEntered) for e in events)
    return events


def test_full_win_playthrough() -> None:
    game = new_game(2026)
    game.tick([NewGame("Alex")], 0.0)
    _assert_scene(game, SceneId.SHOP)

    # Test-level top-up: scripted busts would be the purist route, but the
    # profit rule only compares wallet.balance to starting_bankroll, and the
    # loadout below costs 14_500 against the 10_000 start. Headroom also
    # absorbs any seed-determined stomp fines during the drive.
    game.wallet.earn(60_000)

    for command in (
        SelectVehicle("hearse"),
        BuyItem("vacuum"),
        BuyItem("snare"),
        BuyItem("snare"),
        BuyItem("rig"),
    ):
        game.tick([command], 0.0)
    game.tick([FinishShopping()], 0.0)
    _assert_scene(game, SceneId.MAP)

    game.psi.spike(PSI_MAX)
    events = game.tick([], 0.001)  # one world tick latches the unlock
    assert any(isinstance(e, FinaleUnlocked) for e in events)
    assert game.finale_unlocked

    game.tick([SetDestination(TOWER_POS)], 0.0)
    _assert_scene(game, SceneId.DRIVE)
    _drive_until_arrival(game)
    _assert_scene(game, SceneId.FINALE)
    assert game.finale is not None and game.finale.able_cleaners == 3
    assert game.wallet.balance > game.starting_bankroll  # profit secured pre-run

    _run_one_cleaner_through(game)
    assert game.finale is not None and game.finale.inside == 1
    events = _run_one_cleaner_through(game)  # second entry resolves the game

    won = [e for e in events if isinstance(e, GameWon)]
    assert len(won) == 1
    assert game.result == "won"
    _assert_scene(game, SceneId.GAME_OVER)
    assert decode_account("Alex", won[0].account_code) == game.wallet.balance
    assert game.wallet.balance > STARTING_BANKROLL


def test_full_loss_playthrough() -> None:
    game = new_game(7)
    game.tick([NewGame("Morgan")], 0.0)
    game.tick([SelectVehicle("compact")], 0.0)
    game.tick([BuyItem("snare")], 0.0)  # keeps the bankruptcy rule out of play
    game.tick([FinishShopping()], 0.0)
    _assert_scene(game, SceneId.MAP)

    game.slimed.add(0)  # exactly two able cleaners will enter the finale
    game.psi.spike(PSI_MAX)
    game.tick([], 0.001)
    assert game.finale_unlocked

    game.tick([SetDestination(TOWER_POS)], 0.0)
    _drive_until_arrival(game)
    _assert_scene(game, SceneId.FINALE)
    assert game.finale is not None and game.finale.able_cleaners == 2

    game.tick([], 1.2)  # one hop cycle: the crossing falls in a grounded window
    game.tick([StartRun()], 0.0)  # straight into the landing giant
    events: list[Event] = []
    for _ in range(100):
        evs = game.tick([], 0.05)
        events.extend(evs)
        if any(isinstance(e, RunnerSquashed) for e in evs):
            break
    # With two able cleaners the first squash already leaves
    # inside 0 + remaining_outside 1 + active 0 = 1 < FINALE_NEEDED_INSIDE,
    # so the game resolves LOST on that tick — only one runner ever falls.
    assert sum(isinstance(e, RunnerSquashed) for e in events) == 1
    lost = [e for e in events if isinstance(e, GameLost)]
    assert lost == [GameLost("the Tower claimed the city")]
    assert game.result == "lost"
    _assert_scene(game, SceneId.GAME_OVER)

    game.tick([Continue()], 0.0)  # back to a fresh title screen
    _assert_scene(game, SceneId.TITLE)
    assert game.result is None
    assert game.finale is None
    assert game.wallet.balance == STARTING_BANKROLL

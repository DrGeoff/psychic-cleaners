"""Game-level finale wiring: tower routing, FINALE scene, endgame resolution."""

from __future__ import annotations

from psychic_cleaners.core.codec import decode_account
from psychic_cleaners.core.constants import RUNNER_START_X, TOWER_POS
from psychic_cleaners.core.events import (
    BuyItem,
    Event,
    FinishShopping,
    GameLost,
    GameWon,
    NewGame,
    RunnerEntered,
    RunnerSquashed,
    SceneChanged,
    SceneId,
    SelectVehicle,
    SetDestination,
    StartRun,
)
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import Game, new_game


def _game_at_tower(name: str = "Alex") -> Game:
    """A game parked on the Tower square with the finale unlocked, still in MAP."""
    game = new_game(1)
    game.tick([NewGame(name)], 0.0)
    game.tick([SelectVehicle("compact")], 0.0)
    game.tick([BuyItem("snare")], 0.0)  # keeps the bankruptcy rule out of play
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    game.finale_unlocked = True
    game.position = TOWER_POS
    return game


def test_tower_arrival_enters_finale_with_able_cleaners() -> None:
    game = _game_at_tower()
    events = game.tick([SetDestination(TOWER_POS)], 0.0)  # arrival on the spot
    assert game.scene is SceneId.FINALE
    assert isinstance(game.finale, FinaleSim)
    assert game.finale.able_cleaners == 3
    assert SceneChanged(SceneId.FINALE) in events


def test_tower_arrival_with_too_few_able_cleaners_loses() -> None:
    game = _game_at_tower()
    game.slimed.update({0, 1})  # only one able cleaner: cannot get two inside
    events = game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.GAME_OVER
    assert game.result == "lost"
    assert GameLost("not enough able cleaners") in events
    assert game.finale is None


def test_tower_arrival_without_unlock_stays_on_map() -> None:
    game = _game_at_tower()
    game.finale_unlocked = False
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.MAP
    assert game.finale is None


def _game_in_finale(name: str = "Alex") -> Game:
    game = _game_at_tower(name)
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.FINALE
    return game


def test_start_run_command_launches_runner() -> None:
    game = _game_in_finale()
    game.tick([StartRun()], 0.0)
    assert game.finale is not None
    assert game.finale.runner_x == RUNNER_START_X


def test_squashed_runner_does_not_slime_cleaners() -> None:
    game = _game_in_finale()
    # One full hop cycle before launching: the crossing then falls in the
    # giant's grounded window [1.92, 2.4) and the runner is squashed
    # (verified schedule — see tests/core/test_finale.py).
    game.tick([], 1.2)
    game.tick([StartRun()], 0.0)
    squashed = False
    for _ in range(100):
        if any(isinstance(e, RunnerSquashed) for e in game.tick([], 0.05)):
            squashed = True
            break
    assert squashed
    assert game.slimed == set()  # finale casualties are NOT game-level slime
    assert game.finale is not None
    assert game.finale.squashed == 1
    assert game.scene is SceneId.FINALE  # two able cleaners left: not over yet


def test_finale_win_with_profit_issues_account_code() -> None:
    game = _game_in_finale()
    game.wallet.earn(5_000)  # compact + snare cost 2_600, so balance 12_400 > 10_000
    assert game.finale is not None
    game.finale.inside = 1  # one cleaner already through the door
    game.tick([StartRun()], 0.0)
    events = game.tick([], 3.25)  # one long stride to the door; giant never sampled close
    assert RunnerEntered(2) in events
    won = [e for e in events if isinstance(e, GameWon)]
    assert len(won) == 1
    assert decode_account("Alex", won[0].account_code) == game.wallet.balance
    assert game.result == "won"
    assert game.scene is SceneId.GAME_OVER
    assert SceneChanged(SceneId.GAME_OVER) in events
    assert game.finale is None


def test_finale_win_without_profit_still_loses() -> None:
    game = _game_in_finale()  # balance 7_400 <= starting 10_000: no profit
    assert game.finale is not None
    game.finale.inside = 1
    game.tick([StartRun()], 0.0)
    events = game.tick([], 3.25)
    assert RunnerEntered(2) in events
    assert GameLost("the franchise never turned a profit") in events
    assert game.result == "lost"
    assert game.scene is SceneId.GAME_OVER
    assert game.finale is None


def test_finale_squash_below_needed_loses_the_city() -> None:
    game = _game_at_tower()
    game.slimed.add(2)  # exactly two able cleaners enter the finale
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.finale is not None and game.finale.able_cleaners == 2
    game.tick([], 1.2)  # one hop cycle: the crossing falls in a grounded window
    game.tick([StartRun()], 0.0)
    events: list[Event] = []
    for _ in range(100):
        evs = game.tick([], 0.05)
        events.extend(evs)
        if any(isinstance(e, RunnerSquashed) for e in evs):
            break
    # ONE squash suffices: inside 0 + remaining_outside 1 + active 0 = 1 < 2,
    # so _tick_finale resolves LOST on that same tick and clears the finale.
    assert sum(isinstance(e, RunnerSquashed) for e in events) == 1
    assert GameLost("the Tower claimed the city") in events
    assert game.result == "lost"
    assert game.scene is SceneId.GAME_OVER
    assert game.finale is None

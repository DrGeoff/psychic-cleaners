"""Integration tests for the day cycle, rent, and bank loan mechanics."""

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import (
    DAY_LENGTH_GAME_MINUTES,
    LOAN_BORROW_INCREMENT,
    LOAN_INTEREST_RATE_PER_DAY,
    LOAN_MAX,
    RENT_PER_DAY,
)
from psychic_cleaners.core.events import (
    CommandRejected,
    GameLost,
    LoanRepaid,
    LoanTaken,
    RentCharged,
    RepayLoan,
    SceneId,
    TakeLoan,
)
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout


def _map_game(seed: int) -> Game:
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")  # keeps the snare-fold rule out of play
    game.scene = SceneId.MAP
    return game


def test_day_advances_and_charges_rent_on_boundary() -> None:
    game = _map_game(1)
    balance_before = game.wallet.balance
    assert game.day == 1
    events = game.tick([], DAY_LENGTH_GAME_MINUTES)  # one game-minute-per-real-second clock
    assert game.day == 2
    assert game.wallet.balance == balance_before - RENT_PER_DAY
    assert RentCharged(RENT_PER_DAY, 1) in events


def test_no_rent_charged_before_day_boundary() -> None:
    game = _map_game(2)
    balance_before = game.wallet.balance
    game.tick([], DAY_LENGTH_GAME_MINUTES - 1.0)
    assert game.day == 1
    assert game.wallet.balance == balance_before


def test_multiple_day_boundaries_in_one_tick_charge_rent_once_per_day() -> None:
    # seed 13: no stray city events (e.g. a giant stomp) touch the wallet
    # across this artificially large 3-day-boundary single tick, so the
    # exact-balance assertion below isolates rent's effect.
    game = _map_game(13)
    balance_before = game.wallet.balance
    game.tick([], DAY_LENGTH_GAME_MINUTES * 3)
    assert game.day == 4
    assert game.wallet.balance == balance_before - RENT_PER_DAY * 3


def test_unpayable_rent_folds_the_franchise() -> None:
    game = _map_game(4)
    game.wallet.balance = RENT_PER_DAY - 1  # one dollar short
    events = game.tick([], DAY_LENGTH_GAME_MINUTES)
    assert GameLost("rent due, can't pay — the franchise folds") in events
    assert game.scene is SceneId.GAME_OVER
    assert game.lose_reason == "rent due, can't pay — the franchise folds"


def test_take_loan_at_depot_adds_cash_and_debt() -> None:
    game = _map_game(5)  # starts at the Depot
    balance_before = game.wallet.balance
    events = game.tick([TakeLoan()], 0.0)
    assert game.debt == LOAN_BORROW_INCREMENT
    assert game.wallet.balance == balance_before + LOAN_BORROW_INCREMENT
    assert LoanTaken(LOAN_BORROW_INCREMENT) in events


def test_take_loan_rejected_away_from_depot() -> None:
    game = _map_game(6)
    game.position = (3, 3)
    events = game.tick([TakeLoan()], 0.0)
    assert game.debt == 0
    assert CommandRejected("loans only at the Depot") in events


def test_take_loan_rejected_past_the_cap() -> None:
    game = _map_game(7)
    game.debt = LOAN_MAX
    events = game.tick([TakeLoan()], 0.0)
    assert game.debt == LOAN_MAX
    assert CommandRejected("loan limit reached") in events


def test_repay_loan_reduces_debt_and_spends_cash() -> None:
    game = _map_game(8)
    game.debt = LOAN_BORROW_INCREMENT
    balance_before = game.wallet.balance
    events = game.tick([RepayLoan()], 0.0)
    assert game.debt == 0
    assert game.wallet.balance == balance_before - LOAN_BORROW_INCREMENT
    assert LoanRepaid(LOAN_BORROW_INCREMENT) in events


def test_repay_loan_clamps_to_outstanding_debt() -> None:
    game = _map_game(9)
    game.debt = 400  # less than a full LOAN_BORROW_INCREMENT
    balance_before = game.wallet.balance
    events = game.tick([RepayLoan()], 0.0)
    assert game.debt == 0
    assert game.wallet.balance == balance_before - 400
    assert LoanRepaid(400) in events


def test_repay_loan_rejected_with_no_debt() -> None:
    game = _map_game(10)
    events = game.tick([RepayLoan()], 0.0)
    assert CommandRejected("no debt to repay") in events


def test_debt_accrues_interest_on_day_rollover() -> None:
    game = _map_game(11)
    game.debt = 1_000
    game.tick([], DAY_LENGTH_GAME_MINUTES)
    # rent doesn't touch debt
    assert game.debt == round(1_000 * (1 + LOAN_INTEREST_RATE_PER_DAY)) - 0


def test_reset_clears_day_and_debt() -> None:
    from psychic_cleaners.core.events import NewGame

    game = _map_game(12)
    game.day = 5
    game.debt = 2_000
    # NewGame is only handled from TITLE (see Game._dispatch); route there
    # first so the tick actually reaches Game._reset.
    game.scene = SceneId.TITLE
    game.tick([NewGame("Alex")], 0.0)
    assert game.day == 1
    assert game.debt == 0

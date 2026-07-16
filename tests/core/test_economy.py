"""Wallet invariants and bust fee schedule."""

from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.constants import MAX_BANKROLL, STARTING_BANKROLL
from psychic_cleaners.core.economy import Wallet, bust_fee, net_worth_profited_over


def test_default_balance_is_starting_bankroll() -> None:
    assert Wallet().balance == STARTING_BANKROLL


def test_spend_deducts_and_returns_true() -> None:
    wallet = Wallet(balance=1000)
    assert wallet.spend(600) is True
    assert wallet.balance == 400


def test_spend_insufficient_returns_false_and_leaves_balance_unchanged() -> None:
    wallet = Wallet(balance=500)
    assert wallet.spend(501) is False
    assert wallet.balance == 500


def test_can_afford_boundary() -> None:
    wallet = Wallet(balance=500)
    assert wallet.can_afford(500) is True
    assert wallet.can_afford(501) is False


def test_earn_clamps_at_max_bankroll() -> None:
    wallet = Wallet(balance=MAX_BANKROLL - 10)
    wallet.earn(100)
    assert wallet.balance == MAX_BANKROLL


def test_fine_returns_actual_amount_charged() -> None:
    poor = Wallet(balance=250)
    assert poor.fine(4000) == 250
    assert poor.balance == 0
    rich = Wallet(balance=5000)
    assert rich.fine(4000) == 4000
    assert rich.balance == 1000


@given(
    st.lists(
        st.tuples(st.sampled_from(["spend", "fine", "earn"]), st.integers(0, 20_000)),
        max_size=50,
    )
)
def test_balance_never_negative_and_never_above_cap(ops: list[tuple[str, int]]) -> None:
    wallet = Wallet()
    for op, amount in ops:
        if op == "spend":
            wallet.spend(amount)
        elif op == "fine":
            wallet.fine(amount)
        else:
            wallet.earn(amount)
        assert 0 <= wallet.balance <= MAX_BANKROLL


def test_bust_fee_documented_values() -> None:
    assert bust_fee(0) == 300
    assert bust_fee(999) == 300
    assert bust_fee(1000) == 400
    assert bust_fee(9999) == 1200


def test_net_worth_profited_over_no_debt_matches_plain_profit() -> None:
    assert net_worth_profited_over(balance=10_001, debt=0, starting_balance=10_000) is True
    assert net_worth_profited_over(balance=10_000, debt=0, starting_balance=10_000) is False


def test_net_worth_profited_over_subtracts_debt() -> None:
    # 12,000 balance with 3,000 debt nets to 9,000: not ahead of a 10,000 start.
    assert net_worth_profited_over(balance=12_000, debt=3_000, starting_balance=10_000) is False
    # 12,000 balance with 1,000 debt nets to 11,000: ahead.
    assert net_worth_profited_over(balance=12_000, debt=1_000, starting_balance=10_000) is True


def test_net_worth_profited_over_at_bankroll_cap_counts_as_profit() -> None:
    # Mirrors Wallet.profited_over's documented cap edge case: a wallet
    # pinned at MAX_BANKROLL counts as profitable even with debt outstanding,
    # since balance itself can never be pushed higher to satisfy a strict ">".
    assert (
        net_worth_profited_over(balance=MAX_BANKROLL, debt=5_000, starting_balance=MAX_BANKROLL)
        is True
    )

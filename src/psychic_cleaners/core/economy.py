"""Wallet and fee calculations. The balance never goes negative."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BUST_BASE_FEE,
    BUST_FEE_PER_1000_PSI,
    MAX_BANKROLL,
    STARTING_BANKROLL,
)


@dataclass
class Wallet:
    balance: int = STARTING_BANKROLL

    def can_afford(self, amount: int) -> bool:
        return self.balance >= amount

    def spend(self, amount: int) -> bool:
        """Deduct amount; return False and leave the balance unchanged if insufficient."""
        if not self.can_afford(amount):
            return False
        self.balance -= amount
        return True

    def earn(self, amount: int) -> None:
        """Add amount (>= 0), clamping the total at MAX_BANKROLL."""
        self.balance = min(self.balance + amount, MAX_BANKROLL)

    def fine(self, amount: int) -> int:
        """Charge min(amount, balance); return the amount actually charged."""
        charged = min(amount, self.balance)
        self.balance -= charged
        return charged


def net_worth_profited_over(balance: int, debt: int, starting_balance: int) -> bool:
    """True if balance-minus-debt strictly exceeds starting_balance, or the
    balance itself is pinned at MAX_BANKROLL.

    A wallet clamped at MAX_BANKROLL can never satisfy a strict ">" against a
    starting balance that was itself at the cap, so sitting at the cap counts
    as profitable regardless of debt (mirrors the pre-existing
    Wallet.profited_over cap edge case).
    """
    return balance - debt > starting_balance or balance >= MAX_BANKROLL


def bust_fee(psi_value: int) -> int:
    """City fee for a successful bust: base fee plus a step per 1000 PSI."""
    return BUST_BASE_FEE + BUST_FEE_PER_1000_PSI * (psi_value // 1000)

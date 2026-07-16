"""Guard the documented gameplay values against typos.

Only the historically documented numbers are pinned here; the full constant
set is exercised implicitly by every other core test.
"""

from psychic_cleaners.core import constants


def test_documented_values() -> None:
    assert constants.STARTING_BANKROLL == 10_000
    assert constants.PSI_MAX == 9_999
    assert constants.STOMP_FINE == 4_000
    assert constants.RENT_PER_DAY == 250
    assert constants.LOAN_MAX == 5_000
    assert constants.LOAN_BORROW_INCREMENT == 1_000
    assert constants.LOAN_INTEREST_RATE_PER_DAY == 0.05
    assert constants.DAY_LENGTH_GAME_MINUTES == 90.0

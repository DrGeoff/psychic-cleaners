"""Guard the documented gameplay values against typos.

Only the historically documented numbers are pinned here; the full constant
set is exercised implicitly by every other core test.
"""

from psychic_cleaners.core import constants


def test_documented_values() -> None:
    assert constants.STARTING_BANKROLL == 10_000
    assert constants.PSI_MAX == 9_999
    assert constants.STOMP_FINE == 4_000

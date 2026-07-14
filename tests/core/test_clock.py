"""GameClock converts real seconds into accumulated game minutes."""

import pytest

from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.constants import GAME_MINUTES_PER_REAL_SECOND


def test_starts_at_zero() -> None:
    assert GameClock().minutes == 0.0


def test_advance_sixty_seconds() -> None:
    clock = GameClock()
    clock.advance(60.0)
    assert clock.minutes == pytest.approx(60.0 * GAME_MINUTES_PER_REAL_SECOND)


def test_accumulates_across_calls() -> None:
    clock = GameClock()
    clock.advance(10.0)
    clock.advance(20.0)
    assert clock.minutes == pytest.approx(30.0 * GAME_MINUTES_PER_REAL_SECOND)


def test_fractional_dt() -> None:
    clock = GameClock()
    for _ in range(3):
        clock.advance(1.0 / 60.0)
    assert clock.minutes == pytest.approx((3.0 / 60.0) * GAME_MINUTES_PER_REAL_SECOND)

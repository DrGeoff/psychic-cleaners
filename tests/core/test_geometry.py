"""Tests for the shared clamp, move_toward, and strict proper segment
intersection helpers."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.geometry import Vec, clamp, move_toward, segments_cross


def test_clamp_below_low_returns_low() -> None:
    assert clamp(-5.0, 0.0, 10.0) == 0.0


def test_clamp_above_high_returns_high() -> None:
    assert clamp(15.0, 0.0, 10.0) == 10.0


def test_clamp_inside_range_unchanged() -> None:
    assert clamp(5.0, 0.0, 10.0) == 5.0


def test_clamp_at_exact_boundaries() -> None:
    assert clamp(0.0, 0.0, 10.0) == 0.0
    assert clamp(10.0, 0.0, 10.0) == 10.0


def test_clamp_degenerate_lo_equals_hi() -> None:
    assert clamp(5.0, 3.0, 3.0) == 3.0
    assert clamp(-100.0, 3.0, 3.0) == 3.0


def test_move_toward_at_target_with_zero_stop_radius_does_not_divide_by_zero() -> None:
    # length == stop_radius == 0.0 must hit the early-return guard (length <=
    # stop_radius), not fall through to the dx/length division below it.
    assert move_toward(5.0, 5.0, 5.0, 5.0, max_step=10.0, stop_radius=0.0) == (5.0, 5.0)


def test_move_toward_already_within_stop_radius_is_unchanged() -> None:
    # Not exactly at the target, but already closer than stop_radius.
    assert move_toward(5.0, 5.0, 5.0, 6.0, max_step=10.0, stop_radius=2.0) == (5.0, 5.0)


def test_move_toward_caps_at_max_step_when_target_is_far() -> None:
    x, y = move_toward(0.0, 0.0, 100.0, 0.0, max_step=3.0, stop_radius=0.0)
    assert x == pytest.approx(3.0)
    assert y == pytest.approx(0.0)


def test_move_toward_stops_exactly_at_stop_radius() -> None:
    # Target 10 units away, stop 2 units short: with max_step large enough to
    # cover the whole approach, the step is length - stop_radius, landing
    # precisely stop_radius away rather than overshooting into the target.
    x, y = move_toward(0.0, 0.0, 10.0, 0.0, max_step=100.0, stop_radius=2.0)
    assert x == pytest.approx(8.0)
    assert y == pytest.approx(0.0)
    assert math.hypot(10.0 - x, 0.0 - y) == pytest.approx(2.0)


def test_x_cross_is_true() -> None:
    assert segments_cross((0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (10.0, 0.0))


def test_parallel_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (10.0, 0.0), (0.0, 5.0), (10.0, 5.0))


def test_t_touch_is_false() -> None:
    # b1 lies on the interior of segment a: touching, not properly crossing.
    assert not segments_cross((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (5.0, 10.0))


def test_shared_endpoint_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (10.0, 10.0), (10.0, 10.0), (20.0, 0.0))


def test_collinear_overlap_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (15.0, 0.0))


def test_disjoint_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (1.0, 1.0), (5.0, 5.0), (6.0, 4.0))


_coord = st.integers(min_value=-50, max_value=50)
_point = st.tuples(_coord, _coord)


def _as_vec(p: tuple[int, int]) -> Vec:
    return (float(p[0]), float(p[1]))


@given(_point, _point, _point, _point)
def test_symmetry(
    a1: tuple[int, int],
    a2: tuple[int, int],
    b1: tuple[int, int],
    b2: tuple[int, int],
) -> None:
    va1, va2, vb1, vb2 = _as_vec(a1), _as_vec(a2), _as_vec(b1), _as_vec(b2)
    result = segments_cross(va1, va2, vb1, vb2)
    assert segments_cross(vb1, vb2, va1, va2) == result
    assert segments_cross(va2, va1, vb1, vb2) == result


@given(
    _point,
    _point,
    _point,
    _point,
    st.integers(min_value=-1000, max_value=1000),
    st.integers(min_value=-1000, max_value=1000),
)
def test_translation_invariance(
    a1: tuple[int, int],
    a2: tuple[int, int],
    b1: tuple[int, int],
    b2: tuple[int, int],
    dx: int,
    dy: int,
) -> None:
    def shift(p: tuple[int, int]) -> Vec:
        return (float(p[0] + dx), float(p[1] + dy))

    original = segments_cross(_as_vec(a1), _as_vec(a2), _as_vec(b1), _as_vec(b2))
    assert segments_cross(shift(a1), shift(a2), shift(b1), shift(b2)) == original

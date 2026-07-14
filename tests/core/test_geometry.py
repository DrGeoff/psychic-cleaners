"""Tests for strict proper segment intersection."""

from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.geometry import Vec, segments_cross


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

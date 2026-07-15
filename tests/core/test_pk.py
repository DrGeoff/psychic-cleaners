"""Tests for the city-wide psychic residue (PSI) model."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.constants import (
    PSI_GROWTH_PER_REAL_MINUTE,
    PSI_HAUNT_GROWTH_PER_REAL_MINUTE,
    PSI_MAX,
)
from psychic_cleaners.core.pk import PsiModel


def test_advance_base_growth_per_minute() -> None:
    model = PsiModel()
    model.advance(60.0, active_haunts=0)
    assert model.psi == pytest.approx(PSI_GROWTH_PER_REAL_MINUTE)


def test_advance_scales_with_active_haunts() -> None:
    model = PsiModel()
    model.advance(60.0, active_haunts=2)
    expected = PSI_GROWTH_PER_REAL_MINUTE + 2 * PSI_HAUNT_GROWTH_PER_REAL_MINUTE
    assert model.psi == pytest.approx(expected)


def test_advance_partial_minute() -> None:
    model = PsiModel()
    model.advance(6.0, active_haunts=0)  # a tenth of a minute
    assert model.psi == pytest.approx(PSI_GROWTH_PER_REAL_MINUTE / 10.0)


def test_value_truncates_below_max() -> None:
    model = PsiModel(psi=9998.7)
    assert model.value == 9998
    assert not model.at_max


def test_spike_clamps_to_max() -> None:
    model = PsiModel(psi=5000.0)
    model.spike(1_000_000.0)
    assert model.psi == float(PSI_MAX)
    assert model.value == PSI_MAX
    assert model.at_max


def test_spike_clamps_to_zero() -> None:
    model = PsiModel(psi=50.0)
    model.spike(-1_000_000.0)
    assert model.psi == 0.0
    assert model.value == 0
    assert not model.at_max


def test_value_capped_when_growth_overshoots() -> None:
    model = PsiModel(psi=float(PSI_MAX))
    model.advance(60.0, active_haunts=0)
    assert model.psi > PSI_MAX  # the raw float keeps growing
    assert model.value == PSI_MAX  # but the public value is capped
    assert model.at_max


@given(
    steps=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=3600.0),
            st.integers(min_value=0, max_value=10),
        ),
        max_size=50,
    )
)
def test_advance_monotone_and_value_bounded(steps: list[tuple[float, int]]) -> None:
    model = PsiModel()
    previous = model.psi
    for dt, haunts in steps:
        model.advance(dt, haunts)
        assert model.psi >= previous
        assert 0 <= model.value <= PSI_MAX
        previous = model.psi

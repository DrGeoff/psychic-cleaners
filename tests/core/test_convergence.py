"""The Warden and the Locksmith: spawn corners, drift, and arrival timing."""

import math

import pytest

from psychic_cleaners.core.constants import (
    CONVERGENCE_WALK_SPEED,
    GRID_HEIGHT,
    GRID_WIDTH,
    TOWER_POS,
)
from psychic_cleaners.core.convergence import Convergence


def _distance_to_tower(x: float, y: float) -> float:
    return math.hypot(TOWER_POS[0] - x, TOWER_POS[1] - y)


def test_start_spawns_at_opposite_corners() -> None:
    convergence = Convergence.start()
    assert (convergence.warden.x, convergence.warden.y) == (0.0, 0.0)
    assert (convergence.locksmith.x, convergence.locksmith.y) == (
        float(GRID_WIDTH - 1),
        float(GRID_HEIGHT - 1),
    )
    assert not convergence.arrived


def test_start_is_deterministic() -> None:
    # No rng anywhere: two starts are identical, so replays reproduce the walk.
    first = Convergence.start()
    second = Convergence.start()
    assert (first.warden.x, first.warden.y) == (second.warden.x, second.warden.y)
    assert (first.locksmith.x, first.locksmith.y) == (
        second.locksmith.x,
        second.locksmith.y,
    )


def test_tick_moves_both_toward_tower() -> None:
    convergence = Convergence.start()
    warden_before = _distance_to_tower(convergence.warden.x, convergence.warden.y)
    locksmith_before = _distance_to_tower(convergence.locksmith.x, convergence.locksmith.y)
    convergence.tick(1.0)
    warden_after = _distance_to_tower(convergence.warden.x, convergence.warden.y)
    locksmith_after = _distance_to_tower(convergence.locksmith.x, convergence.locksmith.y)
    assert warden_after == pytest.approx(warden_before - CONVERGENCE_WALK_SPEED)
    assert locksmith_after == pytest.approx(locksmith_before - CONVERGENCE_WALK_SPEED)


def test_not_arrived_while_either_walker_is_out() -> None:
    convergence = Convergence.start()
    # The Locksmith's corner is nearer the tower; walk until only the
    # Warden is still outside the arrival radius.
    locksmith_time = (
        _distance_to_tower(convergence.locksmith.x, convergence.locksmith.y) - 0.5
    ) / CONVERGENCE_WALK_SPEED
    convergence.tick(locksmith_time + 0.01)
    assert not convergence.arrived


def test_arrived_once_both_reach_the_tower() -> None:
    convergence = Convergence.start()
    warden_time = (
        _distance_to_tower(convergence.warden.x, convergence.warden.y) - 0.5
    ) / CONVERGENCE_WALK_SPEED
    convergence.tick(warden_time + 0.01)
    assert convergence.arrived


def test_walkers_stop_at_the_tower() -> None:
    convergence = Convergence.start()
    convergence.tick(10_000.0)  # far beyond any arrival time
    assert _distance_to_tower(convergence.warden.x, convergence.warden.y) < 0.51
    assert _distance_to_tower(convergence.locksmith.x, convergence.locksmith.y) < 0.51

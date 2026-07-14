"""Deterministic tests for City.tick: hauntings and wisps."""

import math

from psychic_cleaners.core.city import City, Wisp
from psychic_cleaners.core.constants import MAX_ACTIVE_HAUNTS
from psychic_cleaners.core.events import GridPos, HauntStarted, WispReachedTower
from psychic_cleaners.core.rng import make_rng


def test_haunts_spawn_and_respect_cap() -> None:
    rng = make_rng(42)
    city = City.new()
    started: list[GridPos] = []
    # 600 ticks of dt=1.0 = ten minutes of rate-clock time; expected uncapped
    # spawns ~= 0.8 * 10 = 8, so >= 1 spawn is a safe deterministic assertion.
    for _ in range(600):
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, HauntStarted):
                started.append(event.pos)
        assert city.active_haunts() <= MAX_ACTIVE_HAUNTS
    assert len(started) >= 1
    assert len(started) <= MAX_ACTIVE_HAUNTS  # nothing clears haunts here
    assert set(started) == set(city.haunted_positions())


def test_haunt_targets_are_unique_buildings() -> None:
    rng = make_rng(42)
    city = City.new()
    started: list[GridPos] = []
    for _ in range(600):
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, HauntStarted):
                started.append(event.pos)
    assert len(started) == len(set(started))
    for pos in started:
        assert pos in city.buildings


def test_no_haunt_with_zero_dt() -> None:
    rng = make_rng(1)
    city = City.new()
    assert city.tick(0.0, psi_value=9999, rng=rng) == []
    assert city.active_haunts() == 0


def test_wisp_drifts_toward_tower_with_normalised_direction() -> None:
    rng = make_rng(1)
    city = City.new()
    # Directly below-left of nothing: (5.0, 0.0) is straight "north" of the
    # tower at (5, 3), so the direction vector is (0, 1): x must not change.
    city.wisps.append(Wisp(x=5.0, y=0.0))
    city.tick(1.0, psi_value=0, rng=rng)
    wisp = city.wisps[0]
    assert wisp.x == 5.0
    assert abs(wisp.y - 0.05) < 1e-9  # WISP_MAP_SPEED cells in one second


def test_wisp_adjacent_to_tower_reaches_it() -> None:
    rng = make_rng(7)
    city = City.new()
    city.wisps.append(Wisp(x=5.0, y=2.0))  # 1.0 cells from the tower at (5, 3)
    reached = 0
    # Needs to close from 1.0 to within 0.5 cells at 0.05 cells/sec: about
    # 10 ticks; 15 gives float-rounding headroom. Wisps spawned by the tick
    # itself (at random buildings) may also reach the tower, so assert on
    # "at least one" arrival rather than an exact count.
    for _ in range(15):
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, WispReachedTower):
                reached += 1
    assert reached >= 1
    # every wisp still in flight is outside the 0.5-cell arrival radius
    assert all(math.hypot(w.x - 5.0, w.y - 3.0) > 0.5 for w in city.wisps)


def test_wisps_spawn_at_buildings_over_time() -> None:
    # Seed chosen so the deterministic spawn actually occurs: threshold-tail
    # seeds (e.g. 11) never roll below the 0.01 per-tick spawn chance in 600
    # ticks, so no wisp would ever spawn under them.
    rng = make_rng(1)
    city = City.new()
    reached = 0
    for _ in range(600):  # ten minutes: expected spawns ~= 0.6 * 10 = 6
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, WispReachedTower):
                reached += 1
    # every spawned wisp is either still drifting or has reached the tower
    assert len(city.wisps) + reached >= 1

"""Tests for the driving lane simulation."""

from psychic_cleaners.core.constants import (
    CAR_X,
    CATCH_RANGE,
    DRIVE_LANES,
    ROAD_LENGTH_VISIBLE,
    VACUUM_BOUNTY,
    WISP_SPAWN_MARGIN,
)
from psychic_cleaners.core.drive import DriveSim, RoadWisp
from psychic_cleaners.core.events import WispCaptured
from psychic_cleaners.core.rng import make_rng


def _sim(*, vacuum: bool = True, lens: bool = False) -> DriveSim:
    return DriveSim(distance_total=400.0, speed=100.0, has_vacuum=vacuum, has_lens=lens)


def test_not_arrived_before_distance_covered() -> None:
    sim = _sim()
    rng = make_rng(1)
    for _ in range(39):  # 3.9 s at 100 units/s -> 390 < 400
        sim.tick(0.1, rng)
    assert not sim.arrived


def test_arrives_after_distance_total_over_speed_seconds() -> None:
    sim = _sim()
    rng = make_rng(1)
    for _ in range(40):  # 4.0 s at 100 units/s -> distance_total/speed seconds
        sim.tick(0.1, rng)
    assert sim.arrived


def test_steer_moves_and_clamps_between_0_and_last_lane() -> None:
    sim = _sim()
    assert sim.lane == 1  # contract default
    sim.steer(-1)
    assert sim.lane == 0
    sim.steer(-1)
    assert sim.lane == 0  # clamped at 0
    sim.steer(1)
    sim.steer(1)
    assert sim.lane == DRIVE_LANES - 1
    sim.steer(1)
    assert sim.lane == DRIVE_LANES - 1  # clamped at DRIVE_LANES - 1


def test_vacuum_catches_wisp_in_same_lane_within_range() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == [WispCaptured(bounty=VACUUM_BOUNTY)]
    assert sim.wisps == []


def test_no_catch_without_vacuum() -> None:
    sim = _sim(vacuum=False)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_no_catch_in_a_different_lane() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=0, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_no_catch_outside_catch_range() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=CAR_X + CATCH_RANGE + 50.0, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_faint_wisp_not_caught_without_lens() -> None:
    sim = _sim(vacuum=True, lens=False)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=True))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_faint_wisp_caught_with_lens() -> None:
    sim = _sim(vacuum=True, lens=True)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=True))
    events = sim.tick(0.01, make_rng(1))
    assert events == [WispCaptured(bounty=VACUUM_BOUNTY)]
    assert sim.wisps == []


def test_wisp_past_the_car_is_removed_silently() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=-CATCH_RANGE - 1.0, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert sim.wisps == []


def test_spawned_wisps_have_valid_lane_and_spawn_past_the_road_edge() -> None:
    # Spawning exactly at ROAD_LENGTH_VISIBLE draws the sprite half on-screen
    # immediately (center == screen edge): WISP_SPAWN_MARGIN pushes the spawn
    # point far enough past the edge that the sprite is fully off-screen and
    # slides into view instead of popping in half-clipped.
    sim = _sim()
    rng = make_rng(7)
    spawned = 0
    faint_seen: set[bool] = set()
    for _ in range(2000):
        sim.wisps.clear()  # isolate this tick's spawns from drifting ones
        sim.tick(0.1, rng)
        for wisp in sim.wisps:
            spawned += 1
            assert wisp.x == ROAD_LENGTH_VISIBLE + WISP_SPAWN_MARGIN
            assert 0 <= wisp.lane < DRIVE_LANES
            faint_seen.add(wisp.faint)
    assert spawned > 0
    assert faint_seen == {True, False}  # FAINT_WISP_CHANCE produces both kinds

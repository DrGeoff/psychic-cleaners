"""Tests for the bust simulation."""

from psychic_cleaners.core.bust import BustOutcome, BustPhase, BustSim
from psychic_cleaners.core.constants import (
    BEAM_AIM_SPREAD,
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_TILT,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
from psychic_cleaners.core.events import BeamsCrossed
from psychic_cleaners.core.rng import make_rng


def _active_sim(left: float = 200.0, right: float = 440.0, snare: float = 320.0) -> BustSim:
    """Drive a fresh sim to the ACTIVE phase with cleaners and snare placed."""
    sim = BustSim()
    sim.cursor_x = left
    sim.place()
    sim.cursor_x = right
    sim.place()
    sim.cursor_x = snare
    sim.place()
    return sim


def test_phase_progression_captures_positions_from_cursor() -> None:
    sim = BustSim()
    assert sim.phase is BustPhase.POSITION_LEFT
    assert sim.cursor_x == 320.0

    sim.move(-120.0)
    sim.place()
    # mypy false positive: narrows sim.phase from the dataclass default and
    # doesn't invalidate it across the place() call above, even though
    # place() does mutate it (see test_game_fsm.py for the same quirk).
    assert sim.phase is BustPhase.POSITION_RIGHT  # type: ignore[comparison-overlap]
    assert sim.left_x == 200.0

    sim.move(240.0)
    sim.place()
    assert sim.phase is BustPhase.SNARE
    assert sim.right_x == 440.0

    sim.move(-120.0)
    sim.place()
    assert sim.phase is BustPhase.ACTIVE
    assert sim.snare_x == 320.0
    assert sim.outcome is None


def test_move_clamps_to_bounds() -> None:
    sim = BustSim()
    sim.move(-10_000.0)
    assert sim.cursor_x == BUST_MIN_X
    sim.move(10_000.0)
    assert sim.cursor_x == BUST_MAX_X


def test_move_ignored_once_active() -> None:
    sim = _active_sim()
    sim.cursor_x = 300.0
    sim.move(50.0)
    assert sim.cursor_x == 300.0


def test_beam_endpoints_none_until_active() -> None:
    sim = BustSim()
    assert sim.beam_endpoints() is None
    sim.place()
    assert sim.beam_endpoints() is None
    sim.place()
    assert sim.beam_endpoints() is None
    sim.place()
    assert sim.beam_endpoints() is not None


def test_beam_tilt_clamped() -> None:
    sim = _active_sim(left=400.0, right=420.0)
    sim.ghost_x = BUST_MIN_X
    beams = sim.beam_endpoints()
    assert beams is not None
    (left_start, left_end), (right_start, right_end) = beams
    assert left_start == (400.0, BUST_GROUND_Y)
    assert left_end == (400.0 - BEAM_MAX_TILT, BEAM_TOP_Y)
    assert right_start == (420.0, BUST_GROUND_Y)
    assert right_end == (420.0 - BEAM_MAX_TILT, BEAM_TOP_Y)


def test_beam_aims_left_and_right_of_ghost_when_within_tilt() -> None:
    # The left cleaner (smaller x) aims BEAM_AIM_SPREAD left of the ghost, the
    # right cleaner aims BEAM_AIM_SPREAD right of it: the tips never meet at a
    # single point, so the beams never look like crossed streams by default.
    sim = _active_sim(left=300.0, right=340.0)
    sim.ghost_x = 320.0
    beams = sim.beam_endpoints()
    assert beams is not None
    assert beams[0][1] == (320.0 - BEAM_AIM_SPREAD, BEAM_TOP_Y)
    assert beams[1][1] == (320.0 + BEAM_AIM_SPREAD, BEAM_TOP_Y)
    # Sanity for Fix 5: unclamped tips keep the left tip strictly left of the
    # right tip, so segments_cross never fires on this ordinary case.
    assert beams[0][1][0] < beams[1][1][0]


def test_spring_caught_when_ghost_over_snare_and_low() -> None:
    sim = _active_sim(snare=320.0)
    sim.ghost_x = 320.0 + SNARE_WIDTH / 2
    sim.ghost_y = SNARE_TRIGGER_Y
    sim.spring()
    assert sim.phase is BustPhase.RESOLVED
    assert sim.outcome is BustOutcome.CAUGHT


def test_spring_missed_when_ghost_off_snare() -> None:
    sim = _active_sim(snare=320.0)
    sim.ghost_x = BUST_MIN_X
    sim.ghost_y = 350.0
    sim.spring()
    assert sim.outcome is BustOutcome.MISSED


def test_spring_missed_when_ghost_too_high() -> None:
    sim = _active_sim(snare=320.0)
    sim.ghost_x = 320.0
    sim.ghost_y = SNARE_TRIGGER_Y - 1.0
    sim.spring()
    assert sim.outcome is BustOutcome.MISSED


def test_spring_ignored_outside_active() -> None:
    sim = BustSim()
    sim.spring()
    assert sim.phase is BustPhase.POSITION_LEFT
    assert sim.outcome is None


def test_tick_inert_outside_active() -> None:
    sim = BustSim()
    assert sim.tick(1.0, make_rng(1)) == []
    assert sim.ghost_x == 320.0
    assert sim.ghost_y == 160.0


def test_backfire_when_ghost_sinks_low_between_cleaners() -> None:
    # min(left, right) < ghost_x < max(left, right) and ghost_y >= BEAM_CROSS_GHOST_Y:
    # the ghost has sunk low between the cleaners, so both beams angle steeply
    # down at it and cross behind it -> BACKFIRE, no rigging required.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = BEAM_CROSS_GHOST_Y + 10.0  # 330.0
    events = sim.tick(1e-6, make_rng(7))
    assert events == [BeamsCrossed()]
    assert sim.outcome is BustOutcome.BACKFIRE
    assert sim.phase is BustPhase.RESOLVED


def test_no_backfire_in_skill_window() -> None:
    # SNARE_TRIGGER_Y (280) < BEAM_CROSS_GHOST_Y (320): in the 40px band between
    # them the ghost is already springable but not yet backfiring.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = (SNARE_TRIGGER_Y + BEAM_CROSS_GHOST_Y) / 2  # 300.0, inside the window
    assert sim.tick(1e-6, make_rng(7)) == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_no_backfire_when_low_ghost_is_outside_the_pair() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 100.0  # left of BOTH cleaners: the beams tilt the same way
    sim.ghost_y = BEAM_CROSS_GHOST_Y + 10.0
    assert sim.tick(1e-6, make_rng(7)) == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_ghost_slimes_left_cleaner_at_ground() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 200.0 - SLIME_RANGE / 2  # brushing the cleaner from OUTSIDE the pair
    sim.ghost_y = BUST_GROUND_Y
    events = sim.tick(1 / 60, make_rng(3))
    assert events == []
    assert sim.outcome is BustOutcome.SLIMED
    assert sim.slimed_side == 0
    assert sim.phase is BustPhase.RESOLVED


def test_ghost_slimes_right_cleaner_at_ground() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 440.0 + SLIME_RANGE / 2
    sim.ghost_y = BUST_GROUND_Y
    sim.tick(1 / 60, make_rng(3))
    assert sim.outcome is BustOutcome.SLIMED
    assert sim.slimed_side == 1


def test_ghost_stays_inside_clamp_bounds_over_many_ticks() -> None:
    sim = _active_sim()
    rng = make_rng(99)
    for _ in range(600):
        sim.tick(1 / 30, rng)
        assert BUST_MIN_X <= sim.ghost_x <= BUST_MAX_X
        assert BEAM_TOP_Y <= sim.ghost_y <= BUST_GROUND_Y

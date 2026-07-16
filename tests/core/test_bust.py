"""Tests for the bust simulation."""

from collections.abc import Sequence

from psychic_cleaners.core.bust import BustOutcome, BustPhase, BustSim
from psychic_cleaners.core.constants import (
    BEAM_AIM_SPREAD,
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_TILT,
    BEAM_NARROW_START_Y,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    BUST_TIMEOUT_SECONDS,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
from psychic_cleaners.core.events import BeamsCrossed
from psychic_cleaners.core.rng import make_rng

_TIMEOUT_TICKS = int(BUST_TIMEOUT_SECONDS * 60) + 2  # +2 absorbs 1/60 float accrual error


class _StillRng:
    """Rng stub whose uniform() is always 0: the ghost sinks but never drifts."""

    def random(self) -> float:
        return 0.0

    def randint(self, a: int, b: int) -> int:
        return a

    def uniform(self, a: float, b: float) -> float:
        return 0.0

    def choice[T](self, seq: Sequence[T]) -> T:
        return seq[0]


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


def test_beams_cross_fires_independently_of_sunk_between() -> None:
    # gap=240 (today's standard test fixture), ghost dead-centered, ghost_y=300
    # is INSIDE the existing 40px "skill window" (280-320) where sunk_between
    # cannot fire (its own threshold is ghost_y >= BEAM_CROSS_GHOST_Y == 320).
    # At this ghost_y the tilt gain is 1.25 (ramping from 1.0 at 280 to
    # BEAM_MAX_GAIN=2.0 at 360), which is already enough to saturate both
    # beams' tilts in opposite directions and produce a genuine ~40px
    # crossing margin — verified by direct computation, not a floating-point
    # tie. This is the mechanism's core deliverable: a reachable cross that
    # sunk_between's own condition cannot explain.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = 300.0
    assert sim.ghost_y < BEAM_CROSS_GHOST_Y  # sunk_between's threshold: confirms isolation
    events = sim.tick(1e-6, make_rng(7))
    assert events == [BeamsCrossed()]
    assert sim.outcome is BustOutcome.BACKFIRE
    assert sim.phase is BustPhase.RESOLVED


def test_gain_stays_at_one_below_narrow_start_y() -> None:
    # Regression guard: at ghost_y exactly BEAM_NARROW_START_Y, gain must
    # still be 1.0 (today's baseline formula), for the same gap/ghost_x that
    # crosses just 20px deeper in test_beams_cross_fires_independently_of_sunk_between.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = BEAM_NARROW_START_Y  # 280.0
    events = sim.tick(1e-6, make_rng(7))
    assert events == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_wide_gap_stays_safe_through_full_narrowing() -> None:
    # A 320px gap (well past the ~300px immunity boundary) stays safe even
    # at BUST_GROUND_Y, where gain reaches its maximum (BEAM_MAX_GAIN).
    # Proves the placement-immunity property end to end: wide-enough
    # placement fully neutralizes the new risk regardless of waiting.
    sim = _active_sim(left=140.0, right=460.0)
    sim.ghost_x = 320.0
    sim.ghost_y = BUST_GROUND_Y
    events = sim.tick(1e-6, make_rng(7))
    assert events == []
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


def test_ghost_at_exact_slime_range_boundary_slimes() -> None:
    # math.hypot(...) <= SLIME_RANGE is inclusive: exactly SLIME_RANGE away
    # must still slime, not require strictly-inside.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 200.0 - SLIME_RANGE  # distance == SLIME_RANGE exactly
    sim.ghost_y = BUST_GROUND_Y
    sim.tick(0.0, _StillRng())  # zero dt + still rng: ghost_x/y unmoved by this tick
    assert sim.outcome is BustOutcome.SLIMED
    assert sim.slimed_side == 0


def test_ghost_just_outside_slime_range_does_not_slime() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 200.0 - SLIME_RANGE - 1.0  # one unit past the boundary
    sim.ghost_y = BUST_GROUND_Y
    events = sim.tick(0.0, _StillRng())
    assert events == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_ghost_in_range_of_both_cleaners_slimes_left_first() -> None:
    # left_x/right_x close enough together (24px apart, inside SLIME_RANGE's
    # 28px) that a ghost just past the left cleaner sits within SLIME_RANGE
    # of both simultaneously. It must NOT sit strictly between them (that
    # would trip the sunk_between backfire check first, not the slime loop).
    # The left/right enumeration order in BustSim.tick must give the left
    # cleaner priority.
    sim = _active_sim(left=200.0, right=224.0)
    sim.ghost_x = 199.0  # just outside (left of) the pair: 1px from left, 25px from right
    sim.ghost_y = BUST_GROUND_Y
    sim.tick(0.0, _StillRng())
    assert sim.outcome is BustOutcome.SLIMED
    assert sim.slimed_side == 0


def test_ghost_escaped_outside_the_pair_still_resolves() -> None:
    # Regression: the old repel pushed away from the nearer cleaner in whatever
    # direction the ghost already was, so a ghost that slipped OUTSIDE the pair
    # was shoved further out and parked just past the repel zone forever — no
    # outcome could reach it. The repel now herds it back toward the farther
    # cleaner, so this exact configuration (formerly ACTIVE for 120+ s) resolves
    # through the dynamics, well before the timeout failsafe.
    sim = BustSim(
        phase=BustPhase.ACTIVE,
        left_x=320.0,
        right_x=590.0,
        snare_x=600.0,
        ghost_x=250.0,
        ghost_y=350.0,
    )
    rng = make_rng(0)
    for _ in range(_TIMEOUT_TICKS):
        sim.tick(1 / 60, rng)
        if sim.phase is BustPhase.RESOLVED:
            break
    assert sim.phase is BustPhase.RESOLVED
    assert sim.outcome is not None
    assert sim.active_seconds < BUST_TIMEOUT_SECONDS


def test_unsprung_busts_resolve_and_both_hazards_are_live() -> None:
    # Sweep placements x seeds with the player never springing: every bust must
    # resolve within the timeout, and BOTH passive hazards must be reachable
    # through the dynamics alone — SLIMED was previously impossible because the
    # repel speed always beat the maximum drift step.
    placements = [
        (200.0, 440.0),
        (100.0, 540.0),
        (280.0, 360.0),
        (150.0, 300.0),
        (340.0, 560.0),
        (60.0, 200.0),
    ]
    outcomes: set[BustOutcome] = set()
    for left, right in placements:
        for seed in range(30):
            sim = _active_sim(left=left, right=right, snare=(left + right) / 2)
            rng = make_rng(seed)
            for _ in range(_TIMEOUT_TICKS):
                sim.tick(1 / 60, rng)
                if sim.phase is BustPhase.RESOLVED:
                    break
            assert sim.phase is BustPhase.RESOLVED, (left, right, seed)
            assert sim.outcome is not None
            outcomes.add(sim.outcome)
    assert BustOutcome.SLIMED in outcomes
    assert BustOutcome.BACKFIRE in outcomes


def test_timeout_resolves_missed_when_nothing_else_happens() -> None:
    # A driftless ghost parked outside the pair (beyond SNARE_WIDTH of either
    # cleaner) triggers nothing; the failsafe resolves it MISSED — a wasted
    # snare — at exactly BUST_TIMEOUT_SECONDS. dt=0.25 is binary-exact, so the
    # accrued time hits 45.0 on the 180th tick with no float slop.
    sim = BustSim(
        phase=BustPhase.ACTIVE,
        left_x=320.0,
        right_x=590.0,
        snare_x=600.0,
        ghost_x=250.0,
        ghost_y=350.0,
    )
    rng = _StillRng()
    ticks_to_timeout = int(BUST_TIMEOUT_SECONDS / 0.25)
    for _ in range(ticks_to_timeout - 1):
        sim.tick(0.25, rng)
        assert sim.phase is BustPhase.ACTIVE
    sim.tick(0.25, rng)
    assert sim.phase is BustPhase.RESOLVED
    assert sim.outcome is BustOutcome.MISSED
    assert sim.active_seconds == BUST_TIMEOUT_SECONDS


def test_ghost_stays_inside_clamp_bounds_over_many_ticks() -> None:
    sim = _active_sim()
    rng = make_rng(99)
    for _ in range(600):
        sim.tick(1 / 30, rng)
        assert BUST_MIN_X <= sim.ghost_x <= BUST_MAX_X
        assert BEAM_TOP_Y <= sim.ghost_y <= BUST_GROUND_Y

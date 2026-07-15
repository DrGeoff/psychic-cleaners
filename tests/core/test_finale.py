"""Unit tests for the finale door-run simulation. Pure and rng-free: no fixtures."""

from __future__ import annotations

from psychic_cleaners.core.constants import (
    DOOR_X,
    FINALE_NEEDED_INSIDE,
    GIANT_AIR_FRACTION,
    GIANT_HOP_PERIOD,
    GIANT_MIN_X,
    RUNNER_START_X,
)
from psychic_cleaners.core.events import Event, RunnerEntered, RunnerSquashed
from psychic_cleaners.core.finale import FinaleOutcome, FinaleSim


def test_giant_advances_at_giant_speed() -> None:
    sim = FinaleSim(able_cleaners=3)
    assert sim.giant_x == GIANT_MIN_X
    assert sim.giant_dir == 1
    assert sim.tick(0.5) == []
    assert sim.giant_x == 290.0  # 180 + 220 * 0.5
    assert sim.giant_dir == 1


def test_giant_reflects_at_max_bound() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.tick(2.0)  # raw 180 + 440 = 620 -> reflects off 460 to 300, now heading left
    assert sim.giant_x == 300.0
    assert sim.giant_dir == -1


def test_giant_reflects_at_min_bound() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.giant_x = 200.0
    sim.giant_dir = -1
    sim.tick(0.5)  # raw 200 - 110 = 90 -> reflects off 180 to 270, now heading right
    assert sim.giant_x == 270.0
    assert sim.giant_dir == 1


def test_start_run_launches_from_start_x() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    assert sim.runner_x == RUNNER_START_X


def test_start_run_ignored_when_nobody_left_outside() -> None:
    sim = FinaleSim(able_cleaners=2, inside=1, squashed=1)
    assert sim.remaining_outside == 0
    sim.start_run()
    assert sim.runner_x is None


def test_remaining_outside_excludes_active_runner() -> None:
    sim = FinaleSim(able_cleaners=3)
    assert sim.remaining_outside == 3
    sim.start_run()
    assert sim.remaining_outside == 2  # the runner is on the field, not outside
    sim.runner_x = DOOR_X - 1.0  # one step from the door
    sim.hop_time = 0.0  # airborne, and the giant is far away regardless
    assert sim.tick(1 / 60) == [RunnerEntered(1)]
    assert sim.remaining_outside == 2  # inside absorbs him: no double count


def test_start_run_ignored_while_runner_active() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    sim.tick(0.05)  # runner advances to 40 + 260 * 0.05 = 53; giant at 191, far away
    sim.start_run()  # must NOT reset the active runner back to the start
    assert sim.runner_x == 53.0


def test_hop_cycle_airborne_windows() -> None:
    sim = FinaleSim(able_cleaners=3)
    assert sim.airborne  # each cycle starts airborne
    sim.hop_time = GIANT_HOP_PERIOD * GIANT_AIR_FRACTION  # 0.72: first grounded instant
    assert not sim.airborne
    sim.hop_time = GIANT_HOP_PERIOD - 1e-9  # end of the grounded window
    assert not sim.airborne
    sim.hop_time = GIANT_HOP_PERIOD  # wraps into the next cycle
    assert sim.airborne


def test_airborne_giant_does_not_squash() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    sim.runner_x = sim.giant_x  # directly underneath the giant
    assert sim.airborne  # fresh cycle: he is in the air
    assert sim.tick(1 / 600) == []  # passes under safely
    assert sim.squashed == 0


def test_runner_dodges_airborne_giant_and_enters() -> None:
    # Honest 60 fps run from the fresh phase (giant at 180 heading right,
    # hop_time 0). Closed forms: runner r(t) = 40 + 260t reaches the door at
    # t = 2.0; the giant turns at 460 at t ~ 1.273, after which the gap
    # closes at 480 px/s and |gap| < 36 only during t in (1.383, 1.533) —
    # entirely inside the second airborne window [1.2, 1.92). The only
    # grounded windows before the door, [0.72, 1.2) and [1.92, 2.0], have
    # gaps > 90 px. The runner is never squashed and enters at tick ~120.
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    events: list[Event] = []
    ticks = 0
    while not events and ticks < 150:
        events = sim.tick(1 / 60)
        ticks += 1
    assert events == [RunnerEntered(1)]
    assert 115 <= ticks <= 125  # door at t = 520 / 260 = 2.0 s
    assert sim.inside == 1
    assert sim.squashed == 0
    assert sim.runner_x is None


def test_runner_into_grounded_giant_is_squashed() -> None:
    # Pre-tick one full hop cycle (1.2 s) before launching: the crossing then
    # falls at t in (2.033, 2.183) — inside the grounded window [1.92, 2.4).
    # Closed forms: r(t) = 260t - 272; giant (post-turn) g(t) = 740 - 220t;
    # gap = 480t - 1012 hits +/-36 at t = 2.033 / 2.183. The giant lands on
    # the runner at the first sampled grounded instant with |gap| < 36.
    sim = FinaleSim(able_cleaners=3)
    for _ in range(72):  # 72 ticks of 1/60 s = 1.2 s
        sim.tick(1 / 60)
    sim.start_run()
    events: list[Event] = []
    ticks = 0
    while not events and ticks < 150:
        events = sim.tick(1 / 60)
        ticks += 1
    assert events == [RunnerSquashed()]
    assert sim.squashed == 1
    assert sim.inside == 0
    assert sim.runner_x is None


def test_outcome_is_none_at_start() -> None:
    assert FinaleSim(able_cleaners=3).outcome is None


def test_outcome_won_at_needed_inside() -> None:
    sim = FinaleSim(able_cleaners=3, inside=FINALE_NEEDED_INSIDE)
    assert sim.outcome is FinaleOutcome.WON


def test_two_able_both_squashed_is_lost() -> None:
    sim = FinaleSim(able_cleaners=2)
    for _ in range(2):
        sim.start_run()
        sim.runner_x = sim.giant_x  # park the runner under the giant...
        sim.hop_time = GIANT_HOP_PERIOD * GIANT_AIR_FRACTION  # ...at a grounded instant
        assert sim.tick(1 / 600) == [RunnerSquashed()]
    assert sim.squashed == 2
    assert sim.inside == 0
    assert sim.outcome is FinaleOutcome.LOST


def test_unwinnable_state_is_lost_while_last_runner_is_mid_run() -> None:
    # Two of three squashed: even if the last runner enters, inside tops out
    # at 1 < FINALE_NEEDED_INSIDE — LOST must not wait for him to resolve.
    sim = FinaleSim(able_cleaners=3, squashed=2)
    assert FINALE_NEEDED_INSIDE > 1
    sim.start_run()
    assert sim.runner_x == RUNNER_START_X  # the gate let the last cleaner run
    assert sim.outcome is FinaleOutcome.LOST


def test_winnable_mid_run_state_is_not_lost() -> None:
    # One squashed, one inside, third mid-run: he can still make it 2 inside.
    sim = FinaleSim(able_cleaners=3, inside=1, squashed=1)
    sim.start_run()
    assert sim.runner_x == RUNNER_START_X
    assert sim.outcome is None  # undecided until he resolves
    sim.runner_x = DOOR_X - 1.0  # one step from the door
    sim.hop_time = 0.0  # airborne, and the giant is far away regardless
    assert sim.tick(1 / 60) == [RunnerEntered(2)]
    assert sim.outcome is FinaleOutcome.WON


def test_three_able_one_squashed_two_entered_is_won() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    sim.runner_x = sim.giant_x  # forced squash: grounded giant, runner underneath
    sim.hop_time = GIANT_HOP_PERIOD * GIANT_AIR_FRACTION
    assert sim.tick(1 / 600) == [RunnerSquashed()]
    assert sim.outcome is None  # two able cleaners left: still winnable
    for expected_inside in (1, 2):
        sim.start_run()
        assert sim.runner_x == RUNNER_START_X
        sim.runner_x = DOOR_X - 1.0  # one step from the door
        sim.hop_time = 0.0  # airborne, and the giant is far away regardless
        assert sim.tick(1 / 60) == [RunnerEntered(expected_inside)]
    assert sim.inside == 2
    assert sim.outcome is FinaleOutcome.WON

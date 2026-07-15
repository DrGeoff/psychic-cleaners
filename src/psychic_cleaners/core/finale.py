"""Finale door-run simulation: triangle-wave giant, runners, the 2-of-3 rule.

Pure and deterministic — no rng, no clock. The shell/Game decide when to tick.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    DOOR_X,
    FINALE_NEEDED_INSIDE,
    GIANT_AIR_FRACTION,
    GIANT_HOP_PERIOD,
    GIANT_MAX_X,
    GIANT_MIN_X,
    GIANT_SPEED,
    RUNNER_SPEED,
    RUNNER_START_X,
    SQUASH_RANGE,
)
from psychic_cleaners.core.events import Event, RunnerEntered, RunnerSquashed


class FinaleOutcome(enum.Enum):
    WON = enum.auto()
    LOST = enum.auto()


@dataclass
class FinaleSim:
    able_cleaners: int
    giant_x: float = GIANT_MIN_X
    giant_dir: int = 1
    hop_time: float = 0.0
    runner_x: float | None = None
    inside: int = 0
    squashed: int = 0

    @property
    def _active(self) -> int:
        return 1 if self.runner_x is not None else 0

    @property
    def remaining_outside(self) -> int:
        # A mid-run runner is on the field, not waiting outside — counting him
        # here would double-count him against `_active` in `outcome`.
        return self.able_cleaners - self.inside - self.squashed - self._active

    @property
    def airborne(self) -> bool:
        # The giant hops continuously: airborne for the first GIANT_AIR_FRACTION
        # of each GIANT_HOP_PERIOD cycle. Runners pass safely UNDER him while he
        # is up — without this the finale is unwinnable (the runner's and the
        # giant's paths must cross; see the milestone intro).
        return (self.hop_time % GIANT_HOP_PERIOD) < GIANT_HOP_PERIOD * GIANT_AIR_FRACTION

    def start_run(self) -> None:
        if self.runner_x is None and self.remaining_outside > 0:
            self.runner_x = RUNNER_START_X

    def tick(self, dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        self.hop_time += dt_seconds
        self._advance_giant(dt_seconds)
        if self.runner_x is not None:
            self.runner_x += RUNNER_SPEED * dt_seconds
            if not self.airborne and abs(self.runner_x - self.giant_x) < SQUASH_RANGE:
                self.squashed += 1
                self.runner_x = None
                events.append(RunnerSquashed())
            elif self.runner_x >= DOOR_X:
                self.inside += 1
                self.runner_x = None
                events.append(RunnerEntered(self.inside))
        return events

    def _advance_giant(self, dt_seconds: float) -> None:
        self.giant_x += self.giant_dir * GIANT_SPEED * dt_seconds
        while self.giant_x > GIANT_MAX_X or self.giant_x < GIANT_MIN_X:
            if self.giant_x > GIANT_MAX_X:
                self.giant_x = 2 * GIANT_MAX_X - self.giant_x
                self.giant_dir = -1
            else:
                self.giant_x = 2 * GIANT_MIN_X - self.giant_x
                self.giant_dir = 1

    @property
    def outcome(self) -> FinaleOutcome | None:
        if self.inside >= FINALE_NEEDED_INSIDE:
            return FinaleOutcome.WON
        if self.inside + self.remaining_outside + self._active < FINALE_NEEDED_INSIDE:
            return FinaleOutcome.LOST
        return None

"""Bust simulation: cleaner placement, snare laying, beams, and outcomes."""

import enum
import math
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BEAM_AIM_SPREAD,
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_GAIN,
    BEAM_MAX_TILT,
    BEAM_NARROW_START_Y,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    BUST_TIMEOUT_SECONDS,
    GHOST_DRIFT_SPEED,
    GHOST_REPEL_SPEED,
    GHOST_SINK_SPEED,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
from psychic_cleaners.core.events import BeamsCrossed, Event
from psychic_cleaners.core.geometry import Vec, clamp, segments_cross
from psychic_cleaners.core.rng import Rng


class BustPhase(enum.Enum):
    POSITION_LEFT = enum.auto()
    POSITION_RIGHT = enum.auto()
    SNARE = enum.auto()
    ACTIVE = enum.auto()
    RESOLVED = enum.auto()


class BustOutcome(enum.Enum):
    CAUGHT = enum.auto()
    MISSED = enum.auto()
    BACKFIRE = enum.auto()
    SLIMED = enum.auto()


_MOVABLE_PHASES = (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT, BustPhase.SNARE)


@dataclass
class BustSim:
    phase: BustPhase = BustPhase.POSITION_LEFT
    cursor_x: float = 320.0
    left_x: float | None = None
    right_x: float | None = None
    snare_x: float | None = None
    ghost_x: float = 320.0
    ghost_y: float = 160.0
    outcome: BustOutcome | None = None
    slimed_side: int | None = None  # 0 = left cleaner, 1 = right cleaner
    active_seconds: float = 0.0

    def move(self, dx: float) -> None:
        if self.phase in _MOVABLE_PHASES:
            self.cursor_x = clamp(self.cursor_x + dx, BUST_MIN_X, BUST_MAX_X)

    def place(self) -> None:
        if self.phase is BustPhase.POSITION_LEFT:
            self.left_x = self.cursor_x
            self.phase = BustPhase.POSITION_RIGHT
        elif self.phase is BustPhase.POSITION_RIGHT:
            self.right_x = self.cursor_x
            self.phase = BustPhase.SNARE
        elif self.phase is BustPhase.SNARE:
            self.snare_x = self.cursor_x
            self.phase = BustPhase.ACTIVE

    def spring(self) -> None:
        if self.phase is not BustPhase.ACTIVE or self.snare_x is None:
            return
        over_snare = abs(self.ghost_x - self.snare_x) <= SNARE_WIDTH / 2
        low_enough = self.ghost_y >= SNARE_TRIGGER_Y
        self.outcome = BustOutcome.CAUGHT if over_snare and low_enough else BustOutcome.MISSED
        self.phase = BustPhase.RESOLVED

    def beam_endpoints(self) -> tuple[tuple[Vec, Vec], tuple[Vec, Vec]] | None:
        left_x = self.left_x
        right_x = self.right_x
        if self.phase is not BustPhase.ACTIVE or left_x is None or right_x is None:
            return None
        return (self._beam(left_x, right_x), self._beam(right_x, left_x))

    def _beam(self, x: float, other_x: float) -> tuple[Vec, Vec]:
        # Aim off the ghost's dead centre — the geometrically LEFT cleaner (the
        # smaller of the two placed x's) aims left of ghost_x, the RIGHT aims
        # right of it — so the two tips never converge to one point (the
        # forbidden "crossed streams" look) even when the ghost sits dead
        # centre between the cleaners, AS LONG AS the tracking gain stays at
        # its baseline of 1.0 (proven: docs/superpowers/specs/2026-07-16-
        # beam-crossing-backfire-design.md). Past BEAM_NARROW_START_Y the gain
        # ramps up with depth, which CAN let the tips invert for a
        # narrow-enough gap and an off-center ghost — that's the intended,
        # now-reachable "crossing the streams" backfire.
        side_sign = -1.0 if x <= other_x else 1.0
        tilt = clamp(
            self._tilt_gain() * (self.ghost_x - x) + side_sign * BEAM_AIM_SPREAD,
            -BEAM_MAX_TILT,
            BEAM_MAX_TILT,
        )
        return ((x, BUST_GROUND_Y), (x + tilt, BEAM_TOP_Y))

    def _tilt_gain(self) -> float:
        """1.0 at/above BEAM_NARROW_START_Y-depth-or-shallower, ramping
        linearly to BEAM_MAX_GAIN by BUST_GROUND_Y."""
        t = clamp(
            (self.ghost_y - BEAM_NARROW_START_Y) / (BUST_GROUND_Y - BEAM_NARROW_START_Y),
            0.0,
            1.0,
        )
        return 1.0 + (BEAM_MAX_GAIN - 1.0) * t

    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]:
        left_x = self.left_x
        right_x = self.right_x
        if self.phase is not BustPhase.ACTIVE or left_x is None or right_x is None:
            return []
        # Drift and sink.
        self.ghost_x += rng.uniform(-1.0, 1.0) * GHOST_DRIFT_SPEED * dt_seconds
        self.ghost_y += GHOST_SINK_SPEED * dt_seconds
        # Repel horizontally away from the nearer beam when it is close, always
        # toward the farther cleaner: a ghost that escaped outside the pair is
        # herded back between them rather than pinned just past the repel zone,
        # where no outcome could ever reach it.
        nearer, farther = sorted((left_x, right_x), key=lambda x: abs(self.ghost_x - x))
        if abs(self.ghost_x - nearer) <= SNARE_WIDTH:
            away = 1.0 if farther >= nearer else -1.0
            self.ghost_x += away * GHOST_REPEL_SPEED * dt_seconds
        self.ghost_x = clamp(self.ghost_x, BUST_MIN_X, BUST_MAX_X)
        self.ghost_y = clamp(self.ghost_y, BEAM_TOP_Y, BUST_GROUND_Y)
        # Backfire, two triggers: (a) the beams properly cross — a defensive
        # geometric check — or (b) the ghost has sunk low BETWEEN the cleaners
        # (ghost_y >= BEAM_CROSS_GHOST_Y), so both beams angle steeply down at
        # it and cross behind it. (b) is the reachable, player-caused hazard:
        # SNARE_TRIGGER_Y (280) < BEAM_CROSS_GHOST_Y (320) leaves a 40px skill
        # window where the ghost is springable but not yet backfiring.
        beams = self.beam_endpoints()
        beams_cross = beams is not None and segments_cross(
            beams[0][0], beams[0][1], beams[1][0], beams[1][1]
        )
        sunk_between = (
            min(left_x, right_x) < self.ghost_x < max(left_x, right_x)
            and self.ghost_y >= BEAM_CROSS_GHOST_Y
        )
        if beams_cross or sunk_between:
            self.outcome = BustOutcome.BACKFIRE
            self.phase = BustPhase.RESOLVED
            return [BeamsCrossed()]
        # Ghost touching a cleaner slimes that side.
        for side, x in enumerate((left_x, right_x)):
            if math.hypot(self.ghost_x - x, self.ghost_y - BUST_GROUND_Y) <= SLIME_RANGE:
                self.outcome = BustOutcome.SLIMED
                self.slimed_side = side
                self.phase = BustPhase.RESOLVED
                return []
        # Failsafe: whatever the dynamics do, an ACTIVE bust that nothing has
        # resolved times out as MISSED — the ghost slips away and the snare is
        # wasted, matching the MISSED cost in game._resolve_bust.
        self.active_seconds += dt_seconds
        if self.active_seconds >= BUST_TIMEOUT_SECONDS:
            self.outcome = BustOutcome.MISSED
            self.phase = BustPhase.RESOLVED
        return []

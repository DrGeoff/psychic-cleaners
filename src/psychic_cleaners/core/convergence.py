"""The Warden and the Locksmith: at max PSI they converge on Threshold Tower.

Spec 4.3/4.7: when city PSI hits its cap the pair appear and walk toward
the Tower; the finale unlocks only once BOTH arrive. Spawn corners are
fixed (the grid's opposite corners) and movement is straight-line at a
constant speed, so the walk needs no rng and replays identically.
"""

import math
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    CONVERGENCE_WALK_SPEED,
    GRID_HEIGHT,
    GRID_WIDTH,
    TOWER_POS,
)
from psychic_cleaners.core.geometry import move_toward

# Same arrival radius the wisps use for reaching the tower (city.py).
_ARRIVE_RADIUS = 0.5
# The stop-short clamp in Walker.tick lands EXACTLY on the radius; rounding
# can leave the distance a few ulps above it, so `arrived` allows that noise.
_ARRIVE_EPSILON = 1e-9


@dataclass
class Walker:
    x: float  # grid coordinates, float
    y: float

    def tick(self, dt_seconds: float) -> None:
        self.x, self.y = move_toward(
            self.x,
            self.y,
            TOWER_POS[0],
            TOWER_POS[1],
            CONVERGENCE_WALK_SPEED * dt_seconds,
            stop_radius=_ARRIVE_RADIUS,
        )

    @property
    def arrived(self) -> bool:
        distance = math.hypot(TOWER_POS[0] - self.x, TOWER_POS[1] - self.y)
        return distance <= _ARRIVE_RADIUS + _ARRIVE_EPSILON


@dataclass
class Convergence:
    warden: Walker
    locksmith: Walker

    @classmethod
    def start(cls) -> Convergence:
        return cls(
            warden=Walker(x=0.0, y=0.0),
            locksmith=Walker(x=float(GRID_WIDTH - 1), y=float(GRID_HEIGHT - 1)),
        )

    def tick(self, dt_seconds: float) -> None:
        self.warden.tick(dt_seconds)
        self.locksmith.tick(dt_seconds)

    @property
    def arrived(self) -> bool:
        return self.warden.arrived and self.locksmith.arrived

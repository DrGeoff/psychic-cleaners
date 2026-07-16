"""Driving lane simulation: forward progress, road wisps, vacuum catch geometry."""

from dataclasses import dataclass, field

from psychic_cleaners.core.constants import (
    CAR_X,
    CATCH_RANGE,
    DRIVE_LANES,
    FAINT_WISP_CHANCE,
    ROAD_LENGTH_VISIBLE,
    ROAD_WISP_SPAWN_PER_SECOND,
    ROAD_WISP_SPEED,
    VACUUM_BOUNTY,
    WISP_SPAWN_MARGIN,
)
from psychic_cleaners.core.events import Event, WispCaptured
from psychic_cleaners.core.geometry import clamp
from psychic_cleaners.core.rng import Rng


@dataclass
class RoadWisp:
    # Spawns at ROAD_LENGTH_VISIBLE + WISP_SPAWN_MARGIN (just off the visible
    # edge), moves toward 0 (toward the car).
    x: float
    lane: int  # 0..DRIVE_LANES-1
    faint: bool


@dataclass
class DriveSim:
    distance_total: float
    speed: float
    has_vacuum: bool
    has_lens: bool
    distance_done: float = 0.0
    lane: int = 1
    wisps: list[RoadWisp] = field(default_factory=list)

    def steer(self, delta: int) -> None:
        self.lane = clamp(self.lane + delta, 0, DRIVE_LANES - 1)

    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]:
        events: list[Event] = []
        self.distance_done += self.speed * dt_seconds
        approach = (ROAD_WISP_SPEED + self.speed) * dt_seconds
        for wisp in self.wisps:
            wisp.x -= approach
        remaining: list[RoadWisp] = []
        for wisp in self.wisps:
            catchable = (
                self.has_vacuum
                and wisp.lane == self.lane
                and abs(wisp.x - CAR_X) <= CATCH_RANGE
                and (not wisp.faint or self.has_lens)
            )
            if catchable:
                events.append(WispCaptured(bounty=VACUUM_BOUNTY))
            elif wisp.x >= -CATCH_RANGE:
                remaining.append(wisp)
            # else: passed off-screen, removed silently
        self.wisps = remaining
        if rng.random() < ROAD_WISP_SPAWN_PER_SECOND * dt_seconds:
            self.wisps.append(
                RoadWisp(
                    x=ROAD_LENGTH_VISIBLE + WISP_SPAWN_MARGIN,
                    lane=rng.randint(0, DRIVE_LANES - 1),
                    faint=rng.random() < FAINT_WISP_CHANCE,
                )
            )
        return events

    @property
    def arrived(self) -> bool:
        return self.distance_done >= self.distance_total

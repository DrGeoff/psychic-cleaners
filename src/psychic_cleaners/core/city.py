"""City model: grid of buildings, haunt bookkeeping, wisps, travel distances."""

import math
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BLOCK_LENGTH,
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    HAUNT_CHANCE_PER_REAL_MINUTE,
    MAX_ACTIVE_HAUNTS,
    PSI_MAX,
    TOWER_ARRIVE_RADIUS,
    TOWER_POS,
    WISP_MAP_SPEED,
    WISP_SPAWN_PER_REAL_MINUTE,
)
from psychic_cleaners.core.events import Event, GridPos, HauntStarted, WispReachedTower
from psychic_cleaners.core.geometry import move_toward
from psychic_cleaners.core.rng import Rng


@dataclass
class Building:
    pos: GridPos
    haunted: bool = False


@dataclass
class Wisp:
    x: float  # grid coordinates, float
    y: float


@dataclass
class City:
    buildings: dict[GridPos, Building]
    wisps: list[Wisp]

    @classmethod
    def new(cls) -> City:
        buildings = {
            (x, y): Building(pos=(x, y))
            for x in range(GRID_WIDTH)
            for y in range(GRID_HEIGHT)
            if (x, y) not in (TOWER_POS, DEPOT_POS)
        }
        return cls(buildings=buildings, wisps=[])

    def haunted_positions(self) -> list[GridPos]:
        return [pos for pos, building in self.buildings.items() if building.haunted]

    def active_haunts(self) -> int:
        return len(self.haunted_positions())

    def clear_haunt(self, pos: GridPos) -> None:
        building = self.buildings.get(pos)
        if building is not None:
            building.haunted = False

    def stompable_positions(self) -> list[GridPos]:
        return list(self.buildings)

    def tick(self, dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]:
        events: list[Event] = []
        events.extend(self._spawn_haunts(dt_seconds, psi_value, rng))
        self._spawn_wisps(dt_seconds, rng)
        events.extend(self._drift_wisps(dt_seconds))
        return events

    def _spawn_haunts(self, dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]:
        if self.active_haunts() >= MAX_ACTIVE_HAUNTS:
            return []
        chance = HAUNT_CHANCE_PER_REAL_MINUTE * (1.0 + psi_value / PSI_MAX)
        if rng.random() >= chance * dt_seconds / 60.0:
            return []
        candidates = [pos for pos, building in self.buildings.items() if not building.haunted]
        if not candidates:
            return []
        target = rng.choice(candidates)
        self.buildings[target].haunted = True
        return [HauntStarted(target)]

    def _spawn_wisps(self, dt_seconds: float, rng: Rng) -> None:
        if rng.random() >= WISP_SPAWN_PER_REAL_MINUTE * dt_seconds / 60.0:
            return
        # Spec 4.3: wisps spawn at random buildings and drift toward the Tower.
        cell = rng.choice(list(self.buildings))
        self.wisps.append(Wisp(x=float(cell[0]), y=float(cell[1])))

    def _drift_wisps(self, dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        tower_x, tower_y = float(TOWER_POS[0]), float(TOWER_POS[1])
        remaining: list[Wisp] = []
        for wisp in self.wisps:
            wisp.x, wisp.y = move_toward(
                wisp.x, wisp.y, tower_x, tower_y, WISP_MAP_SPEED * dt_seconds
            )
            if math.hypot(tower_x - wisp.x, tower_y - wisp.y) <= TOWER_ARRIVE_RADIUS:
                events.append(WispReachedTower())
            else:
                remaining.append(wisp)
        self.wisps = remaining
        return events

    def distance(self, a: GridPos, b: GridPos) -> float:
        return (abs(a[0] - b[0]) + abs(a[1] - b[1])) * BLOCK_LENGTH

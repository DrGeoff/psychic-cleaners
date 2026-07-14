"""City model: grid of buildings, haunt bookkeeping, wisps, travel distances."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BLOCK_LENGTH,
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    TOWER_POS,
)
from psychic_cleaners.core.events import GridPos


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

    def distance(self, a: GridPos, b: GridPos) -> float:
        return (abs(a[0] - b[0]) + abs(a[1] - b[1])) * BLOCK_LENGTH

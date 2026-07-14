"""Vehicle and equipment catalog. Dict insertion order is shop display order."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Vehicle:
    id: str
    name: str
    price: int
    speed: float
    capacity: int


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    price: int
    slots: int


VEHICLES: Final[dict[str, Vehicle]] = {
    "compact": Vehicle(id="compact", name="Compact", price=2000, speed=100.0, capacity=7),
    "hearse": Vehicle(id="hearse", name="Hearse", price=4800, speed=140.0, capacity=9),
    "wagon": Vehicle(id="wagon", name="Wagon", price=6000, speed=140.0, capacity=11),
    "performance": Vehicle(
        id="performance", name="Performance", price=15000, speed=200.0, capacity=14
    ),
}

ITEMS: Final[dict[str, Item]] = {
    "detector": Item(id="detector", name="Residue detector", price=400, slots=1),
    "lens": Item(id="lens", name="Spectral lens", price=800, slots=1),
    "sensor": Item(id="sensor", name="Mascot sensor", price=800, slots=1),
    "bait": Item(id="bait", name="Gummy bait (5)", price=400, slots=1),
    "snare": Item(id="snare", name="Spirit snare", price=600, slots=1),
    "rig": Item(id="rig", name="Containment rig", price=8000, slots=3),
    "vacuum": Item(id="vacuum", name="Roof vacuum", price=500, slots=1),
}

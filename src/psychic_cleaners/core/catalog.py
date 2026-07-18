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
    description: str


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    price: int
    slots: int
    description: str


VEHICLES: Final[dict[str, Vehicle]] = {
    "compact": Vehicle(
        id="compact",
        name="Compact",
        price=2000,
        speed=100.0,
        capacity=7,
        description="Cheap and slow, with the smallest trunk",
    ),
    "hearse": Vehicle(
        id="hearse",
        name="Hearse",
        price=4800,
        speed=140.0,
        capacity=9,
        description="Solid all-rounder: decent speed and room",
    ),
    "wagon": Vehicle(
        id="wagon",
        name="Wagon",
        price=6000,
        speed=140.0,
        capacity=11,
        description="Same speed as the Hearse, more trunk space",
    ),
    "performance": Vehicle(
        id="performance",
        name="Performance",
        price=15000,
        speed=200.0,
        capacity=14,
        description="Fastest car and the biggest trunk",
    ),
}

ITEMS: Final[dict[str, Item]] = {
    "detector": Item(
        id="detector",
        name="Residue detector",
        price=400,
        slots=1,
        description="Reveals wisps on the map; haunted buildings flash",
    ),
    "lens": Item(
        id="lens",
        name="Spectral lens",
        price=800,
        slots=1,
        description="Makes faint wisps visible while driving",
    ),
    "sensor": Item(
        id="sensor",
        name="Mascot sensor",
        price=800,
        slots=1,
        description="Advance warning before Sir Squish rampages",
    ),
    "bait": Item(
        id="bait",
        name="Gummy bait (5)",
        price=400,
        slots=1,
        description="Diverts Sir Squish when deployed during a sensor alert",
    ),
    "snare": Item(
        id="snare",
        name="Spirit snare",
        price=600,
        slots=1,
        description="Needed to trap a ghost; buy more at the Depot anytime",
    ),
    "rig": Item(
        id="rig",
        name="Containment rig",
        price=8000,
        slots=3,
        description="Holds 10 trapped ghosts; skips Depot round-trips",
    ),
    "vacuum": Item(
        id="vacuum",
        name="Roof vacuum",
        price=500,
        slots=1,
        description="Auto-catches road wisps while driving",
    ),
}

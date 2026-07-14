"""Exact catalog data: ids, names, prices, speeds, capacities, slots, display order."""

import pytest

from psychic_cleaners.core.catalog import ITEMS, VEHICLES


def test_vehicle_display_order() -> None:
    assert list(VEHICLES) == ["compact", "hearse", "wagon", "performance"]


def test_item_display_order() -> None:
    assert list(ITEMS) == ["detector", "lens", "sensor", "bait", "snare", "rig", "vacuum"]


@pytest.mark.parametrize(
    ("vehicle_id", "name", "price", "speed", "capacity"),
    [
        ("compact", "Compact", 2000, 100.0, 7),
        ("hearse", "Hearse", 4800, 140.0, 9),
        ("wagon", "Wagon", 6000, 140.0, 11),
        ("performance", "Performance", 15000, 200.0, 14),
    ],
)
def test_vehicle_rows(vehicle_id: str, name: str, price: int, speed: float, capacity: int) -> None:
    vehicle = VEHICLES[vehicle_id]
    assert (vehicle.id, vehicle.name, vehicle.price, vehicle.speed, vehicle.capacity) == (
        vehicle_id,
        name,
        price,
        speed,
        capacity,
    )


@pytest.mark.parametrize(
    ("item_id", "name", "price", "slots"),
    [
        ("detector", "Residue detector", 400, 1),
        ("lens", "Spectral lens", 800, 1),
        ("sensor", "Mascot sensor", 800, 1),
        ("bait", "Gummy bait (5)", 400, 1),
        ("snare", "Spirit snare", 600, 1),
        ("rig", "Containment rig", 8000, 3),
        ("vacuum", "Roof vacuum", 500, 1),
    ],
)
def test_item_rows(item_id: str, name: str, price: int, slots: int) -> None:
    item = ITEMS[item_id]
    assert (item.id, item.name, item.price, item.slots) == (item_id, name, price, slots)

"""Loadout rules: slot accounting, capacity, duplicates, snare/bait stacking."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.constants import BAIT_PACK_SIZE
from psychic_cleaners.core.loadout import Loadout


def _loadout(vehicle_id: str = "hearse") -> Loadout:
    return Loadout(vehicle=VEHICLES[vehicle_id])


def test_empty_loadout_uses_no_slots() -> None:
    assert _loadout().slots_used() == 0


def test_slots_used_sums_item_slots_times_count() -> None:
    loadout = _loadout("performance")
    loadout.add("rig")  # 3 slots
    loadout.add("snare")  # 1 slot
    loadout.add("snare")  # 1 slot
    assert loadout.slots_used() == 5


def test_can_add_false_when_capacity_exceeded() -> None:
    loadout = _loadout("compact")  # capacity 7
    for item_id in ("rig", "detector", "lens", "sensor", "vacuum"):
        loadout.add(item_id)  # 3 + 1 + 1 + 1 + 1 = 7 slots
    assert loadout.slots_used() == 7
    assert loadout.can_add("snare") is False


def test_duplicate_unique_items_rejected() -> None:
    loadout = _loadout()
    loadout.add("vacuum")
    assert loadout.can_add("vacuum") is False
    with pytest.raises(ValueError, match="vacuum"):
        loadout.add("vacuum")


def test_snares_stack() -> None:
    loadout = _loadout()
    for _ in range(4):
        loadout.add("snare")
    assert loadout.count("snare") == 4
    assert loadout.can_add("snare") is True


def test_bait_packs_add_charges_and_one_slot_each() -> None:
    loadout = _loadout()
    loadout.add("bait")
    assert loadout.bait_charges == BAIT_PACK_SIZE
    loadout.add("bait")
    assert loadout.bait_charges == 2 * BAIT_PACK_SIZE
    assert loadout.count("bait") == 2
    assert loadout.slots_used() == 2 * ITEMS["bait"].slots


def test_use_bait_decrements_and_returns_false_at_zero() -> None:
    loadout = _loadout()
    loadout.add("bait")
    for _ in range(BAIT_PACK_SIZE):
        assert loadout.use_bait() is True
    assert loadout.use_bait() is False
    assert loadout.bait_charges == 0


def test_has_reflects_counts() -> None:
    loadout = _loadout()
    assert loadout.has("vacuum") is False
    loadout.add("vacuum")
    assert loadout.has("vacuum") is True


@given(
    vehicle_id=st.sampled_from(list(VEHICLES)),
    item_ids=st.lists(st.sampled_from(list(ITEMS)), max_size=30),
)
def test_slots_used_never_exceeds_capacity(vehicle_id: str, item_ids: list[str]) -> None:
    """Property: any valid sequence of add() calls keeps slots_used() within capacity."""
    loadout = Loadout(vehicle=VEHICLES[vehicle_id])
    for item_id in item_ids:
        if loadout.can_add(item_id):
            loadout.add(item_id)
        assert loadout.slots_used() <= loadout.vehicle.capacity

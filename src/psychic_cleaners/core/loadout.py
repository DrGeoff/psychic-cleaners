"""Loadout: what the franchise carries, constrained by vehicle capacity."""

from dataclasses import dataclass, field
from typing import Final

from psychic_cleaners.core.catalog import ITEMS, Vehicle
from psychic_cleaners.core.constants import BAIT_PACK_SIZE

_STACKABLE: Final[frozenset[str]] = frozenset({"snare", "bait"})


@dataclass
class Loadout:
    vehicle: Vehicle
    counts: dict[str, int] = field(default_factory=dict)  # item_id -> count owned
    bait_charges: int = 0  # BAIT_PACK_SIZE per bait pack bought

    def slots_used(self) -> int:
        return sum(ITEMS[item_id].slots * n for item_id, n in self.counts.items())

    def can_add(self, item_id: str) -> bool:
        item = ITEMS[item_id]
        if item_id not in _STACKABLE and self.count(item_id) > 0:
            return False
        return self.slots_used() + item.slots <= self.vehicle.capacity

    def add(self, item_id: str) -> None:
        if not self.can_add(item_id):
            raise ValueError(f"cannot add {item_id!r} to loadout")
        self.counts[item_id] = self.counts.get(item_id, 0) + 1
        if item_id == "bait":
            self.bait_charges += BAIT_PACK_SIZE

    def count(self, item_id: str) -> int:
        return self.counts.get(item_id, 0)

    def has(self, item_id: str) -> bool:
        return self.count(item_id) > 0

    def use_bait(self) -> bool:
        if self.bait_charges <= 0:
            return False
        self.bait_charges -= 1
        return True

    def use_snare(self) -> None:
        """Consume one snare, wasted in a miss/slime/backfire. Direct
        mutation per contract; the key always exists because entering a
        bust required free_snares() > 0."""
        self.counts["snare"] -= 1

"""Integration tests for Milestone 5: world tick, PSI, map travel, depot services."""

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import (
    CLEANER_COUNT,
    DEPOT_POS,
    PSI_GROWTH_PER_MINUTE,
    PSI_MAX,
    WISP_TOWER_PSI_JUMP,
)
from psychic_cleaners.core.events import (
    BuyItem,
    CleanersRestored,
    Event,
    FinaleUnlocked,
    ItemBought,
    NewGame,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SetDestination,
    SnaresEmptied,
    TravelStarted,
    WispReachedTower,
)
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout


def _map_game(seed: int) -> Game:
    """A game forced onto the map with a vehicle, skipping title/shop flow."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    return game


def test_new_fields_default() -> None:
    game = new_game(1)
    assert game.psi.value == 0
    assert game.city.active_haunts() == 0
    assert len(game.city.buildings) == 58
    assert game.position == DEPOT_POS
    assert game.destination is None
    assert game.finale_unlocked is False
    assert game.slimed == set()
    assert game.snares_full == 0
    assert game.contained == 0


def test_able_cleaners_and_free_snares() -> None:
    game = _map_game(2)
    assert game.able_cleaners() == CLEANER_COUNT
    game.slimed.add(0)
    assert game.able_cleaners() == CLEANER_COUNT - 1
    assert game.loadout is not None
    game.loadout.add("snare")
    game.loadout.add("snare")
    game.snares_full = 1
    assert game.free_snares() == 1


def test_free_snares_without_loadout_is_zero() -> None:
    game = new_game(3)
    assert game.free_snares() == 0


def test_new_game_resets_world_state() -> None:
    game = _map_game(4)
    game.psi.spike(500.0)
    game.city.buildings[(2, 2)].haunted = True
    game.position = (4, 4)
    game.destination = (5, 5)
    game.finale_unlocked = True
    game.slimed = {1}
    game.snares_full = 2
    game.contained = 3
    game.scene = SceneId.TITLE
    game.tick([NewGame("pat")], 0.0)
    assert game.scene is SceneId.SHOP
    assert game.psi.value == 0
    assert game.city.active_haunts() == 0
    assert game.position == DEPOT_POS
    assert game.destination is None
    assert game.finale_unlocked is False
    assert game.slimed == set()
    assert game.snares_full == 0
    assert game.contained == 0


def test_psi_frozen_outside_world_scenes() -> None:
    game = new_game(5)
    assert game.scene is SceneId.TITLE
    game.tick([], 60.0)
    assert game.psi.value == 0


def test_psi_grows_on_map() -> None:
    # Seed 13 (not 6): with dt=60s, WISP_MAP_SPEED*60 = 3.0 grid cells of
    # travel, enough for a wisp spawned this same tick to reach the tower
    # from most spawn points and add a WISP_TOWER_PSI_JUMP contamination
    # (see test_city_tick.py's same caveat). Seed 13 deterministically spawns
    # no such wisp so the exact +250 base rate is observable in isolation.
    game = _map_game(13)
    game.tick([], 60.0)  # one rate-clock minute; no haunts were active before it
    assert game.psi.value == int(PSI_GROWTH_PER_MINUTE)


def test_wisp_reaching_tower_spikes_psi() -> None:
    game = _map_game(7)
    game.city.wisps.append(Wisp(x=5.0, y=2.6))  # already within reach of (5, 3)
    events = game.tick([], 1.0)
    assert any(isinstance(e, WispReachedTower) for e in events)
    assert game.psi.value >= WISP_TOWER_PSI_JUMP


def test_finale_unlocked_exactly_once() -> None:
    game = _map_game(8)
    game.psi.spike(float(PSI_MAX))
    first = game.tick([], 0.0)
    second = game.tick([], 0.0)
    assert sum(isinstance(e, FinaleUnlocked) for e in first) == 1
    assert not any(isinstance(e, FinaleUnlocked) for e in second)
    assert game.finale_unlocked is True


def test_set_destination_to_neighbour_starts_a_drive() -> None:
    # Milestone 6 (Task 21) replaced the Milestone 5 instant-travel placeholder:
    # SetDestination to a different cell now starts a DriveSim and switches to
    # the DRIVE scene instead of teleporting the player there immediately.
    game = _map_game(9)
    events = game.tick([SetDestination((1, 5))], 0.0)
    assert any(isinstance(e, TravelStarted) for e in events)
    assert game.position == DEPOT_POS  # not moved yet
    assert game.destination == (1, 5)
    assert game.scene is SceneId.DRIVE


def test_depot_visit_services_franchise() -> None:
    game = _map_game(10)
    game.position = (3, 4)
    game.snares_full = 2
    game.contained = 5
    game.slimed = {0, 2}
    departure = game.tick([SetDestination(DEPOT_POS)], 0.0)
    assert any(isinstance(e, TravelStarted) for e in departure)
    collected: list[Event] = []
    ticks = 0
    while game.scene is SceneId.DRIVE and ticks < 200:
        collected.extend(game.tick([], 0.1))
        ticks += 1
    assert game.position == DEPOT_POS
    assert game.snares_full == 0
    assert game.contained == 0
    assert game.slimed == set()
    assert any(isinstance(e, SnaresEmptied) for e in collected)
    assert any(isinstance(e, CleanersRestored) for e in collected)
    assert game.scene is SceneId.MAP


def test_depot_snare_restock_buys_a_snare() -> None:
    game = _map_game(11)
    assert game.position == DEPOT_POS
    assert game.loadout is not None
    owned = game.loadout.count("snare")
    balance = game.wallet.balance
    events = game.tick([BuyItem("snare")], 0.0)
    assert ItemBought("snare") in events
    assert game.loadout.count("snare") == owned + 1
    assert game.wallet.balance == balance - 600  # ITEMS["snare"].price
    assert game.notice is None


def test_notice_cleared_once_scene_changes_after_depot_rejection() -> None:
    # Fix 3: a notice must not outlive the scene it was raised on. A depot
    # S-rejection sets game.notice while still on MAP; driving off to
    # another cell must clear it the instant the scene changes to DRIVE, not
    # leave it lingering into the new scene.
    game = _map_game(14)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")  # keeps the bankruptcy rule out of play below
    assert game.position == DEPOT_POS
    events = game.tick([BuyItem("vacuum")], 0.0)  # right place, wrong item
    assert PurchaseRejected("snares only, at the Depot") in events
    assert game.notice == "snares only, at the Depot"
    events = game.tick([SetDestination((1, 5))], 0.0)
    assert game.scene is SceneId.DRIVE
    assert any(isinstance(e, SceneChanged) for e in events)
    assert game.notice is None


def test_depot_restock_rejects_other_items_and_other_places() -> None:
    game = _map_game(12)
    game.position = (3, 3)
    events = game.tick([BuyItem("snare")], 0.0)  # right item, wrong place
    assert PurchaseRejected("snares only, at the Depot") in events
    game.position = DEPOT_POS
    events = game.tick([BuyItem("vacuum")], 0.0)  # right place, wrong item
    assert PurchaseRejected("snares only, at the Depot") in events
    assert game.notice == "snares only, at the Depot"
    assert game.loadout is not None
    assert game.loadout.count("vacuum") == 0

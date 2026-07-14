"""Scripted shop flows against core.game: purchases, rejections, scene transition."""

from psychic_cleaners.core.events import (
    BuyItem,
    FinishShopping,
    ItemBought,
    NewGame,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SelectVehicle,
    VehicleSelected,
)
from psychic_cleaners.core.game import Game, new_game


def _shop_game() -> Game:
    game = new_game(seed=1)
    game.tick([NewGame("Pat")], 0.0)
    assert game.scene == SceneId.SHOP
    return game


def test_happy_path_hearse_two_snares_vacuum() -> None:
    game = _shop_game()

    events = game.tick([SelectVehicle("hearse")], 0.0)
    assert VehicleSelected("hearse") in events

    events = game.tick([BuyItem("snare"), BuyItem("snare"), BuyItem("vacuum")], 0.0)
    assert events.count(ItemBought("snare")) == 2
    assert ItemBought("vacuum") in events

    events = game.tick([FinishShopping()], 0.0)
    assert SceneChanged(SceneId.MAP) in events
    assert game.scene == SceneId.MAP
    assert game.wallet.balance == 10_000 - 4_800 - 2 * 600 - 500  # 3500
    assert game.loadout is not None
    assert game.loadout.vehicle.id == "hearse"
    assert game.loadout.count("snare") == 2
    assert game.loadout.count("vacuum") == 1


def test_unaffordable_vehicle_rejected() -> None:
    game = _shop_game()
    events = game.tick([SelectVehicle("performance")], 0.0)  # 15000 > 10000
    assert PurchaseRejected("cannot afford") in events
    assert game.loadout is None
    assert game.wallet.balance == 10_000


def test_second_vehicle_rejected() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)
    events = game.tick([SelectVehicle("hearse")], 0.0)
    assert PurchaseRejected("vehicle already chosen") in events
    assert game.loadout is not None
    assert game.loadout.vehicle.id == "compact"
    assert game.wallet.balance == 8_000


def test_item_before_vehicle_rejected() -> None:
    game = _shop_game()
    events = game.tick([BuyItem("snare")], 0.0)
    assert PurchaseRejected("choose a vehicle first") in events
    assert game.wallet.balance == 10_000


def test_unaffordable_item_rejected() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("hearse")], 0.0)  # 5200 left
    events = game.tick([BuyItem("rig")], 0.0)  # rig costs 8000
    assert PurchaseRejected("cannot afford") in events
    assert game.loadout is not None
    assert game.loadout.count("rig") == 0
    assert game.wallet.balance == 5_200


def test_full_vehicle_rejects_item() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)  # capacity 7, 8000 left
    fill = ["detector", "lens", "sensor", "bait", "vacuum", "snare", "snare"]  # 7 slots
    game.tick([BuyItem(item_id) for item_id in fill], 0.0)
    events = game.tick([BuyItem("snare")], 0.0)
    assert PurchaseRejected("no room in vehicle") in events
    assert game.loadout is not None
    assert game.loadout.count("snare") == 2


def test_finish_without_vehicle_stays_in_shop() -> None:
    game = _shop_game()
    events = game.tick([FinishShopping()], 0.0)
    assert game.scene == SceneId.SHOP
    assert SceneChanged(SceneId.MAP) not in events


def test_notice_set_on_rejection_and_cleared_on_success() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("performance")], 0.0)  # 15000 > 10000 -> rejected
    assert game.notice == "cannot afford"
    game.tick([SelectVehicle("hearse")], 0.0)  # success clears the notice
    assert game.notice is None


def test_new_game_resets_wallet_loadout_and_notice() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact"), BuyItem("snare")], 0.0)
    game.tick([SelectVehicle("hearse")], 0.0)  # second vehicle -> rejected
    assert game.notice == "vehicle already chosen"
    # NewGame is only dispatched while on TITLE (Task 7 contract, reconfirmed by
    # Task 14's _handle_title); reach TITLE the same way test_game_fsm.py's
    # test_continue_resets_to_fresh_title_preserving_rng does, by setting the
    # scene directly, so this test exercises _reset() itself.
    game.scene = SceneId.TITLE
    game.tick([NewGame("Sam")], 0.0)  # routes through _reset()
    assert game.scene == SceneId.SHOP
    assert game.wallet.balance == 10_000
    assert game.loadout is None
    assert game.notice is None

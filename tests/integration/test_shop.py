"""Scripted shop flows against core.game: purchases, rejections, scene transition."""

from psychic_cleaners.core.events import (
    BuyItem,
    CommandRejected,
    FinishShopping,
    GameLost,
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


def test_buying_sensor_and_bait_arms_the_mascot_defense() -> None:
    # The sensor/bait combo is what lets a player divert a Sir Squish alert
    # instead of eating a stomp fine; it deserves its own purchase coverage
    # rather than only appearing as slot-filler in the full-vehicle tests.
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)  # 8000 left

    events = game.tick([BuyItem("sensor"), BuyItem("bait")], 0.0)
    assert ItemBought("sensor") in events
    assert ItemBought("bait") in events

    assert game.wallet.balance == 10_000 - 2_000 - 800 - 400  # 6800
    assert game.loadout is not None
    assert game.loadout.has("sensor")
    assert game.loadout.count("bait") == 1
    assert game.loadout.bait_charges == 5  # one pack: BAIT_PACK_SIZE


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


def test_unknown_vehicle_id_rejected() -> None:
    # Core must reject unknown catalog ids with an event, not raise KeyError
    # (spec: invalid commands produce rejection Events — not exceptions).
    game = _shop_game()
    events = game.tick([SelectVehicle("tank")], 0.0)
    assert PurchaseRejected("unknown vehicle") in events
    assert game.loadout is None
    assert game.wallet.balance == 10_000


def test_unknown_item_id_rejected() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)
    balance = game.wallet.balance
    events = game.tick([BuyItem("bazooka")], 0.0)
    assert PurchaseRejected("unknown item") in events
    assert game.wallet.balance == balance


def test_finish_without_vehicle_stays_in_shop() -> None:
    game = _shop_game()
    events = game.tick([FinishShopping()], 0.0)
    assert game.scene == SceneId.SHOP
    assert SceneChanged(SceneId.MAP) not in events


def _assert_scene(game: Game, expected: SceneId) -> None:
    """Assert the current scene, re-reading through a widened ``SceneId``.

    Mirrors test_full_game's helper: a plain literal assert narrows
    ``game.scene`` across tick calls, and two differing literal checks in one
    scope would trip mypy's ``comparison-overlap``.
    """
    assert game.scene is expected


def test_finish_snareless_and_broke_warns_once_then_folds() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact"), BuyItem("rig")], 0.0)  # 2000 + 8000 = 10000
    assert game.wallet.balance == 0
    reason = "no snare and no funds — the franchise will fold (F again to leave anyway)"
    events = game.tick([FinishShopping()], 0.0)  # first press: warned, stays
    _assert_scene(game, SceneId.SHOP)
    assert SceneChanged(SceneId.MAP) not in events
    assert CommandRejected(reason) in events
    assert game.notice == reason
    # Second press: leaves SHOP as warned; the same tick's world step then
    # runs the bankruptcy check on MAP, so the fold lands immediately.
    events = game.tick([FinishShopping()], 0.0)
    assert SceneChanged(SceneId.MAP) in events
    assert GameLost("no snares left — the franchise folds") in events
    _assert_scene(game, SceneId.GAME_OVER)


def test_finish_snareless_with_full_slots_warns_once_then_folds() -> None:
    # The doom warning must also cover the solvent-but-slot-full shape: money
    # for a snare but no room to carry one folds on the first MAP tick just
    # like the broke shape, and deserves the same one-shot warning.
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)  # capacity 7, 8000 left
    game.tick([BuyItem("bait")] * 7, 0.0)  # 7 slots of bait: full, 5200 left
    assert game.wallet.balance == 5_200
    reason = "no snare and no room for one — the franchise will fold (F again to leave anyway)"
    events = game.tick([FinishShopping()], 0.0)  # first press: warned, stays
    _assert_scene(game, SceneId.SHOP)
    assert SceneChanged(SceneId.MAP) not in events
    assert CommandRejected(reason) in events
    assert game.notice == reason
    events = game.tick([FinishShopping()], 0.0)  # second press: leaves and folds
    assert SceneChanged(SceneId.MAP) in events
    assert GameLost("no snares left — the franchise folds") in events
    _assert_scene(game, SceneId.GAME_OVER)


def test_shop_fold_warning_resets_on_new_game() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact"), BuyItem("rig")], 0.0)  # doomed loadout
    game.tick([FinishShopping()], 0.0)  # arms the one-shot warning
    assert game.shop_fold_warned
    game.scene = SceneId.TITLE  # reach TITLE directly, as the _reset() tests do
    game.tick([NewGame("Sam")], 0.0)  # routes through _reset()
    assert not game.shop_fold_warned
    game.tick([SelectVehicle("compact"), BuyItem("rig")], 0.0)
    events = game.tick([FinishShopping()], 0.0)  # fresh playthrough: warned again
    assert game.scene == SceneId.SHOP
    assert SceneChanged(SceneId.MAP) not in events


def test_finish_snareless_but_solvent_reaches_map() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)  # 8000 left: can restock at the Depot
    events = game.tick([FinishShopping()], 0.0)
    assert SceneChanged(SceneId.MAP) in events
    assert game.scene == SceneId.MAP


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

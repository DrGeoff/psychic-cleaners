"""Every command is scene-gated in Game._dispatch: sent from the wrong scene,
it must be silently ignored (no Event, no state mutation) — never accepted
and never a crash. test_game_fsm.py already covers NewGame and Continue;
this file covers the remaining twelve.
"""

import pytest

from psychic_cleaners.core.constants import DEPOT_POS
from psychic_cleaners.core.events import (
    BuyItem,
    Command,
    DeployBait,
    EnterAccount,
    FinishShopping,
    LaySnare,
    MoveCleaner,
    NewGame,
    PlaceCleaner,
    SelectVehicle,
    SetDestination,
    SpringSnare,
    StartRun,
    Steer,
)
from psychic_cleaners.core.game import Game, SceneId, new_game


def _in_shop() -> Game:
    game = new_game(1)
    game.tick([NewGame("Ada")], 0.0)
    assert game.scene is SceneId.SHOP
    return game


def _in_map() -> Game:
    game = _in_shop()
    game.tick([SelectVehicle("hearse")], 0.0)
    game.tick([BuyItem("snare")], 0.0)
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    return game


def _in_drive() -> Game:
    game = _in_map()
    dest = next(pos for pos in game.city.buildings if pos != game.position)
    game.tick([SetDestination(dest)], 0.0)
    assert game.scene is SceneId.DRIVE
    return game


def test_enter_account_ignored_outside_title() -> None:
    game = _in_shop()
    name_before, balance_before = game.player_name, game.wallet.balance
    events = game.tick([EnterAccount(name="Zed", code="ABCDEFG")], 0.0)
    assert events == []
    assert game.player_name == name_before
    assert game.wallet.balance == balance_before
    assert game.scene is SceneId.SHOP


def test_select_vehicle_ignored_outside_shop() -> None:
    game = _in_map()
    loadout_before = game.loadout
    events = game.tick([SelectVehicle("compact")], 0.0)
    assert events == []
    assert game.loadout is loadout_before
    assert game.loadout is not None
    assert game.loadout.vehicle.id == "hearse"


def test_buy_item_ignored_outside_shop_and_map() -> None:
    game = _in_drive()
    assert game.loadout is not None
    balance_before, snares_before = game.wallet.balance, game.loadout.count("snare")
    events = game.tick([BuyItem("snare")], 0.0)
    assert events == []
    assert game.wallet.balance == balance_before
    assert game.loadout.count("snare") == snares_before


def test_finish_shopping_ignored_outside_shop() -> None:
    game = _in_map()
    events = game.tick([FinishShopping()], 0.0)
    assert events == []
    assert game.scene is SceneId.MAP


def test_set_destination_ignored_outside_map() -> None:
    game = _in_shop()
    events = game.tick([SetDestination((1, 1))], 0.0)
    assert events == []
    assert game.position == DEPOT_POS
    assert game.drive is None
    assert game.scene is SceneId.SHOP


def test_steer_ignored_outside_drive() -> None:
    game = _in_map()
    events = game.tick([Steer(1)], 0.0)
    assert events == []
    assert game.drive is None
    assert game.scene is SceneId.MAP


@pytest.mark.parametrize("command", [MoveCleaner(1.0), PlaceCleaner(), LaySnare(), SpringSnare()])
def test_bust_commands_ignored_outside_bust(command: Command) -> None:
    game = _in_map()
    events = game.tick([command], 0.0)
    assert events == []
    assert game.bust is None
    assert game.scene is SceneId.MAP


def test_start_run_ignored_outside_finale() -> None:
    game = _in_map()
    events = game.tick([StartRun()], 0.0)
    assert events == []
    assert game.finale is None
    assert game.scene is SceneId.MAP


def test_deploy_bait_ignored_outside_world_scenes() -> None:
    game = _in_shop()
    game.tick([SelectVehicle("compact")], 0.0)
    game.tick([BuyItem("bait")], 0.0)
    assert game.loadout is not None
    charges_before = game.loadout.bait_charges
    events = game.tick([DeployBait()], 0.0)
    assert events == []
    assert game.loadout.bait_charges == charges_before
    assert game.scene is SceneId.SHOP

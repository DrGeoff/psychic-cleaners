"""Integration tests: city travel runs through the driving simulation."""

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import BLOCK_LENGTH, CAR_X, DEPOT_POS, VACUUM_BOUNTY
from psychic_cleaners.core.drive import RoadWisp
from psychic_cleaners.core.events import (
    Arrived,
    BuyItem,
    CleanersRestored,
    Event,
    FinishShopping,
    ItemBought,
    NewGame,
    SceneChanged,
    SceneId,
    SelectVehicle,
    SetDestination,
    SnaresEmptied,
    Steer,
    TravelStarted,
    WispCaptured,
)
from psychic_cleaners.core.game import Game, new_game


def _game_on_map(extra_items: tuple[str, ...] = ()) -> Game:
    """New game, hearse bought, one snare (avoids the no-snares loss rule), on the map."""
    game = new_game(1)
    game.tick([NewGame(name="Ada")], 0.0)
    game.tick([SelectVehicle(vehicle_id="hearse")], 0.0)
    for item_id in ("snare", *extra_items):
        events = game.tick([BuyItem(item_id=item_id)], 0.0)
        assert any(isinstance(e, ItemBought) for e in events)
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    assert game.position == DEPOT_POS
    return game


def test_set_destination_starts_a_drive() -> None:
    game = _game_on_map()
    dest = (3, 5)  # 3 manhattan steps east of DEPOT_POS (0, 5)
    events = game.tick([SetDestination(pos=dest)], 0.0)
    assert TravelStarted(dest=dest, distance=3 * BLOCK_LENGTH) in events
    assert SceneChanged(scene=SceneId.DRIVE) in events
    assert game.scene is SceneId.DRIVE
    assert game.destination == dest
    assert game.drive is not None
    assert game.drive.distance_total == 3 * BLOCK_LENGTH
    assert game.drive.speed == VEHICLES["hearse"].speed
    assert game.position == DEPOT_POS  # not moved yet


def test_drive_sim_reflects_loadout_gear() -> None:
    game = _game_on_map(extra_items=("vacuum",))
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    assert game.drive.has_vacuum is True
    assert game.drive.has_lens is False


def test_hearse_arrives_after_distance_over_speed_seconds() -> None:
    game = _game_on_map()
    dest = (3, 5)
    game.tick([SetDestination(pos=dest)], 0.0)
    expected_seconds = 3 * BLOCK_LENGTH / VEHICLES["hearse"].speed  # 1200/140 ~ 8.57 s
    collected: list[Event] = []
    ticks = 0
    while game.scene is SceneId.DRIVE and ticks < 200:
        collected.extend(game.tick([], 0.1))
        ticks += 1
    assert Arrived(pos=dest) in collected
    assert SceneChanged(scene=SceneId.MAP) in collected
    assert game.scene is SceneId.MAP
    assert game.position == dest
    assert game.destination is None
    assert game.drive is None
    assert abs(ticks * 0.1 - expected_seconds) <= 0.2


def test_destination_equal_to_position_routes_arrival_immediately() -> None:
    game = _game_on_map()
    game.snares_full = 1
    events = game.tick([SetDestination(pos=DEPOT_POS)], 0.0)
    assert Arrived(pos=DEPOT_POS) in events
    assert SnaresEmptied() in events
    assert CleanersRestored() in events
    assert game.snares_full == 0
    assert not any(isinstance(e, TravelStarted) for e in events)
    assert game.scene is SceneId.MAP
    assert game.drive is None


def test_steer_command_changes_lane_while_driving() -> None:
    game = _game_on_map()
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    assert game.drive.lane == 1
    game.tick([Steer(delta=-1)], 0.01)
    assert game.drive is not None
    assert game.drive.lane == 0


def test_wisp_catch_during_travel_pays_the_bounty() -> None:
    game = _game_on_map(extra_items=("vacuum",))
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    balance_before = game.wallet.balance
    game.drive.wisps.append(RoadWisp(x=CAR_X, lane=game.drive.lane, faint=False))
    events = game.tick([], 0.01)
    assert WispCaptured(bounty=VACUUM_BOUNTY) in events
    assert game.wallet.balance == balance_before + VACUUM_BOUNTY


def test_road_catch_removes_one_wisp_from_the_city_population() -> None:
    game = _game_on_map(extra_items=("vacuum",))
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    game.city.wisps.append(Wisp(x=0.0, y=0.0))  # far from the tower: survives city.tick
    balance_before = game.wallet.balance
    game.drive.wisps.append(RoadWisp(x=CAR_X, lane=game.drive.lane, faint=False))
    events = game.tick([], 0.01)
    assert WispCaptured(bounty=VACUUM_BOUNTY) in events
    assert game.city.wisps == []  # road wisps represent the city population
    assert game.wallet.balance == balance_before + VACUUM_BOUNTY

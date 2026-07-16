"""The command/event vocabulary: construction, immutability, value equality."""

import dataclasses

import pytest

from psychic_cleaners.core import events


def _example_commands() -> list[events.Command]:
    return [
        events.NewGame(name="Ada"),
        events.EnterAccount(name="Ada", code="ABCDEFG"),
        events.SelectVehicle(vehicle_id="hearse"),
        events.BuyItem(item_id="snare"),
        events.FinishShopping(),
        events.SetDestination(pos=(3, 2)),
        events.TakeLoan(),
        events.RepayLoan(),
        events.Steer(delta=-1),
        events.MoveCleaner(dx=4.0),
        events.PlaceCleaner(),
        events.LaySnare(),
        events.SpringSnare(),
        events.DeployBait(),
        events.StartRun(),
        events.Continue(),
    ]


def _declared_subclasses(base: type) -> set[type]:
    return {
        obj
        for obj in vars(events).values()
        if isinstance(obj, type) and issubclass(obj, base) and obj is not base
    }


def test_scene_id_has_exactly_seven_members() -> None:
    assert [member.name for member in events.SceneId] == [
        "TITLE",
        "SHOP",
        "MAP",
        "DRIVE",
        "BUST",
        "FINALE",
        "GAME_OVER",
    ]


def test_every_command_class_constructs() -> None:
    constructed = {type(command) for command in _example_commands()}
    assert constructed == _declared_subclasses(events.Command)
    assert len(constructed) == 16


def test_command_equality_by_value() -> None:
    assert events.NewGame(name="Ada") == events.NewGame(name="Ada")
    assert events.NewGame(name="Ada") != events.NewGame(name="Bee")
    assert events.Steer(delta=1) != events.Steer(delta=-1)
    assert events.Continue() == events.Continue()


@pytest.mark.parametrize("command", _example_commands())
def test_commands_are_frozen(command: events.Command) -> None:
    field_name = next((f.name for f in dataclasses.fields(command)), "anything")
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(command, field_name, object())


def _example_events() -> list[events.Event]:
    return [
        events.SceneChanged(scene=events.SceneId.SHOP),
        events.AccountAccepted(name="Ada", bankroll=12_000),
        events.AccountRejected(reason="bad checksum"),
        events.VehicleSelected(vehicle_id="wagon"),
        events.ItemBought(item_id="vacuum"),
        events.PurchaseRejected(reason="cannot afford"),
        events.CommandRejected(reason="no snare laid"),
        events.TravelStarted(dest=(4, 1), distance=800.0),
        events.RentCharged(amount=1000, day=1),
        events.LoanTaken(amount=5000),
        events.LoanRepaid(amount=5000),
        events.Arrived(pos=(4, 1)),
        events.WispCaptured(bounty=100),
        events.HauntStarted(pos=(2, 2)),
        events.HauntCleared(pos=(2, 2)),
        events.WispReachedTower(),
        events.GhostTrapped(fee=400),
        events.BustMissed(),
        events.BeamsCrossed(),
        events.CleanerSlimed(cleaner=1),
        events.SnaresEmptied(),
        events.CleanersRestored(),
        events.MascotAlert(window_seconds=10.0),
        events.BaitDeployed(),
        events.StompTriggered(),
        events.BuildingStomped(pos=(6, 3), fine=4_000),
        events.ConvergenceStarted(),
        events.FinaleUnlocked(),
        events.RunnerEntered(total_inside=1),
        events.RunnerSquashed(),
        events.GameWon(account_code="ABCDEFG"),
        events.GameLost(reason="the Tower claimed the city"),
    ]


def test_every_event_class_constructs() -> None:
    constructed = {type(event) for event in _example_events()}
    assert constructed == _declared_subclasses(events.Event)
    assert len(constructed) == 32


def test_event_equality_by_value() -> None:
    assert events.GhostTrapped(fee=400) == events.GhostTrapped(fee=400)
    assert events.GhostTrapped(fee=400) != events.GhostTrapped(fee=500)
    rejected = events.CommandRejected(reason="no snare laid")
    assert rejected == events.CommandRejected(reason="no snare laid")
    assert rejected != events.CommandRejected(reason="try again")
    assert events.SceneChanged(scene=events.SceneId.MAP) == events.SceneChanged(
        scene=events.SceneId.MAP
    )
    assert events.WispReachedTower() == events.WispReachedTower()


@pytest.mark.parametrize("event", _example_events())
def test_events_are_frozen(event: events.Event) -> None:
    field_name = next((f.name for f in dataclasses.fields(event)), "anything")
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(event, field_name, object())


def test_grid_pos_alias() -> None:
    pos: events.GridPos = (3, 4)
    assert events.Arrived(pos=pos).pos == (3, 4)

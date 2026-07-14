"""Integration tests: the bust flow through the Game FSM."""

from psychic_cleaners.core.bust import BustPhase, BustSim
from psychic_cleaners.core.catalog import ITEMS
from psychic_cleaners.core.constants import (
    BEAM_CROSS_GHOST_Y,
    BUST_GROUND_Y,
    BUST_MIN_X,
    SLIME_RANGE,
)
from psychic_cleaners.core.events import (
    BeamsCrossed,
    BustMissed,
    BuyItem,
    CleanerSlimed,
    CommandRejected,
    FinishShopping,
    GameLost,
    GhostTrapped,
    GridPos,
    HauntCleared,
    LaySnare,
    MoveCleaner,
    NewGame,
    PlaceCleaner,
    SceneId,
    SelectVehicle,
    SetDestination,
    SpringSnare,
)
from psychic_cleaners.core.game import Game, new_game

HAUNT: GridPos = (1, 5)


def _shopped_game(*, snares: int = 1, with_rig: bool = False) -> Game:
    """New game with a hearse plus the given gear, standing at the Depot on the map."""
    game = new_game(1)
    game.tick([NewGame("Pat")], 0.0)
    if with_rig:
        game.wallet.balance = 20_000  # hearse + rig + snare exceeds the starting bankroll
    game.tick([SelectVehicle("hearse")], 0.0)
    if with_rig:
        game.tick([BuyItem("rig")], 0.0)
    for _ in range(snares):
        game.tick([BuyItem("snare")], 0.0)
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    return game


def _arrive_at(game: Game, pos: GridPos) -> None:
    """Travel to pos, skipping the drive by completing the distance directly."""
    game.tick([SetDestination(pos)], 0.0)
    assert game.scene is SceneId.DRIVE
    assert game.drive is not None
    game.drive.distance_done = game.drive.distance_total
    game.tick([], 0.0)


def test_arrival_at_haunt_with_snares_and_cleaners_starts_bust() -> None:
    game = _shopped_game()
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.BUST
    assert isinstance(game.bust, BustSim)
    assert game.bust.phase is BustPhase.POSITION_LEFT


def test_arrival_at_haunt_without_snares_goes_to_map() -> None:
    game = _shopped_game(snares=0)
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.MAP
    assert game.bust is None
    assert HAUNT in game.city.haunted_positions()  # haunting persists


def test_arrival_at_haunt_with_one_able_cleaner_goes_to_map() -> None:
    game = _shopped_game()
    game.slimed = {0, 1}
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.MAP
    assert game.bust is None


def _game_at_bust(*, snares: int = 1, with_rig: bool = False) -> Game:
    game = _shopped_game(snares=snares, with_rig=with_rig)
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.BUST
    return game


def _lay_and_activate(game: Game) -> BustSim:
    game.tick([MoveCleaner(-120.0), PlaceCleaner()], 0.0)  # left cleaner at x=200
    game.tick([MoveCleaner(240.0), PlaceCleaner()], 0.0)  # right cleaner at x=440
    game.tick([MoveCleaner(-120.0), LaySnare()], 0.0)  # snare at x=320
    bust = game.bust
    assert bust is not None
    assert bust.phase is BustPhase.ACTIVE
    return bust


def test_early_lay_snare_ignored_and_early_spring_rejected() -> None:
    game = _game_at_bust()
    bust = game.bust
    assert bust is not None
    events = game.tick([LaySnare(), SpringSnare()], 0.0)
    assert CommandRejected("no snare laid") in events  # SpringSnare outside ACTIVE
    assert bust.phase is BustPhase.POSITION_LEFT  # LaySnare silently ignored
    assert bust.snare_x is None


def test_place_cleaner_does_not_lay_snare() -> None:
    game = _game_at_bust()
    bust = game.bust
    assert bust is not None
    game.tick([PlaceCleaner()], 0.0)
    game.tick([PlaceCleaner()], 0.0)
    assert bust.phase is BustPhase.SNARE
    game.tick([PlaceCleaner()], 0.0)  # only LaySnare may lay the snare
    assert bust.phase is BustPhase.SNARE
    assert bust.snare_x is None


def test_successful_bust_pays_fee_and_clears_haunt() -> None:
    game = _game_at_bust()
    bust = _lay_and_activate(game)
    balance_before = game.wallet.balance
    bust.ghost_x = 320.0  # force the smudge over the snare before springing
    bust.ghost_y = 300.0
    events = game.tick([SpringSnare()], 0.0)
    assert GhostTrapped(300) in events  # psi is 0, so fee == BUST_BASE_FEE
    assert HauntCleared(HAUNT) in events
    assert game.wallet.balance == balance_before + 300
    assert game.snares_full == 1
    assert game.contained == 0
    assert game.free_snares() == 0
    assert game.bust is None
    assert game.scene is SceneId.MAP
    assert HAUNT not in game.city.haunted_positions()


def test_rig_keeps_snare_free_on_catch() -> None:
    game = _game_at_bust(with_rig=True)
    bust = _lay_and_activate(game)
    bust.ghost_x = 320.0
    bust.ghost_y = 300.0
    game.tick([SpringSnare()], 0.0)
    assert game.contained == 1
    assert game.snares_full == 0
    assert game.free_snares() == 1
    assert game.scene is SceneId.MAP


def test_backfire_slimes_two_and_wastes_snare() -> None:
    game = _game_at_bust(snares=2)
    bust = _lay_and_activate(game)
    # The smudge has sunk low BETWEEN the cleaners (200 < 320 < 440 and
    # ghost_y >= BEAM_CROSS_GHOST_Y): both beams angle steeply down at it and
    # cross -> backfire on this tick's bust ticking, resolved the same call.
    bust.ghost_x = 320.0
    bust.ghost_y = BEAM_CROSS_GHOST_Y + 10.0
    events = game.tick([], 0.0)
    assert BeamsCrossed() in events
    assert CleanerSlimed(0) in events
    assert CleanerSlimed(1) in events
    assert BustMissed() not in events
    assert game.slimed == {0, 1}
    assert game.able_cleaners() == 1
    assert game.loadout is not None
    assert game.loadout.count("snare") == 1  # one snare wasted, one left
    assert game.bust is None
    assert game.scene is SceneId.MAP
    assert HAUNT in game.city.haunted_positions()  # smudge escaped


def test_missed_last_snare_when_broke_loses_game() -> None:
    game = _game_at_bust(snares=1)
    bust = _lay_and_activate(game)
    game.wallet.balance = ITEMS["snare"].price - 1  # too broke to restock at the Depot
    bust.ghost_x = BUST_MIN_X  # nowhere near the snare at x=320
    bust.ghost_y = 150.0
    events = game.tick([SpringSnare()], 0.0)
    assert BustMissed() in events
    assert GameLost("no snares left — the franchise folds") in events
    assert game.result == "lost"
    assert game.lose_reason == "no snares left — the franchise folds"
    assert game.scene is SceneId.GAME_OVER
    assert game.free_snares() == 0
    assert game.snares_full == 0
    assert HAUNT in game.city.haunted_positions()


def test_missed_last_snare_with_restock_money_does_not_lose() -> None:
    game = _game_at_bust(snares=1)  # wallet still holds 4600 after hearse + snare
    bust = _lay_and_activate(game)
    bust.ghost_x = BUST_MIN_X
    bust.ghost_y = 150.0
    events = game.tick([SpringSnare()], 0.0)
    assert BustMissed() in events
    assert not any(isinstance(event, GameLost) for event in events)
    assert game.result is None
    assert game.scene is SceneId.MAP
    assert game.free_snares() == 0
    assert game.snares_full == 0
    assert game.wallet.balance >= ITEMS["snare"].price  # rich enough to restock


def test_slimed_bust_reports_game_level_cleaner_index() -> None:
    game = _game_at_bust(snares=2)
    game.slimed = {0}  # cleaner 0 already out: participants are 1 and 2
    bust = _lay_and_activate(game)
    bust.ghost_x = 200.0 - SLIME_RANGE / 2  # brushing the left cleaner from outside...
    bust.ghost_y = BUST_GROUND_Y  # ...at ground level
    events = game.tick([], 0.0)
    assert CleanerSlimed(1) in events  # left side maps to lowest unslimed index
    assert game.slimed == {0, 1}
    assert game.loadout is not None
    assert game.loadout.count("snare") == 1
    assert game.scene is SceneId.MAP

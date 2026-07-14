"""Top-level game state and scene FSM.

This is the skeleton: fields and handlers for TITLE and GAME_OVER only.
Later tasks ADD fields to Game (wallet, psi, city, mascot, loadout, drive,
bust, finale, ...) plus per-scene command handlers in _dispatch, and MUST
extend _reset() with every added field in the same task.

Game.tick keeps the contract's canonical three-step shape:
1. command dispatch, 2. scene ticking, 3. post-tick resolution.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.codec import AccountCodeError, decode_account
from psychic_cleaners.core.constants import STARTING_BANKROLL
from psychic_cleaners.core.economy import Wallet
from psychic_cleaners.core.events import (
    AccountAccepted,
    AccountRejected,
    BuyItem,
    Command,
    Continue,
    EnterAccount,
    Event,
    FinishShopping,
    ItemBought,
    NewGame,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SelectVehicle,
    VehicleSelected,
)
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.core.rng import Rng, make_rng

__all__ = ["Game", "SceneId", "new_game"]


@dataclass
class Game:
    rng: Rng
    clock: GameClock = field(default_factory=GameClock)
    wallet: Wallet = field(default_factory=Wallet)
    scene: SceneId = SceneId.TITLE
    player_name: str = ""
    starting_bankroll: int = STARTING_BANKROLL
    loadout: Loadout | None = None
    result: str | None = None
    notice: str | None = None  # last rejection message, drawn by title/shop scenes

    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        # 1. Command dispatch: per-command, scene-gated handlers.
        for command in commands:
            self._dispatch(command, events)
        # 2. Scene ticking, AFTER the dispatch loop, on the CURRENT scene.
        if self.scene in self._world_scenes():
            # World time passes only here; psi/city/mascot ticks join in
            # later tasks at this same point.
            self.clock.advance(dt_seconds)
        # 3. Post-tick resolution: empty for now; later tasks extend it here
        #    (tower psi spikes, finale unlock, arrival routing, bankruptcy).
        return events

    def _dispatch(self, command: Command, events: list[Event]) -> None:
        # Unknown or invalid commands for the current scene are ignored silently.
        if self.scene is SceneId.TITLE:
            events.extend(self._handle_title(command))
        elif self.scene is SceneId.GAME_OVER and isinstance(command, Continue):
            self._reset()
            self._change_scene(SceneId.TITLE, events)
        elif self.scene is SceneId.SHOP:
            self._handle_shop(command, events)

    def _handle_title(self, command: Command) -> list[Event]:
        """Handle a command received while on the TITLE scene."""
        if isinstance(command, NewGame):
            self._reset()  # restores wallet, loadout, starting_bankroll, notice, ... (Task 7)
            self.player_name = command.name
            self.scene = SceneId.SHOP
            return [SceneChanged(SceneId.SHOP)]
        if isinstance(command, EnterAccount):
            try:
                bankroll = decode_account(command.name, command.code)
            except AccountCodeError:
                self.notice = "invalid account code"
                return [AccountRejected("invalid account code")]
            self.player_name = command.name
            self.wallet.balance = bankroll
            self.starting_bankroll = bankroll
            self.notice = None
            self.scene = SceneId.SHOP
            return [AccountAccepted(command.name, bankroll), SceneChanged(SceneId.SHOP)]
        return []

    def _handle_shop(self, command: Command, events: list[Event]) -> None:
        match command:
            case SelectVehicle(vehicle_id=vehicle_id):
                vehicle = VEHICLES[vehicle_id]
                if self.loadout is not None:
                    reason = "vehicle already chosen"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                elif not self.wallet.can_afford(vehicle.price):
                    reason = "cannot afford"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                else:
                    self.wallet.spend(vehicle.price)
                    self.loadout = Loadout(vehicle=vehicle)
                    self.notice = None
                    events.append(VehicleSelected(vehicle_id))
            case BuyItem(item_id=item_id):
                if self.loadout is None:
                    reason = "choose a vehicle first"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                elif not self.wallet.can_afford(ITEMS[item_id].price):
                    reason = "cannot afford"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                elif not self.loadout.can_add(item_id):
                    reason = "no room in vehicle"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                else:
                    self.wallet.spend(ITEMS[item_id].price)
                    self.loadout.add(item_id)
                    self.notice = None
                    events.append(ItemBought(item_id))
            case FinishShopping():
                if self.loadout is not None:
                    self.notice = None
                    self.scene = SceneId.MAP
                    events.append(SceneChanged(SceneId.MAP))

    def _change_scene(self, s: SceneId, events: list[Event]) -> None:
        self.scene = s
        events.append(SceneChanged(s))

    def _world_scenes(self) -> frozenset[SceneId]:
        return frozenset({SceneId.MAP, SceneId.DRIVE, SceneId.BUST})

    def _reset(self) -> None:
        """Reinitialize every field except rng to a fresh TITLE state.

        CONVENTION: every later task that adds a Game field MUST extend
        this method in the same task.
        """
        self.clock = GameClock()
        self.scene = SceneId.TITLE
        self.player_name = ""
        self.starting_bankroll = STARTING_BANKROLL
        self.result = None
        self.wallet = Wallet()
        self.loadout = None
        self.notice = None


def new_game(seed: int) -> Game:
    return Game(rng=make_rng(seed))

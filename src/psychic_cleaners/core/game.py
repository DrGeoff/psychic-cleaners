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
from psychic_cleaners.core.city import City
from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.codec import AccountCodeError, decode_account
from psychic_cleaners.core.constants import (
    CLEANER_COUNT,
    DEPOT_POS,
    STARTING_BANKROLL,
    WISP_TOWER_PSI_JUMP,
)
from psychic_cleaners.core.economy import Wallet
from psychic_cleaners.core.events import (
    AccountAccepted,
    AccountRejected,
    Arrived,
    BuyItem,
    CleanersRestored,
    Command,
    Continue,
    EnterAccount,
    Event,
    FinaleUnlocked,
    FinishShopping,
    GridPos,
    ItemBought,
    NewGame,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SelectVehicle,
    SetDestination,
    SnaresEmptied,
    VehicleSelected,
    WispReachedTower,
)
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.core.pk import PsiModel
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
    psi: PsiModel = field(default_factory=PsiModel)
    city: City = field(default_factory=City.new)
    slimed: set[int] = field(default_factory=set)  # cleaner indices 0..2
    contained: int = 0  # ghosts held in the containment rig
    snares_full: int = 0
    position: GridPos = DEPOT_POS
    destination: GridPos | None = None
    finale_unlocked: bool = False

    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        # 1. Command dispatch: per-command, scene-gated handlers.
        for command in commands:
            self._dispatch(command, events)
        # 2. scene/world ticking — AFTER the dispatch loop, on the current scene
        if self.scene in (SceneId.MAP, SceneId.DRIVE, SceneId.BUST):
            world_events = self._world_tick(dt_seconds)
            events.extend(world_events)
            # (3) post-tick resolution: wisp PSI jumps, one-shot finale unlock
            for event in world_events:
                if isinstance(event, WispReachedTower):
                    self.psi.spike(float(WISP_TOWER_PSI_JUMP))
            if self.psi.at_max and not self.finale_unlocked:
                self.finale_unlocked = True
                events.append(FinaleUnlocked())
        return events

    def _world_tick(self, dt_seconds: float) -> list[Event]:
        self.clock.advance(dt_seconds)
        self.psi.advance(dt_seconds, self.city.active_haunts())
        return self.city.tick(dt_seconds, self.psi.value, self.rng)

    def _dispatch(self, command: Command, events: list[Event]) -> None:
        # Unknown or invalid commands for the current scene are ignored silently.
        if self.scene is SceneId.TITLE:
            events.extend(self._handle_title(command))
        elif self.scene is SceneId.GAME_OVER and isinstance(command, Continue):
            self._reset()
            self._change_scene(SceneId.TITLE, events)
        elif self.scene is SceneId.SHOP:
            self._handle_shop(command, events)
        elif self.scene is SceneId.MAP:
            events.extend(self._handle_map(command))

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

    def _handle_map(self, command: Command) -> list[Event]:
        if isinstance(command, SetDestination):
            # Instant-travel placeholder: the Drive milestone (Task 21) replaces
            # this with a DriveSim, TravelStarted, and the DRIVE scene.
            self.destination = command.pos
            return self._arrive_at(command.pos)
        if isinstance(command, BuyItem):
            return self._depot_restock(command.item_id)
        return []

    def _depot_restock(self, item_id: str) -> list[Event]:
        """Mid-game snare restock: only "snare", and only at the Depot."""
        if item_id != "snare" or self.position != DEPOT_POS:
            self.notice = "snares only, at the Depot"
            return [PurchaseRejected("snares only, at the Depot")]
        if self.loadout is None:  # defensive: MAP is unreachable without a vehicle
            self.notice = "no vehicle"
            return [PurchaseRejected("no vehicle")]
        if not self.wallet.can_afford(ITEMS["snare"].price):
            self.notice = "cannot afford"
            return [PurchaseRejected("cannot afford")]
        if not self.loadout.can_add("snare"):
            self.notice = "no space in the vehicle"
            return [PurchaseRejected("no space in the vehicle")]
        self.wallet.spend(ITEMS["snare"].price)
        self.loadout.add("snare")
        self.notice = None
        return [ItemBought("snare")]

    def _arrive_at(self, pos: GridPos) -> list[Event]:
        """Arrival routing: an if/elif chain ending in an `else` that routes to MAP.

        Later tasks insert their `elif` branches BETWEEN the depot branch and the
        final `else` (tower before haunted). Every arrival appends Arrived(pos).
        """
        self.position = pos
        self.destination = None
        events: list[Event] = [Arrived(pos)]
        if pos == DEPOT_POS:
            self.snares_full = 0
            self.contained = 0
            self.slimed.clear()
            events.append(SnaresEmptied())
            events.append(CleanersRestored())
            self.scene = SceneId.MAP
        else:
            self.scene = SceneId.MAP
        return events

    def free_snares(self) -> int:
        if self.loadout is None:
            return 0
        return self.loadout.count("snare") - self.snares_full

    def able_cleaners(self) -> int:
        return CLEANER_COUNT - len(self.slimed)

    def _change_scene(self, s: SceneId, events: list[Event]) -> None:
        self.scene = s
        events.append(SceneChanged(s))

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
        self.psi = PsiModel()
        self.city = City.new()
        self.slimed = set()
        self.contained = 0
        self.snares_full = 0
        self.position = DEPOT_POS
        self.destination = None
        self.finale_unlocked = False


def new_game(seed: int) -> Game:
    return Game(rng=make_rng(seed))

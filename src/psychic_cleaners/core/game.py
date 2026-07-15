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
from typing import Final

from psychic_cleaners.core.bust import BustOutcome, BustPhase, BustSim
from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.city import City
from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.codec import AccountCodeError, decode_account, encode_account
from psychic_cleaners.core.constants import (
    CLEANER_COUNT,
    CONTAINMENT_RIG_CAPACITY,
    DEPOT_POS,
    FINALE_NEEDED_INSIDE,
    NOTICE_LIFETIME_SECONDS,
    STARTING_BANKROLL,
    STOMP_FINE,
    STOMP_PSI_SPIKE,
    TOWER_POS,
    VACUUM_BOUNTY,
    WISP_TOWER_PSI_JUMP,
)
from psychic_cleaners.core.drive import DriveSim
from psychic_cleaners.core.economy import Wallet, bust_fee
from psychic_cleaners.core.events import (
    AccountAccepted,
    AccountRejected,
    Arrived,
    BaitDeployed,
    BuildingStomped,
    BustMissed,
    BuyItem,
    CleanerSlimed,
    CleanersRestored,
    Command,
    CommandRejected,
    Continue,
    DeployBait,
    EnterAccount,
    Event,
    FinaleUnlocked,
    FinishShopping,
    GameLost,
    GameWon,
    GhostTrapped,
    GridPos,
    HauntCleared,
    ItemBought,
    LaySnare,
    MoveCleaner,
    NewGame,
    PlaceCleaner,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SelectVehicle,
    SetDestination,
    SnaresEmptied,
    SpringSnare,
    StartRun,
    Steer,
    StompTriggered,
    TravelStarted,
    VehicleSelected,
    WispCaptured,
    WispReachedTower,
)
from psychic_cleaners.core.finale import FinaleOutcome, FinaleSim
from psychic_cleaners.core.giant import MascotModel
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.core.pk import PsiModel
from psychic_cleaners.core.rng import Rng, make_rng

__all__ = ["Game", "SceneId", "new_game"]

# Scenes where the world clock, PSI, city, and mascot all tick.
_WORLD_SCENES: Final[tuple[SceneId, ...]] = (SceneId.MAP, SceneId.DRIVE, SceneId.BUST)

# A forged EnterAccount code with a bankroll below the cheapest vehicle would
# soft-lock the shop (no vehicle affordable, no way to reach MAP). Legitimate
# win codes are always > $10,000, so this only ever rejects forged codes.
_CHEAPEST_VEHICLE_PRICE: Final[int] = min(vehicle.price for vehicle in VEHICLES.values())


@dataclass
class Game:
    rng: Rng
    clock: GameClock = field(default_factory=GameClock)
    wallet: Wallet = field(default_factory=Wallet)
    scene: SceneId = SceneId.TITLE
    player_name: str = ""
    starting_bankroll: int = STARTING_BANKROLL
    loadout: Loadout | None = None
    drive: DriveSim | None = None
    bust: BustSim | None = None
    finale: FinaleSim | None = None
    result: str | None = None
    notice: str | None = None  # last rejection message, drawn by title/shop/map scenes
    notice_remaining: float = 0.0  # real seconds until `notice` auto-clears on MAP/DRIVE/BUST
    last_account_code: str | None = None  # endgame resolution: drawn by GameOverScene
    lose_reason: str | None = None  # endgame resolution: drawn by GameOverScene
    psi: PsiModel = field(default_factory=PsiModel)
    city: City = field(default_factory=City.new)
    mascot: MascotModel = field(default_factory=MascotModel)
    slimed: set[int] = field(default_factory=set)  # cleaner indices 0..2
    contained: int = 0  # ghosts held in the containment rig
    snares_full: int = 0
    position: GridPos = DEPOT_POS
    destination: GridPos | None = None
    finale_unlocked: bool = False

    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        # Capture the scene BEFORE dispatch: a mid-tick arrival that switches to
        # FINALE must not also finale-tick in the same call (Task 7 tick shape).
        scene = self.scene
        # 1. Command dispatch: per-command, scene-gated handlers.
        for command in commands:
            self._dispatch(command, events)
        # 2. scene/world ticking — AFTER the dispatch loop, on the current scene
        if self.scene in _WORLD_SCENES:
            world_events = self._world_tick(dt_seconds)
            events.extend(world_events)
            if self.scene is SceneId.DRIVE and self.drive is not None:
                events.extend(self._tick_drive(dt_seconds))
            if (
                self.scene is SceneId.BUST
                and self.bust is not None
                and self.bust.phase is BustPhase.ACTIVE
            ):
                events.extend(self.bust.tick(dt_seconds, self.rng))
            # (3) post-tick resolution: stomp translation FIRST (so a stomp's psi
            # spike lands before the one-shot finale-unlock check below), then wisp
            # PSI jumps, then one-shot finale unlock.
            events = self._resolve_stomps(events)
            for event in world_events:
                if isinstance(event, WispReachedTower):
                    self.psi.spike(float(WISP_TOWER_PSI_JUMP))
            if self.psi.at_max and not self.finale_unlocked:
                self.finale_unlocked = True
                events.append(FinaleUnlocked())
            if self.drive is not None and self.drive.arrived:
                assert self.destination is not None
                events.extend(self._arrive_at(self.destination))
            if self.bust is not None and self.bust.phase is BustPhase.RESOLVED:
                events.extend(self._resolve_bust())
            # Bankruptcy: the franchise folds only when it cannot field a snare by
            # ANY means — none free, none full (full snares are emptied back to
            # free at the Depot), and too broke to restock one at the Depot
            # (Task 19's MAP-scene BuyItem("snare") flow).
            if (
                self.scene in _WORLD_SCENES
                and self.loadout is not None
                and self.free_snares() == 0
                and self.snares_full == 0
                and self.wallet.balance < ITEMS["snare"].price
            ):
                reason = "no snares left — the franchise folds"
                self.result = "lost"
                self.lose_reason = reason
                events.append(GameLost(reason))
                self._change_scene(SceneId.GAME_OVER, events)
        if scene is SceneId.FINALE:
            events.extend(self._tick_finale(dt_seconds))
        return events

    def _world_tick(self, dt_seconds: float) -> list[Event]:
        self.clock.advance(dt_seconds)
        if self.notice is not None:
            # Notices set on TITLE/SHOP don't reach here (those scenes don't
            # world-tick); only MAP/DRIVE/BUST notices decay and expire.
            self.notice_remaining -= dt_seconds
            if self.notice_remaining <= 0:
                self.notice = None
                self.notice_remaining = 0.0
        self.psi.advance(dt_seconds, self.city.active_haunts())
        events = self.city.tick(dt_seconds, self.psi.value, self.rng)
        has_sensor = self.loadout.has("sensor") if self.loadout is not None else False
        events.extend(self.mascot.tick(dt_seconds, self.psi.value, has_sensor, self.rng))
        return events

    def _set_notice(self, reason: str) -> None:
        """Arm a rejection message with its on-screen lifetime.

        TITLE/SHOP notices are set through this same helper, but those scenes
        never call `_world_tick`, so `notice_remaining` there just sits unused
        until the next assignment or a scene change zeroes it.
        """
        self.notice = reason
        self.notice_remaining = NOTICE_LIFETIME_SECONDS

    def _tick_drive(self, dt_seconds: float) -> list[Event]:
        assert self.drive is not None
        events: list[Event] = []
        for event in self.drive.tick(dt_seconds, self.rng):
            if isinstance(event, WispCaptured):
                self.wallet.earn(VACUUM_BOUNTY)
                if self.city.wisps:
                    self.city.wisps.pop(0)  # one road catch thins the city population
            events.append(event)
        return events

    def _resolve_stomps(self, events: list[Event]) -> list[Event]:
        """Post-tick: translate internal StompTriggered into world consequences."""
        resolved: list[Event] = []
        for event in events:
            if isinstance(event, StompTriggered):
                pos = self.rng.choice(self.city.stompable_positions())
                fine = self.wallet.fine(STOMP_FINE)
                self.psi.spike(STOMP_PSI_SPIKE)
                resolved.append(BuildingStomped(pos, fine))
            else:
                resolved.append(event)
        return resolved

    def _handle_deploy_bait(self) -> list[Event]:
        """Charges are checked FIRST so a chargeless press never cancels the alert."""
        if self.loadout is None or self.loadout.bait_charges <= 0:
            return []
        if self.mascot.deploy_bait() and self.loadout.use_bait():
            return [BaitDeployed()]
        return []

    def _dispatch(self, command: Command, events: list[Event]) -> None:
        # Unknown or invalid commands for the current scene are ignored silently.
        if isinstance(command, DeployBait) and self.scene in _WORLD_SCENES:
            events.extend(self._handle_deploy_bait())
        elif self.scene is SceneId.TITLE:
            events.extend(self._handle_title(command))
        elif self.scene is SceneId.GAME_OVER and isinstance(command, Continue):
            self._reset()
            self._change_scene(SceneId.TITLE, events)
        elif self.scene is SceneId.SHOP:
            self._handle_shop(command, events)
        elif self.scene is SceneId.MAP:
            events.extend(self._handle_map(command))
        elif self.scene is SceneId.DRIVE and isinstance(command, Steer) and self.drive is not None:
            self.drive.steer(command.delta)
        elif self.scene is SceneId.FINALE:
            if isinstance(command, StartRun) and self.finale is not None:
                self.finale.start_run()
        elif self.scene is SceneId.BUST and self.bust is not None:
            bust = self.bust
            if isinstance(command, MoveCleaner):
                bust.move(command.dx)
            elif (
                isinstance(command, PlaceCleaner)
                and bust.phase
                in (
                    BustPhase.POSITION_LEFT,
                    BustPhase.POSITION_RIGHT,
                )
            ) or (isinstance(command, LaySnare) and bust.phase is BustPhase.SNARE):
                bust.place()
            elif isinstance(command, SpringSnare):
                if bust.phase is BustPhase.ACTIVE:
                    bust.spring()
                else:
                    events.append(CommandRejected("no snare laid"))

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
                self._set_notice("invalid account code")
                return [AccountRejected("invalid account code")]
            if bankroll < _CHEAPEST_VEHICLE_PRICE:
                # A forged code with a starvation bankroll would otherwise strand
                # the player in SHOP unable to afford any vehicle. Legitimate win
                # codes are always > $10,000, so only forged codes hit this.
                self._set_notice("account too depleted")
                return [AccountRejected("account too depleted")]
            self.player_name = command.name
            self.wallet.balance = bankroll
            self.starting_bankroll = bankroll
            self.notice = None
            self.notice_remaining = 0.0
            self.scene = SceneId.SHOP
            return [AccountAccepted(command.name, bankroll), SceneChanged(SceneId.SHOP)]
        return []

    def _handle_shop(self, command: Command, events: list[Event]) -> None:
        match command:
            case SelectVehicle(vehicle_id=vehicle_id):
                vehicle = VEHICLES[vehicle_id]
                if self.loadout is not None:
                    reason = "vehicle already chosen"
                    self._set_notice(reason)
                    events.append(PurchaseRejected(reason))
                elif not self.wallet.can_afford(vehicle.price):
                    reason = "cannot afford"
                    self._set_notice(reason)
                    events.append(PurchaseRejected(reason))
                else:
                    self.wallet.spend(vehicle.price)
                    self.loadout = Loadout(vehicle=vehicle)
                    self.notice = None
                    self.notice_remaining = 0.0
                    events.append(VehicleSelected(vehicle_id))
            case BuyItem(item_id=item_id):
                if self.loadout is None:
                    reason = "choose a vehicle first"
                    self._set_notice(reason)
                    events.append(PurchaseRejected(reason))
                elif not self.wallet.can_afford(ITEMS[item_id].price):
                    reason = "cannot afford"
                    self._set_notice(reason)
                    events.append(PurchaseRejected(reason))
                elif not self.loadout.can_add(item_id):
                    reason = "no room in vehicle"
                    self._set_notice(reason)
                    events.append(PurchaseRejected(reason))
                else:
                    self.wallet.spend(ITEMS[item_id].price)
                    self.loadout.add(item_id)
                    self.notice = None
                    self.notice_remaining = 0.0
                    events.append(ItemBought(item_id))
            case FinishShopping():
                if self.loadout is not None:
                    self._change_scene(SceneId.MAP, events)

    def _handle_map(self, command: Command) -> list[Event]:
        if isinstance(command, SetDestination):
            return self._set_destination(command.pos)
        if isinstance(command, BuyItem):
            return self._depot_restock(command.item_id)
        return []

    def _set_destination(self, pos: GridPos) -> list[Event]:
        if pos == self.position:
            return self._arrive_at(pos)
        assert self.loadout is not None  # MAP is only reachable with a vehicle
        distance = self.city.distance(self.position, pos)
        self.destination = pos
        self.drive = DriveSim(
            distance_total=distance,
            speed=self.loadout.vehicle.speed,
            has_vacuum=self.loadout.has("vacuum"),
            has_lens=self.loadout.has("lens"),
        )
        events: list[Event] = [TravelStarted(dest=pos, distance=distance)]
        self._change_scene(SceneId.DRIVE, events)
        return events

    def _depot_restock(self, item_id: str) -> list[Event]:
        """Mid-game snare restock: only "snare", and only at the Depot."""
        if item_id != "snare" or self.position != DEPOT_POS:
            self._set_notice("snares only, at the Depot")
            return [PurchaseRejected("snares only, at the Depot")]
        if self.loadout is None:  # defensive: MAP is unreachable without a vehicle
            self._set_notice("choose a vehicle first")
            return [PurchaseRejected("choose a vehicle first")]
        if not self.wallet.can_afford(ITEMS["snare"].price):
            self._set_notice("cannot afford")
            return [PurchaseRejected("cannot afford")]
        if not self.loadout.can_add("snare"):
            self._set_notice("no room in vehicle")
            return [PurchaseRejected("no room in vehicle")]
        self.wallet.spend(ITEMS["snare"].price)
        self.loadout.add("snare")
        self.notice = None
        self.notice_remaining = 0.0
        return [ItemBought("snare")]

    def _arrive_at(self, pos: GridPos) -> list[Event]:
        """Arrival routing: an if/elif chain ending in an `else` that routes to MAP.

        Later tasks insert their `elif` branches BETWEEN the depot branch and the
        final `else` (tower before haunted). Every arrival appends Arrived(pos).
        """
        self.position = pos
        self.destination = None
        self.drive = None
        events: list[Event] = [Arrived(pos=pos)]
        if pos == DEPOT_POS:
            self.snares_full = 0
            self.contained = 0
            self.slimed.clear()
            events.append(SnaresEmptied())
            events.append(CleanersRestored())
            if self.scene is not SceneId.MAP:
                self._change_scene(SceneId.MAP, events)
        elif pos == TOWER_POS and self.finale_unlocked:
            self._arrive_at_tower(events)
        elif (
            pos in self.city.haunted_positions()
            and self.free_snares() > 0
            and self.able_cleaners() >= 2
        ):
            self.bust = BustSim()
            self._change_scene(SceneId.BUST, events)
        elif pos in self.city.haunted_positions():
            # Haunted, but the crew can't field a bust (no free snare, or
            # fewer than two able cleaners): turn away with an explanation
            # instead of silently dropping the player back on MAP.
            if self.scene is not SceneId.MAP:
                self._change_scene(SceneId.MAP, events)
            if self.free_snares() == 0:
                reason = "no free snare — buy or empty one at the Depot"
            else:
                reason = "cleaners are slimed — restore them at the Depot"
            self._set_notice(reason)
            events.append(CommandRejected(reason))
        else:
            if self.scene is not SceneId.MAP:
                self._change_scene(SceneId.MAP, events)
        return events

    def _arrive_at_tower(self, events: list[Event]) -> None:
        """Tower arrival with the finale unlocked: enter the door run or turn away."""
        if self.able_cleaners() >= FINALE_NEEDED_INSIDE:
            self.finale = FinaleSim(able_cleaners=self.able_cleaners())
            self._change_scene(SceneId.FINALE, events)
        else:
            # An under-crewed team is turned away, not ended: restoring
            # slimed cleaners at the Depot and returning is always possible.
            if self.scene is not SceneId.MAP:
                self._change_scene(SceneId.MAP, events)
            reason = "not enough able cleaners — restore them at the Depot"
            self._set_notice(reason)
            events.append(CommandRejected(reason))

    def _tick_finale(self, dt_seconds: float) -> list[Event]:
        """FINALE scene ticking and resolution: the world is frozen."""
        events: list[Event] = []
        if self.finale is None:
            return events
        # RunnerSquashed passes through untouched: a squashed runner is a
        # finale-local casualty and must NOT be added to self.slimed.
        events.extend(self.finale.tick(dt_seconds))
        outcome = self.finale.outcome
        if outcome is FinaleOutcome.WON:
            if self.wallet.balance > self.starting_bankroll:
                code = encode_account(self.player_name, self.wallet.balance)
                self.result = "won"
                self.last_account_code = code
                events.append(GameWon(code))
            else:
                reason = "the franchise never turned a profit"
                self.result = "lost"
                self.lose_reason = reason
                events.append(GameLost(reason))
        elif outcome is FinaleOutcome.LOST:
            reason = "the Tower claimed the city"
            self.result = "lost"
            self.lose_reason = reason
            events.append(GameLost(reason))
        if outcome is not None:
            self.finale = None
            self._change_scene(SceneId.GAME_OVER, events)
        return events

    def _resolve_bust(self) -> list[Event]:
        bust = self.bust
        loadout = self.loadout
        assert bust is not None and loadout is not None
        events: list[Event] = []
        # The two cleaners fielded in this bust are the two lowest unslimed indices;
        # bust.slimed_side 0/1 maps onto them in order.
        unslimed = sorted(set(range(CLEANER_COUNT)) - self.slimed)
        if bust.outcome is BustOutcome.CAUGHT:
            if loadout.has("rig") and self.contained < CONTAINMENT_RIG_CAPACITY:
                self.contained += 1
            else:
                self.snares_full += 1
            fee = bust_fee(self.psi.value)
            self.wallet.earn(fee)
            events.append(GhostTrapped(fee))
            self.city.clear_haunt(self.position)
            events.append(HauntCleared(self.position))
        elif bust.outcome is BustOutcome.MISSED:
            # Wasted snare. Direct mutation per contract; the key exists because
            # entering a bust required free_snares() > 0.
            loadout.counts["snare"] -= 1
            events.append(BustMissed())
        elif bust.outcome is BustOutcome.SLIMED:
            loadout.counts["snare"] -= 1
            side = bust.slimed_side if bust.slimed_side is not None else 0
            idx = unslimed[side]
            self.slimed.add(idx)
            events.append(CleanerSlimed(idx))
        elif bust.outcome is BustOutcome.BACKFIRE:
            loadout.counts["snare"] -= 1
            for idx in unslimed[:2]:
                self.slimed.add(idx)
                events.append(CleanerSlimed(idx))
        self.bust = None
        self._change_scene(SceneId.MAP, events)
        return events

    def free_snares(self) -> int:
        if self.loadout is None:
            return 0
        return self.loadout.count("snare") - self.snares_full

    def able_cleaners(self) -> int:
        return CLEANER_COUNT - len(self.slimed)

    def _change_scene(self, s: SceneId, events: list[Event]) -> None:
        # Notices are scene-local (drawn only by TITLE/SHOP/MAP); a rejection
        # message must not outlive the scene it was raised on.
        self.notice = None
        self.notice_remaining = 0.0
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
        self.last_account_code = None
        self.lose_reason = None
        self.wallet = Wallet()
        self.loadout = None
        self.drive = None
        self.bust = None
        self.finale = None
        self.notice = None
        self.notice_remaining = 0.0
        self.psi = PsiModel()
        self.city = City.new()
        self.mascot = MascotModel()
        self.slimed = set()
        self.contained = 0
        self.snares_full = 0
        self.position = DEPOT_POS
        self.destination = None
        self.finale_unlocked = False


def new_game(seed: int) -> Game:
    return Game(rng=make_rng(seed))

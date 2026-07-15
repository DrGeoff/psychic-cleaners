"""Scripted playtest of Psychic Cleaners: drives the real App via posted pygame
events, verifies the economy with an independent ledger, and screenshots scenes."""

import copy
import os
import sys
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
# SDL turns SIGTERM into an SDL_QUIT event these scripts never poll; without
# this, `timeout N playtest.py` cannot kill a wedged run.
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")

import pygame

from psychic_cleaners.core.bust import BustPhase
from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.constants import (
    DEPOT_POS,
    MAX_BANKROLL,
    TOWER_POS,
)
from psychic_cleaners.core.events import (
    AccountRejected,
    Arrived,
    BaitDeployed,
    BuildingStomped,
    BustMissed,
    CleanersRestored,
    CommandRejected,
    FinaleUnlocked,
    GameLost,
    GameWon,
    GhostTrapped,
    HauntCleared,
    ItemBought,
    MascotAlert,
    PurchaseRejected,
    RunnerEntered,
    RunnerSquashed,
    SceneId,
    SnaresEmptied,
    TravelStarted,
    VehicleSelected,
    WispCaptured,
)
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.shell.app import App

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(SHOTS, exist_ok=True)

PASS = 0
FAIL = 0


def check(cond: bool, label: str, detail: str = "") -> bool:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {label}")
    else:
        FAIL += 1
        print(f"[FAIL] {label}  {detail}")
    return cond


class FakePressed:
    def __init__(self, held: set[int]) -> None:
        self.held = held

    def __getitem__(self, key: int) -> bool:
        return key in self.held


class Driver:
    def __init__(self, seed: int) -> None:
        self.app = App(seed=seed)
        pygame.event.clear()  # drop leftovers from any earlier session in this process
        self.game = self.app.game
        self.held: set[int] = set()
        pygame.key.get_pressed = lambda: FakePressed(self.held)  # type: ignore[assignment]
        self.expected_balance = self.game.wallet.balance
        self.log: list = []
        self.frame_events: list = []
        orig_tick = self.game.tick

        def tick(cmds, dt):
            evs = orig_tick(cmds, dt)
            self.frame_events = evs
            self.log.extend(evs)
            self._ledger(evs)
            return evs

        self.game.tick = tick  # type: ignore[method-assign]

    # --- ledger -----------------------------------------------------------
    def _ledger(self, evs) -> None:
        for e in evs:
            if isinstance(e, VehicleSelected):
                self.expected_balance -= VEHICLES[e.vehicle_id].price
            elif isinstance(e, ItemBought):
                self.expected_balance -= ITEMS[e.item_id].price
            elif isinstance(e, GhostTrapped):
                self.expected_balance = min(self.expected_balance + e.fee, MAX_BANKROLL)
            elif isinstance(e, WispCaptured):
                self.expected_balance = min(self.expected_balance + e.bounty, MAX_BANKROLL)
            elif isinstance(e, BuildingStomped):
                self.expected_balance -= e.fine
        if self.game.wallet.balance != self.expected_balance:
            check(
                False,
                "LEDGER: balance matches expectations",
                f"wallet={self.game.wallet.balance} expected={self.expected_balance} "
                f"after events {evs}",
            )
            # resync so one failure doesn't cascade
            self.expected_balance = self.game.wallet.balance

    # --- input helpers ----------------------------------------------------
    def key(self, k: int) -> None:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": k, "mod": 0}))

    def type_text(self, s: str) -> None:
        for ch in s:
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, {"text": ch}))

    def step(self, n: int = 1, dt: float = 1 / 60) -> None:
        for _ in range(n):
            self.app.step(dt)

    def shot(self, name: str) -> None:
        pygame.image.save(self.app.logical, os.path.join(SHOTS, f"{name}.png"))
        print(f"       [shot] {name}.png")

    def events_of(self, cls) -> list:
        return [e for e in self.log if isinstance(e, cls)]

    def wait_for(self, pred, max_steps: int, dt: float = 1 / 60, label: str = "") -> bool:
        for _ in range(max_steps):
            self.step(dt=dt)
            if pred():
                return True
        print(f"       [timeout] wait_for {label} after {max_steps} steps")
        return False


def scene_obj(d: Driver):
    from psychic_cleaners.shell.app import SCENES

    return SCENES[d.game.scene]


# ---------------------------------------------------------------------------
def phase_title(d: Driver) -> None:
    print("== TITLE ==")
    d.step(3)
    d.shot("01-title")
    # Enter with empty name does nothing
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.scene is SceneId.TITLE, "TITLE: Enter with empty name stays on title")
    # type name, test backspace
    d.type_text("GEOFFX")
    d.step()
    d.key(pygame.K_BACKSPACE)
    d.step()
    # tab to code field, enter bad code
    d.key(pygame.K_TAB)
    d.step()
    d.type_text("AAAAAAA")
    d.step()
    d.key(pygame.K_RETURN)
    d.step()
    rejected = d.events_of(AccountRejected)
    check(bool(rejected), "TITLE: bad account code rejected", f"log={d.log[-5:]}")
    check(d.game.scene is SceneId.TITLE, "TITLE: still on title after rejection")
    check(d.game.notice is not None, "TITLE: rejection notice set for display")
    d.step(2)
    d.shot("02-title-rejected")
    # clear the code, start a new franchise
    for _ in range(7):
        d.key(pygame.K_BACKSPACE)
    d.step()
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.scene is SceneId.SHOP, "TITLE: Enter with name+blank code starts new game")
    check(d.game.player_name == "GEOFF", f"TITLE: player name kept ({d.game.player_name!r})")


ROWS = [*VEHICLES.keys(), *ITEMS.keys()]  # shop display order


def shop_move_to(d: Driver, row_id: str) -> None:
    target = ROWS.index(row_id)
    cur = scene_obj(d).cursor
    delta = target - cur
    key = pygame.K_DOWN if delta > 0 else pygame.K_UP
    for _ in range(abs(delta)):
        d.key(key)
    d.step()


def phase_shop(d: Driver) -> None:
    print("== SHOP ==")
    d.step(2)
    d.shot("03-shop")
    # buying an item before a vehicle must be rejected
    shop_move_to(d, "detector")
    d.key(pygame.K_RETURN)
    d.step()
    rej = d.events_of(PurchaseRejected)
    check(
        bool(rej) and rej[-1].reason == "choose a vehicle first",
        "SHOP: item before vehicle rejected",
        f"{rej[-1:]}",
    )
    # F before vehicle: should not leave the shop
    d.key(pygame.K_f)
    d.step()
    check(d.game.scene is SceneId.SHOP, "SHOP: F without vehicle stays in shop")
    # cursor wrap: Up from top lands on last row
    shop_move_to(d, "compact")
    d.key(pygame.K_UP)
    d.step()
    check(scene_obj(d).cursor == len(ROWS) - 1, "SHOP: cursor wraps upward")
    d.key(pygame.K_DOWN)
    d.step()
    # buy the compact
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.loadout is not None, "SHOP: compact purchased")
    # second vehicle rejected
    shop_move_to(d, "hearse")
    d.key(pygame.K_RETURN)
    d.step()
    rej = d.events_of(PurchaseRejected)
    check(
        rej[-1].reason == "vehicle already chosen",
        "SHOP: second vehicle rejected",
        f"{rej[-1:]}",
    )
    # gear: detector, lens, sensor, bait, snare, vacuum  (6 of 7 slots)
    for item in ("detector", "lens", "sensor", "bait", "snare", "vacuum"):
        shop_move_to(d, item)
        d.key(pygame.K_RETURN)
        d.step()
    lo = d.game.loadout
    check(
        lo is not None and lo.slots_used() == 6,
        "SHOP: six slots used",
        f"slots={lo.slots_used() if lo else None}",
    )
    # rig: can't afford (8000 > balance)
    shop_move_to(d, "rig")
    d.key(pygame.K_RETURN)
    d.step()
    rej = d.events_of(PurchaseRejected)
    check(rej[-1].reason == "cannot afford", "SHOP: unaffordable rig rejected", f"{rej[-1:]}")
    expected = 10_000 - 2000 - 400 - 800 - 800 - 400 - 600 - 500
    check(
        d.game.wallet.balance == expected,
        f"SHOP: balance after shopping == {expected}",
        f"actual {d.game.wallet.balance}",
    )
    d.step(2)
    d.shot("04-shop-loaded")
    d.key(pygame.K_f)
    d.step()
    check(d.game.scene is SceneId.MAP, "SHOP: F finishes shopping -> MAP")


def map_move_cursor(d: Driver, dest: tuple[int, int]) -> None:
    cur = scene_obj(d).cursor
    dx = dest[0] - cur[0]
    dy = dest[1] - cur[1]
    for _ in range(abs(dx)):
        d.key(pygame.K_RIGHT if dx > 0 else pygame.K_LEFT)
    for _ in range(abs(dy)):
        d.key(pygame.K_DOWN if dy > 0 else pygame.K_UP)
    d.step()
    assert scene_obj(d).cursor == dest, (scene_obj(d).cursor, dest)


def phase_map_depot(d: Driver) -> None:
    print("== MAP / DEPOT ==")
    d.step(2)
    d.shot("05-map")
    # restock a snare at the depot (S)
    before = d.game.wallet.balance
    d.key(pygame.K_s)
    d.step()
    check(
        d.game.loadout is not None and d.game.loadout.count("snare") == 2,
        "MAP: depot snare restock works",
        f"snares={d.game.loadout.count('snare') if d.game.loadout else None}",
    )
    check(d.game.wallet.balance == before - 600, "MAP: snare restock charged $600")
    # capacity now full: another S must be rejected with a notice
    d.key(pygame.K_s)
    d.step()
    rej = d.events_of(PurchaseRejected)
    check(rej[-1].reason == "no room in vehicle", "MAP: full vehicle restock rejected")
    check(d.game.notice == "no room in vehicle", "MAP: rejection notice displayed")
    d.step(2)
    d.shot("06-map-notice")
    # cursor clamps at edges
    for _ in range(4):
        d.key(pygame.K_LEFT)
    for _ in range(8):
        d.key(pygame.K_DOWN)
    d.step()
    check(scene_obj(d).cursor == (0, 5), "MAP: cursor clamps at grid edges")


def phase_drive_to_haunt(d: Driver) -> None:
    print("== DRIVE ==")
    ok = d.wait_for(lambda: d.game.city.active_haunts() > 0, 2400, dt=0.25, label="first haunt")
    check(ok, "MAP: a haunting eventually spawns")
    if not ok:
        return
    target = d.game.city.haunted_positions()[0]
    print(f"       haunt at {target}, psi={d.game.psi.value}")
    d.step(2)
    d.shot("07-map-haunt")
    map_move_cursor(d, target)
    d.key(pygame.K_RETURN)
    d.step()
    check(bool(d.events_of(TravelStarted)), "MAP: Enter starts travel")
    check(d.game.scene is SceneId.DRIVE, "MAP: scene switched to DRIVE")
    # drive: steer toward catchable wisps each frame
    catches_before = len(d.events_of(WispCaptured))
    shot_taken = False
    steps = 0
    while d.game.scene is SceneId.DRIVE and steps < 60 * 120:
        drv = d.game.drive
        if drv is not None:
            ahead = [w for w in drv.wisps if w.x > 90]
            if ahead:
                nearest = min(ahead, key=lambda w: w.x)
                if nearest.lane < drv.lane:
                    d.key(pygame.K_UP)
                elif nearest.lane > drv.lane:
                    d.key(pygame.K_DOWN)
            if not shot_taken and drv.wisps and drv.distance_done > 100:
                d.step(2)
                d.shot("08-drive")
                shot_taken = True
        d.step()
        steps += 1
    if not shot_taken:
        d.shot("08-drive")
    catches = len(d.events_of(WispCaptured)) - catches_before
    print(f"       wisps vacuumed on the road: {catches}")
    check(d.game.scene is SceneId.BUST, "DRIVE: arrival at haunt enters BUST")
    arr = d.events_of(Arrived)
    check(bool(arr) and arr[-1].pos == d.game.position, "DRIVE: Arrived event carries position")


def run_bust(
    d: Driver,
    *,
    left: float,
    right: float,
    snare: float | None,
    spring_policy: str,
    shot_prefix: str | None = None,
) -> None:
    """Drive one bust. spring_policy: 'timed' | 'immediate' | 'never'."""
    bust = d.game.bust
    assert bust is not None

    def move_cursor_to(x: float) -> None:
        for _ in range(60 * 10):
            b = d.game.bust
            if b is None:
                return
            diff = x - b.cursor_x
            if abs(diff) <= 3:
                d.held.clear()
                d.step()
                return
            d.held.clear()
            d.held.add(pygame.K_RIGHT if diff > 0 else pygame.K_LEFT)
            d.step()
        d.held.clear()

    if shot_prefix:
        d.step(2)
        d.shot(f"{shot_prefix}-position")
    move_cursor_to(left)
    d.key(pygame.K_RETURN)
    d.step()
    move_cursor_to(right)
    d.key(pygame.K_RETURN)
    d.step()
    b = d.game.bust
    check(
        b is not None and b.phase is BustPhase.SNARE,
        "BUST: two placements reach SNARE phase",
        f"phase={b.phase if b else None}",
    )
    if snare is not None:
        move_cursor_to(snare)
    d.key(pygame.K_RETURN)  # lay snare
    d.step()
    b = d.game.bust
    check(
        b is not None and b.phase is BustPhase.ACTIVE,
        "BUST: snare laid -> ACTIVE",
        f"phase={b.phase if b else None}",
    )
    if shot_prefix:
        d.step(2)
        d.shot(f"{shot_prefix}-active")
    if spring_policy == "immediate":
        d.key(pygame.K_SPACE)
        d.step()
        return
    steps = 0
    while d.game.bust is not None and steps < 60 * 90:
        b = d.game.bust
        if (
            spring_policy == "timed"
            and b.phase is BustPhase.ACTIVE
            and b.snare_x is not None
            and abs(b.ghost_x - b.snare_x) <= 20
            and b.ghost_y >= 285
        ):
            d.key(pygame.K_SPACE)
        d.step()
        steps += 1


def phase_bust(d: Driver) -> None:
    print("== BUST ==")
    psi_at_bust = d.game.psi.value
    snares_before = d.game.loadout.count("snare") if d.game.loadout else 0
    balance_before = d.game.wallet.balance
    haunt_pos = d.game.position
    run_bust(d, left=250.0, right=390.0, snare=320.0, spring_policy="timed", shot_prefix="09-bust")
    trapped = d.events_of(GhostTrapped)
    if check(bool(trapped), "BUST: ghost caught with the timed spring", f"log tail={d.log[-6:]}"):
        fee = trapped[-1].fee
        expected_fee = 300 + 100 * (psi_at_bust // 1000)
        check(
            abs(fee - expected_fee) <= 100,
            f"BUST: fee {fee} ~= 300+100*(psi//1000) ({expected_fee})",
            f"psi_at_bust={psi_at_bust}",
        )
        check(
            d.game.wallet.balance == balance_before + fee,
            "BUST: fee credited to wallet",
        )
        check(d.game.snares_full == 1, "BUST: catch fills one snare")
        check(
            d.game.loadout is not None and d.game.loadout.count("snare") == snares_before,
            "BUST: catch does not consume the snare item",
        )
        check(
            haunt_pos not in d.game.city.haunted_positions(),
            "BUST: haunting cleared from the city",
        )
        check(bool(d.events_of(HauntCleared)), "BUST: HauntCleared event emitted")
    check(d.game.scene is SceneId.MAP, "BUST: resolution returns to MAP")
    check(
        d.game.free_snares() == snares_before - 1,
        "BUST: free snares = owned - full",
        f"free={d.game.free_snares()}",
    )


def phase_bust_miss(d: Driver) -> None:
    print("== BUST (deliberate miss) ==")
    ok = d.wait_for(lambda: d.game.city.active_haunts() > 0, 2400, dt=0.25, label="haunt 2")
    if not ok:
        return
    target = d.game.city.haunted_positions()[0]
    map_move_cursor(d, target)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(lambda: d.game.scene is not SceneId.DRIVE, 60 * 120, label="arrive 2")
    if d.game.scene is not SceneId.BUST:
        print(f"       [note] expected BUST, got {d.game.scene} (notice={d.game.notice})")
        return
    snares_before = d.game.loadout.count("snare") if d.game.loadout else 0
    # springing before ACTIVE must be rejected
    d.key(pygame.K_SPACE)
    d.step()
    rej = [e for e in d.events_of(CommandRejected) if e.reason == "no snare laid"]
    check(bool(rej), "BUST: Space before snare laid -> 'no snare laid'")
    run_bust(d, left=120.0, right=520.0, snare=320.0, spring_policy="immediate")
    d.step(5)
    check(bool(d.events_of(BustMissed)), "BUST: immediate spring misses")
    check(
        d.game.loadout is not None and d.game.loadout.count("snare") == snares_before - 1,
        "BUST: miss wastes the snare",
    )
    check(d.game.scene is SceneId.MAP, "BUST: miss returns to MAP")


def phase_mascot(d: Driver) -> None:
    print("== MASCOT ==")
    # wait for an alert (sensor owned); ignore it -> stomp + fine
    ok = d.wait_for(
        lambda: d.game.mascot.state is MascotState.ALERT, 4800, dt=0.25, label="alert 1"
    )
    if not ok:
        print("       [note] no mascot alert within budget; skipping mascot checks")
        return
    check(bool(d.events_of(MascotAlert)), "MASCOT: sensor turns rampage into an alert")
    d.step(2)
    d.shot("10-mascot-alert")
    balance_before = d.game.wallet.balance
    stomps_before = len(d.events_of(BuildingStomped))
    d.wait_for(
        lambda: len(d.events_of(BuildingStomped)) > stomps_before,
        400,
        dt=0.25,
        label="stomp",
    )
    stomps = d.events_of(BuildingStomped)
    if check(len(stomps) > stomps_before, "MASCOT: ignored alert becomes a stomp"):
        fine = stomps[-1].fine
        check(
            fine == min(4000, balance_before),
            f"MASCOT: fine is min($4000, balance) = {fine}",
            f"balance_before={balance_before}",
        )
    # next alert: deploy bait with B
    ok = d.wait_for(
        lambda: d.game.mascot.state is MascotState.ALERT, 9600, dt=0.25, label="alert 2"
    )
    if ok:
        charges_before = d.game.loadout.bait_charges if d.game.loadout else 0
        d.key(pygame.K_b)
        d.step()
        check(bool(d.events_of(BaitDeployed)), "MASCOT: B deploys bait on alert")
        check(
            d.game.loadout is not None and d.game.loadout.bait_charges == charges_before - 1,
            "MASCOT: bait charge consumed",
        )
        check(
            d.game.mascot.state is MascotState.CALM,
            "MASCOT: bait calms the mascot (no stomp)",
        )


def phase_depot_return(d: Driver) -> None:
    print("== DEPOT RETURN ==")
    map_move_cursor(d, DEPOT_POS)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(
        lambda: d.game.scene is SceneId.MAP and d.game.drive is None,
        60 * 240,
        label="drive to depot",
    )
    check(d.game.position == DEPOT_POS, "DEPOT: arrived")
    check(bool(d.events_of(SnaresEmptied)), "DEPOT: full snares emptied")
    check(d.game.snares_full == 0, "DEPOT: snares_full reset")
    check(bool(d.events_of(CleanersRestored)), "DEPOT: cleaners restored event")
    check(len(d.game.slimed) == 0, "DEPOT: slimed cleaners restored")


def phase_finale(d: Driver, inject_profit: bool) -> None:
    print(f"== FINALE (inject_profit={inject_profit}) ==")
    ok = d.wait_for(lambda: d.game.finale_unlocked, 40000, dt=0.5, label="psi max")
    check(ok, "PSI: reaches max and unlocks the finale")
    check(bool(d.events_of(FinaleUnlocked)), "PSI: FinaleUnlocked emitted once")
    check(
        len(d.events_of(FinaleUnlocked)) == 1,
        "PSI: FinaleUnlocked emitted exactly once",
        f"count={len(d.events_of(FinaleUnlocked))}",
    )
    if not ok:
        return
    print(f"       psi={d.game.psi.value} balance={d.game.wallet.balance}")
    if inject_profit:
        # state injection to exercise the win path + account code
        d.game.wallet.balance = 60_000
        d.expected_balance = 60_000
    d.step(2)
    d.shot("11-map-psi-max")
    map_move_cursor(d, TOWER_POS)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(lambda: d.game.scene not in (SceneId.DRIVE,), 60 * 240, label="to tower")
    check(
        d.game.scene is SceneId.FINALE,
        "FINALE: tower entered",
        f"scene={d.game.scene} notice={d.game.notice}",
    )
    if d.game.scene is not SceneId.FINALE:
        return
    d.step(2)
    d.shot("12-finale")
    # send runners only when a simulated clone says the run survives
    steps = 0
    shot_runner = False
    while d.game.scene is SceneId.FINALE and steps < 60 * 180:
        sim = d.game.finale
        if sim is not None and sim.runner_x is None and sim.remaining_outside > 0:
            clone = copy.deepcopy(sim)
            clone.start_run()
            for _ in range(60 * 6):
                clone.tick(1 / 60)
                if clone.runner_x is None:
                    break
            if clone.inside > sim.inside:
                d.key(pygame.K_SPACE)
        if not shot_runner and sim is not None and sim.runner_x is not None:
            d.step(2)
            d.shot("13-finale-runner")
            shot_runner = True
        d.step()
        steps += 1
    check(d.game.scene is SceneId.GAME_OVER, "FINALE: resolves to GAME_OVER")
    entered = d.events_of(RunnerEntered)
    squashed = d.events_of(RunnerSquashed)
    print(f"       runners inside={len(entered)} squashed={len(squashed)}")
    d.step(2)
    d.shot("14-gameover")
    if inject_profit:
        won = d.events_of(GameWon)
        if check(bool(won), "FINALE: profitable finale wins", f"log tail={d.log[-6:]}"):
            code = won[-1].account_code
            print(f"       account code: {code}")
            from psychic_cleaners.core.codec import decode_account

            check(
                decode_account("GEOFF", code) == d.game.wallet.balance,
                "CODEC: game-over code decodes to final balance",
            )
            d.game._issued_code = code  # stash for the restore phase
    else:
        lost = d.events_of(GameLost)
        check(bool(lost), "FINALE: unprofitable finale loses")


def phase_restart_and_restore(d: Driver) -> None:
    print("== RESTART / ACCOUNT RESTORE ==")
    code = getattr(d.game, "_issued_code", None)
    final_balance = d.game.wallet.balance
    # The Continue tick resets the wallet to $10,000; tell the ledger before
    # stepping or it flags the intended reset as a mismatch.
    d.expected_balance = 10_000
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.scene is SceneId.TITLE, "GAME_OVER: Enter returns to title")
    check(d.game.wallet.balance == 10_000, "RESET: wallet back to $10,000")
    check(d.game.loadout is None, "RESET: loadout cleared")
    d.step(2)
    d.shot("15-title-after-reset")
    if code is None:
        return
    d.type_text("GEOFF")
    d.key(pygame.K_TAB)
    d.step()
    d.type_text(code)
    # AccountAccepted restores the bankroll on the same tick as the Enter.
    d.expected_balance = final_balance
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.scene is SceneId.SHOP, "RESTORE: valid code accepted -> SHOP")
    check(
        d.game.wallet.balance == final_balance,
        f"RESTORE: bankroll {final_balance} carried over",
        f"actual={d.game.wallet.balance}",
    )
    d.expected_balance = d.game.wallet.balance


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    inject = "--inject-profit" in sys.argv
    print(f"seed={seed} inject_profit={inject}")
    d = Driver(seed)
    try:
        phase_title(d)
        phase_shop(d)
        phase_map_depot(d)
        phase_drive_to_haunt(d)
        phase_bust(d)
        phase_bust_miss(d)
        phase_mascot(d)
        phase_depot_return(d)
        phase_finale(d, inject_profit=inject)
        phase_restart_and_restore(d)
    except Exception:
        traceback.print_exc()
        d.shot("99-crash")
        check(False, "playthrough completed without crashing")
    finally:
        seen = sorted({type(e).__name__ for e in d.log})
        print(f"\nevent types seen: {', '.join(seen)}")
        print(f"\nRESULT: {PASS} passed, {FAIL} failed")
        pygame.quit()
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()

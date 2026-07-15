"""Targeted scenario playtests: failure outcomes, turn-aways, rig, fold, codec,
and pixel-level visual checks that the main playthrough couldn't stage."""

import copy
import os
import random
import sys
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")  # keep `timeout` able to kill us

import pygame
from playtest import Driver, check, map_move_cursor, run_bust, shop_move_to

from psychic_cleaners.core.bust import BustOutcome, BustPhase, BustSim
from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.codec import (
    ALPHABET,
    AccountCodeError,
    decode_account,
    encode_account,
)
from psychic_cleaners.core.constants import DEPOT_POS, TOWER_POS
from psychic_cleaners.core.events import (
    BaitDeployed,
    BeamsCrossed,
    CleanerSlimed,
    GameLost,
    GameWon,
    GhostTrapped,
    RunnerSquashed,
    SceneId,
)
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.core.loadout import Loadout

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")


def new_session(seed: int, items: list[str]) -> Driver:
    d = Driver(seed)
    d.type_text("GEOFF")
    d.key(pygame.K_RETURN)
    d.step()
    shop_move_to(d, "compact")
    d.key(pygame.K_RETURN)
    d.step()
    for item in items:
        shop_move_to(d, item)
        d.key(pygame.K_RETURN)
        d.step()
    d.key(pygame.K_f)
    d.step()
    assert d.game.scene is SceneId.MAP, d.game.scene
    return d


def scenario_backfire_and_lost_finale() -> None:
    print("== SCENARIO: backfire, turn-aways, lost finale ==")
    d = new_session(777, ["snare"])
    # B with no bait charges: must be a silent no-op, not a crash
    d.key(pygame.K_b)
    d.step()
    check(not d.events_of(BaitDeployed), "BAIT: B without charges is a no-op")
    ok = d.wait_for(lambda: d.game.city.active_haunts() > 0, 2400, dt=0.25, label="haunt")
    if not ok:
        return
    target = d.game.city.haunted_positions()[0]
    map_move_cursor(d, target)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(lambda: d.game.scene is not SceneId.DRIVE, 60 * 240, label="arrive")
    if d.game.scene is not SceneId.BUST:
        print(f"       [note] no bust: {d.game.scene} {d.game.notice}")
        return
    # narrow corridor, never spring -> ghost sinks between the beams -> backfire
    run_bust(d, left=280.0, right=360.0, snare=320.0, spring_policy="never")
    if d.game.bust is not None:  # stalemate guard: spring to resolve
        print("       [note] backfire did not trigger in 90s; springing out")
        d.key(pygame.K_SPACE)
        d.step(5)
    backfired = bool(d.events_of(BeamsCrossed))
    check(backfired, "BUST: unsprung bust backfires (BeamsCrossed)")
    if backfired:
        slimed = d.events_of(CleanerSlimed)
        check(
            len(slimed) == 2,
            "BUST: backfire slimes both fielded cleaners",
            f"slimed events={slimed}",
        )
        check(len(d.game.slimed) == 2, "BUST: game tracks two slimed cleaners")
        check(
            d.game.loadout is not None and d.game.loadout.count("snare") == 0,
            "BUST: backfire wastes the snare",
        )
        d.step(2)
        d.shot("20-map-after-backfire")
    # arriving at a haunt with no free snare: turned away with notice
    ok = d.wait_for(lambda: d.game.city.active_haunts() > 0, 2400, dt=0.25, label="haunt2")
    if ok:
        target = d.game.city.haunted_positions()[0]
        map_move_cursor(d, target)
        d.key(pygame.K_RETURN)
        d.step()
        d.wait_for(
            lambda: d.game.scene is SceneId.MAP and d.game.drive is None,
            60 * 240,
            label="turnaway",
        )
        check(
            d.game.notice == "no free snare — buy or empty one at the Depot",
            "ARRIVAL: snare-less haunt arrival turned away with notice",
            f"notice={d.game.notice!r} scene={d.game.scene}",
        )
        d.step(2)
        d.shot("21-turnaway-no-snare")
    # tower with the finale unlocked but only 1 able cleaner: turned away
    d.game.finale_unlocked = True  # injection: unlock without the 40-minute wait
    map_move_cursor(d, TOWER_POS)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(
        lambda: d.game.scene is SceneId.MAP and d.game.drive is None,
        60 * 240,
        label="tower turnaway",
    )
    check(
        d.game.notice == "not enough able cleaners — restore them at the Depot",
        "ARRIVAL: under-crewed tower run turned away",
        f"notice={d.game.notice!r} scene={d.game.scene}",
    )
    # depot: restore crew, restock a snare
    map_move_cursor(d, DEPOT_POS)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(
        lambda: d.game.position == DEPOT_POS and d.game.drive is None, 60 * 240, label="depot"
    )
    check(len(d.game.slimed) == 0, "DEPOT: crew restored after backfire")
    d.key(pygame.K_s)
    d.step()
    check(d.game.free_snares() == 1, "DEPOT: snare restocked for the finale trip")
    # tower again, full crew: deliberately squash two runners -> lost
    map_move_cursor(d, TOWER_POS)
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(lambda: d.game.scene is not SceneId.DRIVE, 60 * 240, label="tower2")
    check(
        d.game.scene is SceneId.FINALE,
        "FINALE: full crew enters the tower",
        f"scene={d.game.scene} notice={d.game.notice}",
    )
    if d.game.scene is not SceneId.FINALE:
        return
    steps = 0
    while d.game.scene is SceneId.FINALE and steps < 60 * 180:
        sim = d.game.finale
        if sim is not None and sim.runner_x is None and sim.remaining_outside > 0:
            clone = copy.deepcopy(sim)
            clone.start_run()
            for _ in range(60 * 6):
                clone.tick(1 / 60)
                if clone.runner_x is None:
                    break
            if clone.squashed > sim.squashed:  # send only doomed runners
                d.key(pygame.K_SPACE)
        d.step()
        steps += 1
    squashed = d.events_of(RunnerSquashed)
    check(len(squashed) >= 2, "FINALE: two runners squashed", f"count={len(squashed)}")
    lost = d.events_of(GameLost)
    check(
        bool(lost) and lost[-1].reason == "the Tower claimed the city",
        "FINALE: squashed crew loses the game",
        f"lost={lost}",
    )
    check(len(d.game.slimed) == 0, "FINALE: squashed runners are not added to slimed")
    d.step(2)
    d.shot("22-gameover-lost")


def scenario_core_rig_fold_profit() -> None:
    print("== SCENARIO: core rig / fold / profit boundary ==")
    # containment rig: a catch goes into the rig, not the snare
    g = new_game(7)
    g.scene = SceneId.BUST
    g.loadout = Loadout(vehicle=VEHICLES["wagon"], counts={"snare": 2, "rig": 1})
    pos = (2, 2)
    g.city.buildings[pos].haunted = True
    g.position = pos
    g.bust = BustSim(phase=BustPhase.RESOLVED, outcome=BustOutcome.CAUGHT)
    evs = g.tick([], 1 / 60)
    trapped = [e for e in evs if isinstance(e, GhostTrapped)]
    check(bool(trapped), "RIG: catch resolves with GhostTrapped")
    check(g.contained == 1, "RIG: ghost goes into the containment rig", f"{g.contained}")
    check(g.snares_full == 0, "RIG: snare stays free while rig has room")
    check(g.wallet.balance == 10_000 + trapped[0].fee, "RIG: fee credited")
    # rig full: catch falls back to filling a snare
    g2 = new_game(8)
    g2.scene = SceneId.BUST
    g2.loadout = Loadout(vehicle=VEHICLES["wagon"], counts={"snare": 2, "rig": 1})
    g2.contained = 10
    g2.position = (2, 2)
    g2.city.buildings[(2, 2)].haunted = True
    g2.bust = BustSim(phase=BustPhase.RESOLVED, outcome=BustOutcome.CAUGHT)
    g2.tick([], 1 / 60)
    check(g2.snares_full == 1 and g2.contained == 10, "RIG: full rig falls back to snare")
    # bankruptcy fold
    g3 = new_game(9)
    g3.scene = SceneId.MAP
    g3.loadout = Loadout(vehicle=VEHICLES["compact"], counts={})
    g3.wallet.balance = 500
    evs = g3.tick([], 1 / 60)
    lost = [e for e in evs if isinstance(e, GameLost)]
    check(
        bool(lost) and "folds" in lost[0].reason,
        "FOLD: snareless + broke folds the franchise",
        f"{lost}",
    )
    check(g3.scene is SceneId.GAME_OVER, "FOLD: goes to GAME_OVER")
    # profit boundary: balance == starting is a LOSS, +1 is a WIN
    for balance, expect_win in ((10_000, False), (10_001, True)):
        g4 = new_game(10)
        g4.player_name = "GEOFF"
        g4.scene = SceneId.FINALE
        g4.loadout = Loadout(vehicle=VEHICLES["compact"], counts={"snare": 1})
        g4.wallet.balance = balance
        g4.finale = FinaleSim(able_cleaners=2, inside=2)
        evs = g4.tick([], 1 / 60)
        won = [e for e in evs if isinstance(e, GameWon)]
        lost = [e for e in evs if isinstance(e, GameLost)]
        if expect_win:
            check(bool(won), f"PROFIT: balance {balance} wins", f"{evs}")
        else:
            check(
                bool(lost) and lost[0].reason == "the franchise never turned a profit",
                f"PROFIT: balance {balance} (no profit) loses",
                f"{evs}",
            )


def scenario_codec_fuzz() -> None:
    print("== SCENARIO: codec fuzz ==")
    rng = random.Random(42)
    ok = True
    for _ in range(300):
        name = "".join(rng.choice("abcdefgh XYZ") for _ in range(rng.randint(1, 20)))
        if not name.strip():
            continue
        bankroll = rng.randint(0, 9_999_999)
        code = encode_account(name, bankroll)
        if decode_account(name, code) != bankroll:
            ok = False
            print(f"       round-trip FAILED for {name!r} {bankroll}")
    check(ok, "CODEC: 300 random (name, bankroll) round-trips")
    # whitespace / case insensitivity
    code = encode_account("Geoff", 123_456)
    check(
        decode_account("Geoff", f"  {code.lower()} ") == 123_456,
        "CODEC: lowercase + padded code accepted",
    )
    check(decode_account("  geoff ", code) == 123_456, "CODEC: name normalization (case/space)")
    # single-character typos: expect near-total rejection
    slipped = 0
    trials = 0
    for _ in range(200):
        bankroll = rng.randint(0, 9_999_999)
        code = encode_account("geoff", bankroll)
        i = rng.randrange(len(code))
        wrong = rng.choice([c for c in ALPHABET if c != code[i]])
        mutated = code[:i] + wrong + code[i + 1 :]
        trials += 1
        try:
            got = decode_account("geoff", mutated)
            if got != bankroll:
                slipped += 1
        except AccountCodeError:
            pass
    check(
        slipped <= 2, f"CODEC: typos rejected ({trials - slipped}/{trials})", f"slipped={slipped}"
    )
    # wrong-name rejection
    rejected = 0
    for _ in range(50):
        code = encode_account("geoff", rng.randint(0, 9_999_999))
        try:
            decode_account("mallory", code)
        except AccountCodeError:
            rejected += 1
    check(rejected >= 49, f"CODEC: wrong-name decode rejected ({rejected}/50)")


def _region_has_color(surface, rect, color, tol=10) -> bool:
    for x in range(rect[0], rect[0] + rect[2], 2):
        for y in range(rect[1], rect[1] + rect[3], 2):
            r, g, b, *_ = surface.get_at((x, y))
            if abs(r - color[0]) <= tol and abs(g - color[1]) <= tol and abs(b - color[2]) <= tol:
                return True
    return False


def scenario_pixels() -> None:
    print("== SCENARIO: pixel checks (banner, wisp visibility) ==")
    d = Driver(31337)
    g = d.game
    d.type_text("GEOFF")
    d.key(pygame.K_RETURN)
    d.step()
    shop_move_to(d, "compact")
    d.key(pygame.K_RETURN)
    d.step()
    for item in ("detector", "sensor", "bait", "snare"):
        shop_move_to(d, item)
        d.key(pygame.K_RETURN)
        d.step()
    d.key(pygame.K_f)
    d.step()
    # mascot banner in its ON flash phase
    g.mascot.state = MascotState.ALERT
    g.mascot.alert_remaining = 9.9  # elapsed ~0.1 after one tick -> banner ON (post-fix formula)
    d.step()
    surf = d.app.logical
    check(
        _region_has_color(surf, (150, 4, 400, 24), (255, 96, 96)),
        "PIXELS: mascot banner visible during ON phase",
    )
    d.shot("23-banner-on")
    d.key(pygame.K_b)  # clear the alert so it doesn't stomp mid-test
    d.step()
    # wisp on the map: visible with detector
    g.city.wisps.append(Wisp(x=8.0, y=0.0))
    d.step()
    wisp_rect = (40 + 8 * 56 + 8, 12 + 0 * 56 + 8, 40, 40)
    check(
        _region_has_color(d.app.logical, wisp_rect, (150, 200, 255)),
        "PIXELS: map wisp visible with detector",
    )
    d.shot("24-wisp-with-detector")
    # invisible without the detector
    assert g.loadout is not None
    del g.loadout.counts["detector"]
    d.step()
    check(
        not _region_has_color(d.app.logical, wisp_rect, (150, 200, 255)),
        "PIXELS: map wisp hidden without detector",
    )


def main() -> None:
    import playtest

    scenarios = [
        scenario_backfire_and_lost_finale,
        scenario_core_rig_fold_profit,
        scenario_codec_fuzz,
        scenario_pixels,
    ]
    for scenario in scenarios:
        try:
            scenario()
        except Exception:
            traceback.print_exc()
            check(False, f"{scenario.__name__} completed without crashing")
    print(f"\nRESULT: {playtest.PASS} passed, {playtest.FAIL} failed")
    pygame.quit()
    sys.exit(1 if playtest.FAIL else 0)


if __name__ == "__main__":
    main()

"""Round-2 playtest: verify the five merged bug fixes end-to-end and probe fresh areas."""

import os
import sys
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")  # keep `timeout` able to kill us

import pygame
from playtest import Driver, check, map_move_cursor, shop_move_to

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import (
    DEPOT_POS,
    MAX_BANKROLL,
    NOTICE_LIFETIME_SECONDS,
    VACUUM_BOUNTY,
)
from psychic_cleaners.core.events import (
    Arrived,
    PurchaseRejected,
    SceneId,
    SnaresEmptied,
)
from psychic_cleaners.core.loadout import Loadout

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")


def _region_has_color(surface, rect, color, tol=12) -> bool:
    for x in range(rect[0], rect[0] + rect[2], 2):
        for y in range(rect[1], rect[1] + rect[3], 2):
            r, g, b, *_ = surface.get_at((x, y))
            if abs(r - color[0]) <= tol and abs(g - color[1]) <= tol and abs(b - color[2]) <= tol:
                return True
    return False


def scenario_fix_verification() -> None:
    print("== FIX VERIFICATION ==")
    d = Driver(2026)
    g = d.game
    # long-name clamp probe on the way in
    d.type_text("ABCDEFGHIJKLMNOPQRSTUVWXY")  # 25 chars
    d.key(pygame.K_RETURN)
    d.step()
    check(
        len(g.player_name) == 20,
        "TITLE: name entry clamps at 20 chars",
        f"name={g.player_name!r}",
    )
    shop_move_to(d, "compact")
    d.key(pygame.K_RETURN)
    d.step()
    # fix 2 regression: shop renders with columns; double bait purchase probe
    for item in ("bait", "bait", "snare"):
        shop_move_to(d, item)
        d.key(pygame.K_RETURN)
        d.step()
    lo = g.loadout
    check(
        lo is not None and lo.bait_charges == 10 and lo.count("bait") == 2,
        "SHOP: two bait packs stack to 10 charges",
        f"charges={lo.bait_charges if lo else None}",
    )
    d.step(2)
    d.shot("30-shop-columns")
    d.key(pygame.K_f)
    d.step()
    # FIX 3: map notice expires after NOTICE_LIFETIME_SECONDS of world time
    g.city.buildings[(3, 3)].haunted = False  # make the arrival a plain MAP return
    map_move_cursor(d, (3, 3))
    d.key(pygame.K_RETURN)
    d.step()
    d.wait_for(lambda: g.scene is SceneId.MAP and g.drive is None, 60 * 240, label="arrive 3,3")
    d.key(pygame.K_s)  # snare restock away from depot -> rejected + notice
    d.step()
    rej = d.events_of(PurchaseRejected)
    check(
        bool(rej) and g.notice == "snares only, at the Depot",
        "NOTICE: depot-only rejection sets notice",
        f"notice={g.notice!r}",
    )
    hold = NOTICE_LIFETIME_SECONDS - 0.5
    d.step(n=int(hold * 60), dt=1 / 60)
    check(
        g.notice is not None,
        f"FIX3: notice still visible {hold:.1f}s in",
        f"notice={g.notice!r} remaining={g.notice_remaining}",
    )
    d.step(n=60, dt=1 / 60)  # cross the 6s lifetime
    check(
        g.notice is None and g.notice_remaining == 0.0,
        "FIX3: notice expires after lifetime on the map",
        f"notice={g.notice!r} remaining={g.notice_remaining}",
    )
    # FIX 1: haunt at (5,4) under the tower is visible (no detector owned)
    pos = (5, 4)
    g.city.buildings[pos].haunted = True
    d.step()
    cell = (40 + 5 * 56 + 4, 12 + 4 * 56 + 4, 48, 48)
    check(
        _region_has_color(d.app.logical, cell, (215, 140, 255)),
        "FIX1: haunted windows at (5,4) visible under the tower",
    )
    d.shot("31-haunt-under-tower")
    g.city.buildings[pos].haunted = False
    # immediate arrival: Enter on the current (haunted) cell skips DRIVE
    here = g.position
    g.city.buildings[here].haunted = True
    map_move_cursor(d, here)
    d.key(pygame.K_RETURN)
    d.step()
    check(
        g.scene is SceneId.BUST and g.drive is None,
        "ARRIVAL: Enter on current haunted cell enters BUST without driving",
        f"scene={g.scene}",
    )
    arr = d.events_of(Arrived)
    check(bool(arr) and arr[-1].pos == here, "ARRIVAL: immediate arrival emits Arrived")


def scenario_probes() -> None:
    print("== NEW PROBES ==")
    d = Driver(4242)
    g = d.game
    d.type_text("GEOFF")
    d.key(pygame.K_RETURN)
    d.step()
    shop_move_to(d, "compact")
    d.key(pygame.K_RETURN)
    d.step()
    shop_move_to(d, "snare")
    d.key(pygame.K_RETURN)
    d.step()
    d.key(pygame.K_f)
    d.step()
    # Enter on depot while standing on it: immediate re-arrival, still MAP
    map_move_cursor(d, DEPOT_POS)
    d.key(pygame.K_RETURN)
    d.step()
    check(
        g.scene is SceneId.MAP and bool(d.events_of(SnaresEmptied)),
        "DEPOT: Enter while parked re-runs depot services without a drive",
        f"scene={g.scene}",
    )
    # wallet clamp at MAX_BANKROLL via a road wisp catch
    g.wallet.balance = MAX_BANKROLL - VACUUM_BOUNTY // 2
    d.expected_balance = g.wallet.balance
    g.wallet.earn(VACUUM_BOUNTY)
    d.expected_balance = MAX_BANKROLL
    check(g.wallet.balance == MAX_BANKROLL, "WALLET: earn clamps at MAX_BANKROLL")
    g.wallet.balance = 10_000
    d.expected_balance = 10_000
    # driving scene: faint wisp invisible without lens (pixel check)
    from psychic_cleaners.core.drive import DriveSim, RoadWisp

    g.loadout = Loadout(vehicle=VEHICLES["compact"], counts={"snare": 1})
    g.scene = SceneId.DRIVE
    g.destination = (3, 5)
    g.drive = DriveSim(distance_total=99999.0, speed=0.0, has_vacuum=False, has_lens=False)
    g.drive.wisps.append(RoadWisp(x=400.0, lane=0, faint=True))
    g.drive.wisps.append(RoadWisp(x=500.0, lane=2, faint=False))
    # draw directly (no tick) so the comparison is deterministic
    from psychic_cleaners.shell.scenes.driving import DrivingScene

    scene = DrivingScene()

    def region_bytes(rect):
        surf = pygame.Surface((640, 400))
        scene.draw(surf, g, d.app.gfx, d.app.text)
        return pygame.image.tobytes(surf.subsurface(pygame.Rect(rect)), "RGB"), surf

    faint_rect = (376, 116, 48, 48)  # around lane-0 wisp at (400, 140)
    normal_rect = (476, 236, 48, 48)  # around lane-2 wisp at (500, 260)
    without_lens_faint, surf0 = region_bytes(faint_rect)
    check(
        _region_has_color(surf0, normal_rect, (150, 200, 255)),
        "DRIVE: normal wisp visible without lens",
    )
    empty = pygame.Surface((640, 400))
    saved = list(g.drive.wisps)
    g.drive.wisps.clear()
    scene.draw(empty, g, d.app.gfx, d.app.text)
    no_wisp_faint = pygame.image.tobytes(empty.subsurface(pygame.Rect(faint_rect)), "RGB")
    g.drive.wisps.extend(saved)
    check(
        without_lens_faint == no_wisp_faint,
        "DRIVE: faint wisp hidden without spectral lens",
    )
    g.loadout.add("lens")
    with_lens_faint, surf1 = region_bytes(faint_rect)
    check(
        with_lens_faint != no_wisp_faint,
        "DRIVE: faint wisp visible with spectral lens",
    )
    pygame.image.save(surf1, os.path.join(SHOTS, "32-drive-faint-wisp.png"))
    print("       [shot] 32-drive-faint-wisp.png")


def main() -> None:
    import playtest

    for scenario in (scenario_fix_verification, scenario_probes):
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

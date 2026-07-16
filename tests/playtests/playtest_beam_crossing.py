"""Targeted playtest of the beam-crossing backfire mechanic: drives the real
App into a BUST encounter with a narrow cleaner gap and confirms BeamsCrossed
fires (via the real BustSim.tick() path) without relying on the pre-existing
sunk_between trigger, plus a wide-gap control case proving the placement
immunity holds. See docs/superpowers/specs/2026-07-16-beam-crossing-backfire-
design.md for the mechanic's design.
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")  # keep `timeout` able to kill us

import playtest
import pygame
from playtest import Driver, check, map_move_cursor, shop_move_to

from psychic_cleaners.core.bust import BustPhase
from psychic_cleaners.core.constants import BUST_GROUND_Y
from psychic_cleaners.core.events import BeamsCrossed, CleanerSlimed, SceneId

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots_beam_crossing")
os.makedirs(SHOTS, exist_ok=True)


def shot(app: pygame.Surface, name: str) -> None:
    pygame.image.save(app, os.path.join(SHOTS, f"{name}.png"))
    print(f"       [shot] {name}.png")


def enter_shop_and_buy_hearse(d: Driver) -> None:
    d.type_text("PLAYTESTER")
    d.step()
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.scene is SceneId.SHOP, "reached SHOP")
    shop_move_to(d, "hearse")
    d.key(pygame.K_RETURN)
    d.step()
    check(d.game.loadout is not None and d.game.loadout.vehicle.id == "hearse", "bought hearse")
    for _ in range(2):
        shop_move_to(d, "snare")
        d.key(pygame.K_RETURN)
        d.step()
    check(d.game.loadout is not None and d.game.loadout.count("snare") == 2, "bought 2 snares")
    d.key(pygame.K_f)
    d.step()
    check(d.game.scene is SceneId.MAP, "F finishes shopping -> MAP")


def travel_to_haunt(d: Driver, pos: tuple[int, int]) -> None:
    d.game.city.buildings[pos].haunted = True
    map_move_cursor(d, pos)
    d.key(pygame.K_RETURN)
    d.step()
    steps = 0
    while d.game.scene is SceneId.DRIVE and steps < 60 * 60:
        d.step()
        steps += 1
    check(d.game.scene is SceneId.BUST, f"arrival at {pos} entered BUST", f"scene={d.game.scene}")


def move_bust_cursor_to(d: Driver, x: float) -> None:
    for _ in range(600):
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


def position_cleaners_and_lay_snare(d: Driver, left: float, right: float, snare: float) -> None:
    move_bust_cursor_to(d, left)
    d.key(pygame.K_RETURN)
    d.step()
    move_bust_cursor_to(d, right)
    d.key(pygame.K_RETURN)
    d.step()
    b = d.game.bust
    check(b is not None and b.phase is BustPhase.SNARE, "reached SNARE placement phase")
    move_bust_cursor_to(d, snare)
    d.key(pygame.K_RETURN)
    d.step()
    b = d.game.bust
    check(b is not None and b.phase is BustPhase.ACTIVE, "snare laid -> ACTIVE")


def inject_ghost_and_tick(d: Driver, ghost_x: float, ghost_y: float) -> None:
    """Force the ghost to a specific position and step exactly one near-zero-
    dt tick, isolating the crossing check itself from drift/sink noise.
    Real-time drift would take many simulated minutes to wander into this
    exact geometry by chance; direct state injection is the harness's own
    established pattern for otherwise unreachable-in-minutes setups (see
    playtest.py's --inject-profit and Game.psi.spike() usage elsewhere)."""
    b = d.game.bust
    assert b is not None
    print(
        f"       [inject] left_x={b.left_x} right_x={b.right_x} "
        f"gap={abs((b.right_x or 0) - (b.left_x or 0)):.1f} -> "
        f"ghost_x={ghost_x} ghost_y={ghost_y}"
    )
    b.ghost_x = ghost_x
    b.ghost_y = ghost_y
    d.log.clear()
    d.step(1, dt=1e-6)


def scenario_narrow_gap_crosses() -> None:
    print("== SCENARIO 1: narrow cleaner gap, off-center ghost near ground ==")
    d = Driver(seed=1)
    d.step(2)
    enter_shop_and_buy_hearse(d)
    travel_to_haunt(d, (1, 5))
    position_cleaners_and_lay_snare(d, left=300.0, right=320.0, snare=310.0)
    # Cursor movement lands within +/-3px of target, which can shift the
    # actual gap enough to fall outside the reliably-reachable crossing
    # zone for a given ghost offset. Pin the exact 24px-gap geometry this
    # feature's own unit tests use (tests/core/test_bust.py) directly on
    # the BustSim after real input reached ACTIVE.
    b = d.game.bust
    assert b is not None
    b.left_x, b.right_x = 300.0, 324.0
    d.step(2)
    shot(d.app.logical, "01-narrow-active")
    inject_ghost_and_tick(d, ghost_x=299.0, ghost_y=BUST_GROUND_Y)  # 1px outside the pair

    crossed = d.events_of(BeamsCrossed)
    slimed = d.events_of(CleanerSlimed)
    check(bool(crossed), "SCENARIO 1: BeamsCrossed fired", f"log={d.frame_events}")
    check(d.game.scene is SceneId.MAP, "SCENARIO 1: bust resolved back to MAP")
    check(
        len(slimed) == 2, "SCENARIO 1: both cleaners slimed (BACKFIRE)", f"slimed events={slimed}"
    )
    check(
        d.game.slimed == {0, 1},
        "SCENARIO 1: game.slimed has both cleaner indices",
        f"{d.game.slimed}",
    )
    print(f"       events this tick: {crossed + slimed}")
    shot(d.app.logical, "02-narrow-resolved")


def scenario_wide_gap_stays_safe() -> None:
    print()
    print("== SCENARIO 2: wide cleaner gap (>=300px), same off-center-at-ground ghost ==")
    d = Driver(seed=2)
    d.step(2)
    enter_shop_and_buy_hearse(d)
    travel_to_haunt(d, (1, 5))
    position_cleaners_and_lay_snare(d, left=100.0, right=420.0, snare=260.0)
    d.step(2)
    shot(d.app.logical, "03-wide-active")
    inject_ghost_and_tick(d, ghost_x=60.0, ghost_y=BUST_GROUND_Y)

    crossed = d.events_of(BeamsCrossed)
    check(
        not crossed,
        "SCENARIO 2: BeamsCrossed did NOT fire (wide-gap immunity)",
        f"log={d.frame_events}",
    )
    check(
        d.game.scene is SceneId.BUST,
        "SCENARIO 2: bust still ACTIVE (no backfire)",
        f"scene={d.game.scene}",
    )
    b = d.game.bust
    check(b is not None and b.outcome is None, "SCENARIO 2: no outcome resolved yet")
    print(f"       events this tick: {d.frame_events}")
    shot(d.app.logical, "04-wide-resolved")


if __name__ == "__main__":
    scenario_narrow_gap_crosses()
    scenario_wide_gap_stays_safe()
    print()
    print(f"PASS={playtest.PASS} FAIL={playtest.FAIL}")
    sys.exit(1 if playtest.FAIL else 0)

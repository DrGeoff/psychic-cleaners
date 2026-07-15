"""Session 3: verify playtest fixes 1-4 through the real UI."""

import os
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")  # keep `timeout` able to kill us

import pygame

from psychic_cleaners.core.constants import DEPOT_POS, TOWER_POS
from psychic_cleaners.core.events import CommandRejected, SceneId
from psychic_cleaners.shell.app import SCENES, App
from psychic_cleaners.shell.scenes.title import TitleScene

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots3")
os.makedirs(SHOTS, exist_ok=True)

app = App(seed=23)
game = app.game
frame = [0]
event_log: list = []
_orig_tick = game.tick


def _tick(commands, dt):
    evs = _orig_tick(commands, dt)
    event_log.extend(evs)
    return evs


game.tick = _tick  # type: ignore[method-assign]
results: list[str] = []


def check(cond, msg):
    results.append(("PASS " if cond else "FAIL ") + msg)
    print(results[-1], flush=True)


def step(n=1, dt=1 / 60):
    for _ in range(n):
        app.step(dt)
        frame[0] += 1


def shot(name):
    pygame.image.save(app.logical, os.path.join(SHOTS, f"{name}.png"))


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0))
    step()
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=k, mod=0))
    step()


def text(s):
    for ch in s:
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=ch))
        step()


_held: set[int] = set()


class _Keys:
    def __getitem__(self, k):
        return k in _held


pygame.key.get_pressed = lambda: _Keys()  # type: ignore[assignment]


def hold(k, frames):
    _held.add(k)
    step(frames)
    _held.discard(k)
    step()


def wait_until(pred, max_frames, dt=1 / 60):
    for _ in range(max_frames):
        if pred():
            return True
        step(1, dt)
    return False


def move_cursor_to(target):
    sc = SCENES[SceneId.MAP]
    for _ in range(40):
        cx, cy = sc.cursor
        if (cx, cy) == target:
            return True
        tx, ty = target
        if cx < tx:
            key(pygame.K_RIGHT)
        elif cx > tx:
            key(pygame.K_LEFT)
        elif cy < ty:
            key(pygame.K_DOWN)
        else:
            key(pygame.K_UP)
    return False


def drive_to(target):
    move_cursor_to(target)
    key(pygame.K_RETURN)
    step(2)
    wait_until(lambda: game.scene is not SceneId.DRIVE, 30000, dt=1 / 30)


try:
    title = SCENES[SceneId.TITLE]
    assert isinstance(title, TitleScene)

    # ---- Fix 1: rejected code preserves both fields ----
    step(5)
    text("GEOFF")
    key(pygame.K_TAB)
    text("AAAAAAA")
    key(pygame.K_RETURN)
    step(3)
    check(game.scene is SceneId.TITLE, "rejected code stays on TITLE")
    check(title._name == "GEOFF", f"name preserved after rejection (got {title._name!r})")
    check(title._code == "AAAAAAA", f"code preserved after rejection (got {title._code!r})")
    shot("01_title_rejected_fields_kept")
    for _ in range(7):
        key(pygame.K_BACKSPACE)  # clear the bad code (focus still on code)
    key(pygame.K_RETURN)  # empty code -> NewGame with the preserved name
    step(3)
    check(game.scene is SceneId.SHOP, "NewGame accepted with preserved name")
    check(game.player_name == "GEOFF", f"player name {game.player_name!r}")

    # ---- quick shop: compact + 1 snare ----
    key(pygame.K_RETURN)  # compact (row 0)
    for _ in range(8):
        key(pygame.K_DOWN)  # -> snare
    key(pygame.K_RETURN)
    key(pygame.K_f)
    step(3)
    check(game.scene is SceneId.MAP, "in MAP after shopping")

    # ---- Fix 3: stale notice cleared on scene change ----
    key(pygame.K_s)  # away from depot? position IS depot at start...
    step(2)
    # we start at the depot, so S actually buys if affordable ($2000-ish left).
    # Force a rejection instead: S at depot with low funds OR use the away case
    # after travelling. Travel first, then S away, then travel again.
    drive_to((3, 3))
    key(pygame.K_s)
    step(2)
    check(game.notice == "snares only, at the Depot", f"S-away notice: {game.notice!r}")
    shot("02_notice_set")
    drive_to((4, 3))
    check(game.notice is None, f"notice cleared after scene change (got {game.notice!r})")
    shot("03_notice_cleared")

    # ---- backfire a bust to slime two cleaners ----
    wait_until(lambda: bool(game.city.haunted_positions()), 4000, dt=0.5)
    target = game.city.haunted_positions()[0]
    drive_to(target)
    check(game.scene is SceneId.BUST, f"bust started (scene={game.scene.name})")
    if game.scene is SceneId.BUST:
        hold(pygame.K_LEFT, 16)
        key(pygame.K_RETURN)
        hold(pygame.K_RIGHT, 32)
        key(pygame.K_RETURN)
        hold(pygame.K_LEFT, 16)
        key(pygame.K_RETURN)
        shot("04_bust_beams_spread")  # beams should no longer meet at one apex
        wait_until(lambda: game.scene is not SceneId.BUST, 4000)  # let it backfire
    check(len(game.slimed) == 2, f"backfire slimed two (slimed={sorted(game.slimed)})")

    # ---- Fix 2: haunted arrival while under-crewed explains itself ----
    wait_until(lambda: bool(game.city.haunted_positions()), 4000, dt=0.5)
    target = game.city.haunted_positions()[0]
    event_log.clear()
    drive_to(target)
    step(2)
    check(game.scene is SceneId.MAP, "under-crewed haunt arrival returns to MAP")
    check(
        game.notice == "cleaners are slimed — restore them at the Depot",
        f"under-crewed notice: {game.notice!r}",
    )
    check(
        any(isinstance(e, CommandRejected) for e in event_log),
        "CommandRejected emitted for under-crewed bust",
    )
    shot("05_undercrewed_notice")

    # ---- Fix 4: tower turns away an under-crewed team ----
    wait_until(lambda: game.finale_unlocked, 40000, dt=0.5)
    drive_to(TOWER_POS)
    step(2)
    check(game.scene is SceneId.MAP, f"tower turn-away to MAP (scene={game.scene.name})")
    check(game.result is None, "game NOT lost at tower while under-crewed")
    check(
        game.notice == "not enough able cleaners — restore them at the Depot",
        f"turn-away notice: {game.notice!r}",
    )
    shot("06_tower_turnaway")

    # ---- restore at depot, then the tower admits us ----
    drive_to(DEPOT_POS)
    check(game.able_cleaners() == 3, "depot restored cleaners")
    drive_to(TOWER_POS)
    step(2)
    check(game.scene is SceneId.FINALE, f"finale entered when healthy ({game.scene.name})")
    shot("07_finale_entered")

except Exception:
    traceback.print_exc()
    shot("99_crash")
    results.append("FAIL crash — see traceback")

print(f"\nframes: {frame[0]}", flush=True)
fails = [r for r in results if r.startswith("FAIL")]
print(f"{len(results) - len(fails)}/{len(results)} checks passed", flush=True)

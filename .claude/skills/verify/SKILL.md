---
name: verify
description: Drive the real Psychic Cleaners App headless to verify a change at its surface (scenes, notices, sprites), instead of re-running pytest.
---

# Verifying Psychic Cleaners changes

The surface is the pygame App. Drive it headless with posted events and
simulated time — never wall-clock waits, never core-API-only calls.

## Handle

Reuse the checked-in playtest harness (`tests/playtests/`, see its README):

```python
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")  # keep `timeout` able to kill us
sys.path.insert(0, "<repo>/tests/playtests")
import playtest
from playtest import Driver, check, shop_move_to, map_move_cursor, scene_obj
playtest.SHOTS = "<scratchpad>/shots"  # keep screenshots out of the repo tree
```

- `Driver(seed)` boots the real `App`; `d.step(n, dt=1/60)` advances simulated
  time (a 20 s in-game drive is 1200 fast headless steps, not 20 wall seconds).
- `d.key(pygame.K_x)` / `d.type_text("name")` post real input events.
- `d.events_of(EventClass)` inspects everything `Game.tick` emitted.
- `d.shot("name")` saves `app.logical` as a PNG — Read it to eyeball frames.
- State injection for unreachable-in-minutes setups follows the harness's own
  pattern (e.g. `d.game.psi.spike(...)`, like `playtest.py --inject-profit`).

## Flows worth driving

- Title → shop (hearse + snare ≈ cheapest solvent loadout) → `F` → map.
- Map travel: `map_move_cursor(d, pos)` + Enter; Depot(0,5)→Tower(5,3) in a
  hearse is exactly 20.0 s (2800 units / 140).
- Pixel probes: scan `d.app.logical` regions for a sprite's signature color
  (cell center = `(40 + x*56 + 28, 12 + y*56 + 28)`).

## Gotchas

- Run under `timeout -k 5 300 uv run python <script>` — SDL swallows SIGTERM
  unless `SDL_NO_SIGNAL_HANDLERS=1` is set (the harness sets it).
- One `App` per production process; a second `App()` in-process is supported
  for probes only because `App.__init__` resets the scene singletons.
- Map/shop notices live 6 s (`NOTICE_LIFETIME_SECONDS`) — a notice on screen
  may be stale by up to that much when asserting pixels right after an event.

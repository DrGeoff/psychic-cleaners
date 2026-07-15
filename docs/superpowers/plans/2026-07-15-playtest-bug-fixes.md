# Playtest bug fixes — 2026-07-15

Five bugs found by a scripted full-playthrough playtest (screenshots + event/economy
ledger over the real `App` loop). Each task is independent; all are small.

## Global Constraints

- Every gameplay number lives in `src/psychic_cleaners/core/constants.py` — it is the
  single tuning point. No magic numbers in scene or core logic.
- `core/` stays pure: zero pygame imports.
- Repo convention (docstring of `Game._reset`): every task that adds a `Game` field
  MUST extend `_reset()` with that field in the same task.
- Gauntlet per task: `uv run pytest` all green, `uv run ruff check .`,
  `uv run ruff format .`, `uv run mypy` (strict) all clean.
- Core coverage gate: `uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90
  --override-ini="addopts=--cov-report=term-missing"` must pass.
- TDD: write the failing test first where the task specifies tests.
- Match existing test style: shell scene tests use the autouse pygame
  init/set_mode fixture pattern (see `tests/shell/test_mascot_overlay.py`).
- One commit per task, message style: `fix: <summary>` matching repo history.

---

## Task 1: Map tower sprite must not cover the building below it

**Bug:** `CityMapScene.draw` blits the full-size tower sprite (56×96) at its cell's
top-left (`city_map.py:79`), so it overlaps the building cell at (5,4) below
`TOWER_POS` (5,3). A haunting at (5,4) is nearly invisible — only a ~16px sliver of
the building shows.

**Fix:**
- In `src/psychic_cleaners/shell/gfx.py`, add a `"tower.map"` builder registered in
  `_BUILDERS`: `pygame.transform.scale(_build_tower(), (28, 48))` — the full tower at
  map-cell height, aspect preserved (56×96 → 28×48).
- In `src/psychic_cleaners/shell/scenes/city_map.py`, replace the
  `surface.blit(gfx.get("tower"), _cell_rect(TOWER_POS).topleft)` blit with the
  `"tower.map"` sprite centered horizontally in the tower's cell rect (48-wide cell,
  28-wide sprite → x offset +10) and aligned to the cell rect's top (sprite height 48
  == cell rect height 48). The finale scene keeps using the full-size `"tower"`.

**Tests (TDD):**
- New behavioral test in `tests/shell/test_city_map_scene.py` (or the closest existing
  file): render the map scene twice into 640×400 surfaces — once with the building at
  (5,4) haunted (no detector in loadout), once not haunted — and assert the pixel
  bytes inside (5,4)'s cell rect differ. This fails with the current full-size tower
  blit (the haunt is covered) and passes once the tower fits its own cell.
  Compute the cell rect exactly as the scene does: `(40 + 5*56 + 4, 12 + 4*56 + 4, 48, 48)`.
- Check existing tests that reference the map tower blit (`tests/shell/test_city_sprites.py`,
  `tests/shell/test_city_map_scene.py`) and update any that pin the old `"tower"`
  sprite name/size on the map — the map now uses `"tower.map"`.

## Task 2: Shop price column is ragged

**Bug:** `ShopScene.draw` builds one padded string per row
(`f"{marker} {row.name:<20} ${row.price}{suffix}"`, `shop.py:68`) but `TextRenderer`
uses pygame's proportional default font, so the `:<20` field width does not align —
prices land at visually random x positions.

**Fix:** In `src/psychic_cleaners/shell/scenes/shop.py`, draw each row as separate
column blits at fixed x positions instead of one padded string, keeping the exact
same y, size, and per-row color logic:
- marker (`>` or nothing) at x=24
- `row.name` at x=44
- `f"${row.price}"` at x=280
- suffix (`  [chosen]` / `  x{owned}` — now without leading spaces) at x=380

Module-level `Final` ints for the four column x positions (they are layout, not
gameplay numbers, so they live in the scene module like `_HUD_Y` does in
`city_map.py`).

**Tests:** pure layout change — no new test required; the existing shop scene tests
must stay green unless one pins the old single-string rendering (update it if so).

## Task 3: Map notices never expire

**Bug:** `Game.notice` is only cleared on scene change, so a rejection like
"no room in vehicle" stays on the MAP HUD for the entire map session — a stale
notice minutes later reads as a current warning.

**Fix (core, so it is deterministic and testable):**
- `constants.py`: add `NOTICE_LIFETIME_SECONDS: Final[float] = 6.0` (new `# ui`
  section at the end of the file).
- `Game`: new field `notice_remaining: float = 0.0`.
- New private helper `Game._set_notice(self, reason: str) -> None` that sets
  `self.notice = reason` and arms `self.notice_remaining = NOTICE_LIFETIME_SECONDS`.
  Convert EVERY `self.notice = <reason>` assignment site to `self._set_notice(...)`
  (title, shop, depot restock, arrival turn-aways, tower turn-away). Success paths
  that do `self.notice = None` and `_change_scene` also zero `notice_remaining`.
- In `_world_tick`, after `self.clock.advance(...)`: if a notice is set, decrement
  `notice_remaining` by `dt_seconds`; at `<= 0`, clear the notice and zero the field.
  (Notices on TITLE/SHOP intentionally do not decay — those scenes do not world-tick
  and their notices answer the player's most recent input.)
- Extend `_reset()` with `notice_remaining` (repo convention).

**Tests (TDD, `tests/core/`):**
- A rejected depot restock on MAP (e.g. `BuyItem("snare")` away from the Depot) sets
  the notice; ticking the world just under `NOTICE_LIFETIME_SECONDS` keeps it;
  crossing the lifetime clears it (both `notice` and `notice_remaining`).
- Scene change still clears immediately (existing behavior — keep any existing test
  green).
- `_reset()` zeroes `notice_remaining`.

## Task 4: "no snare laid" rejection is unreachable

**Bug:** the core rejects a premature `SpringSnare` with
`CommandRejected("no snare laid")` (`game.py` BUST dispatch), which drives the
reject sound — but `BustingScene.commands` only emits `SpringSnare` when
`bust.phase is BustPhase.ACTIVE` (`busting.py:56`), so a too-early Space press is
silently swallowed and the core path is dead code.

**Fix:** in `src/psychic_cleaners/shell/scenes/busting.py`, drop the phase gate:
`elif event.key == pygame.K_SPACE:` always appends `SpringSnare()`. The core decides:
ACTIVE → spring, anything else → `CommandRejected("no snare laid")` → reject sound.

**Tests (TDD):**
- Scene test (`tests/shell/test_busting_scene.py`): a Space KEYDOWN during
  `BustPhase.POSITION_LEFT` yields a `SpringSnare` command.
- Core test only if not already covered (a test for `CommandRejected("no snare laid")`
  on a non-ACTIVE SpringSnare likely exists in `tests/core/` — check first, don't
  duplicate).

## Task 5: Mascot banner starts in its hidden flash phase

**Bug:** `_draw_mascot_banner` gates the flash on
`int(game.mascot.alert_remaining * 2) % 2 != 0` (`shell/scenes/__init__.py:28`).
`alert_remaining` counts DOWN from 10.0, so for the first ~0.5 s of an alert
(remaining in (9.5, 10.0)) the value is 19 → odd → banner hidden. The alert starts
invisible exactly when the player most needs to see it.

**Fix:** flash on elapsed alert time so the banner starts ON:
```python
elapsed = MASCOT_ALERT_WINDOW - game.mascot.alert_remaining
if int(elapsed * 2) % 2 != 0:
    return
```
Import `MASCOT_ALERT_WINDOW` from `psychic_cleaners.core.constants`.

Note: the existing test `test_banner_visible_only_in_alert_and_flash_on_phase`
(`tests/shell/test_mascot_overlay.py`) samples remaining=10.0 (visible) and
remaining=9.5 (hidden) — both stay green under the elapsed formula (elapsed 0.0 → on;
elapsed 0.5 → off).

**Tests (TDD):** extend that test file with the bug case: `alert_remaining = 9.9`
(elapsed 0.1) must be VISIBLE — it is hidden before the fix.

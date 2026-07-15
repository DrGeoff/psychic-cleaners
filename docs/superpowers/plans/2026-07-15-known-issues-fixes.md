# Known-issues fixes — 2026-07-15 (round 2)

Closes out every issue still recorded from the two playtest rounds: two real
player-facing issues and the five cosmetic minors the previous final review triaged.
Base: main at b8b47ce (all five round-1 fixes merged).

## Global Constraints

- Every gameplay number lives in `src/psychic_cleaners/core/constants.py`. Scene-local
  layout numbers live as module-level `Final`s in the scene module.
- `core/` stays pure: zero pygame imports.
- Repo convention: every task that adds a `Game` field MUST extend `_reset()` in the
  same task (no task here adds one).
- Gauntlet per task: `uv run pytest` all green, `uv run ruff check .`,
  `uv run ruff format .`, `uv run mypy` (strict) clean, and the core coverage gate
  `uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90
  --override-ini="addopts=--cov-report=term-missing"`.
- TDD where the task specifies tests. One commit per task, message style `fix: …`.
- Notice copy style: lowercase, em-dash hint, matching e.g.
  "no free snare — buy or empty one at the Depot".

---

## Task 1: Arriving at a locked Tower must explain itself

**Issue:** `_arrive_at` (game.py:402) only routes to `_arrive_at_tower` when
`finale_unlocked` is true. Before the unlock, a trip to `TOWER_POS` falls through to
the plain `else` and silently parks the player on the map — no notice, no sound. The
player has no way to know why the Tower did nothing.

**Fix (core):** in `_arrive_at`, insert a new branch AFTER the
`pos == TOWER_POS and self.finale_unlocked` branch and BEFORE the haunted-position
branch:

```python
elif pos == TOWER_POS:
    if self.scene is not SceneId.MAP:
        self._change_scene(SceneId.MAP, events)
    reason = "the Tower is sealed — return when the city's residue peaks"
    self._set_notice(reason)
    events.append(CommandRejected(reason))
```

This mirrors the existing turn-away branches exactly (scene routing first, then
`_set_notice`, then `CommandRejected`, which already drives the reject sound via
`EVENT_SOUNDS` in shell/app.py).

**Tests (TDD, tests/core/):** travelling to `TOWER_POS` with `finale_unlocked` False
lands on MAP with the notice set and a `CommandRejected` carrying the same reason;
the existing unlocked-tower behavior (FINALE entry / under-crewed turn-away) stays
green. Use the immediate-arrival path (`SetDestination` at the current position or
tick through the drive) — whichever matches existing test style in
`tests/core/test_game*.py` / `tests/integration/`.

## Task 2: Account-code checksum widened to 10 bits

**Issue:** `core/codec.py` packs `raw = (mixed << 8) | checksum8`. A single-character
typo passes undetected when the 8-bit checksum collides (~1/256); the playtest fuzz
observed 1 slip in 200 mutations decoding to a WRONG bankroll. The 7-character
base-30 code space (30^7 ≈ 2.19e10) has room for a 10-bit checksum:
`mixed < 2^24` (bankroll ≤ 9,999,999 xor a 24-bit key), and `2^34 < 30^7`.

**Fix (core/codec.py):**
- `_checksum` masks with `0x3FF` (10 bits) instead of `0xFF`.
- `encode_account`: `raw = (mixed << 10) | _checksum(...)`.
- `decode_account`: `mixed = raw >> 10`, `check = raw & 0x3FF`.
- Introduce a module `Final` for the checksum bits/mask (e.g. `_CHECK_BITS = 10`,
  `_CHECK_MASK = (1 << _CHECK_BITS) - 1`) so encode/decode can't drift apart.
- Update the module docstring ("8-bit CRC checksum" → 10-bit) and the comment on
  `_BASE` (the packing bound is now 2^34 < 30^7).
- Forged-range rejection still holds: a decoded `mixed` above 2^24-1 xors to a
  bankroll > MAX_BANKROLL and is rejected by the existing range check — do not
  change that logic.

**Note:** this invalidates account codes issued by older builds; acceptable pre-release,
and no persistence exists beyond the codes themselves. Say so in the commit body.

**Tests (TDD, tests/core/test_codec.py):** existing round-trip/property tests must
stay green (update any that pin 8-bit internals). Add: an exhaustive
single-character-mutation test for a handful of fixed (name, bankroll) pairs — for
each of the 7 positions substitute all 29 other alphabet characters and assert every
mutation either raises `AccountCodeError` or (rarely) decodes — with the total
undetected-wrong-bankroll count over all 203 mutations per pair asserted == 0 for the
chosen fixed pairs (pick pairs that are fully rejected — deterministic, no flake; if
a chosen pair has a collision, choose a different fixed pair and note it).

## Task 3: Review-minor cleanup batch

Five findings the round-1 reviews recorded; fix four, document one.

1. **city_map.py — derive the tower blit offset.** Replace the hardcoded `+10` with
   arithmetic from the sprite: fetch the sprite once, blit at
   `rect.left + (rect.width - sprite.get_width()) // 2, rect.top`. No new constant
   needed — the offset is now self-maintaining.
2. **shop.py — symmetric guards + drop the stray import.** Guard the marker blit
   (`if index == self.cursor:` or `if marker:`) to match the guarded suffix blit,
   and remove the unneeded `from __future__ import annotations` (nothing in the
   module needs deferred annotations; no other scene module has it).
3. **tests/core/test_notice_lifetime.py — exact-boundary case.** Add a test where the
   decay tick lands exactly on `notice_remaining == 0.0` (arm the notice, then tick
   with `dt_seconds` exactly equal to the remaining lifetime; the `<= 0` in
   `_world_tick` must clear it). Mind the same-tick decrement: the arming tick's own
   `dt` also decays, so compute the follow-up tick as `game.notice_remaining` exactly.
4. **tests/shell/test_busting_scene.py — docstring scope.** Reword the new Space-test
   docstring so it cannot be misread as covering the core rejection (e.g. "scene
   emits SpringSnare in non-ACTIVE phases; the core's rejection is covered by
   tests/integration/test_bust_flow.py").
5. **scenes/__init__.py — clamp elapsed.** `elapsed = max(0.0, MASCOT_ALERT_WINDOW -
   game.mascot.alert_remaining)` so a hypothetical `alert_remaining >
   MASCOT_ALERT_WINDOW` can never produce negative-parity flicker; keep the existing
   comment style. Also leave a one-line comment in `game.py::_world_tick` above the
   notice decay recording the accepted quirk: a notice armed mid-tick is decremented
   by that same tick's dt (~16 ms of a 6 s lifetime) — intentional, not worth
   arm-tick tracking. No behavioral change to the decay itself.

**Tests:** item 3 IS a test; item 5's clamp keeps every existing flash test green
(verify); items 1–2 are covered by the existing pixel/smoke tests which must stay
green. No other new tests required.

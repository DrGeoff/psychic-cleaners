# Beam-crossing backfire — design

Date: 2026-07-16
Status: Approved pending user review

## 1. Background

Main spec §4.5 states: "Crossing the two beams backfires: both cleaners
slimed, snare spent, Smudge escapes." `BustSim.tick()` (`core/bust.py`)
implements this as `beams_cross or sunk_between`, where `beams_cross` is a
`segments_cross()` check on the two beams' geometric endpoints.

A test-completeness review (2026-07-15/16) proved `beams_cross` is
mathematically unreachable under the live constants: given the current aim
formula (each beam targets `ghost_x ± BEAM_AIM_SPREAD`, tilt clamped to
`±BEAM_MAX_TILT`, aim side chosen by comparing actual cleaner positions),
`tip_left ≤ tip_right` holds for every reachable `(left_x, right_x, ghost_x)`
— confirmed both algebraically and by a 2M-sample brute-force search. The
only live backfire trigger is `sunk_between` (the ghost sinking low while
positioned between the cleaners).

Git history explains why: commit `bdc4a75` ("playtest findings ... beam
spread") introduced the `±BEAM_AIM_SPREAD` offset specifically because the
*previous* formula (both beams aiming at the literal same point, `ghost_x`)
made the beams touch/converge by default any time the ghost was centered —
reported as looking broken in real playtesting. The fix was correct for the
problem it solved, but as a side effect it made literal beam-crossing
permanently inert, orphaning the spec's stated mechanic.

## 2. Goals

- Make `beams_cross` genuinely, reliably reachable again — a player must be
  able to see the beams visually cross and get punished for it, matching the
  spec text.
- The risk must be occasional and player-caused, not a default outcome of
  ordinary centered play — the exact problem `bdc4a75` fixed must not
  reappear.
- Risk should scale with **waiting** (letting the ghost sink deeper before
  springing), reusing the same tension `sunk_between` already creates, and
  with **placement** (how close together the two cleaners were positioned) —
  wide placement should be able to fully immunize a player against this
  specific risk.
- `sunk_between` is unchanged; the new mechanic is additive, not a
  replacement.
- Minimal blast radius: confined to `BustSim` in `core/bust.py` plus new
  tuning constants. No changes to `game.py`, `events.py`, or the shell layer.

## 3. Non-goals

- No real-time player control over the beams during `ACTIVE` (out of scope —
  `MoveCleaner` is already disabled once `ACTIVE` begins, by design).
- No change to `sunk_between`'s existing thresholds or behavior.
- No attempt to hit an exact target cross-rate; starting constants are a
  reasoned first pass, expected to be tuned via playtesting the same way
  `BEAM_AIM_SPREAD` itself was.

## 4. Mechanism

Replace the fixed aim offset with a depth-scaled **tracking gain** applied to
each beam's raw pull toward the ghost, keeping today's fixed side offset:

```python
def _beam(self, x: float, other_x: float) -> tuple[Vec, Vec]:
    side_sign = -1.0 if x <= other_x else 1.0
    gain = self._tilt_gain()
    tilt = clamp(gain * (self.ghost_x - x) + side_sign * BEAM_AIM_SPREAD,
                 -BEAM_MAX_TILT, BEAM_MAX_TILT)
    return ((x, BUST_GROUND_Y), (x + tilt, BEAM_TOP_Y))

def _tilt_gain(self) -> float:
    t = clamp(
        (self.ghost_y - BEAM_NARROW_START_Y) / (BUST_GROUND_Y - BEAM_NARROW_START_Y),
        0.0, 1.0,
    )
    return 1.0 + (BEAM_MAX_GAIN - 1.0) * t
```

New constants (`core/constants.py`):

- `BEAM_NARROW_START_Y: Final[float] = SNARE_TRIGGER_Y` (280.0) — narrowing
  begins exactly when springing first becomes viable, so the player's
  "spring now vs. wait for a better shot" decision is exactly when the new
  risk starts accruing.
- `BEAM_MAX_GAIN: Final[float] = 2.0` — gain at `ghost_y == BUST_GROUND_Y`.

At `gain == 1.0` (any `ghost_y ≤ BEAM_NARROW_START_Y`) this reduces to
**exactly** today's live formula — proven safe (2M-sample search, worst-case
margin ~0) and unit-tested as a regression guard. As `ghost_y` sinks past
`BEAM_NARROW_START_Y`, gain ramps linearly to `BEAM_MAX_GAIN` by the time the
ghost reaches the ground.

### Why this satisfies both "waiting" and "placement"

Validated by brute-force search (1M samples, `gain ∈ [1, BEAM_MAX_GAIN]`,
excluding near-tie floating-point noise with a 2px margin):

| cleaner gap | robust cross rate |
|---|---|
| 0–50px | 1–10% |
| 50–250px | 10–24% |
| ≥300px | **0%, no exceptions found** |

The ≥300px cutoff is exact and stable across every `BEAM_MAX_GAIN` value
tested (1.5–4.0) — it falls out of the geometry itself (once the raw pull
exceeds `BEAM_MAX_TILT` symmetrically on both sides, order is structurally
preserved), not from a separate tunable term. No explicit "safe gap"
constant is needed; wide placement is immune by construction.

One caveat found during validation: a **dead-centered** ghost sits on an
exact symmetric knife-edge where crossing is a measure-zero floating-point
tie, not a real risk — real risk comes from the ghost being off-center
between the cleaners, which is the common case in practice since drift/repel
dynamics move it continuously and rarely land it exactly centered.

## 5. Rejected alternatives

- **Shrinking the fixed offset to 0 as the ghost sinks.** Proven (via the
  same brute-force method) to never produce a robust crossing at any offset
  value ≥ 0 — the `x <= other_x` side-comparison that determines aim
  direction is itself what guarantees non-crossing, independent of the
  offset's magnitude. Only multiplying the *position* term (this design's
  approach) breaks that guarantee.
- **Gap-scaled offset alone (no gain/depth term).** Rejected per the same
  proof — any fixed-offset formula with correct side comparison cannot
  cross, regardless of how the offset itself is scaled.
- **Compound boolean trigger** (`if narrow_gap and ghost_low and centered:
  BACKFIRE`, bypassing `segments_cross()` entirely). Simpler, but the beams
  on screen would never actually be seen crossing when it fires — defeats
  the goal of restoring a real, visible mechanic; it would just be
  `sunk_between` wearing the `BeamsCrossed` label.

## 6. Compatibility and testing plan

- The existing test fixture convention (`left_x=200, right_x=440`, gap
  240px) sits inside the newly-reachable zone once gain exceeds 1 for an
  off-center ghost. Direct computation (not just hand algebra) confirmed
  `tests/core/test_bust.py::test_no_backfire_in_skill_window`'s exact
  scenario (ghost centered at 320, `ghost_y=300`) crosses at `gain=1.25` —
  a genuine ~40px margin, not a floating-point tie. **Decided:** keep
  `BEAM_NARROW_START_Y = SNARE_TRIGGER_Y` as specified; this is an accepted,
  intentional difficulty increase for the standard 240px gap, not a
  regression to avoid. `test_no_backfire_in_skill_window` is replaced by two
  tests — one at the standard gap documenting the new risk, one at a wide
  (≥300px) gap preserving the original safe-window story, conditioned on
  placement.
- New unit tests in `test_bust.py`:
  - `gain == 1.0` (`ghost_y <= BEAM_NARROW_START_Y`) never crosses, for a
    range of placements — regression guard matching today's proven-safe
    behavior.
  - A constructed off-center, narrow-gap (<250px), low-`ghost_y` scenario
    produces `BustOutcome.BACKFIRE` via `beams_cross` specifically (assert
    `sunk_between`'s own condition is false in that scenario, isolating the
    new trigger).
  - A wide-gap (≥300px) scenario stays safe even at `ghost_y ==
    BUST_GROUND_Y` — proves the placement-immunity property end to end.
  - Existing `test_no_backfire_in_skill_window` and
    `test_no_backfire_when_low_ghost_is_outside_the_pair` re-verified or
    adjusted per the compatibility note above.
- Full existing suite (445 tests) must still pass; `ruff`/`mypy` clean.

## 7. Open questions / tuning notes for playtesting

- `BEAM_MAX_GAIN=2.0` and `BEAM_NARROW_START_Y=SNARE_TRIGGER_Y` are
  reasoned starting values, not final. Real playtesting (per this project's
  established practice — see `bdc4a75`) may adjust them.
- Resolved (see §6): `test_no_backfire_in_skill_window`'s scenario
  intentionally becomes a new risk at the standard gap; it does not stay
  backfire-free.

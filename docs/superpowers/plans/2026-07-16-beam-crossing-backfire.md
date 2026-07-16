# Beam-Crossing Backfire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `BustSim`'s `beams_cross` backfire trigger genuinely, reliably reachable (matching the main spec's "crossing the two beams backfires"), while staying inert at today's baseline and fully immune above a ~300px cleaner gap.

**Architecture:** Replace the fixed `BEAM_AIM_SPREAD` offset in `BustSim._beam()` with a depth-scaled tracking gain multiplying the ghost-pull term, via a new `_tilt_gain()` helper. At `gain=1.0` (any `ghost_y <= BEAM_NARROW_START_Y`) the formula is byte-for-byte identical to today's live formula. Two new constants in `core/constants.py`. No changes outside `bust.py`/`constants.py`/`test_bust.py`.

**Tech Stack:** Python 3.14, pytest, mypy --strict, ruff. No new dependencies.

## Global Constraints

- `mypy --strict` and `ruff check`/`ruff format` must stay clean (pre-commit enforces this on every commit).
- Full existing suite (445 tests as of this plan) must keep passing except the one test intentionally changed in Task 3 (per the approved design decision).
- No changes to `game.py`, `events.py`, or the shell layer — this is a pure `core/bust.py` + `core/constants.py` + `tests/core/test_bust.py` change.
- Design source of truth: `docs/superpowers/specs/2026-07-16-beam-crossing-backfire-design.md`. Approved decision (superseding that doc's open question): `BEAM_NARROW_START_Y` stays at `SNARE_TRIGGER_Y` (280.0); `test_no_backfire_in_skill_window` is intentionally rewritten rather than protected, because standard 240px placement becoming risky partway through the skill window is accepted as an intended difficulty increase, not a regression to avoid.

---

### Task 1: Add the two new tuning constants

**Files:**
- Modify: `src/psychic_cleaners/core/constants.py:75` (insert after the `BEAM_AIM_SPREAD` line)

**Interfaces:**
- Produces: `BEAM_NARROW_START_Y: Final[float]` (280.0), `BEAM_MAX_GAIN: Final[float]` (2.0) — consumed by Task 2's `_tilt_gain()`.

- [ ] **Step 1: Add the constants**

Insert immediately after line 75 (`BEAM_AIM_SPREAD: Final[float] = 8.0  # keeps the two beam tips from meeting at one point`), before the `BUST_TIMEOUT_SECONDS` comment block:

```python
# Beam-crossing backfire: BEAM_AIM_SPREAD alone can never let the beams
# cross (proven — see docs/superpowers/specs/2026-07-16-beam-crossing-backfire-design.md).
# Past BEAM_NARROW_START_Y the tilt gain ramps toward BEAM_MAX_GAIN, which
# CAN produce a genuine cross for an off-center ghost at a narrow-enough gap;
# gap >= ~300px is immune regardless of gain.
BEAM_NARROW_START_Y: Final[float] = SNARE_TRIGGER_Y
BEAM_MAX_GAIN: Final[float] = 2.0
```

Note: `SNARE_TRIGGER_Y` is defined earlier in the same file (line 71), so no new import is needed — this is a same-module reference.

- [ ] **Step 2: Verify the module still imports cleanly**

Run: `source .venv/bin/activate && python -c "from psychic_cleaners.core import constants; print(constants.BEAM_NARROW_START_Y, constants.BEAM_MAX_GAIN)"`
Expected: `280.0 2.0`

- [ ] **Step 3: Run mypy and ruff**

Run: `source .venv/bin/activate && python -m mypy src/psychic_cleaners/core/constants.py && python -m ruff check src/psychic_cleaners/core/constants.py`
Expected: both clean, no output beyond success messages.

- [ ] **Step 4: Commit**

```bash
git add src/psychic_cleaners/core/constants.py
git commit -m "feat: add beam-crossing narrowing constants

BEAM_NARROW_START_Y and BEAM_MAX_GAIN, unused until the next commit
implements the tilt-gain formula in BustSim._beam()."
```

---

### Task 2: Implement the depth-scaled tilt gain in `BustSim._beam()`

**Files:**
- Modify: `src/psychic_cleaners/core/bust.py:7-22` (imports), `src/psychic_cleaners/core/bust.py:89-97` (`_beam` method)
- Test: `tests/core/test_bust.py`

**Interfaces:**
- Consumes: `BEAM_NARROW_START_Y`, `BEAM_MAX_GAIN` from Task 1.
- Produces: `BustSim._tilt_gain(self) -> float` (new private method), rewritten `BustSim._beam(self, x: float, other_x: float) -> tuple[Vec, Vec]` (same signature as today — no caller changes needed since `beam_endpoints()` at line 87 already calls `self._beam(left_x, right_x)` / `self._beam(right_x, left_x)`).

- [ ] **Step 1: Write the failing test proving the new trigger is reachable**

Add to `tests/core/test_bust.py`, after `test_no_backfire_when_low_ghost_is_outside_the_pair` (currently ending at line 200):

```python
def test_beams_cross_fires_independently_of_sunk_between() -> None:
    # gap=240 (today's standard test fixture), ghost dead-centered, ghost_y=300
    # is INSIDE the existing 40px "skill window" (280-320) where sunk_between
    # cannot fire (its own threshold is ghost_y >= BEAM_CROSS_GHOST_Y == 320).
    # At this ghost_y the tilt gain is 1.25 (ramping from 1.0 at 280 to
    # BEAM_MAX_GAIN=2.0 at 360), which is already enough to saturate both
    # beams' tilts in opposite directions and produce a genuine ~40px
    # crossing margin — verified by direct computation, not a floating-point
    # tie. This is the mechanism's core deliverable: a reachable cross that
    # sunk_between's own condition cannot explain.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = 300.0
    assert sim.ghost_y < BEAM_CROSS_GHOST_Y  # sunk_between's threshold: confirms isolation
    events = sim.tick(1e-6, make_rng(7))
    assert events == [BeamsCrossed()]
    assert sim.outcome is BustOutcome.BACKFIRE
    assert sim.phase is BustPhase.RESOLVED


def test_gain_stays_at_one_below_narrow_start_y() -> None:
    # Regression guard: at ghost_y exactly BEAM_NARROW_START_Y, gain must
    # still be 1.0 (today's baseline formula), for the same gap/ghost_x that
    # crosses just 20px deeper in test_beams_cross_fires_independently_of_sunk_between.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = BEAM_NARROW_START_Y  # 280.0
    events = sim.tick(1e-6, make_rng(7))
    assert events == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_wide_gap_stays_safe_through_full_narrowing() -> None:
    # A 320px gap (well past the ~300px immunity boundary) stays safe even
    # at BUST_GROUND_Y, where gain reaches its maximum (BEAM_MAX_GAIN).
    # Proves the placement-immunity property end to end: wide-enough
    # placement fully neutralizes the new risk regardless of waiting.
    sim = _active_sim(left=140.0, right=460.0)
    sim.ghost_x = 320.0
    sim.ghost_y = BUST_GROUND_Y
    events = sim.tick(1e-6, make_rng(7))
    assert events == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE
```

Add `BEAM_NARROW_START_Y` to the existing `from psychic_cleaners.core.constants import (...)` block at the top of `tests/core/test_bust.py` (alphabetical, between `BEAM_MAX_TILT` and `BEAM_TOP_Y`):

```python
from psychic_cleaners.core.constants import (
    BEAM_AIM_SPREAD,
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_TILT,
    BEAM_NARROW_START_Y,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    BUST_TIMEOUT_SECONDS,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
```

- [ ] **Step 2: Run the new tests to verify they fail correctly**

Run: `source .venv/bin/activate && python -m pytest tests/core/test_bust.py::test_beams_cross_fires_independently_of_sunk_between tests/core/test_bust.py::test_gain_stays_at_one_below_narrow_start_y tests/core/test_bust.py::test_wide_gap_stays_safe_through_full_narrowing -v --no-cov`

Expected: `test_beams_cross_fires_independently_of_sunk_between` FAILS (`events == []`, not `[BeamsCrossed()]` — today's formula never crosses). The other two PASS already (today's code already satisfies "stay safe" — they're characterization tests for behavior that must be preserved, not red/green for new behavior). Confirm exactly one failure.

- [ ] **Step 3: Implement `_tilt_gain()` and rewrite `_beam()`**

In `src/psychic_cleaners/core/bust.py`, change the import block (lines 7-22) to add the two new constants (alphabetical):

```python
from psychic_cleaners.core.constants import (
    BEAM_AIM_SPREAD,
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_GAIN,
    BEAM_MAX_TILT,
    BEAM_NARROW_START_Y,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    BUST_TIMEOUT_SECONDS,
    GHOST_DRIFT_SPEED,
    GHOST_REPEL_SPEED,
    GHOST_SINK_SPEED,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
```

Replace the `_beam` method (lines 89-97):

```python
    def _beam(self, x: float, other_x: float) -> tuple[Vec, Vec]:
        # Aim off the ghost's dead centre — the geometrically LEFT cleaner (the
        # smaller of the two placed x's) aims left of ghost_x, the RIGHT aims
        # right of it — so the two tips never converge to one point (the
        # forbidden "crossed streams" look) even when the ghost sits dead
        # centre between the cleaners, AS LONG AS the tracking gain stays at
        # its baseline of 1.0 (proven: docs/superpowers/specs/2026-07-16-
        # beam-crossing-backfire-design.md). Past BEAM_NARROW_START_Y the gain
        # ramps up with depth, which CAN let the tips invert for a
        # narrow-enough gap and an off-center ghost — that's the intended,
        # now-reachable "crossing the streams" backfire.
        side_sign = -1.0 if x <= other_x else 1.0
        tilt = clamp(
            self._tilt_gain() * (self.ghost_x - x) + side_sign * BEAM_AIM_SPREAD,
            -BEAM_MAX_TILT,
            BEAM_MAX_TILT,
        )
        return ((x, BUST_GROUND_Y), (x + tilt, BEAM_TOP_Y))

    def _tilt_gain(self) -> float:
        """1.0 at/above BEAM_NARROW_START_Y-depth-or-shallower, ramping
        linearly to BEAM_MAX_GAIN by BUST_GROUND_Y."""
        t = clamp(
            (self.ghost_y - BEAM_NARROW_START_Y) / (BUST_GROUND_Y - BEAM_NARROW_START_Y),
            0.0,
            1.0,
        )
        return 1.0 + (BEAM_MAX_GAIN - 1.0) * t
```

- [ ] **Step 4: Run the three new tests again to verify they all pass**

Run: `source .venv/bin/activate && python -m pytest tests/core/test_bust.py::test_beams_cross_fires_independently_of_sunk_between tests/core/test_bust.py::test_gain_stays_at_one_below_narrow_start_y tests/core/test_bust.py::test_wide_gap_stays_safe_through_full_narrowing -v --no-cov`
Expected: all 3 PASS.

- [ ] **Step 5: Run the two existing baseline-formula tests to confirm no regression**

Run: `source .venv/bin/activate && python -m pytest tests/core/test_bust.py::test_beam_tilt_clamped tests/core/test_bust.py::test_beam_aims_left_and_right_of_ghost_when_within_tilt -v --no-cov`
Expected: both PASS unchanged (both use the default `ghost_y=160.0`, well below `BEAM_NARROW_START_Y=280.0`, so `_tilt_gain()` returns exactly 1.0 and the formula is byte-identical to before).

- [ ] **Step 6: Run the full test_bust.py file**

Run: `source .venv/bin/activate && python -m pytest tests/core/test_bust.py -v --no-cov`
Expected: every test passes **except** `test_no_backfire_in_skill_window`, which now fails (this is the expected, approved behavior change — fixed in Task 3). Confirm no other unexpected failures.

- [ ] **Step 7: mypy and ruff**

Run: `source .venv/bin/activate && python -m mypy src/psychic_cleaners/core/bust.py tests/core/test_bust.py && python -m ruff check src/psychic_cleaners/core/bust.py tests/core/test_bust.py && python -m ruff format --check src/psychic_cleaners/core/bust.py tests/core/test_bust.py`
Expected: all clean.

- [ ] **Step 8: Commit**

```bash
git add src/psychic_cleaners/core/bust.py tests/core/test_bust.py
git commit -m "feat: make beam-crossing backfire genuinely reachable

Replace the fixed BEAM_AIM_SPREAD offset in BustSim._beam() with a
depth-scaled tracking gain (_tilt_gain()): gain stays at 1.0 (today's
exact live formula, proven never to cross) until the ghost sinks past
BEAM_NARROW_START_Y, then ramps to BEAM_MAX_GAIN by BUST_GROUND_Y. Past
gain=1.0 the beams can genuinely cross for an off-center ghost at a
narrow-enough cleaner gap (~<250px); gap >= ~300px stays immune
regardless of gain, restoring the main spec's stated mechanic without
reintroducing the by-default convergence bdc4a75 fixed.

test_no_backfire_in_skill_window now fails as an expected consequence
(fixed in the next commit)."
```

---

### Task 3: Update the skill-window test for the new, intended behavior

**Files:**
- Modify: `tests/core/test_bust.py` (replace `test_no_backfire_in_skill_window`)

**Interfaces:**
- Consumes: `BustSim` as modified in Task 2. No production code changes in this task.

- [ ] **Step 1: Replace `test_no_backfire_in_skill_window`**

Find and remove this test (current body, for reference — it now fails after Task 2):

```python
def test_no_backfire_in_skill_window() -> None:
    # SNARE_TRIGGER_Y (280) < BEAM_CROSS_GHOST_Y (320): in the 40px band between
    # them the ghost is already springable but not yet backfiring.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = (SNARE_TRIGGER_Y + BEAM_CROSS_GHOST_Y) / 2  # 300.0, inside the window
    assert sim.tick(1e-6, make_rng(7)) == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE
```

Replace it with:

```python
def test_standard_gap_now_risky_partway_through_skill_window() -> None:
    # Design decision (2026-07-16-beam-crossing-backfire-design.md, approved
    # supersession of its own open question): the 40px "skill window"
    # (SNARE_TRIGGER_Y=280 to BEAM_CROSS_GHOST_Y=320) is deliberately no
    # longer risk-free for the STANDARD 240px cleaner gap this whole test
    # file otherwise uses as its default. This is the same exact scenario as
    # test_beams_cross_fires_independently_of_sunk_between in test_bust.py —
    # duplicated here under this name to keep the skill-window story
    # discoverable at its original location.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = (SNARE_TRIGGER_Y + BEAM_CROSS_GHOST_Y) / 2  # 300.0
    events = sim.tick(1e-6, make_rng(7))
    assert events == [BeamsCrossed()]
    assert sim.outcome is BustOutcome.BACKFIRE


def test_wide_gap_keeps_skill_window_safe() -> None:
    # The ORIGINAL intent of test_no_backfire_in_skill_window — a safe
    # springable-but-not-yet-backfiring window — still holds, but now
    # conditioned on placement: a cleaner gap at or past the ~300px
    # immunity boundary keeps the window fully safe, same ghost_y as above.
    sim = _active_sim(left=140.0, right=460.0)  # gap=320
    sim.ghost_x = 320.0
    sim.ghost_y = (SNARE_TRIGGER_Y + BEAM_CROSS_GHOST_Y) / 2  # 300.0
    assert sim.tick(1e-6, make_rng(7)) == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE
```

- [ ] **Step 2: Run the full test_bust.py file**

Run: `source .venv/bin/activate && python -m pytest tests/core/test_bust.py -v --no-cov`
Expected: all tests pass, including the two new ones and
`test_no_backfire_when_low_ghost_is_outside_the_pair` (unchanged — verify it
still passes: ghost_x=100 is outside the pair, tilt gain at ghost_y=330 is
1.25, and the required tilt magnitude for the far cleaner saturates in a
way that preserves tip ordering — confirmed by direct computation during
design).

- [ ] **Step 3: mypy and ruff**

Run: `source .venv/bin/activate && python -m mypy tests/core/test_bust.py && python -m ruff check tests/core/test_bust.py && python -m ruff format --check tests/core/test_bust.py`
Expected: all clean.

- [ ] **Step 4: Commit**

```bash
git add tests/core/test_bust.py
git commit -m "test: update skill-window expectations for reachable beam-crossing

test_no_backfire_in_skill_window described a guarantee that no longer
holds for the standard 240px cleaner gap after the previous commit;
split into test_standard_gap_now_risky_partway_through_skill_window
(documents the accepted new risk) and test_wide_gap_keeps_skill_window_safe
(preserves the original safe-window story, conditioned on wide placement)."
```

---

### Task 4: Full-suite verification

**Files:** None modified — verification only.

- [ ] **Step 1: Run the complete test suite with coverage**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: all tests pass (446 total: 445 baseline + 1 net new — Task 2 added 3, Task 3 removed 1 and added 2, net +4 from Task 2's baseline... reconcile the exact count from the actual run rather than assuming; the important check is zero failures and zero errors). Coverage stays at or above the prior 99% on `core/`.

- [ ] **Step 2: Run mypy and ruff across the whole project**

Run: `source .venv/bin/activate && python -m mypy src tests && python -m ruff check src tests && python -m ruff format --check src tests`
Expected: all three clean.

- [ ] **Step 3: If everything is green, no further action — the pre-commit hooks already validated each commit in Tasks 1-3.**

If any check fails at this stage (e.g., a cross-file interaction missed by per-task verification), fix it and create a new commit — do not amend prior commits.

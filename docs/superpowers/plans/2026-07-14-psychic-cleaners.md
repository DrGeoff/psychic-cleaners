# Psychic Cleaners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full clean-room Psychic Cleaners game — a mechanically faithful, fully re-themed remake of the 1984 C64 classic — as small, independently testable components, per the approved spec at `docs/superpowers/specs/2026-07-13-psychic-cleaners-design.md`.

**Architecture:** Pure-Python simulation core (`core/` — deterministic, injectable RNG/clock, command-in/event-out, zero pygame imports) under a thin pygame-ce shell (`shell/` — rendering, input mapping, synthesized audio). The top-level `Game` state machine grows field-by-field as each mechanic's module lands, so every milestone ends runnable and CI-green.

**Tech Stack:** Python ≥3.14, pygame-ce, uv, ruff (lint+format), mypy --strict, pytest, pytest-cov, Hypothesis, pre-commit, GitHub Actions.

## Global Constraints

Every task's requirements implicitly include these (from the spec):

- `requires-python = ">=3.14"`; the only runtime dependency is `pygame-ce>=2.5.7`, and only `shell/` may import pygame. `core/` must never import pygame.
- All code passes `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy` (strict) at the end of every task; every task ends with a conventional commit.
- All gameplay numbers live in `core/constants.py` — never inline a tunable.
- Documented original values are fixed: starting bankroll $10,000; PSI cap 9999; stomp fine $4,000; vehicle prices $2,000/$4,800/$6,000/$15,000; equipment prices per the contract appendix.
- The strings "Ghostbusters", "Slimer", "Stay-Puft", "Zuul", "Ecto" must never appear in code, tests, assets, comments, or docs — theme names only (Psychic Cleaners, Wisps, Smudge, Sir Squish, the Warden/Locksmith, Threshold Tower, the Depot).
- Tests touching pygame rely on `tests/conftest.py` exporting `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`; core tests use `make_rng(seed)` for determinism.
- All commands run through uv (`uv run pytest`, `uv run mypy`, …); dependencies are installed only in Task 1.
- The **Interface Contract** appendix at the end of this plan is the single source of truth for names, signatures, and constant values. When a task and the contract disagree, the contract wins.

---

## Milestone 1: Skeleton & tooling

Goal: convert the bare uv-init repo into the contract's src layout with full tooling (uv, ruff, mypy --strict, pytest+coverage, pre-commit, GitHub Actions) and a minimal pygame-ce app shell. When this milestone lands, `uv run psychic-cleaners` opens a 1280x800 window rendering a dark-blue 640x400 logical surface with an FPS counter, closable via the window's close button.

### Task 1: Project skeleton and tooling configuration

**Files:**
- Create: src/psychic_cleaners/__init__.py
- Create: src/psychic_cleaners/py.typed
- Create: src/psychic_cleaners/core/__init__.py (empty)
- Create: src/psychic_cleaners/shell/__init__.py (empty)
- Create: src/psychic_cleaners/shell/scenes/__init__.py (empty for now)
- Create: tests/conftest.py
- Create: tests/core/, tests/integration/, tests/shell/ directories
- Modify: pyproject.toml (complete rewrite)
- Modify: .gitignore (add tool caches and coverage)
- Delete: main.py (uv-init placeholder; untracked, so plain `rm`)
- Test: tests/core/test_sanity.py

**Interfaces:**
- Consumes: the contract's Tooling contract section (dependency groups, ruff/mypy/pytest config) and Package layout section.
- Produces: `psychic_cleaners.__version__ == "0.1.0"`; tests/conftest.py that sets `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` at import time (all later shell tests rely on this); the `uv run pytest` / `uv run ruff check .` / `uv run mypy` quality-gate commands every later task uses. The `rng` fixture is added in Task 4, NOT here.

- [ ] **Step 1: Create the directory skeleton and remove the placeholder entry point**

Run:
```bash
mkdir -p src/psychic_cleaners/core src/psychic_cleaners/shell/scenes \
         tests/core tests/integration tests/shell
touch src/psychic_cleaners/__init__.py \
      src/psychic_cleaners/core/__init__.py \
      src/psychic_cleaners/shell/__init__.py \
      src/psychic_cleaners/shell/scenes/__init__.py
rm main.py
```
All four `__init__.py` files start empty (`__version__` is added test-first in Step 7). `tests/` gets NO `__init__.py` files — plain pytest discovery. Empty directories (`tests/integration`, for now) are not tracked by git; that is fine, later tasks add files to them.

- [ ] **Step 2: Rewrite pyproject.toml completely**

Replace the entire contents of `pyproject.toml` with:
```toml
[project]
name = "psychic-cleaners"
version = "0.1.0"
description = "Clean-room retro remake: run a paranormal sanitation franchise"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "pygame-ce>=2.5.7",
]

[project.scripts]
psychic-cleaners = "psychic_cleaners.shell.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/psychic_cleaners"]

[dependency-groups]
dev = [
    "pytest",
    "pytest-cov",
    "hypothesis",
    "ruff",
    "mypy",
    "pre-commit",
]

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF"]

[tool.mypy]
strict = true
files = ["src", "tests"]
mypy_path = ["src"]
explicit_package_bases = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=psychic_cleaners --cov-report=term-missing"
```
Notes: `explicit_package_bases` + `mypy_path = ["src"]` lets mypy --strict check the `__init__.py`-less `tests/` tree without module-name collisions; no `[[tool.mypy.overrides]]` block is needed. Coverage has NO `fail-under` yet — the gate is added in the project's final task. The `psychic-cleaners` script points at `psychic_cleaners.shell.app:main`, which does not exist until Task 3; entry points are resolved at run time, so installation still succeeds.

- [ ] **Step 3: Extend .gitignore**

Replace the entire contents of `.gitignore` with:
```gitignore
# Python-generated files
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info

# Virtual environments
.venv

# Tool caches and coverage
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
```

- [ ] **Step 4: Install the environment**

Run: `uv sync`
Expected: resolves and installs the project (editable) plus `pygame-ce` and the dev group — output ends with lines listing installed packages including `hypothesis`, `mypy`, `pre-commit`, `pygame-ce`, `pytest`, `pytest-cov`, `ruff`, and `psychic-cleaners==0.1.0`. `uv.lock` is updated. (uv installs the `dev` dependency group by default.)

- [ ] **Step 5: Write tests/conftest.py and the failing sanity test**

Create `tests/conftest.py`:
```python
"""Global test configuration.

Sets SDL dummy drivers at import time, BEFORE any test module can import
pygame, so shell tests run headless on any machine and in CI.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
```
(The fixed-seed `rng` fixture is deliberately NOT added here — Task 4 adds it once `core/rng.py` exists.)

Create `tests/core/test_sanity.py`:
```python
"""Sanity check: the package imports and declares its version."""

import psychic_cleaners


def test_version() -> None:
    assert psychic_cleaners.__version__ == "0.1.0"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/core/test_sanity.py -v`
Expected: FAIL with `AttributeError: module 'psychic_cleaners' has no attribute '__version__'` (the package imports because Step 1 created an empty `__init__.py`, but no version is defined yet).

- [ ] **Step 7: Write minimal implementation**

Replace the (empty) contents of `src/psychic_cleaners/__init__.py` with:
```python
"""Psychic Cleaners: a clean-room retro remake of a 1984 franchise-management game."""

__version__ = "0.1.0"
```
Create the PEP 561 marker so mypy treats the installed package as typed:
```bash
touch src/psychic_cleaners/py.typed
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/core/test_sanity.py -v`
Expected: PASS — `1 passed`, followed by a coverage table showing `src/psychic_cleaners/__init__.py` at 100%.

- [ ] **Step 9: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: `All checks passed!`, `N files left unchanged` (or reformatted on first run — re-run until unchanged), and `Success: no issues found in 6 source files`.

- [ ] **Step 10: Commit**

This is the repository's first commit; the pre-existing untracked files (`README.md`, `.python-version`, `uv.lock`, `.gitignore`, `pyproject.toml`) go in with it:
```bash
git add .gitignore .python-version README.md pyproject.toml uv.lock src tests
git commit -m "chore: src-layout skeleton and uv/ruff/mypy/pytest tooling"
```

### Task 2: Pre-commit hooks and GitHub Actions CI

**Files:**
- Create: .pre-commit-config.yaml
- Create: .github/workflows/ci.yml
- Test: `uv run pre-commit run --all-files` (no pytest test — this task is pure tooling)

**Interfaces:**
- Consumes: Task 1's pyproject configuration (`[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`) and the `pre-commit` dev dependency Task 1 installed.
- Produces: a CI pipeline (`ruff check`, `ruff format --check`, `mypy`, `pytest` under SDL dummy drivers) that every later milestone must keep green, and local pre-commit hooks enforcing the same lint/type gates.

- [ ] **Step 1: Verify pre-commit fails without configuration**

Run: `uv run pre-commit run --all-files`
Expected: FAIL — `No .pre-commit-config.yaml file was found` (exit code 1). Confirms the tool is installed and unconfigured.

- [ ] **Step 2: Write .pre-commit-config.yaml**

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.12.2
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy
        language: system
        types: [python]
        pass_filenames: false
```
The mypy hook is a `local`/`system` hook running `uv run mypy` with `pass_filenames: false`, so it always checks the full `files = ["src", "tests"]` set from pyproject rather than only staged files.

- [ ] **Step 3: Write .github/workflows/ci.yml**

Run: `mkdir -p .github/workflows`

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        run: uv sync
      - name: Lint
        run: uv run ruff check .
      - name: Format check
        run: uv run ruff format --check .
      - name: Type check
        run: uv run mypy
      - name: Tests
        run: uv run pytest
        env:
          SDL_VIDEODRIVER: dummy
          SDL_AUDIODRIVER: dummy
```

- [ ] **Step 4: Stage the new files and verify pre-commit passes**

pre-commit only sees files git knows about, so stage first:
```bash
git add .pre-commit-config.yaml .github/workflows/ci.yml
uv run pre-commit run --all-files
```
Expected: PASS — the first run prints `Installing environment for https://github.com/astral-sh/ruff-pre-commit` once, then:
```
ruff.....................................................................Passed
ruff-format..............................................................Passed
mypy.....................................................................Passed
```

- [ ] **Step 5: Install the git hook and run quality gates**

```bash
uv run pre-commit install
uv run ruff check . && uv run ruff format . && uv run mypy
```
Expected: `pre-commit installed at .git/hooks/pre-commit`; then all gates clean, same as Task 1 Step 9.

- [ ] **Step 6: Commit**

```bash
git add .pre-commit-config.yaml .github/workflows/ci.yml
git commit -m "ci: add pre-commit hooks and GitHub Actions workflow"
```
Expected: the freshly installed pre-commit hook runs ruff, ruff-format, and mypy during the commit and all pass. (CI itself is verified on the next push to GitHub — all four steps must be green.)

### Task 3: App shell: window, fixed timestep, blank frame

**Files:**
- Create: src/psychic_cleaners/shell/app.py
- Create: src/psychic_cleaners/__main__.py
- Test: tests/shell/test_app_smoke.py

**Interfaces:**
- Consumes: `psychic_cleaners` package from Task 1; SDL dummy drivers from tests/conftest.py.
- Produces (per contract, later tasks extend but must not rename): `LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)`, `WINDOW_SCALE: Final[int] = 2`, `FPS: Final[int] = 60`, `class App` with `__init__(self, seed: int | None = None) -> None`, `def step(self, dt: float) -> None`, `def run(self) -> None`, and `def main() -> None` (the `psychic-cleaners` console entry point). `App.logical` is the 640x400 `pygame.Surface` all scene drawing will target. Game state, scenes, `SpriteFactory`, `TextRenderer`, and `AudioBank` arrive in later tasks — this version must NOT reference any of them.

- [ ] **Step 1: Write the failing smoke test**

Create `tests/shell/test_app_smoke.py`:
```python
"""Headless smoke test: the app constructs and renders frames under SDL dummy drivers."""

import pygame

from psychic_cleaners.shell.app import FPS, LOGICAL_SIZE, WINDOW_SCALE, App


def test_shell_constants() -> None:
    assert LOGICAL_SIZE == (640, 400)
    assert WINDOW_SCALE == 2
    assert FPS == 60


def test_app_constructs_and_steps() -> None:
    app = App(seed=1)
    try:
        app.step(1 / 60)
        app.step(1 / 60)
        assert app.logical.get_size() == LOGICAL_SIZE
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_app_smoke.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'psychic_cleaners.shell.app'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/psychic_cleaners/shell/app.py`:
```python
"""Application shell: window, logical surface, fixed-timestep main loop.

Minimal version. Later tasks add the Game, scene registry, sprite factory,
text renderer, and audio bank; the names below are contract-fixed.
"""

from typing import Final

import pygame

LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)
WINDOW_SCALE: Final[int] = 2
FPS: Final[int] = 60

_BACKGROUND: Final[tuple[int, int, int]] = (16, 16, 32)
_FPS_COLOR: Final[tuple[int, int, int]] = (230, 230, 230)


class App:
    """Owns the window, the 640x400 logical surface, and the main loop."""

    def __init__(self, seed: int | None = None) -> None:
        pygame.init()
        self.seed = seed
        self.window = pygame.display.set_mode(
            (LOGICAL_SIZE[0] * WINDOW_SCALE, LOGICAL_SIZE[1] * WINDOW_SCALE)
        )
        pygame.display.set_caption("Psychic Cleaners")
        self.logical = pygame.Surface(LOGICAL_SIZE)
        self._font = pygame.font.Font(None, 20)

    def step(self, dt: float) -> None:
        """Render one frame: clear, draw FPS, scale the logical surface up, flip."""
        fps = 0.0 if dt <= 0.0 else 1.0 / dt
        self.logical.fill(_BACKGROUND)
        fps_surface = self._font.render(f"FPS: {fps:.0f}", True, _FPS_COLOR)
        self.logical.blit(fps_surface, (4, 4))
        pygame.transform.scale(self.logical, self.window.get_size(), self.window)
        pygame.display.flip()

    def run(self) -> None:
        """Fixed-timestep loop at FPS until the window is closed."""
        clock = pygame.time.Clock()
        running = True
        while running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.step(dt)


def main() -> None:
    """Console entry point (see [project.scripts] in pyproject.toml).

    Exception-safe per the contract: pygame.quit() runs exactly once, in the
    finally, even if run() raises.
    """
    app = App()
    try:
        app.run()
    finally:
        pygame.quit()
```

Create `src/psychic_cleaners/__main__.py`:
```python
"""Module entry point: python -m psychic_cleaners."""

from psychic_cleaners.shell.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/shell/test_app_smoke.py -v`
Expected: PASS — `2 passed`. No window appears: conftest.py set `SDL_VIDEODRIVER=dummy` before pygame was imported.

- [ ] **Step 5: Run the full suite and the game by hand**

Run: `uv run pytest`
Expected: `3 passed` (sanity + two smoke tests), coverage table lists `app.py` (its `run`/`main` lines uncovered — acceptable, no fail-under gate yet).

Then, on a machine with a real display, run: `uv run psychic-cleaners`
Expected: a 1280x800 window titled "Psychic Cleaners" filled dark blue with `FPS: 60` (approximately) in the top-left; closing the window exits cleanly with exit code 0. On a headless machine use `SDL_VIDEODRIVER=dummy timeout 2 uv run psychic-cleaners` instead and expect it to idle until the timeout kills it (exit code 124) without a traceback.

- [ ] **Step 6: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: `All checks passed!`, `N files left unchanged`, `Success: no issues found in 9 source files`.

- [ ] **Step 7: Commit**

```bash
git add src/psychic_cleaners/shell/app.py src/psychic_cleaners/__main__.py \
        tests/shell/test_app_smoke.py
git commit -m "feat: app shell with scaled window, fixed-timestep loop, FPS counter"
```
Expected: pre-commit hooks pass; milestone complete — CI green, game runnable.

---

## Milestone 2: Core spine

Goal: put the deterministic heart of the game in place — every gameplay constant, the seedable RNG, the game clock, the full Command/Event vocabulary, and a `Game` state-machine skeleton that later milestones extend with real scene logic. When this milestone lands nothing new appears on screen; the change is that `core.game.Game` becomes drivable headlessly (TITLE → SHOP, GAME_OVER → TITLE, world-time gating) and is fully covered by unit plus integration tests.

### Task 4: Gameplay constants and seedable RNG

**Files:**
- Create: `src/psychic_cleaners/core/constants.py`
- Create: `src/psychic_cleaners/core/rng.py`
- Test: `tests/core/test_constants.py`
- Test: `tests/core/test_rng.py`
- Modify: `tests/conftest.py` (add the `rng` fixture; keeps the SDL dummy-driver lines from Task 1)

**Interfaces:**
- Consumes: nothing (first core modules).
- Produces: every constant in the contract's `core/constants.py` listing (exact names and values, all `Final`); `Rng` Protocol with `random() -> float`, `randint(a: int, b: int) -> int`, `uniform(a: float, b: float) -> float`, `choice[T](seq: Sequence[T]) -> T`; `make_rng(seed: int) -> Rng`; pytest fixture `rng` = `make_rng(1234)` in `tests/conftest.py`.

- [ ] **Step 1: Write the failing constants test**

Create `tests/core/test_constants.py`:

```python
"""Guard the documented gameplay values against typos.

Only the historically documented numbers are pinned here; the full constant
set is exercised implicitly by every other core test.
"""

from psychic_cleaners.core import constants


def test_documented_values() -> None:
    assert constants.STARTING_BANKROLL == 10_000
    assert constants.PSI_MAX == 9_999
    assert constants.STOMP_FINE == 4_000
```

- [ ] **Step 2: Run the constants test to verify it fails**

Run: `uv run pytest tests/core/test_constants.py -v`
Expected: FAIL — collection error, `ImportError: cannot import name 'constants' from 'psychic_cleaners.core'`

- [ ] **Step 3: Write the constants module**

Create `src/psychic_cleaners/core/constants.py`. This is the single tuning point for the whole game — every gameplay number lives here, nowhere else. Values and names are fixed by the interface contract; copy them exactly:

```python
"""Every gameplay number in the game. The single tuning point."""

from typing import Final

# economy (documented values from the original)
STARTING_BANKROLL: Final[int] = 10_000
STOMP_FINE: Final[int] = 4_000
VACUUM_BOUNTY: Final[int] = 100
BUST_BASE_FEE: Final[int] = 300
BUST_FEE_PER_1000_PSI: Final[int] = 100
MAX_BANKROLL: Final[int] = 9_999_999

# psi
PSI_MAX: Final[int] = 9_999
PSI_GROWTH_PER_MINUTE: Final[float] = 250.0
PSI_HAUNT_GROWTH_PER_MINUTE: Final[float] = 100.0  # per active haunting
WISP_TOWER_PSI_JUMP: Final[int] = 100
STOMP_PSI_SPIKE: Final[int] = 500

# time
GAME_MINUTES_PER_REAL_SECOND: Final[float] = 1.0

# cleaners
CLEANER_COUNT: Final[int] = 3
FINALE_NEEDED_INSIDE: Final[int] = 2

# items
BAIT_PACK_SIZE: Final[int] = 5
CONTAINMENT_RIG_CAPACITY: Final[int] = 10

# city grid
GRID_WIDTH: Final[int] = 10
GRID_HEIGHT: Final[int] = 6
TOWER_POS: Final[tuple[int, int]] = (5, 3)
DEPOT_POS: Final[tuple[int, int]] = (0, 5)
BLOCK_LENGTH: Final[float] = 400.0  # travel units per manhattan step
HAUNT_CHANCE_PER_MINUTE: Final[float] = 0.8  # scaled by (1 + psi/PSI_MAX)
MAX_ACTIVE_HAUNTS: Final[int] = 4
WISP_SPAWN_PER_MINUTE: Final[float] = 0.6
WISP_MAP_SPEED: Final[float] = 0.05  # grid cells per real second

# drive scene
DRIVE_LANES: Final[int] = 3
CAR_X: Final[float] = 80.0
ROAD_WISP_SPAWN_PER_SECOND: Final[float] = 0.5
ROAD_WISP_SPEED: Final[float] = 120.0  # toward the car, units/sec
CATCH_RANGE: Final[float] = 24.0
FAINT_WISP_CHANCE: Final[float] = 0.3
ROAD_LENGTH_VISIBLE: Final[float] = 640.0

# bust scene (logical coordinates, 640x400 space)
BUST_GROUND_Y: Final[float] = 360.0
BEAM_TOP_Y: Final[float] = 120.0
BEAM_MAX_TILT: Final[float] = 140.0
GHOST_DRIFT_SPEED: Final[float] = 60.0
GHOST_SINK_SPEED: Final[float] = 8.0
GHOST_REPEL_SPEED: Final[float] = 90.0
SLIME_RANGE: Final[float] = 28.0
SNARE_WIDTH: Final[float] = 48.0
SNARE_TRIGGER_Y: Final[float] = 280.0
CLEANER_SPEED: Final[float] = 180.0  # px/sec while positioning
BUST_MIN_X: Final[float] = 40.0
BUST_MAX_X: Final[float] = 600.0

# mascot (Sir Squish)
MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI: Final[float] = 0.15
MASCOT_ALERT_WINDOW: Final[float] = 10.0  # real seconds to deploy bait

# finale
DOOR_X: Final[float] = 560.0
GIANT_MIN_X: Final[float] = 180.0
GIANT_MAX_X: Final[float] = 460.0
GIANT_SPEED: Final[float] = 220.0  # triangle-wave bounce, px/sec
RUNNER_START_X: Final[float] = 40.0
RUNNER_SPEED: Final[float] = 160.0
SQUASH_RANGE: Final[float] = 36.0
```

- [ ] **Step 4: Run the constants test to verify it passes**

Run: `uv run pytest tests/core/test_constants.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Write the failing RNG test**

Create `tests/core/test_rng.py`. Note `_sample` is annotated to take `Rng` (the Protocol), not `random.Random` — this proves the returned object is usable through the Protocol type:

```python
"""The seedable RNG: determinism per seed, divergence across seeds."""

from collections.abc import Sequence

from psychic_cleaners.core.rng import Rng, make_rng


def _sample(rng: Rng, seq: Sequence[str]) -> tuple[float, int, float, str]:
    return (rng.random(), rng.randint(1, 100), rng.uniform(0.0, 10.0), rng.choice(seq))


def test_same_seed_gives_identical_sequence() -> None:
    a = make_rng(42)
    b = make_rng(42)
    items = ["wisp", "smudge", "snare"]
    for _ in range(20):
        assert _sample(a, items) == _sample(b, items)


def test_different_seeds_give_different_sequences() -> None:
    a = make_rng(1)
    b = make_rng(2)
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_usable_through_the_rng_protocol() -> None:
    value = _sample(make_rng(7), ["only"])
    assert 0.0 <= value[0] < 1.0
    assert 1 <= value[1] <= 100
    assert 0.0 <= value[2] <= 10.0
    assert value[3] == "only"
```

- [ ] **Step 6: Run the RNG test to verify it fails**

Run: `uv run pytest tests/core/test_rng.py -v`
Expected: FAIL — collection error, `ModuleNotFoundError: No module named 'psychic_cleaners.core.rng'`

- [ ] **Step 7: Write the RNG module**

Create `src/psychic_cleaners/core/rng.py`. All core randomness flows through this Protocol so tests can seed it; `random.Random` satisfies it structurally:

```python
"""Seedable RNG protocol. All core randomness is injected through this."""

import random
from collections.abc import Sequence
from typing import Protocol


class Rng(Protocol):
    """The subset of random.Random the core is allowed to use."""

    def random(self) -> float: ...

    def randint(self, a: int, b: int) -> int: ...

    def uniform(self, a: float, b: float) -> float: ...

    def choice[T](self, seq: Sequence[T]) -> T: ...


def make_rng(seed: int) -> Rng:
    """Return a deterministic Rng seeded with `seed`."""
    return random.Random(seed)
```

- [ ] **Step 8: Run the RNG test to verify it passes**

Run: `uv run pytest tests/core/test_rng.py -v`
Expected: PASS (3 passed)

- [ ] **Step 9: Add the `rng` fixture to conftest**

Task 1 created `tests/conftest.py` with the SDL dummy-driver lines. Replace the whole file with the version below — same SDL behaviour, plus the fixed-seed `rng` fixture that later core tests use:

```python
"""Shared pytest configuration.

Sets SDL dummy drivers at import time, before any test module imports
pygame, so shell tests run headless. Provides a fixed-seed rng fixture
for deterministic core tests.
"""

import os

import pytest

from psychic_cleaners.core.rng import Rng, make_rng

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def rng() -> Rng:
    return make_rng(1234)
```

- [ ] **Step 10: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS — everything green, including the Task 1–3 tests

- [ ] **Step 11: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean — no lint errors, `N files left unchanged` (or reformatted before commit), no mypy errors

- [ ] **Step 12: Commit**

```bash
git add src/psychic_cleaners/core/constants.py src/psychic_cleaners/core/rng.py \
    tests/core/test_constants.py tests/core/test_rng.py tests/conftest.py
git commit -m "feat: add gameplay constants and seedable rng protocol"
```

### Task 5: Game clock

**Files:**
- Create: `src/psychic_cleaners/core/clock.py`
- Test: `tests/core/test_clock.py`

**Interfaces:**
- Consumes: `GAME_MINUTES_PER_REAL_SECOND` from `psychic_cleaners.core.constants` (Task 4).
- Produces: `GameClock` dataclass — field `minutes: float = 0.0`, method `advance(dt_seconds: float) -> None`. Task 7's `Game` holds one; Milestone 5's PSI model reads game time through it.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_clock.py`:

```python
"""GameClock converts real seconds into accumulated game minutes."""

import pytest

from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.constants import GAME_MINUTES_PER_REAL_SECOND


def test_starts_at_zero() -> None:
    assert GameClock().minutes == 0.0


def test_advance_sixty_seconds() -> None:
    clock = GameClock()
    clock.advance(60.0)
    assert clock.minutes == pytest.approx(60.0 * GAME_MINUTES_PER_REAL_SECOND)


def test_accumulates_across_calls() -> None:
    clock = GameClock()
    clock.advance(10.0)
    clock.advance(20.0)
    assert clock.minutes == pytest.approx(30.0 * GAME_MINUTES_PER_REAL_SECOND)


def test_fractional_dt() -> None:
    clock = GameClock()
    for _ in range(3):
        clock.advance(1.0 / 60.0)
    assert clock.minutes == pytest.approx((3.0 / 60.0) * GAME_MINUTES_PER_REAL_SECOND)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_clock.py -v`
Expected: FAIL — collection error, `ModuleNotFoundError: No module named 'psychic_cleaners.core.clock'`

- [ ] **Step 3: Write minimal implementation**

Create `src/psychic_cleaners/core/clock.py`:

```python
"""Game-time model: real seconds in, game minutes accumulated."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import GAME_MINUTES_PER_REAL_SECOND


@dataclass
class GameClock:
    minutes: float = 0.0

    def advance(self, dt_seconds: float) -> None:
        self.minutes += dt_seconds * GAME_MINUTES_PER_REAL_SECOND
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_clock.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/clock.py tests/core/test_clock.py
git commit -m "feat: add game clock"
```

### Task 6: Command and event vocabulary

**Files:**
- Create: `src/psychic_cleaners/core/events.py`
- Test: `tests/core/test_events.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `type GridPos = tuple[int, int]`; `SceneId` enum (TITLE, SHOP, MAP, DRIVE, BUST, FINALE, GAME_OVER); frozen dataclass bases `Command` and `Event`; all 14 command classes and all 28 event classes from the contract, with exactly the contract's field names and types. Every later core and shell task imports from this module.

- [ ] **Step 1: Write the failing test for SceneId and the commands**

Create `tests/core/test_events.py`. It cross-checks the example instances against the classes actually declared in the module, so a command added without a test example (or vice versa) fails loudly:

```python
"""The command/event vocabulary: construction, immutability, value equality."""

import dataclasses

import pytest

from psychic_cleaners.core import events


def _example_commands() -> list[events.Command]:
    return [
        events.NewGame(name="Ada"),
        events.EnterAccount(name="Ada", code="ABCDEFG"),
        events.SelectVehicle(vehicle_id="hearse"),
        events.BuyItem(item_id="snare"),
        events.FinishShopping(),
        events.SetDestination(pos=(3, 2)),
        events.Steer(delta=-1),
        events.MoveCleaner(dx=4.0),
        events.PlaceCleaner(),
        events.LaySnare(),
        events.SpringSnare(),
        events.DeployBait(),
        events.StartRun(),
        events.Continue(),
    ]


def _declared_subclasses(base: type) -> set[type]:
    return {
        obj
        for obj in vars(events).values()
        if isinstance(obj, type) and issubclass(obj, base) and obj is not base
    }


def test_scene_id_has_exactly_seven_members() -> None:
    assert [member.name for member in events.SceneId] == [
        "TITLE",
        "SHOP",
        "MAP",
        "DRIVE",
        "BUST",
        "FINALE",
        "GAME_OVER",
    ]


def test_every_command_class_constructs() -> None:
    constructed = {type(command) for command in _example_commands()}
    assert constructed == _declared_subclasses(events.Command)
    assert len(constructed) == 14


def test_command_equality_by_value() -> None:
    assert events.NewGame(name="Ada") == events.NewGame(name="Ada")
    assert events.NewGame(name="Ada") != events.NewGame(name="Bee")
    assert events.Steer(delta=1) != events.Steer(delta=-1)
    assert events.Continue() == events.Continue()


@pytest.mark.parametrize("command", _example_commands())
def test_commands_are_frozen(command: events.Command) -> None:
    field_name = next((f.name for f in dataclasses.fields(command)), "anything")
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(command, field_name, object())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_events.py -v`
Expected: FAIL — collection error, `ImportError: cannot import name 'events' from 'psychic_cleaners.core'`

- [ ] **Step 3: Implement SceneId, the bases, and all commands**

Create `src/psychic_cleaners/core/events.py`:

```python
"""Typed vocabulary crossing the core boundary.

Commands flow shell -> core (player intent); Events flow core -> shell
(things that happened). Both are immutable value objects. SceneId lives
here (not in game.py) to avoid import cycles.
"""

from dataclasses import dataclass
from enum import Enum, auto

type GridPos = tuple[int, int]


class SceneId(Enum):
    TITLE = auto()
    SHOP = auto()
    MAP = auto()
    DRIVE = auto()
    BUST = auto()
    FINALE = auto()
    GAME_OVER = auto()


@dataclass(frozen=True)
class Command:
    """Base for all player-intent messages (shell -> core)."""


@dataclass(frozen=True)
class Event:
    """Base for all things-that-happened messages (core -> shell)."""


# --- commands ---------------------------------------------------------------


@dataclass(frozen=True)
class NewGame(Command):
    name: str


@dataclass(frozen=True)
class EnterAccount(Command):
    name: str
    code: str


@dataclass(frozen=True)
class SelectVehicle(Command):
    vehicle_id: str


@dataclass(frozen=True)
class BuyItem(Command):
    item_id: str


@dataclass(frozen=True)
class FinishShopping(Command):
    pass


@dataclass(frozen=True)
class SetDestination(Command):
    pos: GridPos


@dataclass(frozen=True)
class Steer(Command):
    delta: int  # -1 = lane up, +1 = lane down


@dataclass(frozen=True)
class MoveCleaner(Command):
    dx: float  # signed px this frame


@dataclass(frozen=True)
class PlaceCleaner(Command):
    pass


@dataclass(frozen=True)
class LaySnare(Command):
    pass


@dataclass(frozen=True)
class SpringSnare(Command):
    pass


@dataclass(frozen=True)
class DeployBait(Command):
    pass


@dataclass(frozen=True)
class StartRun(Command):
    pass


@dataclass(frozen=True)
class Continue(Command):
    """Advance past overlays / gameover -> title."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_events.py -v`
Expected: PASS (17 passed — 3 tests plus 14 parametrized frozen checks)

- [ ] **Step 5: Add the failing tests for the events**

Append to the end of `tests/core/test_events.py`:

```python
def _example_events() -> list[events.Event]:
    return [
        events.SceneChanged(scene=events.SceneId.SHOP),
        events.AccountAccepted(name="Ada", bankroll=12_000),
        events.AccountRejected(reason="bad checksum"),
        events.VehicleSelected(vehicle_id="wagon"),
        events.ItemBought(item_id="vacuum"),
        events.PurchaseRejected(reason="cannot afford"),
        events.CommandRejected(reason="no snare laid"),
        events.TravelStarted(dest=(4, 1), distance=800.0),
        events.Arrived(pos=(4, 1)),
        events.WispCaptured(bounty=100),
        events.HauntStarted(pos=(2, 2)),
        events.HauntCleared(pos=(2, 2)),
        events.WispReachedTower(),
        events.GhostTrapped(fee=400),
        events.BustMissed(),
        events.BeamsCrossed(),
        events.CleanerSlimed(cleaner=1),
        events.SnaresEmptied(),
        events.CleanersRestored(),
        events.MascotAlert(window_seconds=10.0),
        events.BaitDeployed(),
        events.StompTriggered(),
        events.BuildingStomped(pos=(6, 3), fine=4_000),
        events.FinaleUnlocked(),
        events.RunnerEntered(total_inside=1),
        events.RunnerSquashed(),
        events.GameWon(account_code="ABCDEFG"),
        events.GameLost(reason="the Tower claimed the city"),
    ]


def test_every_event_class_constructs() -> None:
    constructed = {type(event) for event in _example_events()}
    assert constructed == _declared_subclasses(events.Event)
    assert len(constructed) == 28


def test_event_equality_by_value() -> None:
    assert events.GhostTrapped(fee=400) == events.GhostTrapped(fee=400)
    assert events.GhostTrapped(fee=400) != events.GhostTrapped(fee=500)
    rejected = events.CommandRejected(reason="no snare laid")
    assert rejected == events.CommandRejected(reason="no snare laid")
    assert rejected != events.CommandRejected(reason="try again")
    assert events.SceneChanged(scene=events.SceneId.MAP) == events.SceneChanged(
        scene=events.SceneId.MAP
    )
    assert events.WispReachedTower() == events.WispReachedTower()


@pytest.mark.parametrize("event", _example_events())
def test_events_are_frozen(event: events.Event) -> None:
    field_name = next((f.name for f in dataclasses.fields(event)), "anything")
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(event, field_name, object())


def test_grid_pos_alias() -> None:
    pos: events.GridPos = (3, 4)
    assert events.Arrived(pos=pos).pos == (3, 4)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/core/test_events.py -v`
Expected: FAIL — collection error, `AttributeError: module 'psychic_cleaners.core.events' has no attribute 'SceneChanged'`

- [ ] **Step 7: Implement all event classes**

Append to the end of `src/psychic_cleaners/core/events.py`:

```python
# --- events -----------------------------------------------------------------


@dataclass(frozen=True)
class SceneChanged(Event):
    scene: SceneId


@dataclass(frozen=True)
class AccountAccepted(Event):
    name: str
    bankroll: int


@dataclass(frozen=True)
class AccountRejected(Event):
    reason: str


@dataclass(frozen=True)
class VehicleSelected(Event):
    vehicle_id: str


@dataclass(frozen=True)
class ItemBought(Event):
    item_id: str


@dataclass(frozen=True)
class PurchaseRejected(Event):
    reason: str


@dataclass(frozen=True)
class CommandRejected(Event):
    reason: str  # invalid non-purchase command, e.g. "no snare laid"


@dataclass(frozen=True)
class TravelStarted(Event):
    dest: GridPos
    distance: float


@dataclass(frozen=True)
class Arrived(Event):
    pos: GridPos


@dataclass(frozen=True)
class WispCaptured(Event):
    bounty: int


@dataclass(frozen=True)
class HauntStarted(Event):
    pos: GridPos


@dataclass(frozen=True)
class HauntCleared(Event):
    pos: GridPos


@dataclass(frozen=True)
class WispReachedTower(Event):
    pass


@dataclass(frozen=True)
class GhostTrapped(Event):
    fee: int


@dataclass(frozen=True)
class BustMissed(Event):
    pass


@dataclass(frozen=True)
class BeamsCrossed(Event):
    pass


@dataclass(frozen=True)
class CleanerSlimed(Event):
    cleaner: int  # 0..2 game-level index


@dataclass(frozen=True)
class SnaresEmptied(Event):
    pass


@dataclass(frozen=True)
class CleanersRestored(Event):
    pass


@dataclass(frozen=True)
class MascotAlert(Event):
    window_seconds: float


@dataclass(frozen=True)
class BaitDeployed(Event):
    pass


@dataclass(frozen=True)
class StompTriggered(Event):
    """Internal: emitted by MascotModel; Game turns it into BuildingStomped."""


@dataclass(frozen=True)
class BuildingStomped(Event):
    pos: GridPos
    fine: int


@dataclass(frozen=True)
class FinaleUnlocked(Event):
    pass


@dataclass(frozen=True)
class RunnerEntered(Event):
    total_inside: int


@dataclass(frozen=True)
class RunnerSquashed(Event):
    pass


@dataclass(frozen=True)
class GameWon(Event):
    account_code: str


@dataclass(frozen=True)
class GameLost(Event):
    reason: str
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/core/test_events.py -v`
Expected: PASS (48 passed — 6 plain tests, including the alias test, plus 14 + 28 parametrized frozen checks)

- [ ] **Step 9: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 10: Commit**

```bash
git add src/psychic_cleaners/core/events.py tests/core/test_events.py
git commit -m "feat: add command and event vocabulary"
```

### Task 7: Game state machine skeleton

This task builds the FSM spine only. `Game` deliberately has just six fields for now; later tasks ADD fields (`wallet`, `psi`, `city`, `mascot`, `loadout`, `drive`, `bust`, `finale`, `slimed`, `contained`, `snares_full`, `position`, `destination`, `finale_unlocked`) and scene handlers to this same dataclass — the dispatch in `_dispatch` and the reset in `_reset` are the two extension points they grow. `Game.tick` is laid down in the contract's canonical three-step shape from day one: (1) the per-command dispatch loop, (2) the scene-ticking section AFTER the loop, (3) the post-tick resolution section. Later tasks only add code inside those sections; they never reorder them.

**CONVENTION: every later task that adds a `Game` field MUST extend `_reset()` in the same task.** `NewGame` and `Continue` both route through `_reset()`, so a field missed there leaks state across playthroughs.

**Files:**
- Create: `src/psychic_cleaners/core/game.py`
- Test: `tests/core/test_game_fsm.py`
- Test: `tests/integration/test_walkthrough.py`

**Interfaces:**
- Consumes: `GameClock` (Task 5); `STARTING_BANKROLL` (Task 4); `Rng`, `make_rng` (Task 4); `Command`, `Event`, `NewGame`, `Continue`, `SceneChanged`, `SceneId` (Task 6).
- Produces: `Game` dataclass with fields `rng: Rng`, `clock: GameClock`, `scene: SceneId`, `player_name: str`, `starting_bankroll: int`, `result: str | None`; `Game.tick(commands: Sequence[Command], dt_seconds: float) -> list[Event]` in the contract's canonical three-step shape; private helpers `_dispatch(command: Command, events: list[Event]) -> None`, `_change_scene(s: SceneId, events: list[Event]) -> None`, `_world_scenes() -> frozenset[SceneId]` (returns {MAP, DRIVE, BUST}), and `_reset() -> None` (reinitializes every non-rng field); `new_game(seed: int) -> Game`; `SceneId` re-exported from `psychic_cleaners.core.game`.

- [ ] **Step 1: Write the failing FSM test (TITLE -> SHOP)**

Create `tests/core/test_game_fsm.py` (the `pytest` and constants imports are used by the tests added in Step 5):

```python
"""The Game FSM skeleton: scene transitions and world-time gating."""

import pytest

from psychic_cleaners.core.constants import GAME_MINUTES_PER_REAL_SECOND
from psychic_cleaners.core.events import Continue, NewGame, SceneChanged
from psychic_cleaners.core.game import SceneId, new_game


def test_new_game_moves_title_to_shop() -> None:
    game = new_game(1)
    assert game.scene is SceneId.TITLE
    events = game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Ada"
    assert SceneChanged(SceneId.SHOP) in events


def test_new_game_ignored_outside_title() -> None:
    game = new_game(1)
    game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    events = game.tick([NewGame(name="Bee")], dt_seconds=0.0)
    assert events == []
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Ada"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_game_fsm.py -v`
Expected: FAIL — collection error, `ModuleNotFoundError: No module named 'psychic_cleaners.core.game'`

- [ ] **Step 3: Implement the Game skeleton**

Create `src/psychic_cleaners/core/game.py`. Note that `tick` already has the contract's canonical three-step shape — dispatch loop, then scene ticking, then post-tick resolution — with the last two sections as placeholders (Step 7 fills in the scene-ticking section; later tasks grow both):

```python
"""Top-level game state and scene FSM.

This is the skeleton: fields and handlers for TITLE and GAME_OVER only.
Later tasks ADD fields to Game (wallet, psi, city, mascot, loadout, drive,
bust, finale, ...) plus per-scene command handlers in _dispatch, and MUST
extend _reset() with every added field in the same task.

Game.tick keeps the contract's canonical three-step shape:
1. command dispatch, 2. scene ticking, 3. post-tick resolution.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.constants import STARTING_BANKROLL
from psychic_cleaners.core.events import (
    Command,
    Continue,
    Event,
    NewGame,
    SceneChanged,
    SceneId,
)
from psychic_cleaners.core.rng import Rng, make_rng

__all__ = ["Game", "SceneId", "new_game"]


@dataclass
class Game:
    rng: Rng
    clock: GameClock = field(default_factory=GameClock)
    scene: SceneId = SceneId.TITLE
    player_name: str = ""
    starting_bankroll: int = STARTING_BANKROLL
    result: str | None = None

    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        # 1. Command dispatch: per-command, scene-gated handlers.
        for command in commands:
            self._dispatch(command, events)
        # 2. Scene ticking (AFTER the dispatch loop, on the CURRENT scene):
        #    world-time gating lands in Step 7 of this task.
        # 3. Post-tick resolution: empty for now; later tasks extend it here.
        return events

    def _dispatch(self, command: Command, events: list[Event]) -> None:
        # Unknown or invalid commands for the current scene are ignored silently.
        if self.scene is SceneId.TITLE and isinstance(command, NewGame):
            self._reset()
            self.player_name = command.name
            self._change_scene(SceneId.SHOP, events)
        elif self.scene is SceneId.GAME_OVER and isinstance(command, Continue):
            self._reset()
            self._change_scene(SceneId.TITLE, events)

    def _change_scene(self, s: SceneId, events: list[Event]) -> None:
        self.scene = s
        events.append(SceneChanged(s))

    def _reset(self) -> None:
        """Reinitialize every field except rng to a fresh TITLE state.

        CONVENTION: every later task that adds a Game field MUST extend
        this method in the same task.
        """
        self.clock = GameClock()
        self.scene = SceneId.TITLE
        self.player_name = ""
        self.starting_bankroll = STARTING_BANKROLL
        self.result = None


def new_game(seed: int) -> Game:
    return Game(rng=make_rng(seed))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_game_fsm.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Add the failing world-time gating and reset tests**

Append to the end of `tests/core/test_game_fsm.py`:

```python
def test_clock_frozen_outside_world_scenes() -> None:
    game = new_game(1)
    game.tick([], dt_seconds=5.0)  # TITLE: time must not pass
    assert game.clock.minutes == 0.0
    game.scene = SceneId.SHOP
    game.tick([], dt_seconds=5.0)  # SHOP: still frozen
    assert game.clock.minutes == 0.0


def test_clock_advances_in_world_scenes() -> None:
    game = new_game(1)
    game.scene = SceneId.MAP
    game.tick([], dt_seconds=5.0)
    assert game.clock.minutes == pytest.approx(5.0 * GAME_MINUTES_PER_REAL_SECOND)
    game.scene = SceneId.DRIVE
    game.tick([], dt_seconds=1.0)
    game.scene = SceneId.BUST
    game.tick([], dt_seconds=1.0)
    assert game.clock.minutes == pytest.approx(7.0 * GAME_MINUTES_PER_REAL_SECOND)


def test_continue_resets_to_fresh_title_preserving_rng() -> None:
    game = new_game(1)
    game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    game.clock.advance(10.0)
    rng_before = game.rng
    events = game.tick([Continue()], dt_seconds=0.0)
    assert game.scene is SceneId.TITLE
    assert game.player_name == ""
    assert game.result is None
    assert game.clock.minutes == 0.0
    assert game.rng is rng_before
    assert SceneChanged(SceneId.TITLE) in events


def test_continue_ignored_outside_game_over() -> None:
    game = new_game(1)
    game.tick([NewGame(name="Ada")], dt_seconds=0.0)
    events = game.tick([Continue()], dt_seconds=0.0)
    assert events == []
    assert game.scene is SceneId.SHOP
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/core/test_game_fsm.py -v`
Expected: FAIL — `test_clock_advances_in_world_scenes` fails with `assert 0.0 == 5.0 ± ...` (the clock never advances); the other new tests pass

- [ ] **Step 7: Add the world-tick gating hook**

In `src/psychic_cleaners/core/game.py`, replace the `tick` method with the version below. This is the complete canonical three-step shape from the contract — (1) per-command dispatch loop, (2) scene ticking after the loop, (3) post-tick resolution — now with the scene-ticking section doing real work. Later tasks only add code inside sections 2 and 3:

```python
    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        # 1. Command dispatch: per-command, scene-gated handlers.
        for command in commands:
            self._dispatch(command, events)
        # 2. Scene ticking, AFTER the dispatch loop, on the CURRENT scene.
        if self.scene in self._world_scenes():
            # World time passes only here; psi/city/mascot ticks join in
            # later tasks at this same point.
            self.clock.advance(dt_seconds)
        # 3. Post-tick resolution: empty for now; later tasks extend it here
        #    (tower psi spikes, finale unlock, arrival routing, bankruptcy).
        return events
```

and add this method to `Game`, directly below `_change_scene`:

```python
    def _world_scenes(self) -> frozenset[SceneId]:
        return frozenset({SceneId.MAP, SceneId.DRIVE, SceneId.BUST})
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/core/test_game_fsm.py -v`
Expected: PASS (6 passed)

- [ ] **Step 9: Add the integration walkthrough test**

Create `tests/integration/test_walkthrough.py`. This is the scripted end-to-end FSM walk the milestone promises; scenes that do not yet have command-driven transitions are forced by assignment, and later milestones replace each forced hop with the real command. It integrates behaviour already unit-tested above, so it should pass on the first run:

```python
"""Scripted FSM walkthrough: title -> shop -> (forced) map -> (forced)
game over -> title.

Forced scene assignments below are placeholders; Milestones 3-9 replace
them one by one with real command-driven transitions.
"""

from psychic_cleaners.core.events import Continue, NewGame, SceneChanged
from psychic_cleaners.core.game import SceneId, new_game


def test_walkthrough_title_to_gameover_and_back() -> None:
    game = new_game(99)
    assert game.scene is SceneId.TITLE

    # Title: start a new franchise.
    events = game.tick([NewGame(name="Ada")], dt_seconds=1.0)
    assert events == [SceneChanged(SceneId.SHOP)]
    assert game.clock.minutes == 0.0  # SHOP is not a world scene

    # Shop -> map (forced until Milestone 3 wires FinishShopping).
    game.scene = SceneId.MAP
    game.tick([], dt_seconds=2.0)
    assert game.clock.minutes > 0.0  # world time flows on the map

    # Map -> game over (forced until Milestone 9 wires the finale).
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    events = game.tick([Continue()], dt_seconds=0.0)
    assert events == [SceneChanged(SceneId.TITLE)]
    assert game.scene is SceneId.TITLE
    assert game.result is None
    assert game.clock.minutes == 0.0
```

- [ ] **Step 10: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS — everything green, including `tests/integration/test_walkthrough.py::test_walkthrough_title_to_gameover_and_back`

- [ ] **Step 11: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 12: Commit**

```bash
git add src/psychic_cleaners/core/game.py tests/core/test_game_fsm.py \
    tests/integration/test_walkthrough.py
git commit -m "feat: add game state machine skeleton"
```

---

## Milestone 3: Shell foundation & shop

Goal: stand up the pygame shell (scene protocol, sprite factory, text renderer, scene registry wired into the fixed-timestep loop) and the complete shop economy (wallet, catalog, loadout) with a real interactive shop scene. When this milestone lands, `uv run psychic-cleaners` runs all seven scenes as labelled placeholders, and the SHOP scene is a working store: pick a vehicle, buy gear against a live balance with capacity limits, and finish shopping into the city map.

### Task 8: Shell foundation: Scene protocol, sprite factory, text, placeholder scenes

**Files:**
- Create: src/psychic_cleaners/shell/text.py
- Create: src/psychic_cleaners/shell/gfx.py
- Create: src/psychic_cleaners/shell/scenes/__init__.py
- Modify: src/psychic_cleaners/shell/app.py (full replacement shown below; supersedes the Milestone 1 demo loop, keeps `LOGICAL_SIZE`/`WINDOW_SCALE`/`FPS` and `main()`, drops the FPS-counter demo drawing)
- Test: tests/shell/test_foundation.py

**Interfaces:**
- Consumes: `core.game.Game`, `core.game.new_game(seed: int) -> Game`, `Game.tick(commands, dt_seconds)`, `Game.scene` (Task 7); `core.events.SceneId`, `core.events.Continue`, `core.events.Command` (Task 6); `tests/conftest.py` SDL dummy drivers (Milestone 1)
- Produces: `shell.scenes.Scene` (Protocol), `shell.scenes.PlaceholderScene(name: str)`, `shell.text.TextRenderer`, `shell.gfx.SpriteFactory` (sprites `"logo"`, `"cleaner"`), `shell.app.SCENES: Final[dict[SceneId, Scene]]` (explicit dict literal, one entry per `SceneId`), `shell.app.App` with `game`/`gfx`/`text` attributes and the contract `step()` order (events -> commands -> tick -> draw -> scale-blit), exception-safe `shell.app.main()`. Audio (`shell.audio`, `EVENT_SOUNDS`, `App.audio`) is owned by the audio milestone and is NOT built here.

- [ ] **Step 1: Write the failing tests for TextRenderer and SpriteFactory**

Create `tests/shell/test_foundation.py`:

```python
"""Shell foundation smoke tests: text, sprites, placeholder scenes, App.step."""

import pygame
import pytest

from psychic_cleaners.core.events import Continue, SceneId
from psychic_cleaners.core.game import new_game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer


def test_sprite_factory_caches_surfaces() -> None:
    pygame.init()
    factory = SpriteFactory()
    first = factory.get("cleaner")
    second = factory.get("cleaner")
    assert first is second
    assert first.get_size() == (24, 32)


def test_sprite_factory_builds_logo() -> None:
    pygame.init()
    factory = SpriteFactory()
    logo = factory.get("logo")
    assert logo.get_width() > 0
    assert logo.get_height() > 0


def test_sprite_factory_unknown_name_raises_key_error() -> None:
    pygame.init()
    factory = SpriteFactory()
    with pytest.raises(KeyError):
        factory.get("does-not-exist")


def test_text_renderer_draws_without_error() -> None:
    pygame.init()
    surface = pygame.Surface((640, 400))
    text = TextRenderer()
    text.draw(surface, "hello", (10, 10))
    text.draw(surface, "big", (10, 40), size=32, color=(255, 0, 0))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_foundation.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.shell.gfx'`

- [ ] **Step 3: Implement TextRenderer and SpriteFactory**

Create `src/psychic_cleaners/shell/text.py`:

```python
"""Font caching and text drawing helpers."""

import pygame


class TextRenderer:
    """Renders text using the default pygame font, cached per point size."""

    def __init__(self) -> None:
        self._fonts: dict[int, pygame.font.Font] = {}

    def _font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            if not pygame.font.get_init():
                pygame.font.init()
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def draw(
        self,
        surface: pygame.Surface,
        message: str,
        pos: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = (230, 230, 230),
    ) -> None:
        rendered = self._font(size).render(message, True, color)
        surface.blit(rendered, pos)
```

Create `src/psychic_cleaners/shell/gfx.py`:

```python
"""Code-generated sprite factory. All art is drawn in code; no asset files."""

from collections.abc import Callable

import pygame


def _build_logo() -> pygame.Surface:
    """Drawn wordmark rectangle used on the title screen."""
    surface = pygame.Surface((200, 48), pygame.SRCALPHA)
    surface.fill((30, 30, 60))
    pygame.draw.rect(surface, (120, 220, 160), surface.get_rect(), width=3)
    pygame.draw.rect(surface, (120, 220, 160), pygame.Rect(12, 20, 176, 8))
    return surface


def _build_cleaner() -> pygame.Surface:
    """Simple 24x32 figure: head, overalls, boots."""
    surface = pygame.Surface((24, 32), pygame.SRCALPHA)
    pygame.draw.rect(surface, (210, 180, 90), pygame.Rect(6, 12, 12, 16))
    pygame.draw.circle(surface, (240, 210, 170), (12, 7), 5)
    pygame.draw.rect(surface, (90, 90, 100), pygame.Rect(4, 28, 6, 4))
    pygame.draw.rect(surface, (90, 90, 100), pygame.Rect(14, 28, 6, 4))
    return surface


_BUILDERS: dict[str, Callable[[], pygame.Surface]] = {
    "logo": _build_logo,
    "cleaner": _build_cleaner,
}


class SpriteFactory:
    """Generates and caches sprites by name. Unknown names raise KeyError."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = _BUILDERS[name]()
        return self._cache[name]
```

Later milestones extend `_BUILDERS` with the remaining contract sprite names; the registry pattern (`dict[str, Callable[[], pygame.Surface]]`) is the extension point.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_foundation.py -v`

Expected: PASS (4 tests)

- [ ] **Step 5: Append failing tests for PlaceholderScene and App.step**

Append to `tests/shell/test_foundation.py`:

```python
def test_placeholder_scene_maps_return_key_to_continue() -> None:
    from psychic_cleaners.shell.scenes import PlaceholderScene

    scene = PlaceholderScene("TEST")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert scene.commands([event], new_game(1)) == [Continue()]


def test_placeholder_scene_ignores_other_events() -> None:
    from psychic_cleaners.shell.scenes import PlaceholderScene

    scene = PlaceholderScene("TEST")
    other_key = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    key_up = pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN)
    assert scene.commands([other_key, key_up], new_game(1)) == []


def test_app_step_runs_for_every_scene_id() -> None:
    from psychic_cleaners.shell.app import App

    app = App(seed=1)
    for scene_id in SceneId:
        app.game.scene = scene_id
        app.step(1 / 60)


def test_app_registry_covers_every_scene_id() -> None:
    from psychic_cleaners.shell.app import SCENES

    assert set(SCENES) == set(SceneId)
```

- [ ] **Step 6: Run tests to verify the new ones fail**

Run: `uv run pytest tests/shell/test_foundation.py -v`

Expected: FAIL — the 4 new tests error with `ModuleNotFoundError: No module named 'psychic_cleaners.shell.scenes'` (or `ImportError: cannot import name 'SCENES'` from `shell.app`); the first 4 still pass

- [ ] **Step 7: Implement the Scene protocol, PlaceholderScene, and the new App**

Create `src/psychic_cleaners/shell/scenes/__init__.py`:

```python
"""Scene protocol and the placeholder scene used before real scenes land."""

from typing import Protocol

import pygame

from psychic_cleaners.core.events import Command, Continue
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer


class Scene(Protocol):
    """One thin shell module per core mechanic: input -> Commands, state -> pixels."""

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]: ...

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None: ...


class PlaceholderScene:
    """Labelled stand-in scene: shows its name, turns Return into Continue()."""

    def __init__(self, name: str) -> None:
        self.name = name

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        return [
            Continue()
            for event in events
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        ]

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None:
        surface.fill((16, 16, 24))
        width, height = surface.get_size()
        text.draw(surface, self.name, (width // 2 - 5 * len(self.name), height // 2 - 12), size=24)
        text.draw(surface, "press Enter", (width // 2 - 40, height // 2 + 16), size=16)
```

Replace the entire contents of `src/psychic_cleaners/shell/app.py` with:

```python
"""Main loop: fixed-rate stepping, logical surface scaled to the window."""

import os
from typing import Final

import pygame

from psychic_cleaners.core.events import SceneId
from psychic_cleaners.core.game import new_game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import PlaceholderScene, Scene
from psychic_cleaners.shell.text import TextRenderer

LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)
WINDOW_SCALE: Final[int] = 2
FPS: Final[int] = 60

SCENES: Final[dict[SceneId, Scene]] = {
    SceneId.TITLE: PlaceholderScene("TITLE"),
    SceneId.SHOP: PlaceholderScene("SHOP"),
    SceneId.MAP: PlaceholderScene("MAP"),
    SceneId.DRIVE: PlaceholderScene("DRIVE"),
    SceneId.BUST: PlaceholderScene("BUST"),
    SceneId.FINALE: PlaceholderScene("FINALE"),
    SceneId.GAME_OVER: PlaceholderScene("GAME_OVER"),
}


class App:
    """Owns the window, the Game, and the per-frame pipeline."""

    def __init__(self, seed: int | None = None) -> None:
        pygame.init()
        window_size = (LOGICAL_SIZE[0] * WINDOW_SCALE, LOGICAL_SIZE[1] * WINDOW_SCALE)
        self.window = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Psychic Cleaners")
        self.logical = pygame.Surface(LOGICAL_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.game = new_game(seed if seed is not None else int.from_bytes(os.urandom(4)))
        self.gfx = SpriteFactory()
        self.text = TextRenderer()

    def step(self, dt: float) -> None:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
        scene = SCENES[self.game.scene]
        commands = scene.commands(events, self.game)
        self.game.tick(commands, dt)
        scene.draw(self.logical, self.game, self.gfx, self.text)
        pygame.transform.scale(self.logical, self.window.get_size(), self.window)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)


def main() -> None:
    app = App()
    try:
        app.run()
    finally:
        pygame.quit()
```

Note the contract-mandated frame order inside `step()`: gather pygame events, map them to commands via the current scene, `game.tick(commands, dt)`, then draw the same scene object and scale-blit. `SCENES` is an explicit dict literal with exactly one entry per `SceneId` so that later tasks change a single entry's value in place (e.g. Task 12 swaps `SceneId.SHOP`'s value to `ShopScene()`); do not collapse it into a comprehension. Audio (`shell/audio.py`, `App.audio`, `EVENT_SOUNDS`, and an audio-cue step) belongs entirely to the audio milestone and must not appear here — until then `App` is game/gfx/text-only. `main()` is exception-safe per the contract: `pygame.quit()` runs in a `finally` even if the loop raises.

- [ ] **Step 8: Run the full shell test file to verify everything passes**

Run: `uv run pytest tests/shell/test_foundation.py -v`

Expected: PASS (8 tests)

- [ ] **Step 9: Run the whole suite to catch regressions from the app.py replacement**

Run: `uv run pytest -v`

Expected: PASS. If a Milestone 1 test asserted on the old demo loop's internals (e.g. an FPS-counter attribute), replace the body of that test with exactly:

```python
def test_app_constructs_and_steps() -> None:
    from psychic_cleaners.shell.app import App

    app = App(seed=1)
    app.step(1 / 60)
    assert app.running is True
```

(keep the original test's module and rename it to `test_app_constructs_and_steps` if it had a demo-specific name). The public surface (`App`, `LOGICAL_SIZE`, `WINDOW_SCALE`, `FPS`, `main`) is unchanged.

- [ ] **Step 10: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean (no lint errors, no reformats needed, `Success: no issues found`)

- [ ] **Step 11: Commit**

```bash
git add src/psychic_cleaners/shell/text.py src/psychic_cleaners/shell/gfx.py \
    src/psychic_cleaners/shell/scenes/__init__.py \
    src/psychic_cleaners/shell/app.py tests/shell/test_foundation.py
git commit -m "feat: shell foundation with scene registry, sprite factory, and text"
```

### Task 9: Economy: wallet and bust fees

**Files:**
- Create: src/psychic_cleaners/core/economy.py
- Test: tests/core/test_economy.py

**Interfaces:**
- Consumes: `core.constants.STARTING_BANKROLL`, `MAX_BANKROLL`, `BUST_BASE_FEE`, `BUST_FEE_PER_1000_PSI` (Task 4)
- Produces: `core.economy.Wallet` (`balance`, `can_afford`, `spend`, `earn`, `fine`), `core.economy.bust_fee(psi_value: int) -> int` — used by Task 12 (shop) and the bust/mascot milestones

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_economy.py`:

```python
"""Wallet invariants and bust fee schedule."""

from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.constants import MAX_BANKROLL, STARTING_BANKROLL
from psychic_cleaners.core.economy import Wallet, bust_fee


def test_default_balance_is_starting_bankroll() -> None:
    assert Wallet().balance == STARTING_BANKROLL


def test_spend_deducts_and_returns_true() -> None:
    wallet = Wallet(balance=1000)
    assert wallet.spend(600) is True
    assert wallet.balance == 400


def test_spend_insufficient_returns_false_and_leaves_balance_unchanged() -> None:
    wallet = Wallet(balance=500)
    assert wallet.spend(501) is False
    assert wallet.balance == 500


def test_can_afford_boundary() -> None:
    wallet = Wallet(balance=500)
    assert wallet.can_afford(500) is True
    assert wallet.can_afford(501) is False


def test_earn_clamps_at_max_bankroll() -> None:
    wallet = Wallet(balance=MAX_BANKROLL - 10)
    wallet.earn(100)
    assert wallet.balance == MAX_BANKROLL


def test_fine_returns_actual_amount_charged() -> None:
    poor = Wallet(balance=250)
    assert poor.fine(4000) == 250
    assert poor.balance == 0
    rich = Wallet(balance=5000)
    assert rich.fine(4000) == 4000
    assert rich.balance == 1000


@given(
    st.lists(
        st.tuples(st.sampled_from(["spend", "fine", "earn"]), st.integers(0, 20_000)),
        max_size=50,
    )
)
def test_balance_never_negative_and_never_above_cap(ops: list[tuple[str, int]]) -> None:
    wallet = Wallet()
    for op, amount in ops:
        if op == "spend":
            wallet.spend(amount)
        elif op == "fine":
            wallet.fine(amount)
        else:
            wallet.earn(amount)
        assert 0 <= wallet.balance <= MAX_BANKROLL


def test_bust_fee_documented_values() -> None:
    assert bust_fee(0) == 300
    assert bust_fee(999) == 300
    assert bust_fee(1000) == 400
    assert bust_fee(9999) == 1200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_economy.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.core.economy'`

- [ ] **Step 3: Write the implementation**

Create `src/psychic_cleaners/core/economy.py`:

```python
"""Wallet and fee calculations. The balance never goes negative."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BUST_BASE_FEE,
    BUST_FEE_PER_1000_PSI,
    MAX_BANKROLL,
    STARTING_BANKROLL,
)


@dataclass
class Wallet:
    balance: int = STARTING_BANKROLL

    def can_afford(self, amount: int) -> bool:
        return self.balance >= amount

    def spend(self, amount: int) -> bool:
        """Deduct amount; return False and leave the balance unchanged if insufficient."""
        if not self.can_afford(amount):
            return False
        self.balance -= amount
        return True

    def earn(self, amount: int) -> None:
        """Add amount (>= 0), clamping the total at MAX_BANKROLL."""
        self.balance = min(self.balance + amount, MAX_BANKROLL)

    def fine(self, amount: int) -> int:
        """Charge min(amount, balance); return the amount actually charged."""
        charged = min(amount, self.balance)
        self.balance -= charged
        return charged


def bust_fee(psi_value: int) -> int:
    """City fee for a successful bust: base fee plus a step per 1000 PSI."""
    return BUST_BASE_FEE + BUST_FEE_PER_1000_PSI * (psi_value // 1000)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_economy.py -v`

Expected: PASS (8 tests, including the Hypothesis property)

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/economy.py tests/core/test_economy.py
git commit -m "feat: wallet economy with non-negative invariant and bust fee schedule"
```

### Task 10: Catalog: vehicles and equipment data

**Files:**
- Create: src/psychic_cleaners/core/catalog.py
- Test: tests/core/test_catalog.py

**Interfaces:**
- Consumes: nothing beyond the standard library
- Produces: `core.catalog.Vehicle`, `core.catalog.Item` (frozen dataclasses), `core.catalog.VEHICLES: Final[dict[str, Vehicle]]`, `core.catalog.ITEMS: Final[dict[str, Item]]` — insertion order is display order; used by Tasks 11 and 12 and by the drive/bust/mascot milestones

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_catalog.py`:

```python
"""Exact catalog data: ids, names, prices, speeds, capacities, slots, display order."""

import pytest

from psychic_cleaners.core.catalog import ITEMS, VEHICLES


def test_vehicle_display_order() -> None:
    assert list(VEHICLES) == ["compact", "hearse", "wagon", "performance"]


def test_item_display_order() -> None:
    assert list(ITEMS) == ["detector", "lens", "sensor", "bait", "snare", "rig", "vacuum"]


@pytest.mark.parametrize(
    ("vehicle_id", "name", "price", "speed", "capacity"),
    [
        ("compact", "Compact", 2000, 100.0, 7),
        ("hearse", "Hearse", 4800, 140.0, 9),
        ("wagon", "Wagon", 6000, 140.0, 11),
        ("performance", "Performance", 15000, 200.0, 14),
    ],
)
def test_vehicle_rows(vehicle_id: str, name: str, price: int, speed: float, capacity: int) -> None:
    vehicle = VEHICLES[vehicle_id]
    assert (vehicle.id, vehicle.name, vehicle.price, vehicle.speed, vehicle.capacity) == (
        vehicle_id,
        name,
        price,
        speed,
        capacity,
    )


@pytest.mark.parametrize(
    ("item_id", "name", "price", "slots"),
    [
        ("detector", "Residue detector", 400, 1),
        ("lens", "Spectral lens", 800, 1),
        ("sensor", "Mascot sensor", 800, 1),
        ("bait", "Gummy bait (5)", 400, 1),
        ("snare", "Spirit snare", 600, 1),
        ("rig", "Containment rig", 8000, 3),
        ("vacuum", "Roof vacuum", 500, 1),
    ],
)
def test_item_rows(item_id: str, name: str, price: int, slots: int) -> None:
    item = ITEMS[item_id]
    assert (item.id, item.name, item.price, item.slots) == (item_id, name, price, slots)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_catalog.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.core.catalog'`

- [ ] **Step 3: Write the implementation**

Create `src/psychic_cleaners/core/catalog.py`:

```python
"""Vehicle and equipment catalog. Dict insertion order is shop display order."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Vehicle:
    id: str
    name: str
    price: int
    speed: float
    capacity: int


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    price: int
    slots: int


VEHICLES: Final[dict[str, Vehicle]] = {
    "compact": Vehicle(id="compact", name="Compact", price=2000, speed=100.0, capacity=7),
    "hearse": Vehicle(id="hearse", name="Hearse", price=4800, speed=140.0, capacity=9),
    "wagon": Vehicle(id="wagon", name="Wagon", price=6000, speed=140.0, capacity=11),
    "performance": Vehicle(
        id="performance", name="Performance", price=15000, speed=200.0, capacity=14
    ),
}

ITEMS: Final[dict[str, Item]] = {
    "detector": Item(id="detector", name="Residue detector", price=400, slots=1),
    "lens": Item(id="lens", name="Spectral lens", price=800, slots=1),
    "sensor": Item(id="sensor", name="Mascot sensor", price=800, slots=1),
    "bait": Item(id="bait", name="Gummy bait (5)", price=400, slots=1),
    "snare": Item(id="snare", name="Spirit snare", price=600, slots=1),
    "rig": Item(id="rig", name="Containment rig", price=8000, slots=3),
    "vacuum": Item(id="vacuum", name="Roof vacuum", price=500, slots=1),
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_catalog.py -v`

Expected: PASS (13 tests)

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/catalog.py tests/core/test_catalog.py
git commit -m "feat: vehicle and equipment catalog with exact documented prices"
```

### Task 11: Loadout: capacity and inventory rules

**Files:**
- Create: src/psychic_cleaners/core/loadout.py
- Test: tests/core/test_loadout.py

**Interfaces:**
- Consumes: `core.catalog.ITEMS`, `core.catalog.VEHICLES`, `core.catalog.Vehicle` (Task 10); `core.constants.BAIT_PACK_SIZE` (Task 4)
- Produces: `core.loadout.Loadout` (`vehicle`, `counts`, `bait_charges`, `slots_used()`, `can_add(item_id)`, `add(item_id)`, `count(item_id)`, `has(item_id)`, `use_bait()`) — used by Task 12 and every gameplay milestone

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_loadout.py`:

```python
"""Loadout rules: slot accounting, capacity, duplicates, snare/bait stacking."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.constants import BAIT_PACK_SIZE
from psychic_cleaners.core.loadout import Loadout


def _loadout(vehicle_id: str = "hearse") -> Loadout:
    return Loadout(vehicle=VEHICLES[vehicle_id])


def test_empty_loadout_uses_no_slots() -> None:
    assert _loadout().slots_used() == 0


def test_slots_used_sums_item_slots_times_count() -> None:
    loadout = _loadout("performance")
    loadout.add("rig")  # 3 slots
    loadout.add("snare")  # 1 slot
    loadout.add("snare")  # 1 slot
    assert loadout.slots_used() == 5


def test_can_add_false_when_capacity_exceeded() -> None:
    loadout = _loadout("compact")  # capacity 7
    for item_id in ("rig", "detector", "lens", "sensor", "vacuum"):
        loadout.add(item_id)  # 3 + 1 + 1 + 1 + 1 = 7 slots
    assert loadout.slots_used() == 7
    assert loadout.can_add("snare") is False


def test_duplicate_unique_items_rejected() -> None:
    loadout = _loadout()
    loadout.add("vacuum")
    assert loadout.can_add("vacuum") is False
    with pytest.raises(ValueError, match="vacuum"):
        loadout.add("vacuum")


def test_snares_stack() -> None:
    loadout = _loadout()
    for _ in range(4):
        loadout.add("snare")
    assert loadout.count("snare") == 4
    assert loadout.can_add("snare") is True


def test_bait_packs_add_charges_and_one_slot_each() -> None:
    loadout = _loadout()
    loadout.add("bait")
    assert loadout.bait_charges == BAIT_PACK_SIZE
    loadout.add("bait")
    assert loadout.bait_charges == 2 * BAIT_PACK_SIZE
    assert loadout.count("bait") == 2
    assert loadout.slots_used() == 2 * ITEMS["bait"].slots


def test_use_bait_decrements_and_returns_false_at_zero() -> None:
    loadout = _loadout()
    loadout.add("bait")
    for _ in range(BAIT_PACK_SIZE):
        assert loadout.use_bait() is True
    assert loadout.use_bait() is False
    assert loadout.bait_charges == 0


def test_has_reflects_counts() -> None:
    loadout = _loadout()
    assert loadout.has("vacuum") is False
    loadout.add("vacuum")
    assert loadout.has("vacuum") is True


@given(
    vehicle_id=st.sampled_from(list(VEHICLES)),
    item_ids=st.lists(st.sampled_from(list(ITEMS)), max_size=30),
)
def test_slots_used_never_exceeds_capacity(vehicle_id: str, item_ids: list[str]) -> None:
    """Property: any valid sequence of add() calls keeps slots_used() within capacity."""
    loadout = Loadout(vehicle=VEHICLES[vehicle_id])
    for item_id in item_ids:
        if loadout.can_add(item_id):
            loadout.add(item_id)
        assert loadout.slots_used() <= loadout.vehicle.capacity
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_loadout.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.core.loadout'`

- [ ] **Step 3: Write the implementation**

Create `src/psychic_cleaners/core/loadout.py`:

```python
"""Loadout: what the franchise carries, constrained by vehicle capacity."""

from dataclasses import dataclass, field
from typing import Final

from psychic_cleaners.core.catalog import ITEMS, Vehicle
from psychic_cleaners.core.constants import BAIT_PACK_SIZE

_STACKABLE: Final[frozenset[str]] = frozenset({"snare", "bait"})


@dataclass
class Loadout:
    vehicle: Vehicle
    counts: dict[str, int] = field(default_factory=dict)  # item_id -> count owned
    bait_charges: int = 0  # BAIT_PACK_SIZE per bait pack bought

    def slots_used(self) -> int:
        return sum(ITEMS[item_id].slots * n for item_id, n in self.counts.items())

    def can_add(self, item_id: str) -> bool:
        item = ITEMS[item_id]
        if item_id not in _STACKABLE and self.count(item_id) > 0:
            return False
        return self.slots_used() + item.slots <= self.vehicle.capacity

    def add(self, item_id: str) -> None:
        if not self.can_add(item_id):
            raise ValueError(f"cannot add {item_id!r} to loadout")
        self.counts[item_id] = self.counts.get(item_id, 0) + 1
        if item_id == "bait":
            self.bait_charges += BAIT_PACK_SIZE

    def count(self, item_id: str) -> int:
        return self.counts.get(item_id, 0)

    def has(self, item_id: str) -> bool:
        return self.count(item_id) > 0

    def use_bait(self) -> bool:
        if self.bait_charges <= 0:
            return False
        self.bait_charges -= 1
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_loadout.py -v`

Expected: PASS (9 tests, including the Hypothesis capacity property)

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/loadout.py tests/core/test_loadout.py
git commit -m "feat: loadout capacity and inventory rules with bait charge tracking"
```

### Task 12: Shop flow in Game plus shop scene

**Files:**
- Modify: src/psychic_cleaners/core/game.py (add `wallet`/`loadout`/`notice` fields, extend `_reset()`, handle SHOP commands)
- Create: src/psychic_cleaners/shell/scenes/shop.py
- Modify: src/psychic_cleaners/shell/app.py (swap the `SCENES` literal's `SceneId.SHOP` entry to `ShopScene()`)
- Test: tests/integration/test_shop.py, tests/shell/test_shop_scene.py

**Interfaces:**
- Consumes: `core.game.Game`, `new_game`, `Game.tick`, `Game._reset()` and the TITLE handling of `NewGame` (Task 7); `core.events`: `NewGame`, `SelectVehicle(vehicle_id)`, `BuyItem(item_id)`, `FinishShopping`, `VehicleSelected(vehicle_id)`, `ItemBought(item_id)`, `PurchaseRejected(reason)`, `SceneChanged(scene)`, `SceneId` (Task 6); `core.economy.Wallet` (Task 9); `core.catalog.VEHICLES`, `ITEMS`, `Vehicle`, `Item` (Task 10); `core.loadout.Loadout` (Task 11); `shell.scenes.Scene`, `shell.app.SCENES`, `shell.gfx.SpriteFactory`, `shell.text.TextRenderer` (Task 8)
- Produces: `Game.wallet: Wallet`, `Game.loadout: Loadout | None`, `Game.notice: str | None`, contract SHOP behaviour of `Game.tick`; `shell.scenes.shop.ShopScene` (draws `game.notice` when set). Note: `EnterAccount` handling is Task 14, NOT here.

- [ ] **Step 1: Write the failing integration tests for the core shop flow**

Create `tests/integration/test_shop.py`:

```python
"""Scripted shop flows against core.game: purchases, rejections, scene transition."""

from psychic_cleaners.core.events import (
    BuyItem,
    FinishShopping,
    ItemBought,
    NewGame,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SelectVehicle,
    VehicleSelected,
)
from psychic_cleaners.core.game import Game, new_game


def _shop_game() -> Game:
    game = new_game(seed=1)
    game.tick([NewGame("Pat")], 0.0)
    assert game.scene == SceneId.SHOP
    return game


def test_happy_path_hearse_two_snares_vacuum() -> None:
    game = _shop_game()

    events = game.tick([SelectVehicle("hearse")], 0.0)
    assert VehicleSelected("hearse") in events

    events = game.tick([BuyItem("snare"), BuyItem("snare"), BuyItem("vacuum")], 0.0)
    assert events.count(ItemBought("snare")) == 2
    assert ItemBought("vacuum") in events

    events = game.tick([FinishShopping()], 0.0)
    assert SceneChanged(SceneId.MAP) in events
    assert game.scene == SceneId.MAP
    assert game.wallet.balance == 10_000 - 4_800 - 2 * 600 - 500  # 3500
    assert game.loadout is not None
    assert game.loadout.vehicle.id == "hearse"
    assert game.loadout.count("snare") == 2
    assert game.loadout.count("vacuum") == 1


def test_unaffordable_vehicle_rejected() -> None:
    game = _shop_game()
    events = game.tick([SelectVehicle("performance")], 0.0)  # 15000 > 10000
    assert PurchaseRejected("cannot afford") in events
    assert game.loadout is None
    assert game.wallet.balance == 10_000


def test_second_vehicle_rejected() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)
    events = game.tick([SelectVehicle("hearse")], 0.0)
    assert PurchaseRejected("vehicle already chosen") in events
    assert game.loadout is not None
    assert game.loadout.vehicle.id == "compact"
    assert game.wallet.balance == 8_000


def test_item_before_vehicle_rejected() -> None:
    game = _shop_game()
    events = game.tick([BuyItem("snare")], 0.0)
    assert PurchaseRejected("choose a vehicle first") in events
    assert game.wallet.balance == 10_000


def test_unaffordable_item_rejected() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("hearse")], 0.0)  # 5200 left
    events = game.tick([BuyItem("rig")], 0.0)  # rig costs 8000
    assert PurchaseRejected("cannot afford") in events
    assert game.loadout is not None
    assert game.loadout.count("rig") == 0
    assert game.wallet.balance == 5_200


def test_full_vehicle_rejects_item() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact")], 0.0)  # capacity 7, 8000 left
    fill = ["detector", "lens", "sensor", "bait", "vacuum", "snare", "snare"]  # 7 slots
    game.tick([BuyItem(item_id) for item_id in fill], 0.0)
    events = game.tick([BuyItem("snare")], 0.0)
    assert PurchaseRejected("no room in vehicle") in events
    assert game.loadout is not None
    assert game.loadout.count("snare") == 2


def test_finish_without_vehicle_stays_in_shop() -> None:
    game = _shop_game()
    events = game.tick([FinishShopping()], 0.0)
    assert game.scene == SceneId.SHOP
    assert SceneChanged(SceneId.MAP) not in events


def test_notice_set_on_rejection_and_cleared_on_success() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("performance")], 0.0)  # 15000 > 10000 -> rejected
    assert game.notice == "cannot afford"
    game.tick([SelectVehicle("hearse")], 0.0)  # success clears the notice
    assert game.notice is None


def test_new_game_resets_wallet_loadout_and_notice() -> None:
    game = _shop_game()
    game.tick([SelectVehicle("compact"), BuyItem("snare")], 0.0)
    game.tick([SelectVehicle("hearse")], 0.0)  # second vehicle -> rejected
    assert game.notice == "vehicle already chosen"
    game.tick([NewGame("Sam")], 0.0)  # routes through _reset()
    assert game.scene == SceneId.SHOP
    assert game.wallet.balance == 10_000
    assert game.loadout is None
    assert game.notice is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_shop.py -v`

Expected: FAIL — every test fails on its first shop assertion (e.g. `assert VehicleSelected('hearse') in events` or `AttributeError: 'Game' object has no attribute 'wallet'`); the exact first failure depends on the Task 7 stub FSM, but all 9 tests must fail before the changes below

- [ ] **Step 3: Implement the shop flow in core/game.py**

Make four edits to `src/psychic_cleaners/core/game.py` (Task 7 created this file; keep its existing structure and slot these in):

Edit 1 — add these imports alongside the existing ones (Task 7 already imports `dataclass`/`field` and the events module):

```python
from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.economy import Wallet
from psychic_cleaners.core.loadout import Loadout
```

and ensure these names are imported from `psychic_cleaners.core.events` (add any missing to the existing import):

```python
from psychic_cleaners.core.events import (
    BuyItem,
    Command,
    Event,
    FinishShopping,
    ItemBought,
    PurchaseRejected,
    SceneChanged,
    SceneId,
    SelectVehicle,
    VehicleSelected,
)
```

Edit 2 — add three fields to the `Game` dataclass at their contract positions. Insert `wallet` directly after the `clock` field (it is 3rd in the contract's field order):

```python
    wallet: Wallet = field(default_factory=Wallet)
```

insert `loadout` directly after the `starting_bankroll` field (the contract places it between `starting_bankroll` and `drive`):

```python
    loadout: Loadout | None = None
```

and add `notice` — directly after the `result` field if Task 7's skeleton already defines `result`, otherwise after the last existing field (the contract orders it between `result` and `last_account_code`):

```python
    notice: str | None = None  # last rejection message, drawn by title/shop scenes
```

Edit 3 — extend `_reset()` (Task 7 created it; the contract convention is that every task adding a `Game` field reinitializes it in `_reset()` in the same task). Add these lines to the end of the existing `_reset()` body:

```python
        self.wallet = Wallet()
        self.loadout = None
        self.notice = None
```

Do NOT edit the `NewGame` handler itself — Task 7 already routes it through `_reset()`, so the new fields are reinitialized automatically.

Edit 4 — add this method to `Game`, matching Task 7's canonical dispatch shape (command-outer, scene-gated: `tick` runs `for command in commands: self._dispatch(command, events)`, and `_dispatch` routes each command to the current scene's handler). Every `PurchaseRejected` records its reason in `self.notice`; every successful shop command clears it to `None`:

```python
    def _handle_shop(self, command: Command, events: list[Event]) -> None:
        match command:
            case SelectVehicle(vehicle_id=vehicle_id):
                vehicle = VEHICLES[vehicle_id]
                if self.loadout is not None:
                    reason = "vehicle already chosen"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                elif not self.wallet.can_afford(vehicle.price):
                    reason = "cannot afford"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                else:
                    self.wallet.spend(vehicle.price)
                    self.loadout = Loadout(vehicle=vehicle)
                    self.notice = None
                    events.append(VehicleSelected(vehicle_id))
            case BuyItem(item_id=item_id):
                if self.loadout is None:
                    reason = "choose a vehicle first"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                elif not self.wallet.can_afford(ITEMS[item_id].price):
                    reason = "cannot afford"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                elif not self.loadout.can_add(item_id):
                    reason = "no room in vehicle"
                    self.notice = reason
                    events.append(PurchaseRejected(reason))
                else:
                    self.wallet.spend(ITEMS[item_id].price)
                    self.loadout.add(item_id)
                    self.notice = None
                    events.append(ItemBought(item_id))
            case FinishShopping():
                if self.loadout is not None:
                    self.notice = None
                    self.scene = SceneId.MAP
                    events.append(SceneChanged(SceneId.MAP))
```

Wire it into Task 7's `_dispatch(self, command: Command, events: list[Event]) -> None`, alongside the existing TITLE gate:

```python
        if self.scene is SceneId.SHOP:
            self._handle_shop(command, events)
```

Do NOT handle `EnterAccount` in this task — that is Task 14. World time does not advance in SHOP (contract: only MAP, DRIVE, BUST tick the clock/psi/city/mascot).

- [ ] **Step 4: Run integration tests to verify they pass**

Run: `uv run pytest tests/integration/test_shop.py -v`

Expected: PASS (9 tests)

- [ ] **Step 5: Write the failing shell tests for ShopScene**

Create `tests/shell/test_shop_scene.py`:

```python
"""ShopScene key mapping and draw smoke test (SDL dummy driver)."""

import pygame

from psychic_cleaners.core.events import (
    BuyItem,
    FinishShopping,
    NewGame,
    SceneId,
    SelectVehicle,
)
from psychic_cleaners.core.game import new_game
from psychic_cleaners.shell.app import SCENES
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.shop import ShopScene
from psychic_cleaners.shell.text import TextRenderer


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_enter_on_first_row_selects_first_vehicle() -> None:
    scene = ShopScene()
    game = new_game(1)
    assert scene.commands([_key(pygame.K_RETURN)], game) == [SelectVehicle("compact")]


def test_cursor_down_reaches_first_item_row() -> None:
    scene = ShopScene()
    game = new_game(1)
    scene.commands([_key(pygame.K_DOWN)] * 4, game)  # past the 4 vehicles
    assert scene.commands([_key(pygame.K_RETURN)], game) == [BuyItem("detector")]


def test_cursor_up_wraps_to_last_row() -> None:
    scene = ShopScene()
    game = new_game(1)
    scene.commands([_key(pygame.K_UP)], game)
    assert scene.commands([_key(pygame.K_RETURN)], game) == [BuyItem("vacuum")]


def test_f_emits_finish_shopping() -> None:
    scene = ShopScene()
    game = new_game(1)
    assert scene.commands([_key(pygame.K_f)], game) == [FinishShopping()]


def test_other_keys_emit_nothing() -> None:
    scene = ShopScene()
    game = new_game(1)
    assert scene.commands([_key(pygame.K_SPACE)], game) == []


def test_shop_scene_registered_in_app() -> None:
    assert isinstance(SCENES[SceneId.SHOP], ShopScene)


def test_draw_smoke_before_and_after_purchases() -> None:
    pygame.init()
    surface = pygame.Surface((640, 400))
    scene = ShopScene()
    gfx = SpriteFactory()
    text = TextRenderer()
    game = new_game(1)
    game.tick([NewGame("Pat")], 0.0)
    scene.draw(surface, game, gfx, text)  # no vehicle chosen yet
    game.tick([SelectVehicle("hearse"), BuyItem("snare")], 0.0)
    scene.draw(surface, game, gfx, text)  # vehicle chosen, one item owned
    game.tick([SelectVehicle("compact")], 0.0)  # second vehicle -> rejected
    assert game.notice == "vehicle already chosen"
    scene.draw(surface, game, gfx, text)  # notice line rendered when set
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_shop_scene.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.shell.scenes.shop'`

- [ ] **Step 7: Implement ShopScene and register it**

Create `src/psychic_cleaners/shell/scenes/shop.py`:

```python
"""Interactive store: pick one vehicle, fill it with gear, F to finish."""

import pygame

from psychic_cleaners.core.catalog import ITEMS, VEHICLES, Item, Vehicle
from psychic_cleaners.core.events import BuyItem, Command, FinishShopping, SelectVehicle
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_ROWS: list[Vehicle | Item] = [*VEHICLES.values(), *ITEMS.values()]

_WHITE = (235, 235, 235)
_GREY = (110, 110, 110)
_RED = (240, 120, 120)


class ShopScene:
    """Vertical menu: 4 vehicles then 7 items. Up/Down moves, Enter buys, F finishes."""

    def __init__(self) -> None:
        self.cursor = 0

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        commands: list[Command] = []
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self.cursor = (self.cursor - 1) % len(_ROWS)
            elif event.key == pygame.K_DOWN:
                self.cursor = (self.cursor + 1) % len(_ROWS)
            elif event.key == pygame.K_RETURN:
                row = _ROWS[self.cursor]
                if isinstance(row, Vehicle):
                    commands.append(SelectVehicle(row.id))
                else:
                    commands.append(BuyItem(row.id))
            elif event.key == pygame.K_f:
                commands.append(FinishShopping())
        return commands

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None:
        surface.fill((18, 14, 28))
        text.draw(surface, "PSYCHIC CLEANERS OUTFITTERS", (24, 16), size=24)
        text.draw(surface, f"Balance: ${game.wallet.balance}", (24, 44), size=16)
        if game.loadout is None:
            text.draw(surface, "Choose a vehicle (Enter). F when done.", (24, 62), size=16)
        else:
            loadout = game.loadout
            status = (
                f"Vehicle: {loadout.vehicle.name}   "
                f"Slots: {loadout.slots_used()}/{loadout.vehicle.capacity}"
            )
            text.draw(surface, status, (24, 62), size=16)
        for index, row in enumerate(_ROWS):
            y = 96 + index * 22
            marker = ">" if index == self.cursor else " "
            color = _WHITE if game.wallet.can_afford(row.price) else _GREY
            if isinstance(row, Vehicle):
                chosen = game.loadout is not None and game.loadout.vehicle.id == row.id
                suffix = "  [chosen]" if chosen else ""
            else:
                owned = game.loadout.count(row.id) if game.loadout is not None else 0
                suffix = f"  x{owned}" if owned else ""
            label = f"{marker} {row.name:<20} ${row.price}{suffix}"
            text.draw(surface, label, (24, y), size=16, color=color)
        if game.notice is not None:
            text.draw(surface, game.notice, (24, 376), size=16, color=_RED)
```

Modify `src/psychic_cleaners/shell/app.py`: add the import

```python
from psychic_cleaners.shell.scenes.shop import ShopScene
```

and change exactly one entry of the `SCENES` dict literal in place — replace

```python
    SceneId.SHOP: PlaceholderScene("SHOP"),
```

with

```python
    SceneId.SHOP: ShopScene(),
```

(the registry deliberately starts as an explicit all-placeholder literal; each scene task edits its single entry's value in place.)

- [ ] **Step 8: Run the shell tests to verify they pass**

Run: `uv run pytest tests/shell/test_shop_scene.py -v`

Expected: PASS (7 tests)

- [ ] **Step 9: Run the whole suite**

Run: `uv run pytest -v`

Expected: PASS — including tests/shell/test_foundation.py's every-scene `App.step` loop, which now exercises the real ShopScene for `SceneId.SHOP`

- [ ] **Step 10: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean

- [ ] **Step 11: Commit**

```bash
git add src/psychic_cleaners/core/game.py src/psychic_cleaners/shell/scenes/shop.py \
    src/psychic_cleaners/shell/app.py tests/integration/test_shop.py \
    tests/shell/test_shop_scene.py
git commit -m "feat: shop flow in game FSM with interactive shop scene"
```

<!-- CONTRACT-NOTE: The contract only names PurchaseRejected("cannot afford") for SHOP and otherwise says PurchaseRejected(reason); this plan pins the remaining reason strings as "vehicle already chosen" (second SelectVehicle), "choose a vehicle first" (BuyItem before a vehicle), and "no room in vehicle" (capacity exceeded). Task 12's integration tests and later milestones must use these exact strings, and each is mirrored into Game.notice for the shop scene's feedback line. -->
<!-- CONTRACT-NOTE: Shop scene keys (Up/Down/Enter/F) and ShopScene's internal cursor state are not in the contract; chosen per the milestone brief and kept private to the shell. -->


---

## Milestone 4: Accounts & title

Goal: the password-save system — a checksummed 7-character account code that encodes (name, bankroll) — plus the real title screen where the player types a name and optionally a code. When this milestone lands, launching the game shows a working title screen: type a name and press Enter to start a fresh $10,000 franchise, or Tab into the code field and restore a saved bankroll, then land in the shop.

### Task 13: Account code codec

**Files:**
- Create: src/psychic_cleaners/core/codec.py
- Test: tests/core/test_codec.py

**Interfaces:**
- Consumes: `MAX_BANKROLL` from `psychic_cleaners.core.constants` (value 9_999_999, exists since the constants task).
- Produces: `AccountCodeError(ValueError)`, `ALPHABET: Final[str]` (the 30-char string `"ABCDEFGHJKMNPQRSTVWXYZ23456789"`), `encode_account(name: str, bankroll: int) -> str` (7-char code), `decode_account(name: str, code: str) -> int` (bankroll, or raises `AccountCodeError`). Task 14 and the finale task (`GameWon(encode_account(...))`) call these.

Algorithm (contract, both directions): `_norm(name) = " ".join(name.split()).casefold()` (empty → error); `key = zlib.crc32(_norm(name).encode()) & 0xFFFFFF`; require `0 <= bankroll <= MAX_BANKROLL`; `mixed = bankroll ^ key`; `check = zlib.crc32(f"{_norm(name)}:{bankroll}".encode()) & 0xFF`; `raw = (mixed << 8) | check`; emit raw as exactly 7 base-30 digits, most significant first. `raw` is at most 32 bits and 30**7 ≈ 21.9e9 > 2**32, so 7 digits always suffice. On decode, the incoming code is normalized with `.strip().upper()` before validation, so users can paste codes with stray whitespace or in lowercase.

All test vectors below were computed with a reference implementation of exactly this algorithm; treat them as fixed.

- [ ] **Step 1: Write the failing tests for encoding**

Create `tests/core/test_codec.py`:

```python
"""Tests for the account-code codec (encode half; decode tests are added below)."""

import pytest

from psychic_cleaners.core.codec import ALPHABET, AccountCodeError, encode_account
from psychic_cleaners.core.constants import MAX_BANKROLL


def test_known_answer_vector() -> None:
    assert encode_account("Pat Jones", 10_000) == "CPDG8JX"


def test_code_shape() -> None:
    code = encode_account("Geoff", MAX_BANKROLL)
    assert code == "D9XGTT7"
    assert len(code) == 7
    assert all(ch in ALPHABET for ch in code)


def test_name_normalization_is_applied() -> None:
    # Case, leading/trailing space, and repeated internal whitespace are all folded.
    assert encode_account("  pat   JONES ", 10_000) == "CPDG8JX"


@pytest.mark.parametrize("bankroll", [-1, MAX_BANKROLL + 1])
def test_out_of_range_bankroll_raises(bankroll: int) -> None:
    with pytest.raises(AccountCodeError):
        encode_account("Pat", bankroll)


@pytest.mark.parametrize("name", ["", "   ", " \t\n"])
def test_empty_normalized_name_raises_on_encode(name: str) -> None:
    with pytest.raises(AccountCodeError):
        encode_account(name, 100)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/core/test_codec.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.core.codec'`.

- [ ] **Step 3: Implement the encoder**

Create `src/psychic_cleaners/core/codec.py`:

```python
"""Account-code codec.

Encodes (player name, bankroll) into a 7-character code over a 30-letter
alphabet with no easily-confused glyphs. The bankroll is xor-mixed with a
CRC-derived key of the normalized name, and an 8-bit CRC checksum of
"name:bankroll" is appended, so a code only decodes for the name it was
issued to and single-character typos are (almost always) rejected.
"""

import zlib
from typing import Final

from psychic_cleaners.core.constants import MAX_BANKROLL


class AccountCodeError(ValueError):
    """Raised for an invalid name, bankroll, or account code."""


ALPHABET: Final[str] = "ABCDEFGHJKMNPQRSTVWXYZ23456789"

_CODE_LENGTH: Final[int] = 7
_BASE: Final[int] = len(ALPHABET)  # 30; 30**7 > 2**32, so 7 digits hold any raw value
_CHAR_VALUES: Final[dict[str, int]] = {ch: i for i, ch in enumerate(ALPHABET)}


def _norm(name: str) -> str:
    normalized = " ".join(name.split()).casefold()
    if not normalized:
        raise AccountCodeError("name must not be empty")
    return normalized


def _key(norm_name: str) -> int:
    return zlib.crc32(norm_name.encode()) & 0xFFFFFF


def _checksum(norm_name: str, bankroll: int) -> int:
    return zlib.crc32(f"{norm_name}:{bankroll}".encode()) & 0xFF


def encode_account(name: str, bankroll: int) -> str:
    """Return the 7-character account code for (name, bankroll)."""
    norm_name = _norm(name)
    if not 0 <= bankroll <= MAX_BANKROLL:
        raise AccountCodeError(f"bankroll out of range: {bankroll}")
    mixed = bankroll ^ _key(norm_name)
    raw = (mixed << 8) | _checksum(norm_name, bankroll)
    digits: list[str] = []
    for _ in range(_CODE_LENGTH):
        digits.append(ALPHABET[raw % _BASE])
        raw //= _BASE
    return "".join(reversed(digits))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_codec.py -v`
Expected: PASS — pytest reports `8 passed` (5 test functions; the two parametrized ones expand to 2 + 3 items).

- [ ] **Step 5: Write the failing tests for decoding (unit + Hypothesis properties)**

Replace the import block at the top of `tests/core/test_codec.py` with:

```python
"""Tests for the account-code codec (encode half; decode tests are added below)."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from psychic_cleaners.core.codec import (
    ALPHABET,
    AccountCodeError,
    decode_account,
    encode_account,
)
from psychic_cleaners.core.constants import MAX_BANKROLL
```

then append to the end of the same file:

```python
def test_decode_known_answer() -> None:
    assert decode_account("Pat Jones", "CPDG8JX") == 10_000


def test_decode_normalizes_code_and_name() -> None:
    # Codes are accepted case-insensitively with surrounding whitespace stripped,
    # and names get the same normalization as on encode.
    assert decode_account("  PAT   jones ", "  cpdg8jx\n") == 10_000


@pytest.mark.parametrize("code", ["CPDG8J", "CPDG8JXA", ""])
def test_wrong_length_raises(code: str) -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Pat Jones", code)


@pytest.mark.parametrize("code", ["CPDG8J0", "CPDG8JI"])  # 0 and I are not in ALPHABET
def test_invalid_character_raises(code: str) -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Pat Jones", code)


def test_empty_normalized_name_raises_on_decode() -> None:
    with pytest.raises(AccountCodeError):
        decode_account("   ", "CPDG8JX")


def test_wrong_name_raises() -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Someone Else", "CPDG8JX")


def test_corrupted_code_raises() -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Pat Jones", "APDG8JX")  # first char flipped


def _normalizes_nonempty(name: str) -> bool:
    return " ".join(name.split()).casefold() != ""


names: st.SearchStrategy[str] = st.text(min_size=1, max_size=40).filter(_normalizes_nonempty)
bankrolls: st.SearchStrategy[int] = st.integers(min_value=0, max_value=MAX_BANKROLL)


@given(name=names, bankroll=bankrolls)
def test_round_trip(name: str, bankroll: int) -> None:
    code = encode_account(name, bankroll)
    assert len(code) == 7
    assert all(ch in ALPHABET for ch in code)
    assert decode_account(name, code) == bankroll


@given(
    name=names,
    bankroll=bankrolls,
    pos=st.integers(min_value=0, max_value=6),
    replacement=st.sampled_from(ALPHABET),
)
def test_single_substitution_never_restores_the_original_account(
    name: str, bankroll: int, pos: int, replacement: str
) -> None:
    code = encode_account(name, bankroll)
    assume(code[pos] != replacement)
    corrupted = code[:pos] + replacement + code[pos + 1 :]
    try:
        decoded = decode_account(name, corrupted)
    except AccountCodeError:
        return  # the corruption was detected — the common case
    # An 8-bit checksum collides on roughly 0.4% of substitutions. Even then the
    # decoded value is provably a DIFFERENT account than the one that was typed
    # over: it can never equal the original bankroll, and its canonical code is
    # the corrupted string, not the original one.
    assert decoded != bankroll
    assert encode_account(name, decoded) != code
```

- [ ] **Step 6: Run the tests to verify the new ones fail**

Run: `uv run pytest tests/core/test_codec.py -v`
Expected: FAIL at collection with `ImportError: cannot import name 'decode_account' from 'psychic_cleaners.core.codec'`.

- [ ] **Step 7: Implement the decoder**

Append to `src/psychic_cleaners/core/codec.py`:

```python
def decode_account(name: str, code: str) -> int:
    """Return the bankroll stored in ``code`` for ``name``.

    The code is normalized with .strip().upper() first, so pasted codes with
    stray whitespace or in lowercase are accepted. Raises AccountCodeError on
    any mismatch: wrong length, characters outside ALPHABET, a bankroll out of
    range for this name's key, or a checksum failure.
    """
    norm_name = _norm(name)
    normalized_code = code.strip().upper()
    if len(normalized_code) != _CODE_LENGTH:
        raise AccountCodeError("account code must be exactly 7 characters")
    raw = 0
    for ch in normalized_code:
        value = _CHAR_VALUES.get(ch)
        if value is None:
            raise AccountCodeError(f"invalid character in account code: {ch!r}")
        raw = raw * _BASE + value
    mixed = raw >> 8
    check = raw & 0xFF
    bankroll = mixed ^ _key(norm_name)
    if not 0 <= bankroll <= MAX_BANKROLL:
        raise AccountCodeError("account code does not match this name")
    if check != _checksum(norm_name, bankroll):
        raise AccountCodeError("account code failed its checksum")
    return bankroll
```

- [ ] **Step 8: Run the full codec test file to verify it passes**

Run: `uv run pytest tests/core/test_codec.py -v`
Expected: PASS — pytest reports `20 passed` (12 test functions expanding to 18 items via parametrization, plus the two Hypothesis properties; no Hypothesis health-check warnings).

- [ ] **Step 9: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: ruff clean, format changes nothing (or reformats only the files in this task — re-run pytest if it does), mypy `Success: no issues found`.

- [ ] **Step 10: Commit**

```
git add src/psychic_cleaners/core/codec.py tests/core/test_codec.py
git commit -m "feat: account code codec with crc key, checksum, and property tests"
```

### Task 14: Title flow — account restore in Game

**Files:**
- Modify: src/psychic_cleaners/core/game.py (TITLE-scene command handling: add `EnterAccount` support, route `NewGame` through `_reset()`)
- Test: tests/core/test_game_accounts.py

**Interfaces:**
- Consumes: `encode_account` / `decode_account` / `AccountCodeError` (Task 13); the `Game` skeleton, `new_game(seed)`, `_reset()`, and the existing TITLE dispatch in `Game.tick` (Task 7); `Wallet` (Task 9); the `notice` and shop fields on `Game` (Task 12); `STARTING_BANKROLL` from constants; commands `NewGame(name)`, `EnterAccount(name, code)`; events `AccountAccepted(name, bankroll)`, `AccountRejected(reason)`, `SceneChanged(scene)`, `SceneId` — all already defined in `core/events.py` per the contract.
- Produces: contract TITLE behaviour of `Game.tick`; `game.starting_bankroll` is now trustworthy — the finale task compares `wallet.balance > starting_bankroll` for the win condition. The rejection reason string is exactly `"invalid account code"`, and per the contract's notice convention `game.notice` is set to that string on rejection and cleared to `None` on acceptance — Task 15's `TitleScene.draw` renders it.

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_game_accounts.py`:

```python
"""TITLE-scene account handling in Game.tick."""

from psychic_cleaners.core.codec import encode_account
from psychic_cleaners.core.constants import STARTING_BANKROLL
from psychic_cleaners.core.events import (
    AccountAccepted,
    AccountRejected,
    EnterAccount,
    NewGame,
    SceneChanged,
    SceneId,
)
from psychic_cleaners.core.game import new_game


def test_valid_account_restores_exact_bankroll() -> None:
    game = new_game(1234)
    code = encode_account("Pat", 123_456)
    assert code == "BRAE99D"  # pinned so a codec regression is loud here too
    events = game.tick([EnterAccount("Pat", code)], 0.0)
    assert AccountAccepted("Pat", 123_456) in events
    assert SceneChanged(SceneId.SHOP) in events
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Pat"
    assert game.wallet.balance == 123_456
    assert game.starting_bankroll == 123_456


def test_invalid_code_rejected_and_stays_on_title() -> None:
    game = new_game(1234)
    # "AAAAAAA" decodes to raw 0 and fails the checksum for the name "Pat".
    events = game.tick([EnterAccount("Pat", "AAAAAAA")], 0.0)
    assert AccountRejected("invalid account code") in events
    assert game.scene is SceneId.TITLE
    assert game.player_name == ""
    assert game.wallet.balance == STARTING_BANKROLL
    assert game.starting_bankroll == STARTING_BANKROLL


def test_notice_set_on_rejection_and_cleared_on_success() -> None:
    game = new_game(1234)
    game.tick([EnterAccount("Pat", "AAAAAAA")], 0.0)
    assert game.notice == "invalid account code"  # TitleScene draws this verbatim
    events = game.tick([EnterAccount("Pat", encode_account("Pat", 123_456))], 0.0)
    assert AccountAccepted("Pat", 123_456) in events
    assert game.notice is None


def test_new_game_resets_starting_bankroll() -> None:
    game = new_game(1234)
    game.starting_bankroll = 42  # simulate leftover state from a previous restore
    game.notice = "stale notice"
    events = game.tick([NewGame("Pat")], 0.0)
    assert SceneChanged(SceneId.SHOP) in events
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Pat"
    assert game.wallet.balance == STARTING_BANKROLL
    assert game.starting_bankroll == STARTING_BANKROLL
    assert game.notice is None  # _reset() reinitializes every field
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/core/test_game_accounts.py -v`
Expected: FAIL — `test_valid_account_restores_exact_bankroll` and `test_invalid_code_rejected_and_stays_on_title` fail their first event assertion, and `test_notice_set_on_rejection_and_cleared_on_success` fails its first notice assertion (`EnterAccount` is not yet handled in TITLE, so no `AccountAccepted`/`AccountRejected` is emitted and `game.notice` stays `None`). `test_new_game_resets_starting_bankroll` already passes — Task 7's `NewGame` handling routes through `_reset()` — and stays in the file as a regression guard for this task's refactor.

- [ ] **Step 3: Implement the TITLE handler in Game**

In `src/psychic_cleaners/core/game.py`, make sure these imports are present (add whichever are missing to the existing import block; ruff will sort them in the quality-gate step):

```python
from psychic_cleaners.core.codec import AccountCodeError, decode_account
from psychic_cleaners.core.events import (
    AccountAccepted,
    AccountRejected,
    Command,
    EnterAccount,
    Event,
    NewGame,
    SceneChanged,
    SceneId,
)
```

Add this method to the `Game` dataclass:

```python
    def _handle_title(self, command: Command) -> list[Event]:
        """Handle a command received while on the TITLE scene."""
        if isinstance(command, NewGame):
            self._reset()  # restores wallet, loadout, starting_bankroll, notice, ... (Task 7)
            self.player_name = command.name
            self.scene = SceneId.SHOP
            return [SceneChanged(SceneId.SHOP)]
        if isinstance(command, EnterAccount):
            try:
                bankroll = decode_account(command.name, command.code)
            except AccountCodeError:
                self.notice = "invalid account code"
                return [AccountRejected("invalid account code")]
            self.player_name = command.name
            self.wallet.balance = bankroll
            self.starting_bankroll = bankroll
            self.notice = None
            self.scene = SceneId.SHOP
            return [AccountAccepted(command.name, bankroll), SceneChanged(SceneId.SHOP)]
        return []
```

Note that `NewGame` does NOT touch `wallet.balance`, `starting_bankroll`, or `loadout` inline — restoring all defaults (including the loadout reset) is `_reset()`'s job per the Task 7 convention, and every field-owning task keeps `_reset()` up to date.

Then, in `Game.tick`, find where commands are dispatched while `self.scene is SceneId.TITLE` (Task 7 created this branch with inline `NewGame` handling that calls `_reset()`, sets `player_name`, and moves to SHOP). Delete that inline handling and route every TITLE-scene command through the new method, so the TITLE arm of the per-command dispatch becomes exactly:

```python
            if self.scene is SceneId.TITLE:
                events.extend(self._handle_title(command))
```

(where `events` is the frame's `list[Event]` accumulator and `command` the loop variable — keep the surrounding loop and the other scene arms untouched).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_game_accounts.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the whole core and integration suites to check for regressions**

Run: `uv run pytest tests/core tests/integration -v`
Expected: PASS — the core-spine FSM walkthrough still works because `NewGame` still lands in SHOP with a `SceneChanged(SceneId.SHOP)` event.

- [ ] **Step 6: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: all clean, mypy `Success: no issues found`.

- [ ] **Step 7: Commit**

```
git add src/psychic_cleaners/core/game.py tests/core/test_game_accounts.py
git commit -m "feat: restore accounts from codes on the title screen"
```

### Task 15: Title scene with account entry

**Files:**
- Create: src/psychic_cleaners/shell/scenes/title.py
- Modify: src/psychic_cleaners/shell/app.py (register `TitleScene()` for `SceneId.TITLE` in `SCENES`)
- Test: tests/shell/test_title_scene.py

**Interfaces:**
- Consumes: the `Scene` protocol from `shell/scenes/__init__.py` (Task 8) (`commands(events, game) -> list[Command]`, `draw(surface, game, gfx, text) -> None`); `Game` / `new_game` from `core.game` (Task 7) and its `notice` field (Task 12, set/cleared by Task 14); commands `NewGame`, `EnterAccount`; `SpriteFactory.get("logo")` and `TextRenderer.draw` (Task 8); `SCENES` and `LOGICAL_SIZE` from `shell/app.py`; `tests/conftest.py` already sets `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy`.
- Produces: `TitleScene` registered at `SCENES[SceneId.TITLE]` — the app boots into a usable title screen.

Behaviour: two text fields, name (max 20 chars) and account code (max 7 chars, stored uppercased). Tab toggles focus; `pygame.TEXTINPUT` events append printable characters to the focused field; Backspace deletes the last character of the focused field; Enter emits `EnterAccount(name, code)` when the code field is non-empty, otherwise `NewGame(name)`, and is ignored while the name is empty (whitespace-only counts as empty). Focus and both buffers are plain instance state. `draw` renders `game.notice` as a visible error line when it is set — the contract requires TitleScene to draw rejection feedback (Task 14 sets it to `"invalid account code"` on a bad code).

- [ ] **Step 1: Write the failing input-handling tests**

Create `tests/shell/test_title_scene.py`:

```python
"""TitleScene: text entry, focus handling, command emission, draw smoke test."""

import pygame

from psychic_cleaners.core.events import EnterAccount, NewGame
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.shell.scenes.title import TitleScene


def _text(text: str) -> pygame.event.Event:
    return pygame.event.Event(pygame.TEXTINPUT, text=text)


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def _game() -> Game:
    return new_game(1)


def test_textinput_appends_to_name_field() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _text("t")], _game())
    assert scene._name == "Pat"
    assert scene._code == ""


def test_tab_moves_focus_and_code_is_uppercased() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _key(pygame.K_TAB), _text("a"), _text("b"), _text("7")], _game())
    assert scene._name == "P"
    assert scene._code == "AB7"


def test_tab_toggles_back_to_name() -> None:
    scene = TitleScene()
    scene.commands([_key(pygame.K_TAB), _key(pygame.K_TAB), _text("x")], _game())
    assert scene._name == "x"
    assert scene._code == ""


def test_backspace_edits_the_focused_field() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _key(pygame.K_BACKSPACE)], _game())
    assert scene._name == "P"
    scene.commands([_key(pygame.K_TAB), _text("x"), _key(pygame.K_BACKSPACE)], _game())
    assert scene._code == ""
    # Backspace on an already-empty field is a no-op, not an error.
    scene.commands([_key(pygame.K_BACKSPACE)], _game())
    assert scene._code == ""


def test_field_length_limits() -> None:
    scene = TitleScene()
    scene.commands([_text("a")] * 25, _game())
    assert scene._name == "a" * 20
    scene.commands([_key(pygame.K_TAB)], _game())
    scene.commands([_text("b")] * 10, _game())
    assert scene._code == "B" * 7


def test_enter_with_empty_code_emits_new_game() -> None:
    scene = TitleScene()
    out = scene.commands([_text("P"), _text("a"), _text("t"), _key(pygame.K_RETURN)], _game())
    assert out == [NewGame("Pat")]


def test_enter_with_code_emits_enter_account() -> None:
    scene = TitleScene()
    scene.commands([_text("P"), _text("a"), _text("t"), _key(pygame.K_TAB)], _game())
    out = scene.commands([_text(ch) for ch in "cpdg8jx"] + [_key(pygame.K_RETURN)], _game())
    assert out == [EnterAccount("Pat", "CPDG8JX")]


def test_enter_ignored_while_name_empty() -> None:
    scene = TitleScene()
    assert scene.commands([_key(pygame.K_RETURN)], _game()) == []
    scene.commands([_text(" ")], _game())  # whitespace-only name still counts as empty
    assert scene.commands([_key(pygame.K_RETURN)], _game()) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/shell/test_title_scene.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'psychic_cleaners.shell.scenes.title'`.

- [ ] **Step 3: Implement the scene's state and input handling**

Create `src/psychic_cleaners/shell/scenes/title.py`:

```python
"""Title scene: name entry and account-code restore."""

import enum
from typing import Final

import pygame

from psychic_cleaners.core.events import Command, EnterAccount, NewGame
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_NAME_MAX: Final[int] = 20
_CODE_MAX: Final[int] = 7


class _Field(enum.Enum):
    NAME = enum.auto()
    CODE = enum.auto()


class TitleScene:
    """Two text fields (name, account code); Enter starts the game.

    A non-empty code field means "restore my account" (EnterAccount);
    an empty one starts a fresh franchise (NewGame).
    """

    def __init__(self) -> None:
        self._name: str = ""
        self._code: str = ""
        self._focus: _Field = _Field.NAME

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.TEXTINPUT:
                self._append(str(event.text))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self._focus = _Field.CODE if self._focus is _Field.NAME else _Field.NAME
                elif event.key == pygame.K_BACKSPACE:
                    if self._focus is _Field.NAME:
                        self._name = self._name[:-1]
                    else:
                        self._code = self._code[:-1]
                elif event.key == pygame.K_RETURN and self._name.strip():
                    if self._code:
                        out.append(EnterAccount(self._name, self._code))
                    else:
                        out.append(NewGame(self._name))
        return out

    def _append(self, text: str) -> None:
        printable = "".join(ch for ch in text if ch.isprintable())
        if self._focus is _Field.NAME:
            self._name = (self._name + printable)[:_NAME_MAX]
        else:
            self._code = (self._code + printable.upper())[:_CODE_MAX]
```

(`draw` is added in the next cycle; `SpriteFactory` and `TextRenderer` are imported now so the file's import block is final.) If ruff flags the two imports as unused at this intermediate point, ignore it until Step 7 adds `draw` — the quality gates only run at the end of the task.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/shell/test_title_scene.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Write the failing rendering and registry tests**

Append to `tests/shell/test_title_scene.py`:

```python
def test_draw_smoke() -> None:
    pygame.init()  # dummy video/audio drivers via tests/conftest.py
    surface = pygame.Surface(LOGICAL_SIZE)
    scene = TitleScene()
    scene.commands([_text("P"), _key(pygame.K_TAB), _text("x")], _game())
    scene.draw(surface, _game(), SpriteFactory(), TextRenderer())
    rejected = _game()
    rejected.notice = "invalid account code"
    scene.draw(surface, rejected, SpriteFactory(), TextRenderer())  # exercises the error line


def test_registry_uses_title_scene() -> None:
    assert isinstance(SCENES[SceneId.TITLE], TitleScene)
```

and replace the import block at the top of the file with:

```python
import pygame

from psychic_cleaners.core.events import EnterAccount, NewGame, SceneId
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.shell.app import LOGICAL_SIZE, SCENES
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.title import TitleScene
from psychic_cleaners.shell.text import TextRenderer
```

- [ ] **Step 6: Run the tests to verify the new ones fail**

Run: `uv run pytest tests/shell/test_title_scene.py -v`
Expected: FAIL — `test_draw_smoke` with `AttributeError: 'TitleScene' object has no attribute 'draw'`, and `test_registry_uses_title_scene` with an assertion error (the registry still holds the core-spine placeholder scene).

- [ ] **Step 7: Implement draw and register the scene**

Append these two methods to the `TitleScene` class in `src/psychic_cleaners/shell/scenes/title.py`:

```python
    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((14, 10, 38))
        logo = gfx.get("logo")
        surface.blit(logo, ((surface.get_width() - logo.get_width()) // 2, 32))
        name_focused = self._focus is _Field.NAME
        self._draw_field(surface, text, "Name", self._name, 200, focused=name_focused)
        self._draw_field(surface, text, "Account code", self._code, 250, focused=not name_focused)
        if game.notice is not None:
            text.draw(surface, game.notice, (110, 305), size=16, color=(255, 96, 96))
        text.draw(
            surface,
            "Tab switches fields. Enter starts. Blank code = new $10,000 franchise.",
            (110, 340),
            size=14,
            color=(160, 160, 190),
        )

    def _draw_field(
        self,
        surface: pygame.Surface,
        text: TextRenderer,
        label: str,
        value: str,
        y: int,
        *,
        focused: bool,
    ) -> None:
        color = (255, 214, 90) if focused else (110, 110, 140)
        text.draw(surface, label, (110, y + 6), size=16, color=color)
        box = pygame.Rect(250, y, 280, 28)
        pygame.draw.rect(surface, color, box, width=2)
        cursor = "_" if focused else ""
        text.draw(surface, value + cursor, (258, y + 6), size=16)
```

Then in `src/psychic_cleaners/shell/app.py`:
1. Add to the import block: `from psychic_cleaners.shell.scenes.title import TitleScene`
2. In the `SCENES` registry dict, change only the value for the `SceneId.TITLE` key (the core-spine milestone registered a placeholder scene there) so the entry reads exactly:

```python
    SceneId.TITLE: TitleScene(),
```

Leave the other six entries untouched. If a core-spine smoke test asserts the placeholder type for the TITLE entry, update that one assertion to expect `TitleScene`.

- [ ] **Step 8: Run the scene tests to verify they pass**

Run: `uv run pytest tests/shell/test_title_scene.py -v`
Expected: PASS (10 tests).

- [ ] **Step 9: Run the full test suite**

Run: `uv run pytest`
Expected: PASS — everything green, including the app/scene smoke tests that now render `TitleScene` for `SceneId.TITLE`.

- [ ] **Step 10: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: all clean, mypy `Success: no issues found` (mypy structurally checks `TitleScene` against the `Scene` protocol via the `SCENES` registry annotation).

- [ ] **Step 11: Commit**

```
git add src/psychic_cleaners/shell/scenes/title.py src/psychic_cleaners/shell/app.py tests/shell/test_title_scene.py
git commit -m "feat: title scene with name and account-code entry"
```

<!-- CONTRACT-NOTE: decode_account normalizes the incoming code with .strip().upper() before any validation, exactly as the contract's core/codec.py algorithm specifies ("decode normalizes the incoming code with .strip().upper() before any validation"). Codes pasted with stray whitespace or typed lowercase therefore decode fine. -->
<!-- CONTRACT-NOTE: the briefed single-substitution property ("decode raises OR re-encoding the decoded value differs from the corrupted code") is unsatisfiable as written: whenever a corrupted code passes the 8-bit checksum (~0.4% of substitutions, verified empirically), re-encoding the decoded value reproduces the corrupted code exactly, because the 7-digit base-30 encoding is bijective below 30**7. The test instead asserts the sound guarantee: decode raises, or the decoded bankroll differs from the original AND its canonical code differs from the original code (i.e. corruption never silently restores the typed-over account). -->
<!-- CONTRACT-NOTE: AccountRejected reason string fixed as "invalid account code" (from the Task 14 brief); AccountAccepted is emitted before SceneChanged in the same tick. -->
<!-- CONTRACT-NOTE: TitleScene treats a whitespace-only name as empty for the Enter key (matches the codec's name normalization, which would reject it anyway). -->

---

## Milestone 5: City & PSI — the world starts ticking

Goal: build the pure-core PSI (psychic residue) model and the city simulation (grid, hauntings, wisps drifting toward Threshold Tower), then wire them into `Game`'s world tick and give the shell a real city-map scene with a HUD. When this milestone lands, finishing shopping drops you onto a living city map: buildings flash haunted, wisps drift toward the Tower, PSI climbs on the HUD, and pressing Enter instantly teleports the van to the cursor (Task 21 in the Drive milestone replaces instant travel with the real drive scene).

All paths are relative to the repo root `/home/geoff/code/psychic-cleaners/`. Source lives under `src/psychic_cleaners/`. Every constant, event, and signature used below is defined in the interface contract appendix — use those exact names.

---

### Task 16: Psychic Residue Model (`PsiModel`)

**Files:**
- Create: `src/psychic_cleaners/core/pk.py`
- Test: `tests/core/test_pk.py`

**Interfaces:**
- Consumes: `PSI_GROWTH_PER_MINUTE`, `PSI_HAUNT_GROWTH_PER_MINUTE`, `PSI_MAX` from `psychic_cleaners.core.constants` (Task 4).
- Produces: `PsiModel` with `psi: float = 0.0`, `advance(dt_seconds: float, active_haunts: int) -> None`, `spike(amount: float) -> None`, properties `value: int` and `at_max: bool`. Tasks 18–19 and the finale milestone rely on these exactly.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_pk.py`:

```python
"""Tests for the city-wide psychic residue (PSI) model."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.constants import (
    PSI_GROWTH_PER_MINUTE,
    PSI_HAUNT_GROWTH_PER_MINUTE,
    PSI_MAX,
)
from psychic_cleaners.core.pk import PsiModel


def test_advance_base_growth_per_minute() -> None:
    model = PsiModel()
    model.advance(60.0, active_haunts=0)
    assert model.psi == pytest.approx(PSI_GROWTH_PER_MINUTE)


def test_advance_scales_with_active_haunts() -> None:
    model = PsiModel()
    model.advance(60.0, active_haunts=2)
    expected = PSI_GROWTH_PER_MINUTE + 2 * PSI_HAUNT_GROWTH_PER_MINUTE
    assert model.psi == pytest.approx(expected)


def test_advance_partial_minute() -> None:
    model = PsiModel()
    model.advance(6.0, active_haunts=0)  # a tenth of a minute
    assert model.psi == pytest.approx(PSI_GROWTH_PER_MINUTE / 10.0)


def test_value_truncates_below_max() -> None:
    model = PsiModel(psi=9998.7)
    assert model.value == 9998
    assert not model.at_max


def test_spike_clamps_to_max() -> None:
    model = PsiModel(psi=5000.0)
    model.spike(1_000_000.0)
    assert model.psi == float(PSI_MAX)
    assert model.value == PSI_MAX
    assert model.at_max


def test_spike_clamps_to_zero() -> None:
    model = PsiModel(psi=50.0)
    model.spike(-1_000_000.0)
    assert model.psi == 0.0
    assert model.value == 0
    assert not model.at_max


def test_value_capped_when_growth_overshoots() -> None:
    model = PsiModel(psi=float(PSI_MAX))
    model.advance(60.0, active_haunts=0)
    assert model.psi > PSI_MAX  # the raw float keeps growing
    assert model.value == PSI_MAX  # but the public value is capped
    assert model.at_max


@given(
    steps=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=3600.0),
            st.integers(min_value=0, max_value=10),
        ),
        max_size=50,
    )
)
def test_advance_monotone_and_value_bounded(steps: list[tuple[float, int]]) -> None:
    model = PsiModel()
    previous = model.psi
    for dt, haunts in steps:
        model.advance(dt, haunts)
        assert model.psi >= previous
        assert 0 <= model.value <= PSI_MAX
        previous = model.psi
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_pk.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'psychic_cleaners.core.pk'`

- [ ] **Step 3: Write minimal implementation**

Create `src/psychic_cleaners/core/pk.py`:

```python
"""City-wide psychic residue (PSI) model: growth, spikes, thresholds."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    PSI_GROWTH_PER_MINUTE,
    PSI_HAUNT_GROWTH_PER_MINUTE,
    PSI_MAX,
)


@dataclass
class PsiModel:
    """Raw PSI is a float that only `spike` clamps; `value` caps the public int."""

    psi: float = 0.0

    def advance(self, dt_seconds: float, active_haunts: int) -> None:
        rate = PSI_GROWTH_PER_MINUTE + PSI_HAUNT_GROWTH_PER_MINUTE * active_haunts
        self.psi += rate * dt_seconds / 60.0

    def spike(self, amount: float) -> None:
        self.psi = min(max(self.psi + amount, 0.0), float(PSI_MAX))

    @property
    def value(self) -> int:
        return min(max(int(self.psi), 0), PSI_MAX)

    @property
    def at_max(self) -> bool:
        return self.value >= PSI_MAX
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_pk.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: no lint errors, no reformats reported as errors, `Success: no issues found` from mypy

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/pk.py tests/core/test_pk.py
git commit -m "feat: add psychic residue (PSI) model with growth and clamped spikes"
```

---

### Task 17: City Grid and Distances

**Files:**
- Create: `src/psychic_cleaners/core/city.py`
- Test: `tests/core/test_city.py`

**Interfaces:**
- Consumes: `GRID_WIDTH`, `GRID_HEIGHT`, `TOWER_POS`, `DEPOT_POS`, `BLOCK_LENGTH` from `core.constants` (Task 4); `GridPos` from `core.events` (Task 6).
- Produces: `Building(pos: GridPos, haunted: bool = False)`, `Wisp(x: float, y: float)`, `City(buildings: dict[GridPos, Building], wisps: list[Wisp])` with `City.new()`, `haunted_positions()`, `active_haunts()`, `clear_haunt(pos)`, `stompable_positions()`, `distance(a, b)`. Task 18 adds `City.tick`; do NOT define `tick` here (no `NotImplementedError` stubs either).

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_city.py`:

```python
"""Tests for the city grid: buildings, haunt bookkeeping, distances."""

from psychic_cleaners.core.city import Building, City
from psychic_cleaners.core.constants import (
    BLOCK_LENGTH,
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    TOWER_POS,
)


def test_new_city_has_58_buildings() -> None:
    city = City.new()
    assert len(city.buildings) == GRID_WIDTH * GRID_HEIGHT - 2 == 58
    assert city.wisps == []


def test_tower_and_depot_cells_are_empty() -> None:
    city = City.new()
    assert TOWER_POS not in city.buildings
    assert DEPOT_POS not in city.buildings


def test_buildings_know_their_positions_and_start_unhaunted() -> None:
    city = City.new()
    assert city.buildings[(0, 0)] == Building(pos=(0, 0), haunted=False)
    assert city.buildings[(9, 5)] == Building(pos=(9, 5), haunted=False)


def test_distance_is_manhattan_times_block_length() -> None:
    city = City.new()
    assert city.distance((0, 0), (3, 2)) == 5 * BLOCK_LENGTH
    assert city.distance((3, 2), (0, 0)) == 5 * BLOCK_LENGTH
    assert city.distance((4, 4), (4, 4)) == 0.0


def test_haunt_bookkeeping() -> None:
    city = City.new()
    assert city.active_haunts() == 0
    city.buildings[(2, 2)].haunted = True
    city.buildings[(7, 1)].haunted = True
    assert city.active_haunts() == 2
    assert set(city.haunted_positions()) == {(2, 2), (7, 1)}
    city.clear_haunt((2, 2))
    assert city.haunted_positions() == [(7, 1)]


def test_clear_haunt_is_idempotent_and_safe() -> None:
    city = City.new()
    city.clear_haunt((2, 2))  # never haunted: no error, no change
    city.clear_haunt((2, 2))
    city.clear_haunt(TOWER_POS)  # not even a building: still no error
    assert city.active_haunts() == 0


def test_stompable_positions_are_all_buildings() -> None:
    city = City.new()
    assert set(city.stompable_positions()) == set(city.buildings)
    assert len(city.stompable_positions()) == 58
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_city.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'psychic_cleaners.core.city'`

- [ ] **Step 3: Write minimal implementation**

Create `src/psychic_cleaners/core/city.py`:

```python
"""City model: grid of buildings, haunt bookkeeping, wisps, travel distances."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BLOCK_LENGTH,
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    TOWER_POS,
)
from psychic_cleaners.core.events import GridPos


@dataclass
class Building:
    pos: GridPos
    haunted: bool = False


@dataclass
class Wisp:
    x: float  # grid coordinates, float
    y: float


@dataclass
class City:
    buildings: dict[GridPos, Building]
    wisps: list[Wisp]

    @classmethod
    def new(cls) -> "City":
        buildings = {
            (x, y): Building(pos=(x, y))
            for x in range(GRID_WIDTH)
            for y in range(GRID_HEIGHT)
            if (x, y) not in (TOWER_POS, DEPOT_POS)
        }
        return cls(buildings=buildings, wisps=[])

    def haunted_positions(self) -> list[GridPos]:
        return [pos for pos, building in self.buildings.items() if building.haunted]

    def active_haunts(self) -> int:
        return len(self.haunted_positions())

    def clear_haunt(self, pos: GridPos) -> None:
        building = self.buildings.get(pos)
        if building is not None:
            building.haunted = False

    def stompable_positions(self) -> list[GridPos]:
        return list(self.buildings)

    def distance(self, a: GridPos, b: GridPos) -> float:
        return (abs(a[0] - b[0]) + abs(a[1] - b[1])) * BLOCK_LENGTH
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_city.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/city.py tests/core/test_city.py
git commit -m "feat: add city grid with buildings, wisps, and manhattan distances"
```

---

### Task 18: City Simulation Tick — Hauntings and Wisps

**Files:**
- Modify: `src/psychic_cleaners/core/city.py` (adds `tick` and private helpers)
- Test: `tests/core/test_city_tick.py`

**Interfaces:**
- Consumes: Task 17's `City`/`Wisp`; `HAUNT_CHANCE_PER_MINUTE`, `MAX_ACTIVE_HAUNTS`, `PSI_MAX`, `WISP_SPAWN_PER_MINUTE`, `WISP_MAP_SPEED`, `TOWER_POS` from `core.constants` (Task 4); `Rng`/`make_rng` from `core.rng`; `Event`, `HauntStarted`, `WispReachedTower` from `core.events` (Task 6). Probability-per-time pattern from the contract: `rng.random() < rate_per_minute * (dt_seconds / 60.0)`.
- Produces: `City.tick(dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]`. Task 19's `Game._world_tick` calls it.

This task has two TDD cycles: (A) haunt spawning, (B) wisp spawn/drift/tower arrival.

- [ ] **Step 1: Write the failing haunt tests (cycle A)**

Create `tests/core/test_city_tick.py`:

```python
"""Deterministic tests for City.tick: hauntings and wisps."""

from psychic_cleaners.core.city import City
from psychic_cleaners.core.constants import MAX_ACTIVE_HAUNTS
from psychic_cleaners.core.events import GridPos, HauntStarted
from psychic_cleaners.core.rng import make_rng


def test_haunts_spawn_and_respect_cap() -> None:
    rng = make_rng(42)
    city = City.new()
    started: list[GridPos] = []
    # 600 ticks of dt=1.0 = ten minutes of rate-clock time; expected uncapped
    # spawns ~= 0.8 * 10 = 8, so >= 1 spawn is a safe deterministic assertion.
    for _ in range(600):
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, HauntStarted):
                started.append(event.pos)
        assert city.active_haunts() <= MAX_ACTIVE_HAUNTS
    assert len(started) >= 1
    assert len(started) <= MAX_ACTIVE_HAUNTS  # nothing clears haunts here
    assert set(started) == set(city.haunted_positions())


def test_haunt_targets_are_unique_buildings() -> None:
    rng = make_rng(42)
    city = City.new()
    started: list[GridPos] = []
    for _ in range(600):
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, HauntStarted):
                started.append(event.pos)
    assert len(started) == len(set(started))
    for pos in started:
        assert pos in city.buildings


def test_no_haunt_with_zero_dt() -> None:
    rng = make_rng(1)
    city = City.new()
    assert city.tick(0.0, psi_value=9999, rng=rng) == []
    assert city.active_haunts() == 0
```

- [ ] **Step 2: Run tests to verify they fail (cycle A)**

Run: `uv run pytest tests/core/test_city_tick.py -v`
Expected: FAIL with `AttributeError: 'City' object has no attribute 'tick'`

- [ ] **Step 3: Implement haunt spawning (cycle A)**

In `src/psychic_cleaners/core/city.py`, replace the entire import block at the top of the file with (this is the final block for the whole task — the wisp names are used in cycle B):

```python
"""City model: grid of buildings, haunt bookkeeping, wisps, travel distances."""

import math
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BLOCK_LENGTH,
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    HAUNT_CHANCE_PER_MINUTE,
    MAX_ACTIVE_HAUNTS,
    PSI_MAX,
    TOWER_POS,
    WISP_MAP_SPEED,
    WISP_SPAWN_PER_MINUTE,
)
from psychic_cleaners.core.events import Event, GridPos, HauntStarted, WispReachedTower
from psychic_cleaners.core.rng import Rng
```

Then add these two methods to the `City` class, after `stompable_positions` and before `distance`:

```python
    def tick(self, dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]:
        events: list[Event] = []
        events.extend(self._spawn_haunts(dt_seconds, psi_value, rng))
        return events

    def _spawn_haunts(self, dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]:
        if self.active_haunts() >= MAX_ACTIVE_HAUNTS:
            return []
        chance = HAUNT_CHANCE_PER_MINUTE * (1.0 + psi_value / PSI_MAX)
        if rng.random() >= chance * dt_seconds / 60.0:
            return []
        candidates = [pos for pos, building in self.buildings.items() if not building.haunted]
        if not candidates:
            return []
        target = rng.choice(candidates)
        self.buildings[target].haunted = True
        return [HauntStarted(target)]
```

- [ ] **Step 4: Run tests to verify they pass (cycle A)**

Run: `uv run pytest tests/core/test_city_tick.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the failing wisp tests (cycle B)**

Append to `tests/core/test_city_tick.py` (and add `Wisp` and `WispReachedTower` to the existing imports — add `import math` at the top and the import lines become `from psychic_cleaners.core.city import City, Wisp` and `from psychic_cleaners.core.events import GridPos, HauntStarted, WispReachedTower`):

```python
def test_wisp_drifts_toward_tower_with_normalised_direction() -> None:
    rng = make_rng(1)
    city = City.new()
    # Directly below-left of nothing: (5.0, 0.0) is straight "north" of the
    # tower at (5, 3), so the direction vector is (0, 1): x must not change.
    city.wisps.append(Wisp(x=5.0, y=0.0))
    city.tick(1.0, psi_value=0, rng=rng)
    wisp = city.wisps[0]
    assert wisp.x == 5.0
    assert abs(wisp.y - 0.05) < 1e-9  # WISP_MAP_SPEED cells in one second


def test_wisp_adjacent_to_tower_reaches_it() -> None:
    rng = make_rng(7)
    city = City.new()
    city.wisps.append(Wisp(x=5.0, y=2.0))  # 1.0 cells from the tower at (5, 3)
    reached = 0
    # Needs to close from 1.0 to within 0.5 cells at 0.05 cells/sec: about
    # 10 ticks; 15 gives float-rounding headroom. Wisps spawned by the tick
    # itself (at random buildings) may also reach the tower, so assert on
    # "at least one" arrival rather than an exact count.
    for _ in range(15):
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, WispReachedTower):
                reached += 1
    assert reached >= 1
    # every wisp still in flight is outside the 0.5-cell arrival radius
    assert all(math.hypot(w.x - 5.0, w.y - 3.0) > 0.5 for w in city.wisps)


def test_wisps_spawn_at_buildings_over_time() -> None:
    rng = make_rng(11)
    city = City.new()
    reached = 0
    for _ in range(600):  # ten minutes: expected spawns ~= 0.6 * 10 = 6
        for event in city.tick(1.0, psi_value=0, rng=rng):
            if isinstance(event, WispReachedTower):
                reached += 1
    # every spawned wisp is either still drifting or has reached the tower
    assert len(city.wisps) + reached >= 1
```

- [ ] **Step 6: Run tests to verify they fail (cycle B)**

Run: `uv run pytest tests/core/test_city_tick.py -v`
Expected: the three new tests FAIL — the first with `AssertionError` (wisp never moved, `wisp.y == 0.0`), the others likewise, because `tick` ignores wisps entirely

- [ ] **Step 7: Implement wisp spawn, drift, and tower arrival (cycle B)**

In `src/psychic_cleaners/core/city.py`, replace the `tick` method body so the whole method reads:

```python
    def tick(self, dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]:
        events: list[Event] = []
        events.extend(self._spawn_haunts(dt_seconds, psi_value, rng))
        self._spawn_wisps(dt_seconds, rng)
        events.extend(self._drift_wisps(dt_seconds))
        return events
```

Add these two methods after `_spawn_haunts`:

```python
    def _spawn_wisps(self, dt_seconds: float, rng: Rng) -> None:
        if rng.random() >= WISP_SPAWN_PER_MINUTE * dt_seconds / 60.0:
            return
        # Spec 4.3: wisps spawn at random buildings and drift toward the Tower.
        cell = rng.choice(list(self.buildings))
        self.wisps.append(Wisp(x=float(cell[0]), y=float(cell[1])))

    def _drift_wisps(self, dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        tower_x, tower_y = float(TOWER_POS[0]), float(TOWER_POS[1])
        remaining: list[Wisp] = []
        for wisp in self.wisps:
            dx = tower_x - wisp.x
            dy = tower_y - wisp.y
            length = math.hypot(dx, dy)
            if length > 0.0:
                step = min(WISP_MAP_SPEED * dt_seconds, length)
                wisp.x += dx / length * step
                wisp.y += dy / length * step
            if math.hypot(tower_x - wisp.x, tower_y - wisp.y) <= 0.5:
                events.append(WispReachedTower())
            else:
                remaining.append(wisp)
        self.wisps = remaining
        return events
```

- [ ] **Step 8: Run all city tests to verify they pass**

Run: `uv run pytest tests/core/test_city_tick.py tests/core/test_city.py -v`
Expected: PASS (13 tests)

- [ ] **Step 9: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 10: Commit**

```bash
git add src/psychic_cleaners/core/city.py tests/core/test_city_tick.py
git commit -m "feat: add city simulation tick for haunt spawning and wisp drift"
```

---

### Task 19: Map Flow in Game, City Map Scene, and HUD

**Files:**
- Modify: `src/psychic_cleaners/core/game.py` (new fields, helpers, world tick, MAP handler)
- Modify: `src/psychic_cleaners/shell/gfx.py` (five new sprite builders)
- Modify: `src/psychic_cleaners/shell/app.py` (register `CityMapScene` under `SceneId.MAP`)
- Create: `src/psychic_cleaners/shell/scenes/city_map.py`
- Test: `tests/integration/test_map_flow.py`, `tests/shell/test_city_sprites.py`, `tests/shell/test_city_map_scene.py`

**Interfaces:**
- Consumes: `PsiModel` (Task 16); `City`, `Wisp` (Tasks 17–18); the `Game` skeleton, `new_game`, and `Game._reset()` (Task 7) plus the TITLE/SHOP handling and `SCENES` registry from Milestone 2; `Wallet`, `Loadout`, and the `game.notice` convention (Task 12); `VEHICLES`/`ITEMS` from the Milestone 3 catalog; `SpriteFactory` (Task 8) and `TextRenderer` from Milestone 1; constants `DEPOT_POS`, `TOWER_POS`, `GRID_WIDTH`, `GRID_HEIGHT`, `CLEANER_COUNT`, `WISP_TOWER_PSI_JUMP`, `PSI_MAX` (Task 4); events `SetDestination`, `Arrived`, `BuyItem`, `ItemBought`, `PurchaseRejected`, `SnaresEmptied`, `CleanersRestored`, `FinaleUnlocked`, `WispReachedTower`, `GridPos`, `SceneId` (Task 6).
- Produces: `Game.psi`, `Game.city`, `Game.position`, `Game.destination`, `Game.finale_unlocked`, `Game.slimed`, `Game.snares_full`, `Game.contained`, `Game.free_snares()`, `Game.able_cleaners()`, the world-tick gate (scenes MAP/DRIVE/BUST), the arrival routing hook `Game._arrive_at` (extended by the Drive/Bust/Finale milestones), the Depot snare restock (`BuyItem` on the MAP scene), `CityMapScene`, and sprites `"building"`, `"building.haunted"`, `"tower"`, `"depot"`, `"wisp"`.

NOTE: this task implements INSTANT TRAVEL on the map (arrive in the same tick). That is a deliberate placeholder; Task 21 (Drive milestone) replaces the `SetDestination` branch with a `DriveSim`, `TravelStarted`, and the DRIVE scene, exactly as the contract's MAP section describes. The test `test_instant_travel_to_neighbour` (Step 9 below) deliberately encodes the placeholder behaviour, so Task 21 MUST rewrite that test to assert the contract behaviour (scene becomes DRIVE, `TravelStarted` emitted, `Arrived` only after the drive completes) — it is a known casualty of this task, not a regression guard.

This task has five TDD cycles: (1) Game fields + helpers + `_reset` extension, (2) world tick, (3) instant travel + depot services + Depot snare restock, (4) city sprites, (5) the scene itself.

- [ ] **Step 1: Write the failing Game-field tests (cycle 1)**

Create `tests/integration/test_map_flow.py`. The import block below is the complete final one for this file; later cycles append tests that use the remaining names.

```python
"""Integration tests for Milestone 5: world tick, PSI, map travel, depot services."""

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import (
    CLEANER_COUNT,
    DEPOT_POS,
    PSI_GROWTH_PER_MINUTE,
    PSI_MAX,
    WISP_TOWER_PSI_JUMP,
)
from psychic_cleaners.core.events import (
    Arrived,
    BuyItem,
    CleanersRestored,
    FinaleUnlocked,
    ItemBought,
    NewGame,
    PurchaseRejected,
    SceneId,
    SetDestination,
    SnaresEmptied,
    WispReachedTower,
)
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout


def _map_game(seed: int) -> Game:
    """A game forced onto the map with a vehicle, skipping title/shop flow."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    return game


def test_new_fields_default() -> None:
    game = new_game(1)
    assert game.psi.value == 0
    assert game.city.active_haunts() == 0
    assert len(game.city.buildings) == 58
    assert game.position == DEPOT_POS
    assert game.destination is None
    assert game.finale_unlocked is False
    assert game.slimed == set()
    assert game.snares_full == 0
    assert game.contained == 0


def test_able_cleaners_and_free_snares() -> None:
    game = _map_game(2)
    assert game.able_cleaners() == CLEANER_COUNT
    game.slimed.add(0)
    assert game.able_cleaners() == CLEANER_COUNT - 1
    assert game.loadout is not None
    game.loadout.add("snare")
    game.loadout.add("snare")
    game.snares_full = 1
    assert game.free_snares() == 1


def test_free_snares_without_loadout_is_zero() -> None:
    game = new_game(3)
    assert game.free_snares() == 0


def test_new_game_resets_world_state() -> None:
    game = _map_game(4)
    game.psi.spike(500.0)
    game.city.buildings[(2, 2)].haunted = True
    game.position = (4, 4)
    game.destination = (5, 5)
    game.finale_unlocked = True
    game.slimed = {1}
    game.snares_full = 2
    game.contained = 3
    game.scene = SceneId.TITLE
    game.tick([NewGame("pat")], 0.0)
    assert game.scene is SceneId.SHOP
    assert game.psi.value == 0
    assert game.city.active_haunts() == 0
    assert game.position == DEPOT_POS
    assert game.destination is None
    assert game.finale_unlocked is False
    assert game.slimed == set()
    assert game.snares_full == 0
    assert game.contained == 0
```

- [ ] **Step 2: Run tests to verify they fail (cycle 1)**

Run: `uv run pytest tests/integration/test_map_flow.py -v`
Expected: FAIL with `AttributeError: 'Game' object has no attribute 'psi'` (and similar for the other new fields)

- [ ] **Step 3: Add fields, helpers, and the `_reset` extension to Game (cycle 1)**

Open `src/psychic_cleaners/core/game.py` (skeleton and `_reset` from Task 7, extended in Milestones 3–4).

First, make sure these names are imported — merge them into the existing `from ... import ...` statements rather than duplicating lines; ruff's `I` rule keeps them sorted:

```python
from psychic_cleaners.core.city import City
from psychic_cleaners.core.constants import CLEANER_COUNT, DEPOT_POS, WISP_TOWER_PSI_JUMP
from psychic_cleaners.core.events import (
    Arrived,
    CleanersRestored,
    FinaleUnlocked,
    GridPos,
    SetDestination,
    SnaresEmptied,
    WispReachedTower,
)
from psychic_cleaners.core.pk import PsiModel
```

Inside the `Game` dataclass, after the existing `loadout: Loadout | None = None` field (position among defaulted fields does not matter), add:

```python
    psi: PsiModel = field(default_factory=PsiModel)
    city: City = field(default_factory=City.new)
    slimed: set[int] = field(default_factory=set)  # cleaner indices 0..2
    contained: int = 0  # ghosts held in the containment rig
    snares_full: int = 0
    position: GridPos = DEPOT_POS
    destination: GridPos | None = None
    finale_unlocked: bool = False
```

Add these two methods to `Game` (next to any existing helpers):

```python
    def free_snares(self) -> int:
        if self.loadout is None:
            return 0
        return self.loadout.count("snare") - self.snares_full

    def able_cleaners(self) -> int:
        return CLEANER_COUNT - len(self.slimed)
```

Finally, extend `Game._reset()` (Task 7's convention: `NewGame` and `Continue` both route through `_reset()`, and every task that adds a `Game` field MUST add that field's reinitialization to `_reset()` in the same task). Add these lines to `_reset`, next to the existing field resets — do NOT put them in the `NewGame` handler itself:

```python
        self.psi = PsiModel()
        self.city = City.new()
        self.slimed = set()
        self.contained = 0
        self.snares_full = 0
        self.position = DEPOT_POS
        self.destination = None
        self.finale_unlocked = False
```

- [ ] **Step 4: Run tests to verify they pass (cycle 1)**

Run: `uv run pytest tests/integration/test_map_flow.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write the failing world-tick tests (cycle 2)**

Append to `tests/integration/test_map_flow.py`:

```python
def test_psi_frozen_outside_world_scenes() -> None:
    game = new_game(5)
    assert game.scene is SceneId.TITLE
    game.tick([], 60.0)
    assert game.psi.value == 0


def test_psi_grows_on_map() -> None:
    game = _map_game(6)
    game.tick([], 60.0)  # one rate-clock minute; no haunts were active before it
    assert game.psi.value == int(PSI_GROWTH_PER_MINUTE)


def test_wisp_reaching_tower_spikes_psi() -> None:
    game = _map_game(7)
    game.city.wisps.append(Wisp(x=5.0, y=2.6))  # already within reach of (5, 3)
    events = game.tick([], 1.0)
    assert any(isinstance(e, WispReachedTower) for e in events)
    assert game.psi.value >= WISP_TOWER_PSI_JUMP


def test_finale_unlocked_exactly_once() -> None:
    game = _map_game(8)
    game.psi.spike(float(PSI_MAX))
    first = game.tick([], 0.0)
    second = game.tick([], 0.0)
    assert sum(isinstance(e, FinaleUnlocked) for e in first) == 1
    assert not any(isinstance(e, FinaleUnlocked) for e in second)
    assert game.finale_unlocked is True
```

- [ ] **Step 6: Run tests to verify they fail (cycle 2)**

Run: `uv run pytest tests/integration/test_map_flow.py -v`
Expected: the four new tests FAIL — `test_psi_grows_on_map` with `AssertionError: assert 0 == 250` (PSI never advanced), the others similarly

- [ ] **Step 7: Implement the world tick (cycle 2)**

Add this method to `Game` in `src/psychic_cleaners/core/game.py` (world ticking only — resolution lives in `tick` below):

```python
    def _world_tick(self, dt_seconds: float) -> list[Event]:
        self.clock.advance(dt_seconds)
        self.psi.advance(dt_seconds, self.city.active_haunts())
        return self.city.tick(dt_seconds, self.psi.value, self.rng)
```

Wire it into `Game.tick` following the contract's canonical order: (1) the command dispatch loop runs FIRST (Milestone 2 established the `events: list[Event] = []` accumulator followed by the per-command dispatch loop), (2) scene/world ticking happens AFTER the loop, using the CURRENT (post-dispatch) scene, (3) post-tick resolution runs last. Immediately after the dispatch loop ends and before `return events`, insert:

```python
        # (2) scene/world ticking — AFTER the dispatch loop, on the current scene
        if self.scene in (SceneId.MAP, SceneId.DRIVE, SceneId.BUST):
            world_events = self._world_tick(dt_seconds)
            events.extend(world_events)
            # (3) post-tick resolution: wisp PSI jumps, one-shot finale unlock
            for event in world_events:
                if isinstance(event, WispReachedTower):
                    self.psi.spike(float(WISP_TOWER_PSI_JUMP))
            if self.psi.at_max and not self.finale_unlocked:
                self.finale_unlocked = True
                events.append(FinaleUnlocked())
```

(Later milestones extend phase 2 with drive/bust/mascot ticking and phase 3 with arrival routing, bust resolution, and the bankruptcy check — this block is the slot they extend.)

`_world_tick` now owns `clock.advance`. If Milestone 2's `tick` already calls `self.clock.advance(dt_seconds)` for world scenes, delete that call so the clock is not advanced twice (the contract freezes world time outside MAP/DRIVE/BUST, so an unconditional advance must also be removed).

- [ ] **Step 8: Run tests to verify they pass (cycle 2)**

Run: `uv run pytest tests/integration/test_map_flow.py -v`
Expected: PASS (8 tests)

- [ ] **Step 9: Write the failing travel and depot-restock tests (cycle 3)**

Append to `tests/integration/test_map_flow.py`:

```python
def test_instant_travel_to_neighbour() -> None:
    # PLACEHOLDER BEHAVIOUR: Milestone 5 travels instantly. The Drive
    # milestone (Task 21) replaces the MAP handler with DriveSim/TravelStarted
    # and MUST rewrite this test to match the contract's MAP section.
    game = _map_game(9)
    events = game.tick([SetDestination((1, 5))], 0.0)
    assert game.position == (1, 5)
    assert game.destination is None
    assert game.scene is SceneId.MAP
    assert Arrived((1, 5)) in events


def test_depot_visit_services_franchise() -> None:
    game = _map_game(10)
    game.position = (3, 4)
    game.snares_full = 2
    game.contained = 5
    game.slimed = {0, 2}
    events = game.tick([SetDestination(DEPOT_POS)], 0.0)
    assert game.position == DEPOT_POS
    assert game.snares_full == 0
    assert game.contained == 0
    assert game.slimed == set()
    assert any(isinstance(e, SnaresEmptied) for e in events)
    assert any(isinstance(e, CleanersRestored) for e in events)
    assert game.scene is SceneId.MAP


def test_depot_snare_restock_buys_a_snare() -> None:
    game = _map_game(11)
    assert game.position == DEPOT_POS
    assert game.loadout is not None
    owned = game.loadout.count("snare")
    balance = game.wallet.balance
    events = game.tick([BuyItem("snare")], 0.0)
    assert ItemBought("snare") in events
    assert game.loadout.count("snare") == owned + 1
    assert game.wallet.balance == balance - 600  # ITEMS["snare"].price
    assert game.notice is None


def test_depot_restock_rejects_other_items_and_other_places() -> None:
    game = _map_game(12)
    game.position = (3, 3)
    events = game.tick([BuyItem("snare")], 0.0)  # right item, wrong place
    assert PurchaseRejected("snares only, at the Depot") in events
    game.position = DEPOT_POS
    events = game.tick([BuyItem("vacuum")], 0.0)  # right place, wrong item
    assert PurchaseRejected("snares only, at the Depot") in events
    assert game.notice == "snares only, at the Depot"
    assert game.loadout is not None
    assert game.loadout.count("vacuum") == 0
```

- [ ] **Step 10: Run tests to verify they fail (cycle 3)**

Run: `uv run pytest tests/integration/test_map_flow.py -v`
Expected: the four new tests FAIL with `AssertionError` — `SetDestination` and `BuyItem` are ignored on the map, so `game.position` never changes and no `ItemBought`/`PurchaseRejected` events appear

- [ ] **Step 11: Implement the MAP handler, Depot restock, and arrival routing (cycle 3)**

First merge two more imports into `game.py`: `ITEMS` from `psychic_cleaners.core.catalog`, and `BuyItem`, `ItemBought`, `PurchaseRejected` into the existing `core.events` import block.

Add these three methods to `Game`:

```python
    def _handle_map(self, command: Command) -> list[Event]:
        if isinstance(command, SetDestination):
            # Instant-travel placeholder: the Drive milestone (Task 21) replaces
            # this with a DriveSim, TravelStarted, and the DRIVE scene.
            self.destination = command.pos
            return self._arrive_at(command.pos)
        if isinstance(command, BuyItem):
            return self._depot_restock(command.item_id)
        return []

    def _depot_restock(self, item_id: str) -> list[Event]:
        """Mid-game snare restock: only "snare", and only at the Depot."""
        if item_id != "snare" or self.position != DEPOT_POS:
            self.notice = "snares only, at the Depot"
            return [PurchaseRejected("snares only, at the Depot")]
        if self.loadout is None:  # defensive: MAP is unreachable without a vehicle
            self.notice = "no vehicle"
            return [PurchaseRejected("no vehicle")]
        if not self.wallet.can_afford(ITEMS["snare"].price):
            self.notice = "cannot afford"
            return [PurchaseRejected("cannot afford")]
        if not self.loadout.can_add("snare"):
            self.notice = "no space in the vehicle"
            return [PurchaseRejected("no space in the vehicle")]
        self.wallet.spend(ITEMS["snare"].price)
        self.loadout.add("snare")
        self.notice = None
        return [ItemBought("snare")]

    def _arrive_at(self, pos: GridPos) -> list[Event]:
        """Arrival routing: an if/elif chain ending in an `else` that routes to MAP.

        Later tasks insert their `elif` branches BETWEEN the depot branch and the
        final `else` (tower before haunted). Every arrival appends Arrived(pos).
        """
        self.position = pos
        self.destination = None
        events: list[Event] = [Arrived(pos)]
        if pos == DEPOT_POS:
            self.snares_full = 0
            self.contained = 0
            self.slimed.clear()
            events.append(SnaresEmptied())
            events.append(CleanersRestored())
            self.scene = SceneId.MAP
        else:
            self.scene = SceneId.MAP
        return events
```

The wallet/capacity checks in `_depot_restock` mirror the SHOP `BuyItem` path (Task 12 / Milestone 4); if that path already factored the checks into a helper, reuse it here so SHOP and Depot report identical messages — the Depot gate (`"snare"` at `DEPOT_POS` only, exact rejection `"snares only, at the Depot"`) is the only new rule. In this milestone every arrival happens while MAP is already the current scene, so both `self.scene = SceneId.MAP` assignments change nothing and no `SceneChanged` is emitted; Task 21, arriving from the DRIVE scene, adds the `SceneChanged(SceneId.MAP)` emission when the scene actually changes.

Wire the handler into `Game.tick`'s per-command scene dispatch, alongside the existing TITLE and SHOP branches. If the dispatch is a `match` on `self.scene`, add:

```python
            case SceneId.MAP:
                events.extend(self._handle_map(command))
```

If it is an `if`/`elif` chain, add the equivalent:

```python
            elif self.scene is SceneId.MAP:
                events.extend(self._handle_map(command))
```

- [ ] **Step 12: Run tests to verify they pass (cycle 3)**

Run: `uv run pytest tests/integration/test_map_flow.py -v`
Expected: PASS (12 tests)

- [ ] **Step 13: Write the failing sprite tests (cycle 4)**

Create `tests/shell/test_city_sprites.py` (relies on `tests/conftest.py` having set `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`):

```python
"""Existence and caching for the Milestone 5 city sprites."""

import pygame

from psychic_cleaners.shell.gfx import SpriteFactory


def test_city_sprites_exist() -> None:
    pygame.init()
    factory = SpriteFactory()
    for name in ("building", "building.haunted", "tower", "depot", "wisp"):
        sprite = factory.get(name)
        assert sprite.get_width() > 0
        assert sprite.get_height() > 0


def test_city_sprites_are_cached() -> None:
    pygame.init()
    factory = SpriteFactory()
    assert factory.get("building") is factory.get("building")
```

(These tests deliberately do NOT pin sprite sizes: the contract fixes FINAL sizes only in the polish milestone and forbids earlier tests from pinning them.)

- [ ] **Step 14: Run tests to verify they fail (cycle 4)**

Run: `uv run pytest tests/shell/test_city_sprites.py -v`
Expected: FAIL — `SpriteFactory` does not know the new names (typically `KeyError: 'building'` or the factory's unknown-sprite error from Task 8)

- [ ] **Step 15: Add the five sprite builders to gfx.py (cycle 4)**

In `src/psychic_cleaners/shell/gfx.py`, add these module-level builder functions (`pygame` is already imported there):

```python
def _build_building() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    surface.fill((70, 80, 110))
    pygame.draw.rect(surface, (40, 45, 70), pygame.Rect(0, 0, 48, 48), width=2)
    for wx in range(8, 41, 12):
        for wy in range(8, 41, 12):
            pygame.draw.rect(surface, (240, 220, 140), pygame.Rect(wx, wy, 6, 8))
    return surface


def _build_building_haunted() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    surface.fill((60, 105, 75))
    pygame.draw.rect(surface, (30, 60, 40), pygame.Rect(0, 0, 48, 48), width=2)
    for wx in range(8, 41, 12):
        for wy in range(8, 41, 12):
            pygame.draw.rect(surface, (180, 255, 130), pygame.Rect(wx, wy, 6, 8))
    pygame.draw.circle(surface, (200, 255, 160), (24, 6), 5)
    return surface


def _build_tower() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.rect(surface, (90, 60, 130), pygame.Rect(8, 16, 32, 32))
    pygame.draw.polygon(surface, (120, 80, 170), [(8, 16), (24, 0), (40, 16)])
    pygame.draw.rect(surface, (240, 230, 120), pygame.Rect(21, 34, 6, 14))
    return surface


def _build_depot() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    surface.fill((150, 70, 60))
    pygame.draw.rect(surface, (90, 40, 35), pygame.Rect(0, 0, 48, 48), width=2)
    pygame.draw.rect(surface, (230, 230, 230), pygame.Rect(16, 22, 16, 26))
    pygame.draw.rect(surface, (250, 250, 200), pygame.Rect(6, 6, 36, 10))
    return surface


def _build_wisp() -> pygame.Surface:
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.circle(surface, (180, 240, 255), (8, 8), 7)
    pygame.draw.circle(surface, (255, 255, 255), (6, 6), 3)
    return surface
```

Task 8 built `SpriteFactory.get` around the module-level `_BUILDERS: dict[str, Callable[[], pygame.Surface]]` registry of zero-argument builder functions (consulted on cache miss). Add these five entries to `_BUILDERS`:

```python
    "building": _build_building,
    "building.haunted": _build_building_haunted,
    "tower": _build_tower,
    "depot": _build_depot,
    "wisp": _build_wisp,
```

(`"wisp"` is introduced here; the Drive milestone reuses it and must not re-add it. The 48x48 / 16x16 dimensions are placeholders — the polish milestone lands the contract's final sizes.)

- [ ] **Step 16: Run tests to verify they pass (cycle 4)**

Run: `uv run pytest tests/shell/test_city_sprites.py -v`
Expected: PASS (2 tests)

- [ ] **Step 17: Write the failing scene tests (cycle 5)**

Create `tests/shell/test_city_map_scene.py`:

```python
"""Cursor handling and draw smoke test for the city map scene."""

import pygame

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import DEPOT_POS
from psychic_cleaners.core.events import SceneId, SetDestination
from psychic_cleaners.core.game import new_game
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.text import TextRenderer


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_cursor_moves_and_clamps_to_grid() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(1)
    assert scene.cursor == DEPOT_POS  # (0, 5)
    scene.commands([_key(pygame.K_RIGHT)], game)
    assert scene.cursor == (1, 5)
    scene.commands([_key(pygame.K_UP)], game)
    assert scene.cursor == (1, 4)
    scene.commands([_key(pygame.K_LEFT), _key(pygame.K_LEFT)], game)
    assert scene.cursor == (0, 4)  # clamped at x=0
    scene.commands([_key(pygame.K_DOWN), _key(pygame.K_DOWN)], game)
    assert scene.cursor == (0, 5)  # clamped at y=GRID_HEIGHT-1


def test_enter_emits_set_destination_at_cursor() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(2)
    scene.commands([_key(pygame.K_RIGHT)], game)
    commands = scene.commands([_key(pygame.K_RETURN)], game)
    assert commands == [SetDestination((1, 5))]


def test_draw_smoke_without_detector_hides_wisps() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(3)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])  # no detector
    game.scene = SceneId.MAP
    game.city.buildings[(2, 2)].haunted = True  # drawn as the static haunted sprite
    game.city.wisps.append(Wisp(x=4.5, y=2.5))  # centre pixel (320, 180): grid gutter
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 180)) == (24, 26, 34, 255)  # background: no wisp drawn


def test_draw_smoke_with_detector_shows_wisps() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(4)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("detector")
    game.scene = SceneId.MAP
    game.city.buildings[(2, 2)].haunted = True  # flashes: either sprite is valid
    game.city.wisps.append(Wisp(x=4.5, y=2.5))
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 180)) != (24, 26, 34, 255)  # wisp visible
```

- [ ] **Step 18: Run tests to verify they fail (cycle 5)**

Run: `uv run pytest tests/shell/test_city_map_scene.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'psychic_cleaners.shell.scenes.city_map'`

- [ ] **Step 19: Implement CityMapScene (cycle 5)**

Create `src/psychic_cleaners/shell/scenes/city_map.py`:

```python
"""City map scene: pick destinations, watch hauntings and wisps, read the HUD."""

import pygame

from psychic_cleaners.core.constants import (
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    PSI_MAX,
    TOWER_POS,
)
from psychic_cleaners.core.events import Command, GridPos, SetDestination
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_CELL: int = 56
_ORIGIN_X: int = 40
_ORIGIN_Y: int = 12
_HUD_Y: int = 356


def _cell_rect(pos: GridPos) -> pygame.Rect:
    return pygame.Rect(_ORIGIN_X + pos[0] * _CELL + 4, _ORIGIN_Y + pos[1] * _CELL + 4, 48, 48)


class CityMapScene:
    """Scene registered under SceneId.MAP."""

    def __init__(self) -> None:
        self.cursor: GridPos = DEPOT_POS

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        commands: list[Command] = []
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            x, y = self.cursor
            if event.key == pygame.K_LEFT:
                self.cursor = (max(x - 1, 0), y)
            elif event.key == pygame.K_RIGHT:
                self.cursor = (min(x + 1, GRID_WIDTH - 1), y)
            elif event.key == pygame.K_UP:
                self.cursor = (x, max(y - 1, 0))
            elif event.key == pygame.K_DOWN:
                self.cursor = (x, min(y + 1, GRID_HEIGHT - 1))
            elif event.key == pygame.K_RETURN:
                commands.append(SetDestination(self.cursor))
        return commands

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((24, 26, 34))
        detector = game.loadout is not None and game.loadout.has("detector")
        flash = int(pygame.time.get_ticks() / 250) % 2 == 0  # ~2 Hz toggle
        for pos, building in game.city.buildings.items():
            if not building.haunted:
                name = "building"
            elif detector:
                # residue detector: haunted buildings flash between the sprites
                name = "building.haunted" if flash else "building"
            else:
                name = "building.haunted"
            surface.blit(gfx.get(name), _cell_rect(pos).topleft)
        surface.blit(gfx.get("tower"), _cell_rect(TOWER_POS).topleft)
        surface.blit(gfx.get("depot"), _cell_rect(DEPOT_POS).topleft)
        if detector:
            # wisps are invisible without the residue detector
            wisp_sprite = gfx.get("wisp")
            for wisp in game.city.wisps:
                px = int(_ORIGIN_X + wisp.x * _CELL + _CELL / 2) - 8
                py = int(_ORIGIN_Y + wisp.y * _CELL + _CELL / 2) - 8
                surface.blit(wisp_sprite, (px, py))
        car = _cell_rect(game.position)
        car_rect = pygame.Rect(car.left + 16, car.top + 36, 16, 10)
        pygame.draw.rect(surface, (250, 250, 250), car_rect)
        cursor_rect = _cell_rect(self.cursor).inflate(6, 6)
        pygame.draw.rect(surface, (255, 230, 90), cursor_rect, width=2)
        self._draw_hud(surface, game, text)

    def _draw_hud(self, surface: pygame.Surface, game: Game, text: TextRenderer) -> None:
        pygame.draw.rect(surface, (12, 12, 18), pygame.Rect(0, _HUD_Y, 640, 400 - _HUD_Y))
        text.draw(surface, f"${game.wallet.balance}", (10, _HUD_Y + 6), size=16)
        text.draw(surface, f"PSI {game.psi.value:>4}", (10, _HUD_Y + 24), size=16)
        bar = pygame.Rect(90, _HUD_Y + 26, 120, 10)
        pygame.draw.rect(surface, (60, 60, 70), bar)
        fill_width = int(bar.width * game.psi.value / PSI_MAX)
        pygame.draw.rect(surface, (170, 90, 220), pygame.Rect(bar.left, bar.top, fill_width, 10))
        snares = f"snares {game.free_snares()} free / {game.snares_full} full"
        text.draw(surface, snares, (240, _HUD_Y + 6), size=16)
        text.draw(surface, f"contained {game.contained}", (240, _HUD_Y + 24), size=16)
        text.draw(surface, f"slimed {len(game.slimed)}", (430, _HUD_Y + 6), size=16)
```

Layout sanity: the grid occupies x 40..600 and y 12..348 of the 640x400 logical surface; the HUD strip fills y 356..400.

- [ ] **Step 20: Run tests to verify they pass (cycle 5)**

Run: `uv run pytest tests/shell/test_city_map_scene.py -v`
Expected: PASS (4 tests)

- [ ] **Step 21: Register CityMapScene in the scene registry**

In `src/psychic_cleaners/shell/app.py`, add the import (merged with the other scene imports):

```python
from psychic_cleaners.shell.scenes.city_map import CityMapScene
```

and in the `SCENES` registry, replace the Milestone 2 stub entry for the map so it reads:

```python
    SceneId.MAP: CityMapScene(),
```

Milestone 2's shell smoke test renders one frame of every scene in `SCENES`, so the next step verifies this registration (no dedicated new test needed).

- [ ] **Step 22: Run the full test suite**

Run: `uv run pytest`
Expected: PASS — everything from Milestones 1–4 plus the 39 tests added in this milestone (test_pk 8, test_city 7, test_city_tick 6, test_map_flow 12, test_city_sprites 2, test_city_map_scene 4)

- [ ] **Step 23: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 24: Commit**

```bash
git add src/psychic_cleaners/core/game.py \
        src/psychic_cleaners/shell/gfx.py \
        src/psychic_cleaners/shell/app.py \
        src/psychic_cleaners/shell/scenes/city_map.py \
        tests/integration/test_map_flow.py \
        tests/shell/test_city_sprites.py \
        tests/shell/test_city_map_scene.py
git commit -m "feat: wire PSI and city into game world tick with map scene and HUD"
```

---

<!-- CONTRACT-NOTE: Task 19 implements SetDestination as instant travel (position=pos + Arrived in the same tick) as a deliberate placeholder; the Drive milestone's Task 21 replaces it with DriveSim/TravelStarted/DRIVE per the contract's MAP section, and MUST also rewrite tests/integration/test_map_flow.py::test_instant_travel_to_neighbour, which encodes the placeholder behaviour. Game._arrive_at(pos) is the arrival-routing hook whose if/elif chain later milestones extend (elif branches inserted between the depot branch and the final else, tower before haunted). -->
<!-- CONTRACT-NOTE: The contract does not pin the depot-restock rejection messages beyond "snares only, at the Depot"; the wallet/capacity rejection strings here ("cannot afford", "no space in the vehicle", "no vehicle") should match whatever Milestone 4's shop handler uses. -->
<!-- CONTRACT-NOTE: The contract's city.tick comment specifies no wisp spawn location; per spec section 4.3 ("Wisps spawn at random buildings and drift toward the Tower") wisps spawn at an rng-chosen building position. -->
<!-- CONTRACT-NOTE: The sprite "wisp" (16x16) is created here in Milestone 5; the Drive milestone reuses it and must not register it a second time. -->

---

## Milestone 6: Driving

Goal: build the pure-core driving lane simulation (`core/drive.py`), route all map travel in `core/game.py` through it (replacing Task 19's instant teleport), and add the pygame driving scene with car sprites, wisps, and a progress bar. When this milestone lands, picking a destination on the city map plays a steerable three-lane driving sequence — with vacuum wisp catches paying bounties and thinning the city's wisp population — before the car arrives.

### Task 20: Driving simulation (core/drive.py)

**Files:**
- Create: src/psychic_cleaners/core/drive.py
- Test: tests/core/test_drive.py

**Interfaces:**
- Consumes: `core/constants.py` — `DRIVE_LANES`, `CAR_X`, `CATCH_RANGE`, `ROAD_WISP_SPAWN_PER_SECOND`, `ROAD_WISP_SPEED`, `FAINT_WISP_CHANCE`, `ROAD_LENGTH_VISIBLE`, `VACUUM_BOUNTY` (Task 4); `core/events.py` — `Event`, `WispCaptured(bounty: int)` (Task 6); `core/rng.py` — `Rng`, `make_rng(seed)` (Task 4).
- Produces: `RoadWisp(x: float, lane: int, faint: bool)` and `DriveSim(distance_total, speed, has_vacuum, has_lens, distance_done=0.0, lane=1, wisps=[])` with `steer(delta: int) -> None`, `tick(dt_seconds: float, rng: Rng) -> list[Event]`, `arrived: bool` property — consumed by Tasks 21 and 22 exactly as specified in the contract's `core/drive.py` section.

Processing order inside `tick` (fixed by this task, relied on by the tests): 1) advance `distance_done`, 2) move existing wisps toward the car, 3) catch or cull wisps, 4) maybe spawn one new wisp at `x == ROAD_LENGTH_VISIBLE`. Spawning last means a freshly spawned wisp ends its first tick exactly at the spawn x.

- [ ] **Step 1: Write the failing tests for progress and steering**

Create `tests/core/test_drive.py` with the full import block (later cycles append tests that use all of these imports; quality gates run only at the end of the task):

```python
"""Tests for the driving lane simulation."""

from psychic_cleaners.core.constants import (
    CAR_X,
    CATCH_RANGE,
    DRIVE_LANES,
    ROAD_LENGTH_VISIBLE,
    VACUUM_BOUNTY,
)
from psychic_cleaners.core.drive import DriveSim, RoadWisp
from psychic_cleaners.core.events import WispCaptured
from psychic_cleaners.core.rng import make_rng


def _sim(*, vacuum: bool = True, lens: bool = False) -> DriveSim:
    return DriveSim(distance_total=400.0, speed=100.0, has_vacuum=vacuum, has_lens=lens)


def test_not_arrived_before_distance_covered() -> None:
    sim = _sim()
    rng = make_rng(1)
    for _ in range(39):  # 3.9 s at 100 units/s -> 390 < 400
        sim.tick(0.1, rng)
    assert not sim.arrived


def test_arrives_after_distance_total_over_speed_seconds() -> None:
    sim = _sim()
    rng = make_rng(1)
    for _ in range(40):  # 4.0 s at 100 units/s -> distance_total/speed seconds
        sim.tick(0.1, rng)
    assert sim.arrived


def test_steer_moves_and_clamps_between_0_and_last_lane() -> None:
    sim = _sim()
    assert sim.lane == 1  # contract default
    sim.steer(-1)
    assert sim.lane == 0
    sim.steer(-1)
    assert sim.lane == 0  # clamped at 0
    sim.steer(1)
    sim.steer(1)
    assert sim.lane == DRIVE_LANES - 1
    sim.steer(1)
    assert sim.lane == DRIVE_LANES - 1  # clamped at DRIVE_LANES - 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_drive.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psychic_cleaners.core.drive'` (collection error).

- [ ] **Step 3: Write the minimal implementation (progress + steering)**

Create `src/psychic_cleaners/core/drive.py`:

```python
"""Driving lane simulation: forward progress, road wisps, vacuum catch geometry."""

from dataclasses import dataclass, field

from psychic_cleaners.core.constants import (
    CAR_X,
    CATCH_RANGE,
    DRIVE_LANES,
    FAINT_WISP_CHANCE,
    ROAD_LENGTH_VISIBLE,
    ROAD_WISP_SPAWN_PER_SECOND,
    ROAD_WISP_SPEED,
    VACUUM_BOUNTY,
)
from psychic_cleaners.core.events import Event, WispCaptured
from psychic_cleaners.core.rng import Rng


@dataclass
class RoadWisp:
    x: float  # 0..ROAD_LENGTH_VISIBLE, moves toward 0 (toward the car)
    lane: int  # 0..DRIVE_LANES-1
    faint: bool


@dataclass
class DriveSim:
    distance_total: float
    speed: float
    has_vacuum: bool
    has_lens: bool
    distance_done: float = 0.0
    lane: int = 1
    wisps: list[RoadWisp] = field(default_factory=list)

    def steer(self, delta: int) -> None:
        self.lane = max(0, min(DRIVE_LANES - 1, self.lane + delta))

    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]:
        self.distance_done += self.speed * dt_seconds
        return []

    @property
    def arrived(self) -> bool:
        return self.distance_done >= self.distance_total
```

(The `CAR_X`, `CATCH_RANGE`, `FAINT_WISP_CHANCE`, `ROAD_LENGTH_VISIBLE`, `ROAD_WISP_SPAWN_PER_SECOND`, `ROAD_WISP_SPEED`, `VACUUM_BOUNTY`, `WispCaptured` imports are used by the next two cycles in this same task.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_drive.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 5: Write the failing tests for vacuum catch geometry**

Append to `tests/core/test_drive.py`. Every test ticks once with `dt=0.01`: movement is `(ROAD_WISP_SPEED + speed) * 0.01 = 2.2` units, small against `CATCH_RANGE = 24.0`, and the spawn probability per tick is `0.5 * 0.01 = 0.005`, which seed 1's first `random()` call (≈0.134) never triggers — so these assertions stay exact even after the spawn cycle lands.

```python
def test_vacuum_catches_wisp_in_same_lane_within_range() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == [WispCaptured(bounty=VACUUM_BOUNTY)]
    assert sim.wisps == []


def test_no_catch_without_vacuum() -> None:
    sim = _sim(vacuum=False)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_no_catch_in_a_different_lane() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=0, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_no_catch_outside_catch_range() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=CAR_X + CATCH_RANGE + 50.0, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_faint_wisp_not_caught_without_lens() -> None:
    sim = _sim(vacuum=True, lens=False)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=True))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert len(sim.wisps) == 1


def test_faint_wisp_caught_with_lens() -> None:
    sim = _sim(vacuum=True, lens=True)
    sim.wisps.append(RoadWisp(x=CAR_X, lane=1, faint=True))
    events = sim.tick(0.01, make_rng(1))
    assert events == [WispCaptured(bounty=VACUUM_BOUNTY)]
    assert sim.wisps == []


def test_wisp_past_the_car_is_removed_silently() -> None:
    sim = _sim(vacuum=True)
    sim.wisps.append(RoadWisp(x=-CATCH_RANGE - 1.0, lane=1, faint=False))
    events = sim.tick(0.01, make_rng(1))
    assert events == []
    assert sim.wisps == []
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_drive.py -v`
Expected: FAIL — 3 failed, 7 passed. The three positive-outcome tests fail with `AssertionError` because the stub `tick` returns `[]` and never removes wisps: `test_vacuum_catches_wisp_in_same_lane_within_range` and `test_faint_wisp_caught_with_lens` fail on `events == [WispCaptured(bounty=VACUUM_BOUNTY)]`, and `test_wisp_past_the_car_is_removed_silently` fails on `sim.wisps == []`. The other four new tests (`test_no_catch_without_vacuum`, `test_no_catch_in_a_different_lane`, `test_no_catch_outside_catch_range`, `test_faint_wisp_not_caught_without_lens`) assert no events and a retained wisp, which the stub already satisfies — they pass now and stay green as guard rails once Step 7 lands.

- [ ] **Step 7: Implement movement, catch, and cull**

Replace the `tick` method in `src/psychic_cleaners/core/drive.py` with:

```python
    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]:
        events: list[Event] = []
        self.distance_done += self.speed * dt_seconds
        approach = (ROAD_WISP_SPEED + self.speed) * dt_seconds
        for wisp in self.wisps:
            wisp.x -= approach
        remaining: list[RoadWisp] = []
        for wisp in self.wisps:
            catchable = (
                self.has_vacuum
                and wisp.lane == self.lane
                and abs(wisp.x - CAR_X) <= CATCH_RANGE
                and (not wisp.faint or self.has_lens)
            )
            if catchable:
                events.append(WispCaptured(bounty=VACUUM_BOUNTY))
            elif wisp.x >= -CATCH_RANGE:
                remaining.append(wisp)
            # else: passed off-screen, removed silently
        self.wisps = remaining
        return events
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_drive.py -v`
Expected: PASS — 10 passed.

- [ ] **Step 9: Write the failing test for wisp spawning**

Append to `tests/core/test_drive.py`:

```python
def test_spawned_wisps_have_valid_lane_and_spawn_at_road_edge() -> None:
    sim = _sim()
    rng = make_rng(7)
    spawned = 0
    faint_seen: set[bool] = set()
    for _ in range(2000):
        sim.wisps.clear()  # isolate this tick's spawns from drifting ones
        sim.tick(0.1, rng)
        for wisp in sim.wisps:
            spawned += 1
            assert wisp.x == ROAD_LENGTH_VISIBLE
            assert 0 <= wisp.lane < DRIVE_LANES
            faint_seen.add(wisp.faint)
    assert spawned > 0
    assert faint_seen == {True, False}  # FAINT_WISP_CHANCE produces both kinds
```

- [ ] **Step 10: Run test to verify it fails**

Run: `uv run pytest tests/core/test_drive.py::test_spawned_wisps_have_valid_lane_and_spawn_at_road_edge -v`
Expected: FAIL — `AssertionError` on `assert spawned > 0` (nothing spawns yet).

- [ ] **Step 11: Implement spawning**

In `src/psychic_cleaners/core/drive.py`, add the spawn block at the end of `tick`, immediately before `return events`:

```python
        if rng.random() < ROAD_WISP_SPAWN_PER_SECOND * dt_seconds:
            self.wisps.append(
                RoadWisp(
                    x=ROAD_LENGTH_VISIBLE,
                    lane=rng.randint(0, DRIVE_LANES - 1),
                    faint=rng.random() < FAINT_WISP_CHANCE,
                )
            )
```

The final `tick` method is:

```python
    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]:
        events: list[Event] = []
        self.distance_done += self.speed * dt_seconds
        approach = (ROAD_WISP_SPEED + self.speed) * dt_seconds
        for wisp in self.wisps:
            wisp.x -= approach
        remaining: list[RoadWisp] = []
        for wisp in self.wisps:
            catchable = (
                self.has_vacuum
                and wisp.lane == self.lane
                and abs(wisp.x - CAR_X) <= CATCH_RANGE
                and (not wisp.faint or self.has_lens)
            )
            if catchable:
                events.append(WispCaptured(bounty=VACUUM_BOUNTY))
            elif wisp.x >= -CATCH_RANGE:
                remaining.append(wisp)
            # else: passed off-screen, removed silently
        self.wisps = remaining
        if rng.random() < ROAD_WISP_SPAWN_PER_SECOND * dt_seconds:
            self.wisps.append(
                RoadWisp(
                    x=ROAD_LENGTH_VISIBLE,
                    lane=rng.randint(0, DRIVE_LANES - 1),
                    faint=rng.random() < FAINT_WISP_CHANCE,
                )
            )
        return events
```

- [ ] **Step 12: Run the whole file to verify everything passes**

Run: `uv run pytest tests/core/test_drive.py -v`
Expected: PASS — 11 passed.

- [ ] **Step 13: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean — no ruff errors, files unchanged or reformatted, `Success: no issues found`.

- [ ] **Step 14: Commit**

```bash
git add src/psychic_cleaners/core/drive.py tests/core/test_drive.py
git commit -m "feat: add driving lane simulation with vacuum catch geometry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 21: Travel via driving in Game

**Files:**
- Modify: src/psychic_cleaners/core/game.py (replace Task 19's instant travel on `SetDestination` with `DriveSim`-based travel; add DRIVE-scene command handling and drive ticking; add arrival routing helper)
- Test: tests/integration/test_travel.py

**Interfaces:**
- Consumes: `DriveSim`, `RoadWisp` (Task 20); `Game`, `new_game(seed)`, and the `_reset()` convention (Task 7); the SHOP flow (shop milestone) and the MAP scene flow/fields (Task 19); `City.distance(a, b)`, `City.wisps`, `Wisp` (Task 17); `Wallet.earn` (Task 9); events `SetDestination(pos)`, `Steer(delta)`, `TravelStarted(dest, distance)`, `Arrived(pos)`, `WispCaptured(bounty)`, `SnaresEmptied()`, `CleanersRestored()`, `SceneChanged(scene)` (Task 6); constants `DEPOT_POS`, `BLOCK_LENGTH`, `VACUUM_BOUNTY`, `CAR_X` (Task 4); catalog `VEHICLES` (Task 10).
- Produces: `Game.drive: DriveSim | None` — declared by this task, populated during travel, reinitialized in `_reset()`; `Game._arrive_at(pos) -> list[Event]` — the single arrival-routing helper, an if/elif chain ending in an `else:` that routes to MAP, which Task 25 (bust routing) and Task 30 (finale routing) extend with elif branches above the else.

Background for whoever executes this task: after Task 19, `Game.tick` handles `SetDestination(pos)` in the MAP scene by moving `position` instantly and running depot services on arrival. This task replaces that with real travel: create a `DriveSim`, switch to the DRIVE scene, tick the sim in the scene-ticking step of the canonical tick shape (dispatch loop first, then scene ticking, then post-tick resolution), and route arrival in post-tick resolution when the sim finishes. This task declares the contract's `drive: DriveSim | None = None` field on `Game` — no earlier task declares it — and adds its reinitialization to `Game._reset()` per the Task 7 convention.

- [ ] **Step 1: Write the failing test for departure**

Create `tests/integration/test_travel.py` with the full import block (later cycles in this task use all of it):

```python
"""Integration tests: city travel runs through the driving simulation."""

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.city import Wisp
from psychic_cleaners.core.constants import BLOCK_LENGTH, CAR_X, DEPOT_POS, VACUUM_BOUNTY
from psychic_cleaners.core.drive import RoadWisp
from psychic_cleaners.core.events import (
    Arrived,
    BuyItem,
    CleanersRestored,
    Event,
    FinishShopping,
    ItemBought,
    NewGame,
    SceneChanged,
    SceneId,
    SelectVehicle,
    SetDestination,
    SnaresEmptied,
    Steer,
    TravelStarted,
    WispCaptured,
)
from psychic_cleaners.core.game import Game, new_game


def _game_on_map(extra_items: tuple[str, ...] = ()) -> Game:
    """New game, hearse bought, one snare (avoids the no-snares loss rule), on the map."""
    game = new_game(1)
    game.tick([NewGame(name="Ada")], 0.0)
    game.tick([SelectVehicle(vehicle_id="hearse")], 0.0)
    for item_id in ("snare", *extra_items):
        events = game.tick([BuyItem(item_id=item_id)], 0.0)
        assert any(isinstance(e, ItemBought) for e in events)
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    assert game.position == DEPOT_POS
    return game


def test_set_destination_starts_a_drive() -> None:
    game = _game_on_map()
    dest = (3, 5)  # 3 manhattan steps east of DEPOT_POS (0, 5)
    events = game.tick([SetDestination(pos=dest)], 0.0)
    assert TravelStarted(dest=dest, distance=3 * BLOCK_LENGTH) in events
    assert SceneChanged(scene=SceneId.DRIVE) in events
    assert game.scene is SceneId.DRIVE
    assert game.destination == dest
    assert game.drive is not None
    assert game.drive.distance_total == 3 * BLOCK_LENGTH
    assert game.drive.speed == VEHICLES["hearse"].speed
    assert game.position == DEPOT_POS  # not moved yet


def test_drive_sim_reflects_loadout_gear() -> None:
    game = _game_on_map(extra_items=("vacuum",))
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    assert game.drive.has_vacuum is True
    assert game.drive.has_lens is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_travel.py -v`
Expected: FAIL — `AssertionError`: `TravelStarted(...) in events` is false (Task 19 teleports instantly and never creates a `DriveSim`; `game.drive is not None` also fails).

- [ ] **Step 3: Implement departure**

Open `src/psychic_cleaners/core/game.py`. Ensure these imports exist (add any that are missing to the existing import block):

```python
from psychic_cleaners.core.constants import DEPOT_POS, VACUUM_BOUNTY
from psychic_cleaners.core.drive import DriveSim
from psychic_cleaners.core.events import (
    Arrived,
    CleanersRestored,
    SceneChanged,
    SetDestination,
    SnaresEmptied,
    Steer,
    TravelStarted,
    WispCaptured,
)
```

Declare the travel field on the `Game` dataclass exactly as in the contract (this task declares it; place it after `loadout` to match the contract's field order):

```python
    drive: DriveSim | None = None
```

and extend `Game._reset()` with its reinitialization, per the Task 7 convention (every task that adds a `Game` field reinitializes it in `_reset()` in the same task; `NewGame` and `Continue` both route through `_reset()`, so no inline `NewGame` handler edit for `drive` is needed):

```python
        self.drive = None
```

Add this method to the `Game` class:

```python
    def _set_destination(self, pos: GridPos) -> list[Event]:
        if pos == self.position:
            return self._arrive_at(pos)
        assert self.loadout is not None  # MAP is only reachable with a vehicle
        distance = self.city.distance(self.position, pos)
        self.destination = pos
        self.drive = DriveSim(
            distance_total=distance,
            speed=self.loadout.vehicle.speed,
            has_vacuum=self.loadout.has("vacuum"),
            has_lens=self.loadout.has("lens"),
        )
        events: list[Event] = [TravelStarted(dest=pos, distance=distance)]
        self.scene = SceneId.DRIVE
        events.append(SceneChanged(scene=SceneId.DRIVE))
        return events
```

Also add the canonical arrival-routing helper to the `Game` class now (Step 7 wires drive arrival to it in post-tick resolution). Per the contract, `_arrive_at` is ONE method shaped as an if/elif chain ending in an `else:` branch that routes to MAP — NOT an unconditional trailing "if scene is not MAP" block after the chain, which would clobber the BUST/FINALE routing later tasks insert as elif branches. Task 25 inserts its haunted-building elif and Task 30 its tower elif ABOVE the else. (Task 30's tower elif goes above Task 25's haunted elif: tower before haunted before the else.) Delete Task 19's instant-arrival routing — whether it was an inline block in the `SetDestination` handler or a private helper under another name — and point any remaining callers at `_arrive_at`, so this is the single arrival-routing point. The method always ends with `return events`, never a bare `return`:

```python
    def _arrive_at(self, pos: GridPos) -> list[Event]:
        self.position = pos
        self.destination = None
        self.drive = None
        events: list[Event] = [Arrived(pos=pos)]
        if pos == DEPOT_POS:
            self.snares_full = 0
            self.contained = 0
            self.slimed.clear()
            events.append(SnaresEmptied())
            events.append(CleanersRestored())
            if self.scene is not SceneId.MAP:
                self.scene = SceneId.MAP
                events.append(SceneChanged(scene=SceneId.MAP))
        # Task 30 inserts its tower elif here, then Task 25 its haunted-building
        # elif below it — both ABOVE the else.
        else:
            if self.scene is not SceneId.MAP:
                self.scene = SceneId.MAP
                events.append(SceneChanged(scene=SceneId.MAP))
        return events
```

In `Game.tick`'s command dispatch for the MAP scene, replace the entire Task 19 `SetDestination` handling with:

```python
                if isinstance(command, SetDestination):
                    events.extend(self._set_destination(command.pos))
```

(Adapt the `if isinstance` line to the dispatch style already in `tick` — `match command:` with `case SetDestination(pos=pos):` is equivalent — but the body must be exactly one call to `self._set_destination`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_travel.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Write the failing tests for arrival**

Append to `tests/integration/test_travel.py`:

```python
def test_hearse_arrives_after_distance_over_speed_seconds() -> None:
    game = _game_on_map()
    dest = (3, 5)
    game.tick([SetDestination(pos=dest)], 0.0)
    expected_seconds = 3 * BLOCK_LENGTH / VEHICLES["hearse"].speed  # 1200/140 ~ 8.57 s
    collected: list[Event] = []
    ticks = 0
    while game.scene is SceneId.DRIVE and ticks < 200:
        collected.extend(game.tick([], 0.1))
        ticks += 1
    assert Arrived(pos=dest) in collected
    assert SceneChanged(scene=SceneId.MAP) in collected
    assert game.scene is SceneId.MAP
    assert game.position == dest
    assert game.destination is None
    assert game.drive is None
    assert abs(ticks * 0.1 - expected_seconds) <= 0.2


def test_destination_equal_to_position_routes_arrival_immediately() -> None:
    game = _game_on_map()
    game.snares_full = 1
    events = game.tick([SetDestination(pos=DEPOT_POS)], 0.0)
    assert Arrived(pos=DEPOT_POS) in events
    assert SnaresEmptied() in events
    assert CleanersRestored() in events
    assert game.snares_full == 0
    assert not any(isinstance(e, TravelStarted) for e in events)
    assert game.scene is SceneId.MAP
    assert game.drive is None
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_travel.py -v`
Expected: FAIL — 1 failed, 3 passed. `test_hearse_arrives_after_distance_over_speed_seconds` loops 200 ticks with `game.scene` stuck in DRIVE (the drive sim is never ticked), then fails on `Arrived(pos=dest) in collected`. `test_destination_equal_to_position_routes_arrival_immediately` already passes: Step 3's `_set_destination` routes same-cell destinations through the `_arrive_at` helper installed in Step 3.

- [ ] **Step 7: Implement drive ticking and arrival routing**

The canonical `_arrive_at` was installed in Step 3; confirm it matches that code block exactly (it is the single arrival-routing point — Task 25 inserts its haunted-building elif and Task 30 its tower elif above the else). What is missing is ticking the drive sim and routing arrival when it finishes. Both slot into the canonical `Game.tick` shape: the command dispatch loop runs first, then scene ticking, then post-tick resolution.

Add the drive-ticking helper to `Game`:

```python
    def _tick_drive(self, dt_seconds: float) -> list[Event]:
        assert self.drive is not None
        return list(self.drive.tick(dt_seconds, self.rng))
```

Wire it into `Game.tick`'s scene-ticking step, which runs AFTER the dispatch loop: the world tick (clock, psi, city, mascot — wired in Task 19) already runs there in scenes MAP, DRIVE, and BUST. Immediately after that world-tick block, still inside the scene-ticking step, add:

```python
        if self.scene is SceneId.DRIVE and self.drive is not None:
            events.extend(self._tick_drive(dt_seconds))
```

Then, in `Game.tick`'s post-tick resolution step (after all scene ticking, alongside Task 19's WispReachedTower handling), add the arrival routing:

```python
        if self.drive is not None and self.drive.arrived:
            assert self.destination is not None
            events.extend(self._arrive_at(self.destination))
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_travel.py -v`
Expected: PASS — 4 passed.

- [ ] **Step 9: Write the failing tests for steering, wisp bounty, and city population**

Append to `tests/integration/test_travel.py`:

```python
def test_steer_command_changes_lane_while_driving() -> None:
    game = _game_on_map()
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    assert game.drive.lane == 1
    game.tick([Steer(delta=-1)], 0.01)
    assert game.drive is not None
    assert game.drive.lane == 0


def test_wisp_catch_during_travel_pays_the_bounty() -> None:
    game = _game_on_map(extra_items=("vacuum",))
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    balance_before = game.wallet.balance
    game.drive.wisps.append(RoadWisp(x=CAR_X, lane=game.drive.lane, faint=False))
    events = game.tick([], 0.01)
    assert WispCaptured(bounty=VACUUM_BOUNTY) in events
    assert game.wallet.balance == balance_before + VACUUM_BOUNTY


def test_road_catch_removes_one_wisp_from_the_city_population() -> None:
    game = _game_on_map(extra_items=("vacuum",))
    game.tick([SetDestination(pos=(3, 5))], 0.0)
    assert game.drive is not None
    game.city.wisps.append(Wisp(x=0.0, y=0.0))  # far from the tower: survives city.tick
    balance_before = game.wallet.balance
    game.drive.wisps.append(RoadWisp(x=CAR_X, lane=game.drive.lane, faint=False))
    events = game.tick([], 0.01)
    assert WispCaptured(bounty=VACUUM_BOUNTY) in events
    assert game.city.wisps == []  # road wisps represent the city population
    assert game.wallet.balance == balance_before + VACUUM_BOUNTY
```

- [ ] **Step 10: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_travel.py -v`
Expected: FAIL — `test_steer_command_changes_lane_while_driving` fails with `AssertionError` (`lane` stays 1: no DRIVE command dispatch yet); `test_wisp_catch_during_travel_pays_the_bounty` fails on the balance assertion (the event passes through but nothing calls `wallet.earn`); `test_road_catch_removes_one_wisp_from_the_city_population` fails on `game.city.wisps == []` (nothing removes a city wisp on a road catch yet).

- [ ] **Step 11: Implement DRIVE command dispatch, the bounty, and the city-population removal**

In `Game.tick`'s command dispatch, add a DRIVE-scene branch (same dispatch style as the other scenes):

```python
                if isinstance(command, Steer) and self.drive is not None:
                    self.drive.steer(command.delta)
```

(Guard the branch so it only runs when `self.scene is SceneId.DRIVE`, matching how the existing per-scene dispatch is structured.)

Then replace `_tick_drive` with the final version that, per captured wisp, pays the bounty AND removes one wisp from `city.wisps` if any remain (road wisps represent the city population — contract). Arrival routing stays where Step 7 put it, in `Game.tick`'s post-tick resolution:

```python
    def _tick_drive(self, dt_seconds: float) -> list[Event]:
        assert self.drive is not None
        events: list[Event] = []
        for event in self.drive.tick(dt_seconds, self.rng):
            if isinstance(event, WispCaptured):
                self.wallet.earn(VACUUM_BOUNTY)
                if self.city.wisps:
                    self.city.wisps.pop(0)  # one road catch thins the city population
            events.append(event)
        return events
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_travel.py -v`
Expected: PASS — 7 passed.

- [ ] **Step 13: Run the full suite to catch regressions in earlier milestones' tests**

Run: `uv run pytest -v`
Expected: PASS — all tests pass. If a Task 19 test asserted instant arrival on `SetDestination` to a *different* cell, that assertion is now obsolete by design: update that test to expect `TravelStarted` + scene DRIVE instead (same-cell destinations still arrive instantly, so depot-service tests keep passing).

- [ ] **Step 14: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean — no ruff errors, `Success: no issues found`.

- [ ] **Step 15: Commit**

```bash
git add src/psychic_cleaners/core/game.py tests/integration/test_travel.py
git commit -m "feat: route city travel through the driving simulation

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(If Step 13 required updating a Task 19 test file, `git add` that file too.)

### Task 22: Driving scene (shell)

**Files:**
- Create: src/psychic_cleaners/shell/scenes/driving.py
- Modify: src/psychic_cleaners/shell/gfx.py (add builders for "car.compact", "car.hearse", "car.wagon", "car.performance", "wisp.faint")
- Modify: src/psychic_cleaners/shell/app.py (replace the `SCENES[SceneId.DRIVE]` stub with `DrivingScene()`)
- Test: tests/shell/test_driving_scene.py

**Interfaces:**
- Consumes: `DriveSim`, `RoadWisp` (Task 20); `Game` with `drive` (Task 21) plus `loadout` and `wallet` from earlier milestones; `Steer(delta)`, `Command`, `SceneId` (Task 6); `SpriteFactory.get(name)` (Task 8 — the builder registry is established in Task 8 and extended in Task 19 with the map sprites, including "wisp"); `TextRenderer.draw(...)` (Task 8); the `Scene` protocol from `shell/scenes/__init__.py` (Task 8); constants `CAR_X`, `DRIVE_LANES` (Task 4).
- Produces: `DrivingScene` registered as `SCENES[SceneId.DRIVE]`; sprites "car.compact", "car.hearse", "car.wagon", "car.performance" (48x24) and "wisp.faint" (translucent, contract-pinned alpha 90), available to any scene via `SpriteFactory.get`.

All tests in this task run under the SDL dummy drivers set by `tests/conftest.py` (Task 1).

- [ ] **Step 1: Write the failing sprite tests**

Create `tests/shell/test_driving_scene.py` with the full import block (later cycles in this task use all of it):

```python
"""Key-mapping, sprite, and draw-smoke tests for the driving scene."""

from collections.abc import Iterator

import pygame
import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.drive import DriveSim, RoadWisp
from psychic_cleaners.core.events import SceneId, Steer
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.driving import DrivingScene
from psychic_cleaners.shell.text import TextRenderer


@pytest.fixture(autouse=True)
def _pygame() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.mark.parametrize("vehicle_id", ["compact", "hearse", "wagon", "performance"])
def test_car_sprites_are_48_by_24(vehicle_id: str) -> None:
    sprite = SpriteFactory().get(f"car.{vehicle_id}")
    assert sprite.get_size() == (48, 24)


def test_car_sprites_have_distinct_body_colours() -> None:
    factory = SpriteFactory()
    bodies = {
        tuple(factory.get(f"car.{vid}").get_at((24, 14)))
        for vid in ("compact", "hearse", "wagon", "performance")
    }
    assert len(bodies) == 4


def test_faint_wisp_sprite_is_translucent() -> None:
    sprite = SpriteFactory().get("wisp.faint")
    assert sprite.get_flags() & pygame.SRCALPHA
    alphas = {
        sprite.get_at((x, y)).a
        for x in range(sprite.get_width())
        for y in range(sprite.get_height())
    }
    assert 90 in alphas  # drawn pixels use the contract-pinned alpha 90
    assert 255 not in alphas  # nothing fully opaque
```

(The `DrivingScene` import fails until Step 7's module exists; to run only this cycle first, comment that one import out, then restore it in Step 5. The `Game`, `new_game`, `DriveSim`, `RoadWisp`, `Loadout`, `SceneId`, `Steer`, `VEHICLES`, `TextRenderer` imports are used by Steps 5 and 9.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_driving_scene.py -v`
Expected: FAIL — with the `DrivingScene` import temporarily commented out, the sprite tests fail inside `SpriteFactory.get` with the factory's unknown-name error (`KeyError: 'car.compact'` or equivalent) because no builders exist for these names yet.

- [ ] **Step 3: Add the sprite builders to gfx.py**

Add these module-level functions to `src/psychic_cleaners/shell/gfx.py`:

```python
def _build_car(
    body: tuple[int, int, int],
    roof: tuple[int, int, int],
    roof_rect: tuple[int, int, int, int],
    stripe: bool = False,
) -> pygame.Surface:
    surf = pygame.Surface((48, 24), pygame.SRCALPHA)
    pygame.draw.rect(surf, body, pygame.Rect(2, 8, 44, 10), border_radius=4)
    pygame.draw.rect(surf, roof, pygame.Rect(*roof_rect), border_radius=3)
    if stripe:
        pygame.draw.rect(surf, (250, 250, 250), pygame.Rect(2, 15, 44, 2))
    for wheel_x in (12, 36):
        pygame.draw.circle(surf, (25, 25, 30), (wheel_x, 20), 4)
        pygame.draw.circle(surf, (190, 190, 200), (wheel_x, 20), 2)
    return surf


def _build_car_compact() -> pygame.Surface:
    return _build_car((90, 175, 160), (140, 215, 205), (14, 3, 20, 8))


def _build_car_hearse() -> pygame.Surface:
    return _build_car((72, 62, 96), (52, 44, 70), (8, 3, 34, 8))


def _build_car_wagon() -> pygame.Surface:
    return _build_car((155, 110, 70), (120, 82, 50), (10, 3, 30, 8))


def _build_car_performance() -> pygame.Surface:
    return _build_car((205, 55, 55), (150, 30, 30), (18, 4, 16, 7), stripe=True)


def _build_wisp_faint() -> pygame.Surface:
    surf = pygame.Surface((24, 24), pygame.SRCALPHA)
    pygame.draw.circle(surf, (180, 240, 255, 90), (12, 10), 8)
    pygame.draw.circle(surf, (235, 255, 255, 90), (12, 10), 4)
    pygame.draw.rect(surf, (180, 240, 255, 90), pygame.Rect(6, 14, 12, 6), border_radius=3)
    return surf
```

The contract pins the "wisp.faint" alpha at 90: every drawn pixel of `_build_wisp_faint` uses alpha 90 and nothing is fully opaque. A later milestone's replacement sprite also keeps alpha 90, so Step 1's `90 in alphas` assertion stays valid across milestones — do not change the alpha value in either the builder or the test.

Then register the five names in the module-level `_BUILDERS: dict[str, Callable[[], pygame.Surface]]` registry in `shell/gfx.py` (established in Task 8, extended in Task 19 with the map sprites). Add exactly these entries:

```python
    "car.compact": _build_car_compact,
    "car.hearse": _build_car_hearse,
    "car.wagon": _build_car_wagon,
    "car.performance": _build_car_performance,
    "wisp.faint": _build_wisp_faint,
```

The Step 1 tests are the acceptance criterion.

- [ ] **Step 4: Run the sprite tests to verify they pass**

Run: `uv run pytest tests/shell/test_driving_scene.py -v`
Expected: PASS — 6 passed (4 size checks, distinct colours, translucency). Restore the `DrivingScene` import if it was commented out (the next step needs it and will fail on it first).

- [ ] **Step 5: Write the failing key-mapping tests**

Append to `tests/shell/test_driving_scene.py`:

```python
def _driving_game() -> Game:
    game = new_game(1)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.DRIVE
    drive = DriveSim(distance_total=1200.0, speed=140.0, has_vacuum=True, has_lens=False)
    drive.distance_done = 480.0
    drive.wisps.append(RoadWisp(x=320.0, lane=0, faint=False))
    drive.wisps.append(RoadWisp(x=400.0, lane=2, faint=True))
    game.drive = drive
    return game


def test_up_key_steers_toward_lane_zero() -> None:
    scene = DrivingScene()
    events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)]
    assert scene.commands(events, _driving_game()) == [Steer(delta=-1)]


def test_down_key_steers_toward_last_lane() -> None:
    scene = DrivingScene()
    events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)]
    assert scene.commands(events, _driving_game()) == [Steer(delta=1)]


def test_other_events_produce_no_commands() -> None:
    scene = DrivingScene()
    events = [
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE),
        pygame.event.Event(pygame.KEYUP, key=pygame.K_UP),
    ]
    assert scene.commands(events, _driving_game()) == []
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_driving_scene.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psychic_cleaners.shell.scenes.driving'` (collection error).

- [ ] **Step 7: Create the scene module with commands()**

Create `src/psychic_cleaners/shell/scenes/driving.py`:

```python
"""Driving scene: three-lane road, steerable car, road wisps, progress bar."""

import pygame

from psychic_cleaners.core.events import Command, Steer
from psychic_cleaners.core.game import Game


class DrivingScene:
    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    out.append(Steer(delta=-1))
                elif event.key == pygame.K_DOWN:
                    out.append(Steer(delta=1))
        return out
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_driving_scene.py -v`
Expected: PASS — 9 passed.

- [ ] **Step 9: Write the failing draw-smoke and registry tests**

Append to `tests/shell/test_driving_scene.py`:

```python
def test_draw_renders_an_active_drive_without_error() -> None:
    surface = pygame.Surface((640, 400))
    DrivingScene().draw(surface, _driving_game(), SpriteFactory(), TextRenderer())


def test_draw_with_lens_owned_renders_faint_wisps_without_error() -> None:
    game = _driving_game()
    assert game.loadout is not None
    game.loadout.add("lens")
    surface = pygame.Surface((640, 400))
    DrivingScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_draw_without_an_active_drive_does_not_crash() -> None:
    game = _driving_game()
    game.drive = None
    surface = pygame.Surface((640, 400))
    DrivingScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_scene_registry_uses_driving_scene() -> None:
    from psychic_cleaners.shell.app import SCENES

    assert isinstance(SCENES[SceneId.DRIVE], DrivingScene)
```

- [ ] **Step 10: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_driving_scene.py -v`
Expected: FAIL — the three draw tests fail with `AttributeError: 'DrivingScene' object has no attribute 'draw'`; the registry test fails its `isinstance` assertion (the Milestone 2 stub is still registered).

- [ ] **Step 11: Implement draw() and register the scene**

Replace the full contents of `src/psychic_cleaners/shell/scenes/driving.py` with:

```python
"""Driving scene: three-lane road, steerable car, road wisps, progress bar."""

from typing import Final

import pygame

from psychic_cleaners.core.constants import CAR_X, DRIVE_LANES
from psychic_cleaners.core.events import Command, Steer
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_ROAD_TOP: Final[int] = 110
_LANE_HEIGHT: Final[int] = 60
_GRASS: Final[tuple[int, int, int]] = (24, 44, 30)
_LANE_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (52, 52, 60),
    (62, 62, 70),
    (52, 52, 60),
)
_LANE_MARK: Final[tuple[int, int, int]] = (205, 205, 95)
_BAR_RECT: Final[pygame.Rect] = pygame.Rect(120, 24, 400, 12)
_BAR_BACK: Final[tuple[int, int, int]] = (40, 40, 48)
_BAR_FILL: Final[tuple[int, int, int]] = (120, 220, 140)
_BAR_EDGE: Final[tuple[int, int, int]] = (205, 205, 210)


def _lane_center_y(lane: int) -> int:
    return _ROAD_TOP + lane * _LANE_HEIGHT + _LANE_HEIGHT // 2


class DrivingScene:
    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    out.append(Steer(delta=-1))
                elif event.key == pygame.K_DOWN:
                    out.append(Steer(delta=1))
        return out

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill(_GRASS)
        width = surface.get_width()
        for lane in range(DRIVE_LANES):
            band = pygame.Rect(0, _ROAD_TOP + lane * _LANE_HEIGHT, width, _LANE_HEIGHT)
            pygame.draw.rect(surface, _LANE_COLORS[lane % len(_LANE_COLORS)], band)
        for boundary in range(1, DRIVE_LANES):
            y = _ROAD_TOP + boundary * _LANE_HEIGHT
            for x in range(0, width, 40):
                pygame.draw.line(surface, _LANE_MARK, (x, y), (x + 20, y), 2)
        drive = game.drive
        loadout = game.loadout
        if drive is None or loadout is None:
            return
        has_lens = loadout.has("lens")
        for wisp in drive.wisps:
            if wisp.faint and not has_lens:
                continue
            sprite = gfx.get("wisp.faint" if wisp.faint else "wisp")
            rect = sprite.get_rect(center=(int(wisp.x), _lane_center_y(wisp.lane)))
            surface.blit(sprite, rect)
        car = gfx.get(f"car.{loadout.vehicle.id}")
        car_rect = car.get_rect(center=(int(CAR_X), _lane_center_y(drive.lane)))
        surface.blit(car, car_rect)
        fraction = min(1.0, drive.distance_done / max(drive.distance_total, 1.0))
        pygame.draw.rect(surface, _BAR_BACK, _BAR_RECT)
        fill_width = int(_BAR_RECT.width * fraction)
        fill = pygame.Rect(_BAR_RECT.x, _BAR_RECT.y, fill_width, _BAR_RECT.height)
        pygame.draw.rect(surface, _BAR_FILL, fill)
        pygame.draw.rect(surface, _BAR_EDGE, _BAR_RECT, 1)
        text.draw(surface, f"${game.wallet.balance}", (16, 16), size=20)
```

Then in `src/psychic_cleaners/shell/app.py`: add the import

```python
from psychic_cleaners.shell.scenes.driving import DrivingScene
```

and in the `SCENES` registry replace the `SceneId.DRIVE` entry (currently the Milestone 2 stub scene) with:

```python
    SceneId.DRIVE: DrivingScene(),
```

Remove the stub-scene import from app.py if `SceneId.DRIVE` was its last remaining use.

- [ ] **Step 12: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_driving_scene.py -v`
Expected: PASS — 13 passed.

- [ ] **Step 13: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS — all tests pass, including earlier shell smoke tests (any Milestone 2 smoke test that renders every registered scene now renders `DrivingScene`; its `draw` returns early when `game.drive` is None, so it renders safely from any game state).

- [ ] **Step 14: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean — no ruff errors, `Success: no issues found`.

- [ ] **Step 15: Commit**

```bash
git add src/psychic_cleaners/shell/scenes/driving.py src/psychic_cleaners/shell/gfx.py \
  src/psychic_cleaners/shell/app.py tests/shell/test_driving_scene.py
git commit -m "feat: add driving scene with car sprites, faint wisps, and progress bar

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

<!-- CONTRACT-NOTE: The contract pins _arrive_at (if/elif chain ending in an else that routes to MAP) but does not name Game's other private helpers; this milestone additionally defines _set_destination and _tick_drive as plan-level names. -->
<!-- CONTRACT-NOTE: DriveSim.tick's internal ordering is not pinned by the contract; Task 20 fixes it as distance -> move -> catch/cull -> spawn so freshly spawned wisps end their first tick at exactly x == ROAD_LENGTH_VISIBLE. -->
<!-- CONTRACT-NOTE: Drive-scene lane layout values (_ROAD_TOP=110, _LANE_HEIGHT=60) are shell-private constants, not added to core/constants.py, since the contract defines no shell layout constants. -->

---

## Milestone 7: Busting

Goal: the core bust mechanic — strict beam-crossing geometry, the `BustSim` state machine
(position two cleaners, lay a snare, steer the smudge, spring), full wiring into the `Game`
FSM (fees, snare accounting, sliming, bankruptcy), and the pygame busting scene.
When this milestone lands you can drive to a haunted building, place cleaners with the
arrow keys, lay a snare with Enter, spring it with Space, and get paid — or lose the game
when your last snare is wasted and the wallet cannot afford a Depot restock.

### Task 23: Segment Intersection Geometry

**Files:**
- Create: `src/psychic_cleaners/core/geometry.py`
- Test: `tests/core/test_geometry.py`

**Interfaces:**
- Consumes: nothing from the project (pure stdlib; `hypothesis` was installed as a dev
  dependency in Task 1).
- Produces: `type Vec = tuple[float, float]` and
  `segments_cross(a1: Vec, a2: Vec, b1: Vec, b2: Vec) -> bool` — Task 24 (`core/bust.py`)
  imports both.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_geometry.py` with exactly:

```python
"""Tests for strict proper segment intersection."""

from hypothesis import given
from hypothesis import strategies as st

from psychic_cleaners.core.geometry import Vec, segments_cross


def test_x_cross_is_true() -> None:
    assert segments_cross((0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (10.0, 0.0))


def test_parallel_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (10.0, 0.0), (0.0, 5.0), (10.0, 5.0))


def test_t_touch_is_false() -> None:
    # b1 lies on the interior of segment a: touching, not properly crossing.
    assert not segments_cross((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (5.0, 10.0))


def test_shared_endpoint_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (10.0, 10.0), (10.0, 10.0), (20.0, 0.0))


def test_collinear_overlap_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (15.0, 0.0))


def test_disjoint_is_false() -> None:
    assert not segments_cross((0.0, 0.0), (1.0, 1.0), (5.0, 5.0), (6.0, 4.0))


_coord = st.integers(min_value=-50, max_value=50)
_point = st.tuples(_coord, _coord)


def _as_vec(p: tuple[int, int]) -> Vec:
    return (float(p[0]), float(p[1]))


@given(_point, _point, _point, _point)
def test_symmetry(
    a1: tuple[int, int],
    a2: tuple[int, int],
    b1: tuple[int, int],
    b2: tuple[int, int],
) -> None:
    va1, va2, vb1, vb2 = _as_vec(a1), _as_vec(a2), _as_vec(b1), _as_vec(b2)
    result = segments_cross(va1, va2, vb1, vb2)
    assert segments_cross(vb1, vb2, va1, va2) == result
    assert segments_cross(va2, va1, vb1, vb2) == result


@given(
    _point,
    _point,
    _point,
    _point,
    st.integers(min_value=-1000, max_value=1000),
    st.integers(min_value=-1000, max_value=1000),
)
def test_translation_invariance(
    a1: tuple[int, int],
    a2: tuple[int, int],
    b1: tuple[int, int],
    b2: tuple[int, int],
    dx: int,
    dy: int,
) -> None:
    def shift(p: tuple[int, int]) -> Vec:
        return (float(p[0] + dx), float(p[1] + dy))

    original = segments_cross(_as_vec(a1), _as_vec(a2), _as_vec(b1), _as_vec(b2))
    assert segments_cross(shift(a1), shift(a2), shift(b1), shift(b2)) == original
```

(Integer coordinates keep every cross product exact in float arithmetic, so both
properties hold with `==`, no tolerance needed.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_geometry.py -v`
Expected: FAIL — collection error
`ModuleNotFoundError: No module named 'psychic_cleaners.core.geometry'`

- [ ] **Step 3: Write minimal implementation**

Create `src/psychic_cleaners/core/geometry.py` with exactly:

```python
"""Strict proper segment intersection, used for beam-crossing detection."""

type Vec = tuple[float, float]


def _orient(a: Vec, b: Vec, c: Vec) -> float:
    """Twice the signed area of triangle abc (positive = counter-clockwise)."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_cross(a1: Vec, a2: Vec, b1: Vec, b2: Vec) -> bool:
    """True iff the open segments a1-a2 and b1-b2 properly intersect.

    Strict test via orientation cross products: the endpoints of each segment
    must lie strictly on opposite sides of the other segment's line. Parallel
    or collinear segments, T-touches, and shared endpoints all return False,
    because at least one orientation is exactly zero (or has equal signs).
    """
    d1 = _orient(b1, b2, a1)
    d2 = _orient(b1, b2, a2)
    d3 = _orient(a1, a2, b1)
    d4 = _orient(a1, a2, b2)
    return d1 * d2 < 0 and d3 * d4 < 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_geometry.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: no ruff errors, no files reformatted (or only the new files), `Success: no issues found` from mypy

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/core/geometry.py tests/core/test_geometry.py
git commit -m "feat: add strict segment intersection geometry"
```

### Task 24: Bust Simulation

**Files:**
- Create: `src/psychic_cleaners/core/bust.py`
- Test: `tests/core/test_bust.py`

**Interfaces:**
- Consumes: `Vec`, `segments_cross` (Task 23, `core/geometry.py`); constants
  `BUST_MIN_X`, `BUST_MAX_X`, `BUST_GROUND_Y`, `BEAM_TOP_Y`, `BEAM_MAX_TILT`,
  `BEAM_CROSS_GHOST_Y`, `GHOST_DRIFT_SPEED`, `GHOST_SINK_SPEED`, `GHOST_REPEL_SPEED`,
  `SLIME_RANGE`, `SNARE_WIDTH`, `SNARE_TRIGGER_Y` (Task 4, `core/constants.py` — that
  file is contract-complete, so `BEAM_CROSS_GHOST_Y` already exists there; just import
  it, do not add a step creating or editing constants); `Event`, `BeamsCrossed`
  (Task 6, `core/events.py`); `Rng`, `make_rng` (`core/rng.py`).
- Produces: `BustPhase` (POSITION_LEFT, POSITION_RIGHT, SNARE, ACTIVE, RESOLVED),
  `BustOutcome` (CAUGHT, MISSED, BACKFIRE, SLIMED), and `BustSim` with
  `move(dx: float) -> None`, `place() -> None`, `spring() -> None`,
  `beam_endpoints() -> tuple[tuple[Vec, Vec], tuple[Vec, Vec]] | None`,
  `tick(dt_seconds: float, rng: Rng) -> list[Event]` — Tasks 25 and 26 depend on all of it.

This task has two TDD cycles: (1) phases, movement, placement, springing, beam
endpoints; (2) the `tick` simulation (drift, sink, repel, backfire, slime, clamping).

- [ ] **Step 1: Write the failing tests for phases, move, place, spring, beams**

Create `tests/core/test_bust.py` with exactly:

```python
"""Tests for the bust simulation."""

from psychic_cleaners.core.bust import BustOutcome, BustPhase, BustSim
from psychic_cleaners.core.constants import (
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_TILT,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
from psychic_cleaners.core.events import BeamsCrossed
from psychic_cleaners.core.rng import make_rng


def _active_sim(left: float = 200.0, right: float = 440.0, snare: float = 320.0) -> BustSim:
    """Drive a fresh sim to the ACTIVE phase with cleaners and snare placed."""
    sim = BustSim()
    sim.cursor_x = left
    sim.place()
    sim.cursor_x = right
    sim.place()
    sim.cursor_x = snare
    sim.place()
    return sim


def test_phase_progression_captures_positions_from_cursor() -> None:
    sim = BustSim()
    assert sim.phase is BustPhase.POSITION_LEFT
    assert sim.cursor_x == 320.0

    sim.move(-120.0)
    sim.place()
    assert sim.phase is BustPhase.POSITION_RIGHT
    assert sim.left_x == 200.0

    sim.move(240.0)
    sim.place()
    assert sim.phase is BustPhase.SNARE
    assert sim.right_x == 440.0

    sim.move(-120.0)
    sim.place()
    assert sim.phase is BustPhase.ACTIVE
    assert sim.snare_x == 320.0
    assert sim.outcome is None


def test_move_clamps_to_bounds() -> None:
    sim = BustSim()
    sim.move(-10_000.0)
    assert sim.cursor_x == BUST_MIN_X
    sim.move(10_000.0)
    assert sim.cursor_x == BUST_MAX_X


def test_move_ignored_once_active() -> None:
    sim = _active_sim()
    sim.cursor_x = 300.0
    sim.move(50.0)
    assert sim.cursor_x == 300.0


def test_beam_endpoints_none_until_active() -> None:
    sim = BustSim()
    assert sim.beam_endpoints() is None
    sim.place()
    assert sim.beam_endpoints() is None
    sim.place()
    assert sim.beam_endpoints() is None
    sim.place()
    assert sim.beam_endpoints() is not None


def test_beam_tilt_clamped() -> None:
    sim = _active_sim(left=400.0, right=420.0)
    sim.ghost_x = BUST_MIN_X
    beams = sim.beam_endpoints()
    assert beams is not None
    (left_start, left_end), (right_start, right_end) = beams
    assert left_start == (400.0, BUST_GROUND_Y)
    assert left_end == (400.0 - BEAM_MAX_TILT, BEAM_TOP_Y)
    assert right_start == (420.0, BUST_GROUND_Y)
    assert right_end == (420.0 - BEAM_MAX_TILT, BEAM_TOP_Y)


def test_beam_aims_at_ghost_when_within_tilt() -> None:
    sim = _active_sim(left=300.0, right=340.0)
    sim.ghost_x = 320.0
    beams = sim.beam_endpoints()
    assert beams is not None
    assert beams[0][1] == (320.0, BEAM_TOP_Y)
    assert beams[1][1] == (320.0, BEAM_TOP_Y)


def test_spring_caught_when_ghost_over_snare_and_low() -> None:
    sim = _active_sim(snare=320.0)
    sim.ghost_x = 320.0 + SNARE_WIDTH / 2
    sim.ghost_y = SNARE_TRIGGER_Y
    sim.spring()
    assert sim.phase is BustPhase.RESOLVED
    assert sim.outcome is BustOutcome.CAUGHT


def test_spring_missed_when_ghost_off_snare() -> None:
    sim = _active_sim(snare=320.0)
    sim.ghost_x = BUST_MIN_X
    sim.ghost_y = 350.0
    sim.spring()
    assert sim.outcome is BustOutcome.MISSED


def test_spring_missed_when_ghost_too_high() -> None:
    sim = _active_sim(snare=320.0)
    sim.ghost_x = 320.0
    sim.ghost_y = SNARE_TRIGGER_Y - 1.0
    sim.spring()
    assert sim.outcome is BustOutcome.MISSED


def test_spring_ignored_outside_active() -> None:
    sim = BustSim()
    sim.spring()
    assert sim.phase is BustPhase.POSITION_LEFT
    assert sim.outcome is None
```

(`BeamsCrossed`, `make_rng`, `SLIME_RANGE`, `BEAM_CROSS_GHOST_Y` are used by the second
cycle's tests added in Step 5 — leave the imports in place.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_bust.py -v`
Expected: FAIL — collection error
`ModuleNotFoundError: No module named 'psychic_cleaners.core.bust'`

- [ ] **Step 3: Write the implementation (everything except tick)**

Create `src/psychic_cleaners/core/bust.py` with exactly:

```python
"""Bust simulation: cleaner placement, snare laying, beams, and outcomes."""

import enum
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BEAM_MAX_TILT,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
from psychic_cleaners.core.geometry import Vec


class BustPhase(enum.Enum):
    POSITION_LEFT = enum.auto()
    POSITION_RIGHT = enum.auto()
    SNARE = enum.auto()
    ACTIVE = enum.auto()
    RESOLVED = enum.auto()


class BustOutcome(enum.Enum):
    CAUGHT = enum.auto()
    MISSED = enum.auto()
    BACKFIRE = enum.auto()
    SLIMED = enum.auto()


_MOVABLE_PHASES = (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT, BustPhase.SNARE)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class BustSim:
    phase: BustPhase = BustPhase.POSITION_LEFT
    cursor_x: float = 320.0
    left_x: float | None = None
    right_x: float | None = None
    snare_x: float | None = None
    ghost_x: float = 320.0
    ghost_y: float = 160.0
    outcome: BustOutcome | None = None
    slimed_side: int | None = None  # 0 = left cleaner, 1 = right cleaner

    def move(self, dx: float) -> None:
        if self.phase in _MOVABLE_PHASES:
            self.cursor_x = _clamp(self.cursor_x + dx, BUST_MIN_X, BUST_MAX_X)

    def place(self) -> None:
        if self.phase is BustPhase.POSITION_LEFT:
            self.left_x = self.cursor_x
            self.phase = BustPhase.POSITION_RIGHT
        elif self.phase is BustPhase.POSITION_RIGHT:
            self.right_x = self.cursor_x
            self.phase = BustPhase.SNARE
        elif self.phase is BustPhase.SNARE:
            self.snare_x = self.cursor_x
            self.phase = BustPhase.ACTIVE

    def spring(self) -> None:
        if self.phase is not BustPhase.ACTIVE or self.snare_x is None:
            return
        over_snare = abs(self.ghost_x - self.snare_x) <= SNARE_WIDTH / 2
        low_enough = self.ghost_y >= SNARE_TRIGGER_Y
        self.outcome = BustOutcome.CAUGHT if over_snare and low_enough else BustOutcome.MISSED
        self.phase = BustPhase.RESOLVED

    def beam_endpoints(self) -> tuple[tuple[Vec, Vec], tuple[Vec, Vec]] | None:
        left_x = self.left_x
        right_x = self.right_x
        if self.phase is not BustPhase.ACTIVE or left_x is None or right_x is None:
            return None
        return (self._beam(left_x), self._beam(right_x))

    def _beam(self, x: float) -> tuple[Vec, Vec]:
        tilt = _clamp(self.ghost_x - x, -BEAM_MAX_TILT, BEAM_MAX_TILT)
        return ((x, BUST_GROUND_Y), (x + tilt, BEAM_TOP_Y))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_bust.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Write the failing tests for tick (drift, backfire, slime, clamping)**

Append to `tests/core/test_bust.py`:

```python
def test_tick_inert_outside_active() -> None:
    sim = BustSim()
    assert sim.tick(1.0, make_rng(1)) == []
    assert sim.ghost_x == 320.0
    assert sim.ghost_y == 160.0


def test_backfire_when_ghost_sinks_low_between_cleaners() -> None:
    # min(left, right) < ghost_x < max(left, right) and ghost_y >= BEAM_CROSS_GHOST_Y:
    # the ghost has sunk low between the cleaners, so both beams angle steeply
    # down at it and cross behind it -> BACKFIRE, no rigging required.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = BEAM_CROSS_GHOST_Y + 10.0  # 330.0
    events = sim.tick(1e-6, make_rng(7))
    assert events == [BeamsCrossed()]
    assert sim.outcome is BustOutcome.BACKFIRE
    assert sim.phase is BustPhase.RESOLVED


def test_no_backfire_in_skill_window() -> None:
    # SNARE_TRIGGER_Y (280) < BEAM_CROSS_GHOST_Y (320): in the 40px band between
    # them the ghost is already springable but not yet backfiring.
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 320.0
    sim.ghost_y = (SNARE_TRIGGER_Y + BEAM_CROSS_GHOST_Y) / 2  # 300.0, inside the window
    assert sim.tick(1e-6, make_rng(7)) == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_no_backfire_when_low_ghost_is_outside_the_pair() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 100.0  # left of BOTH cleaners: the beams tilt the same way
    sim.ghost_y = BEAM_CROSS_GHOST_Y + 10.0
    assert sim.tick(1e-6, make_rng(7)) == []
    assert sim.outcome is None
    assert sim.phase is BustPhase.ACTIVE


def test_ghost_slimes_left_cleaner_at_ground() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 200.0 - SLIME_RANGE / 2  # brushing the cleaner from OUTSIDE the pair
    sim.ghost_y = BUST_GROUND_Y
    events = sim.tick(1 / 60, make_rng(3))
    assert events == []
    assert sim.outcome is BustOutcome.SLIMED
    assert sim.slimed_side == 0
    assert sim.phase is BustPhase.RESOLVED


def test_ghost_slimes_right_cleaner_at_ground() -> None:
    sim = _active_sim(left=200.0, right=440.0)
    sim.ghost_x = 440.0 + SLIME_RANGE / 2
    sim.ghost_y = BUST_GROUND_Y
    sim.tick(1 / 60, make_rng(3))
    assert sim.outcome is BustOutcome.SLIMED
    assert sim.slimed_side == 1


def test_ghost_stays_inside_clamp_bounds_over_many_ticks() -> None:
    sim = _active_sim()
    rng = make_rng(99)
    for _ in range(600):
        sim.tick(1 / 30, rng)
        assert BUST_MIN_X <= sim.ghost_x <= BUST_MAX_X
        assert BEAM_TOP_Y <= sim.ghost_y <= BUST_GROUND_Y
```

(Geometry notes. Backfire test: with `dt = 1e-6` the drift/sink displacements are under
a tenth of a pixel, so 200 < ~320 < 440 and ghost_y ~330 >= 320 hold for any seed. The
slime tests park the ghost `SLIME_RANGE / 2 = 14` px OUTSIDE the pair because at ground
level BETWEEN the cleaners the sunk-low backfire rule fires first; drift moves the ghost
at most 1 px per 1/60 s tick and the repel push is 1.5 px outward, so it stays within
`SLIME_RANGE = 28.0` of its cleaner for any seed.)

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/core/test_bust.py -v`
Expected: FAIL — the 7 new tests error with
`AttributeError: 'BustSim' object has no attribute 'tick'` (the 10 earlier tests still pass)

- [ ] **Step 7: Implement tick**

In `src/psychic_cleaners/core/bust.py`, extend the imports at the top of the file:

```python
"""Bust simulation: cleaner placement, snare laying, beams, and outcomes."""

import enum
import math
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    BEAM_CROSS_GHOST_Y,
    BEAM_MAX_TILT,
    BEAM_TOP_Y,
    BUST_GROUND_Y,
    BUST_MAX_X,
    BUST_MIN_X,
    GHOST_DRIFT_SPEED,
    GHOST_REPEL_SPEED,
    GHOST_SINK_SPEED,
    SLIME_RANGE,
    SNARE_TRIGGER_Y,
    SNARE_WIDTH,
)
from psychic_cleaners.core.events import BeamsCrossed, Event
from psychic_cleaners.core.geometry import Vec, segments_cross
from psychic_cleaners.core.rng import Rng
```

and add this method to `BustSim`, after `_beam`:

```python
    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]:
        left_x = self.left_x
        right_x = self.right_x
        if self.phase is not BustPhase.ACTIVE or left_x is None or right_x is None:
            return []
        # Drift and sink.
        self.ghost_x += rng.uniform(-1.0, 1.0) * GHOST_DRIFT_SPEED * dt_seconds
        self.ghost_y += GHOST_SINK_SPEED * dt_seconds
        # Repel horizontally away from the nearer beam when it is close.
        nearer = min((left_x, right_x), key=lambda x: abs(self.ghost_x - x))
        if abs(self.ghost_x - nearer) <= SNARE_WIDTH:
            away = 1.0 if self.ghost_x >= nearer else -1.0
            self.ghost_x += away * GHOST_REPEL_SPEED * dt_seconds
        self.ghost_x = _clamp(self.ghost_x, BUST_MIN_X, BUST_MAX_X)
        self.ghost_y = _clamp(self.ghost_y, BEAM_TOP_Y, BUST_GROUND_Y)
        # Backfire, two triggers: (a) the beams properly cross — a defensive
        # geometric check — or (b) the ghost has sunk low BETWEEN the cleaners
        # (ghost_y >= BEAM_CROSS_GHOST_Y), so both beams angle steeply down at
        # it and cross behind it. (b) is the reachable, player-caused hazard:
        # SNARE_TRIGGER_Y (280) < BEAM_CROSS_GHOST_Y (320) leaves a 40px skill
        # window where the ghost is springable but not yet backfiring.
        beams = self.beam_endpoints()
        beams_cross = beams is not None and segments_cross(
            beams[0][0], beams[0][1], beams[1][0], beams[1][1]
        )
        sunk_between = (
            min(left_x, right_x) < self.ghost_x < max(left_x, right_x)
            and self.ghost_y >= BEAM_CROSS_GHOST_Y
        )
        if beams_cross or sunk_between:
            self.outcome = BustOutcome.BACKFIRE
            self.phase = BustPhase.RESOLVED
            return [BeamsCrossed()]
        # Ghost touching a cleaner slimes that side.
        for side, x in enumerate((left_x, right_x)):
            if math.hypot(self.ghost_x - x, self.ghost_y - BUST_GROUND_Y) <= SLIME_RANGE:
                self.outcome = BustOutcome.SLIMED
                self.slimed_side = side
                self.phase = BustPhase.RESOLVED
                break
        return []
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/core/test_bust.py -v`
Expected: PASS — 17 passed

- [ ] **Step 9: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean (`Success: no issues found` from mypy)

- [ ] **Step 10: Commit**

```bash
git add src/psychic_cleaners/core/bust.py tests/core/test_bust.py
git commit -m "feat: add bust simulation with snare, backfire, and slime outcomes"
```

### Task 25: Bust Flow in Game

**Files:**
- Modify: `src/psychic_cleaners/core/game.py` (arrival routing to BUST, BUST command
  handling, bust world-ticking, `_resolve_bust` with fees/snare accounting/sliming/
  bankruptcy)
- Test: `tests/integration/test_bust_flow.py`

**Interfaces:**
- Consumes: `BustPhase`, `BustOutcome`, `BustSim` (Task 24); `Wallet` / `bust_fee`
  (Task 9, `core/economy.py`); `ITEMS` (Task 10, `core/catalog.py`); `CLEANER_COUNT`,
  `CONTAINMENT_RIG_CAPACITY` (Task 4, `core/constants.py`); commands `MoveCleaner`,
  `PlaceCleaner`, `LaySnare`, `SpringSnare` and events `GhostTrapped`, `HauntCleared`,
  `BustMissed`, `CleanerSlimed`, `CommandRejected`, `GameLost`, `SceneChanged`
  (Task 6, `core/events.py`); `City` haunting queries (Tasks 17-18, `core/city.py`);
  the `Game` FSM with shop flow (Milestone 3), the `_arrive_at` routing chain (Task 21),
  the Depot snare restock (Task 19), and helpers `free_snares()` / `able_cleaners()`
  (contract).
- Produces: the complete BUST scene behaviour of `Game.tick` that Task 26's shell scene
  drives; `Game.bust: BustSim | None` populated while a bust is in progress.

Preconditions from earlier tasks (verify, do not reinvent): `Game` already has the
contract fields including `bust: BustSim | None = None` — if the Milestone 2 spine left
that field out, add it to the dataclass now, defaulted to `None`. Task 21 gave `Game`
the single `_arrive_at(pos)` arrival-routing method: an if/elif chain that ends in
`else: route MAP` (no trailing override after it). Per the Task 7 `_reset()` convention
(every task that adds a `Game` field reinitializes it in `_reset()`; `NewGame` and
`Continue` both route through `_reset()`), this task extends `_reset()` with
`self.bust = None` in Step 3 — there are no inline bust resets in the NewGame handler.

Three TDD cycles: (A) arrival routing into BUST, (B) commands + CAUGHT resolution
(fee, rig, haunt cleared), (C) MISSED/SLIMED/BACKFIRE + bankruptcy.

- [ ] **Step 1: Write the failing routing tests**

Create `tests/integration/test_bust_flow.py` with exactly (the import block covers all
three cycles; some names are first used in Steps 5 and 9):

```python
"""Integration tests: the bust flow through the Game FSM."""

from psychic_cleaners.core.bust import BustPhase, BustSim
from psychic_cleaners.core.catalog import ITEMS
from psychic_cleaners.core.constants import (
    BEAM_CROSS_GHOST_Y,
    BUST_GROUND_Y,
    BUST_MIN_X,
    SLIME_RANGE,
)
from psychic_cleaners.core.events import (
    BeamsCrossed,
    BustMissed,
    BuyItem,
    CleanerSlimed,
    CommandRejected,
    FinishShopping,
    GameLost,
    GhostTrapped,
    GridPos,
    HauntCleared,
    LaySnare,
    MoveCleaner,
    NewGame,
    PlaceCleaner,
    SceneId,
    SelectVehicle,
    SetDestination,
    SpringSnare,
)
from psychic_cleaners.core.game import Game, new_game

HAUNT: GridPos = (1, 5)


def _shopped_game(*, snares: int = 1, with_rig: bool = False) -> Game:
    """New game with a hearse plus the given gear, standing at the Depot on the map."""
    game = new_game(1)
    game.tick([NewGame("Pat")], 0.0)
    if with_rig:
        game.wallet.balance = 20_000  # hearse + rig + snare exceeds the starting bankroll
    game.tick([SelectVehicle("hearse")], 0.0)
    if with_rig:
        game.tick([BuyItem("rig")], 0.0)
    for _ in range(snares):
        game.tick([BuyItem("snare")], 0.0)
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    return game


def _arrive_at(game: Game, pos: GridPos) -> None:
    """Travel to pos, skipping the drive by completing the distance directly."""
    game.tick([SetDestination(pos)], 0.0)
    assert game.scene is SceneId.DRIVE
    assert game.drive is not None
    game.drive.distance_done = game.drive.distance_total
    game.tick([], 0.0)


def test_arrival_at_haunt_with_snares_and_cleaners_starts_bust() -> None:
    game = _shopped_game()
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.BUST
    assert isinstance(game.bust, BustSim)
    assert game.bust.phase is BustPhase.POSITION_LEFT


def test_arrival_at_haunt_without_snares_goes_to_map() -> None:
    game = _shopped_game(snares=0)
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.MAP
    assert game.bust is None
    assert HAUNT in game.city.haunted_positions()  # haunting persists


def test_arrival_at_haunt_with_one_able_cleaner_goes_to_map() -> None:
    game = _shopped_game()
    game.slimed = {0, 1}
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.MAP
    assert game.bust is None
```

Every `tick` in this file uses `dt_seconds=0.0`, so no probabilistic world event can
fire and every assertion (including the fee amount later) is exact and seed-independent.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_bust_flow.py -v`
Expected: FAIL — `test_arrival_at_haunt_with_snares_and_cleaners_starts_bust` hits
`AssertionError` on `assert game.scene is SceneId.BUST` (Task 21's fallback routed to
MAP); the two ...goes_to_map tests may already pass.

- [ ] **Step 3: Implement the arrival routing**

Three edits to `src/psychic_cleaners/core/game.py`.

(a) Ensure these imports are present (merge into the existing import statements; several
already exist from earlier tasks — constants are Task 4, events Task 6, economy Task 9,
catalog Task 10, bust Task 24):

```python
from psychic_cleaners.core.bust import BustOutcome, BustPhase, BustSim
from psychic_cleaners.core.catalog import ITEMS
from psychic_cleaners.core.constants import CLEANER_COUNT, CONTAINMENT_RIG_CAPACITY
from psychic_cleaners.core.economy import bust_fee
from psychic_cleaners.core.events import (
    BustMissed,
    CleanerSlimed,
    CommandRejected,
    GameLost,
    GhostTrapped,
    HauntCleared,
    LaySnare,
    MoveCleaner,
    PlaceCleaner,
    SceneChanged,
    SpringSnare,
)
```

(`ITEMS` and `CommandRejected` are first used in Steps 7 and 11; the quality gates only
run at the end of the task.)

(b) Task 21's `_arrive_at(pos)` is the single arrival-routing method — an if/elif chain
ending in `else: route MAP`, with no trailing override after it. Insert the BUST branch
as an `elif` immediately ABOVE that final `else`, keeping the local names (`pos` for the
arrival position, `events` for the event list) that the surrounding code uses. The exact
resulting chain (only the haunted `elif` is new; Task 21's branch bodies, elided here,
stay untouched):

```python
        if pos == DEPOT_POS:
            ...  # Task 21's depot branch: empty snares, restore cleaners, -> MAP
        elif (
            pos in self.city.haunted_positions()
            and self.free_snares() > 0
            and self.able_cleaners() >= 2
        ):
            self.bust = BustSim()
            self.scene = SceneId.BUST
            events.append(SceneChanged(SceneId.BUST))
        else:
            ...  # Task 21's fallback: route to MAP
```

(Milestone 9 will later insert its Tower-finale `elif` between the depot branch and this
one — tower before haunted before the else, per the contract.) The final `else` (scene
MAP) stays: a haunted arrival without a free snare or with fewer than 2 able cleaners
falls through to MAP and the haunting persists.

(c) Per the Task 7 `_reset()` convention, add the field's reinitialization to
`Game._reset()` (no inline reset in the NewGame handler — NewGame and Continue both
route through `_reset()`):

```python
        self.bust = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_bust_flow.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Write the failing tests for commands and CAUGHT resolution**

Append to `tests/integration/test_bust_flow.py`:

```python
def _game_at_bust(*, snares: int = 1, with_rig: bool = False) -> Game:
    game = _shopped_game(snares=snares, with_rig=with_rig)
    game.city.buildings[HAUNT].haunted = True
    _arrive_at(game, HAUNT)
    assert game.scene is SceneId.BUST
    return game


def _lay_and_activate(game: Game) -> BustSim:
    game.tick([MoveCleaner(-120.0), PlaceCleaner()], 0.0)  # left cleaner at x=200
    game.tick([MoveCleaner(240.0), PlaceCleaner()], 0.0)  # right cleaner at x=440
    game.tick([MoveCleaner(-120.0), LaySnare()], 0.0)  # snare at x=320
    bust = game.bust
    assert bust is not None
    assert bust.phase is BustPhase.ACTIVE
    return bust


def test_early_lay_snare_ignored_and_early_spring_rejected() -> None:
    game = _game_at_bust()
    bust = game.bust
    assert bust is not None
    events = game.tick([LaySnare(), SpringSnare()], 0.0)
    assert CommandRejected("no snare laid") in events  # SpringSnare outside ACTIVE
    assert bust.phase is BustPhase.POSITION_LEFT  # LaySnare silently ignored
    assert bust.snare_x is None


def test_place_cleaner_does_not_lay_snare() -> None:
    game = _game_at_bust()
    bust = game.bust
    assert bust is not None
    game.tick([PlaceCleaner()], 0.0)
    game.tick([PlaceCleaner()], 0.0)
    assert bust.phase is BustPhase.SNARE
    game.tick([PlaceCleaner()], 0.0)  # only LaySnare may lay the snare
    assert bust.phase is BustPhase.SNARE
    assert bust.snare_x is None


def test_successful_bust_pays_fee_and_clears_haunt() -> None:
    game = _game_at_bust()
    bust = _lay_and_activate(game)
    balance_before = game.wallet.balance
    bust.ghost_x = 320.0  # force the smudge over the snare before springing
    bust.ghost_y = 300.0
    events = game.tick([SpringSnare()], 0.0)
    assert GhostTrapped(300) in events  # psi is 0, so fee == BUST_BASE_FEE
    assert HauntCleared(HAUNT) in events
    assert game.wallet.balance == balance_before + 300
    assert game.snares_full == 1
    assert game.contained == 0
    assert game.free_snares() == 0
    assert game.bust is None
    assert game.scene is SceneId.MAP
    assert HAUNT not in game.city.haunted_positions()


def test_rig_keeps_snare_free_on_catch() -> None:
    game = _game_at_bust(with_rig=True)
    bust = _lay_and_activate(game)
    bust.ghost_x = 320.0
    bust.ghost_y = 300.0
    game.tick([SpringSnare()], 0.0)
    assert game.contained == 1
    assert game.snares_full == 0
    assert game.free_snares() == 1
    assert game.scene is SceneId.MAP
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_bust_flow.py -v`
Expected: FAIL — `_lay_and_activate` raises `AssertionError` on
`assert bust.phase is BustPhase.ACTIVE` (BUST commands are not handled yet);
`test_early_lay_snare_ignored_and_early_spring_rejected` fails on the missing
`CommandRejected`; `test_place_cleaner_does_not_lay_snare` passes vacuously or fails
depending on the Milestone 2 stub, either is fine.

- [ ] **Step 7: Implement BUST command handling and CAUGHT resolution**

Three edits to `src/psychic_cleaners/core/game.py`.

(a) In `Game.tick`'s per-command dispatch (the `for command in commands:` loop with
scene-keyed branches), add a BUST branch alongside the existing scene branches:

```python
            elif self.scene is SceneId.BUST and self.bust is not None:
                bust = self.bust
                if isinstance(command, MoveCleaner):
                    bust.move(command.dx)
                elif isinstance(command, PlaceCleaner) and bust.phase in (
                    BustPhase.POSITION_LEFT,
                    BustPhase.POSITION_RIGHT,
                ):
                    bust.place()
                elif isinstance(command, LaySnare) and bust.phase is BustPhase.SNARE:
                    bust.place()
                elif isinstance(command, SpringSnare):
                    if bust.phase is BustPhase.ACTIVE:
                        bust.spring()
                    else:
                        events.append(CommandRejected("no snare laid"))
```

(`SpringSnare` outside the ACTIVE phase answers with `CommandRejected("no snare laid")`
per the contract — Task 6's event; `LaySnare` outside the SNARE phase stays a silent
ignore.)

(b) Bust ticking and resolution slot into the canonical `Game.tick` shape (dispatch
loop -> scene ticking -> post-tick resolution). In the scene-ticking section (the block
guarded by `self.scene in (SceneId.MAP, SceneId.DRIVE, SceneId.BUST)` where
clock/psi/city/mascot advance — BUST is already a world scene there), append after the
existing model ticking:

```python
        if (
            self.scene is SceneId.BUST
            and self.bust is not None
            and self.bust.phase is BustPhase.ACTIVE
        ):
            events.extend(self.bust.tick(dt_seconds, self.rng))
```

Then in the post-tick resolution step (the same step that routes drive arrivals through
`_arrive_at`), add bust resolution:

```python
        if self.bust is not None and self.bust.phase is BustPhase.RESOLVED:
            events.extend(self._resolve_bust())
```

Command dispatch runs before scene ticking and resolution, so
`game.tick([SpringSnare()], 0.0)` springs the snare in the dispatch loop, the sim is
RESOLVED by the time the resolution step runs, and the payout events come back in the
SAME call's return value — exactly what the tests below assert.

(c) Add this method to `Game` (extended with the other outcomes in Step 11):

```python
    def _resolve_bust(self) -> list[Event]:
        bust = self.bust
        loadout = self.loadout
        assert bust is not None and loadout is not None
        events: list[Event] = []
        if bust.outcome is BustOutcome.CAUGHT:
            if loadout.has("rig") and self.contained < CONTAINMENT_RIG_CAPACITY:
                self.contained += 1
            else:
                self.snares_full += 1
            fee = bust_fee(self.psi.value)
            self.wallet.earn(fee)
            events.append(GhostTrapped(fee))
            self.city.clear_haunt(self.position)
            events.append(HauntCleared(self.position))
        self.bust = None
        self.scene = SceneId.MAP
        events.append(SceneChanged(SceneId.MAP))
        return events
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_bust_flow.py -v`
Expected: PASS — 7 passed (the 3 routing tests plus the 4 added in Step 5;
`_game_at_bust` and `_lay_and_activate` are helpers, not tests)

- [ ] **Step 9: Write the failing tests for backfire, missed snare, and bankruptcy**

Append to `tests/integration/test_bust_flow.py`:

```python
def test_backfire_slimes_two_and_wastes_snare() -> None:
    game = _game_at_bust(snares=2)
    bust = _lay_and_activate(game)
    # The smudge has sunk low BETWEEN the cleaners (200 < 320 < 440 and
    # ghost_y >= BEAM_CROSS_GHOST_Y): both beams angle steeply down at it and
    # cross -> backfire on this tick's bust ticking, resolved the same call.
    bust.ghost_x = 320.0
    bust.ghost_y = BEAM_CROSS_GHOST_Y + 10.0
    events = game.tick([], 0.0)
    assert BeamsCrossed() in events
    assert CleanerSlimed(0) in events
    assert CleanerSlimed(1) in events
    assert BustMissed() not in events
    assert game.slimed == {0, 1}
    assert game.able_cleaners() == 1
    assert game.loadout is not None
    assert game.loadout.count("snare") == 1  # one snare wasted, one left
    assert game.bust is None
    assert game.scene is SceneId.MAP
    assert HAUNT in game.city.haunted_positions()  # smudge escaped


def test_missed_last_snare_when_broke_loses_game() -> None:
    game = _game_at_bust(snares=1)
    bust = _lay_and_activate(game)
    game.wallet.balance = ITEMS["snare"].price - 1  # too broke to restock at the Depot
    bust.ghost_x = BUST_MIN_X  # nowhere near the snare at x=320
    bust.ghost_y = 150.0
    events = game.tick([SpringSnare()], 0.0)
    assert BustMissed() in events
    assert GameLost("no snares left — the franchise folds") in events
    assert game.result == "lost"
    assert game.lose_reason == "no snares left — the franchise folds"
    assert game.scene is SceneId.GAME_OVER
    assert game.free_snares() == 0
    assert game.snares_full == 0
    assert HAUNT in game.city.haunted_positions()


def test_missed_last_snare_with_restock_money_does_not_lose() -> None:
    game = _game_at_bust(snares=1)  # wallet still holds 4600 after hearse + snare
    bust = _lay_and_activate(game)
    bust.ghost_x = BUST_MIN_X
    bust.ghost_y = 150.0
    events = game.tick([SpringSnare()], 0.0)
    assert BustMissed() in events
    assert not any(isinstance(event, GameLost) for event in events)
    assert game.result is None
    assert game.scene is SceneId.MAP
    assert game.free_snares() == 0
    assert game.snares_full == 0
    assert game.wallet.balance >= ITEMS["snare"].price  # rich enough to restock


def test_slimed_bust_reports_game_level_cleaner_index() -> None:
    game = _game_at_bust(snares=2)
    game.slimed = {0}  # cleaner 0 already out: participants are 1 and 2
    bust = _lay_and_activate(game)
    bust.ghost_x = 200.0 - SLIME_RANGE / 2  # brushing the left cleaner from outside...
    bust.ghost_y = BUST_GROUND_Y  # ...at ground level
    events = game.tick([], 0.0)
    assert CleanerSlimed(1) in events  # left side maps to lowest unslimed index
    assert game.slimed == {0, 1}
    assert game.loadout is not None
    assert game.loadout.count("snare") == 1
    assert game.scene is SceneId.MAP
```

(All ticks stay at `dt_seconds=0.0`: `BustSim.tick` runs its backfire and slime checks
on every ACTIVE tick regardless of `dt`, and zero `dt` means zero drift/sink/repel, so
every position is exact and seed-independent. The slimed test parks the ghost
`SLIME_RANGE / 2 = 14` px OUTSIDE the cleaner pair — at ground level BETWEEN the
cleaners the sunk-low backfire rule would fire first. Starting that bust with cleaner 0
slimed is legal: `able_cleaners() == 2`.)

- [ ] **Step 10: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_bust_flow.py -v`
Expected: FAIL — the 4 new tests fail: no `CleanerSlimed`/`BustMissed`/`GameLost` events
and `loadout.count("snare")` unchanged (only the CAUGHT branch of `_resolve_bust`
exists).

- [ ] **Step 11: Implement the remaining outcomes and the bankruptcy check**

Two edits to `src/psychic_cleaners/core/game.py`.

(a) Replace the whole `_resolve_bust` method with:

```python
    def _resolve_bust(self) -> list[Event]:
        bust = self.bust
        loadout = self.loadout
        assert bust is not None and loadout is not None
        events: list[Event] = []
        # The two cleaners fielded in this bust are the two lowest unslimed indices;
        # bust.slimed_side 0/1 maps onto them in order.
        unslimed = sorted(set(range(CLEANER_COUNT)) - self.slimed)
        if bust.outcome is BustOutcome.CAUGHT:
            if loadout.has("rig") and self.contained < CONTAINMENT_RIG_CAPACITY:
                self.contained += 1
            else:
                self.snares_full += 1
            fee = bust_fee(self.psi.value)
            self.wallet.earn(fee)
            events.append(GhostTrapped(fee))
            self.city.clear_haunt(self.position)
            events.append(HauntCleared(self.position))
        elif bust.outcome is BustOutcome.MISSED:
            # Wasted snare. Direct mutation per contract; the key exists because
            # entering a bust required free_snares() > 0.
            loadout.counts["snare"] -= 1
            events.append(BustMissed())
        elif bust.outcome is BustOutcome.SLIMED:
            loadout.counts["snare"] -= 1
            side = bust.slimed_side if bust.slimed_side is not None else 0
            idx = unslimed[side]
            self.slimed.add(idx)
            events.append(CleanerSlimed(idx))
        elif bust.outcome is BustOutcome.BACKFIRE:
            loadout.counts["snare"] -= 1
            for idx in unslimed[:2]:
                self.slimed.add(idx)
                events.append(CleanerSlimed(idx))
        self.bust = None
        self.scene = SceneId.MAP
        events.append(SceneChanged(SceneId.MAP))
        return events
```

(b) In the post-tick resolution step, append the bankruptcy check immediately after the
bust-resolution block added in Step 7(b). It is scene-gated to the world scenes per the
contract, so it runs on every world tick — including the tick that just resolved a bust
(resolution lands the game back in MAP, a world scene):

```python
        # Bankruptcy: the franchise folds only when it cannot field a snare by
        # ANY means — none free, none full (full snares are emptied back to
        # free at the Depot), and too broke to restock one at the Depot
        # (Task 19's MAP-scene BuyItem("snare") flow).
        if (
            self.scene in (SceneId.MAP, SceneId.DRIVE, SceneId.BUST)
            and self.loadout is not None
            and self.free_snares() == 0
            and self.snares_full == 0
            and self.wallet.balance < ITEMS["snare"].price
        ):
            reason = "no snares left — the franchise folds"
            self.result = "lost"
            self.lose_reason = reason
            events.append(GameLost(reason))
            self.scene = SceneId.GAME_OVER
            events.append(SceneChanged(SceneId.GAME_OVER))
```

A wasted last snare with money still in the wallet does NOT end the game — the player
can drive to the Depot and restock (`free_snares() == 0` merely blocks new busts until
then).

- [ ] **Step 12: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_bust_flow.py -v`
Expected: PASS — 11 passed (7 from Steps 1 and 5 plus the 4 added in Step 9).
Also run the full suite to catch regressions in earlier
milestones' FSM tests: `uv run pytest` — expected all green.

- [ ] **Step 13: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 14: Commit**

```bash
git add src/psychic_cleaners/core/game.py tests/integration/test_bust_flow.py
git commit -m "feat: wire bust flow into game FSM with fees and snare accounting"
```

### Task 26: Busting Scene

**Files:**
- Create: `src/psychic_cleaners/shell/scenes/busting.py` (replace the Milestone 2 stub if
  one exists at that path)
- Modify: `src/psychic_cleaners/shell/gfx.py` (add "smudge", "cleaner.slimed", "snare"
  sprite builders)
- Modify: `src/psychic_cleaners/shell/app.py` (register `BustingScene()` as
  `SCENES[SceneId.BUST]`)
- Test: `tests/shell/test_busting_scene.py`

**Interfaces:**
- Consumes: `BustPhase`, `BustSim` (Task 24); `Game`, `new_game` (`core/game.py`; the
  `bust` field's flow is Task 25); commands `MoveCleaner`, `PlaceCleaner`, `LaySnare`,
  `SpringSnare` and `SceneId` (Task 6, `core/events.py`); constants `BUST_GROUND_Y`,
  `CLEANER_SPEED` (Task 4, `core/constants.py`); shell `SpriteFactory` and the
  module-level `_BUILDERS` registry in `shell/gfx.py`, `TextRenderer`, `FPS`, `SCENES`,
  and the `Scene` protocol from `shell/scenes/__init__.py` (all Task 8, Milestone 3;
  the gfx registry was extended by Tasks 19 and 22).
- Produces: `BustingScene` (class name per contract) registered in `SCENES[SceneId.BUST]`;
  sprites `"smudge"` (32x32), `"cleaner.slimed"` (same size as `"cleaner"`), `"snare"`
  (24x12) available from `SpriteFactory.get`.

Three TDD cycles: (1) the three new sprites, (2) `commands()` key mapping per phase,
(3) `draw()` smoke in the ACTIVE phase + scene registration.

- [ ] **Step 1: Write the failing sprite tests**

Create `tests/shell/test_busting_scene.py` with exactly (`tests/conftest.py` already sets
`SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`; the import block covers all three
cycles):

```python
"""Input mapping and draw smoke tests for the busting scene."""

import pygame
import pytest

from psychic_cleaners.core.bust import BustPhase, BustSim
from psychic_cleaners.core.constants import CLEANER_SPEED
from psychic_cleaners.core.events import (
    LaySnare,
    MoveCleaner,
    PlaceCleaner,
    SceneId,
    SpringSnare,
)
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.shell.app import FPS, SCENES
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.busting import BustingScene
from psychic_cleaners.shell.text import TextRenderer


def _init_video() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))


def test_new_sprites_have_expected_sizes() -> None:
    _init_video()
    gfx = SpriteFactory()
    assert gfx.get("smudge").get_size() == (32, 32)
    assert gfx.get("snare").get_size() == (24, 12)
    assert gfx.get("cleaner.slimed").get_size() == gfx.get("cleaner").get_size()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_busting_scene.py -v`
Expected: FAIL. Either a collection error
(`ModuleNotFoundError: No module named 'psychic_cleaners.shell.scenes.busting'` /
`ImportError: cannot import name 'BustingScene'` if Milestone 2 left no stub or a bare
stub) or, if the module imports, the sprite test fails with the registry's unknown-name
error (`KeyError: 'smudge'` from the Task 8 `_BUILDERS` lookup). If the
failure is the import error, create a minimal placeholder now so the sprite cycle can run
red/green on its own — `src/psychic_cleaners/shell/scenes/busting.py`:

```python
"""Bust scene: position cleaners, lay the snare, steer the smudge, spring it."""

import pygame

from psychic_cleaners.core.events import Command
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer


class BustingScene:
    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        return []

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((16, 14, 24))
```

Re-run; now only `test_new_sprites_have_expected_sizes` fails, on the `"smudge"` lookup.

- [ ] **Step 3: Add the sprite builders**

`shell/gfx.py` dispatches `SpriteFactory.get(name)` through the module-level
`_BUILDERS: dict[str, Callable[[], pygame.Surface]]` registry of zero-argument builder
functions (pattern established in Task 8, Milestone 3, and extended by Tasks 19 and 22).
Per the contract, sprite builders are module-level functions — never instance methods,
and there is no `self._builders` in `__init__`; `get` only caches and calls
`_BUILDERS[name]()`. Add these three module-level functions to `shell/gfx.py`:

```python
def _build_smudge() -> pygame.Surface:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(surf, (146, 188, 92), (16, 19), 12)  # greasy body
    pygame.draw.circle(surf, (186, 222, 124), (13, 15), 8)  # highlight
    pygame.draw.circle(surf, (32, 32, 32), (12, 14), 2)  # eyes
    pygame.draw.circle(surf, (32, 32, 32), (20, 14), 2)
    return surf


def _build_cleaner_slimed() -> pygame.Surface:
    surf = _build_cleaner()  # fresh surface from the module-level cleaner builder
    tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    tint.fill((110, 210, 110, 255))
    surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)  # green tint
    return surf


def _build_snare() -> pygame.Surface:
    surf = pygame.Surface((24, 12), pygame.SRCALPHA)
    pygame.draw.rect(surf, (58, 58, 70), pygame.Rect(0, 0, 24, 12))
    pygame.draw.rect(surf, (250, 208, 84), pygame.Rect(0, 0, 24, 12), width=2)
    pygame.draw.line(surf, (250, 208, 84), (11, 2), (11, 9), width=2)
    return surf
```

Then register them by adding three entries to the module-level `_BUILDERS` dict literal:

```python
    "smudge": _build_smudge,
    "cleaner.slimed": _build_cleaner_slimed,
    "snare": _build_snare,
```

A module-level `_build_cleaner` should already exist and be registered under
`"cleaner"` (the name is in the contract's sprite list). If no earlier task added it,
add this one too, with the dict entry `"cleaner": _build_cleaner,`:

```python
def _build_cleaner() -> pygame.Surface:
    surf = pygame.Surface((16, 24), pygame.SRCALPHA)
    pygame.draw.rect(surf, (210, 190, 150), pygame.Rect(4, 10, 8, 14))  # overalls
    pygame.draw.circle(surf, (235, 200, 170), (8, 6), 5)  # head
    pygame.draw.rect(surf, (120, 90, 60), pygame.Rect(2, 12, 3, 8))  # residue pack
    return surf
```

(`_build_cleaner_slimed` calls the builder function directly rather than going through
`SpriteFactory.get`, so it tints a fresh surface and needs no `.copy()` — and the
factory's cached `"cleaner"` surface is never mutated.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/shell/test_busting_scene.py -v`
Expected: PASS — 1 passed

- [ ] **Step 5: Write the failing key-mapping tests**

Append to `tests/shell/test_busting_scene.py`:

```python
class _Pressed:
    """Stand-in for pygame.key.get_pressed() supporting index access."""

    def __init__(self, *keys: int) -> None:
        self._down = set(keys)

    def __getitem__(self, key: int) -> bool:
        return key in self._down


def _press(monkeypatch: pytest.MonkeyPatch, *keys: int) -> None:
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Pressed(*keys))


@pytest.fixture
def bust_game() -> Game:
    game = new_game(1)
    game.scene = SceneId.BUST
    game.bust = BustSim()
    return game


def test_held_arrows_move_cursor_in_positioning_phases(
    monkeypatch: pytest.MonkeyPatch, bust_game: Game
) -> None:
    scene = BustingScene()
    step = CLEANER_SPEED / FPS
    _press(monkeypatch, pygame.K_LEFT)
    assert scene.commands([], bust_game) == [MoveCleaner(-step)]
    _press(monkeypatch, pygame.K_RIGHT)
    assert scene.commands([], bust_game) == [MoveCleaner(step)]
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.SNARE
    _press(monkeypatch, pygame.K_LEFT)
    assert scene.commands([], bust_game) == [MoveCleaner(-step)]


def test_arrows_ignored_when_active(monkeypatch: pytest.MonkeyPatch, bust_game: Game) -> None:
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.ACTIVE
    _press(monkeypatch, pygame.K_LEFT, pygame.K_RIGHT)
    assert BustingScene().commands([], bust_game) == []


def test_enter_places_cleaners_then_lays_snare(
    monkeypatch: pytest.MonkeyPatch, bust_game: Game
) -> None:
    scene = BustingScene()
    _press(monkeypatch)  # nothing held
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert bust_game.bust is not None
    assert scene.commands([enter], bust_game) == [PlaceCleaner()]
    bust_game.bust.phase = BustPhase.POSITION_RIGHT
    assert scene.commands([enter], bust_game) == [PlaceCleaner()]
    bust_game.bust.phase = BustPhase.SNARE
    assert scene.commands([enter], bust_game) == [LaySnare()]
    bust_game.bust.phase = BustPhase.ACTIVE
    assert scene.commands([enter], bust_game) == []


def test_space_springs_snare(bust_game: Game) -> None:
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.ACTIVE
    space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    assert BustingScene().commands([space], bust_game) == [SpringSnare()]
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_busting_scene.py -v`
Expected: FAIL — the 4 new tests fail with `AssertionError` (the placeholder
`commands()` returns `[]` where commands are expected)

- [ ] **Step 7: Implement commands()**

Replace `src/psychic_cleaners/shell/scenes/busting.py` entirely with (the `draw` body is
completed in Step 11):

```python
"""Bust scene: position cleaners, lay the snare, steer the smudge, spring it."""

import pygame

from psychic_cleaners.core.bust import BustPhase
from psychic_cleaners.core.constants import BUST_GROUND_Y, CLEANER_SPEED
from psychic_cleaners.core.events import (
    Command,
    LaySnare,
    MoveCleaner,
    PlaceCleaner,
    SpringSnare,
)
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_POSITIONING = (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT, BustPhase.SNARE)

_HINTS: dict[BustPhase, str] = {
    BustPhase.POSITION_LEFT: "Arrows: move first cleaner - Enter: place",
    BustPhase.POSITION_RIGHT: "Arrows: move second cleaner - Enter: place",
    BustPhase.SNARE: "Arrows: move snare - Enter: lay it down",
    BustPhase.ACTIVE: "Space: spring the snare when the smudge is above it",
    BustPhase.RESOLVED: "",
}


class BustingScene:
    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        # Runtime import: app.py imports the scene modules at import time, so a
        # module-level import of shell.app here would be circular.
        from psychic_cleaners.shell.app import FPS

        bust = game.bust
        if bust is None:
            return []
        cmds: list[Command] = []
        if bust.phase in _POSITIONING:
            pressed = pygame.key.get_pressed()
            step = CLEANER_SPEED / FPS
            if pressed[pygame.K_LEFT]:
                cmds.append(MoveCleaner(-step))
            if pressed[pygame.K_RIGHT]:
                cmds.append(MoveCleaner(step))
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_RETURN:
                if bust.phase in (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT):
                    cmds.append(PlaceCleaner())
                elif bust.phase is BustPhase.SNARE:
                    cmds.append(LaySnare())
            elif event.key == pygame.K_SPACE and bust.phase is BustPhase.ACTIVE:
                cmds.append(SpringSnare())
        return cmds

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((16, 14, 24))
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/shell/test_busting_scene.py -v`
Expected: PASS — 5 passed

- [ ] **Step 9: Write the failing draw-smoke and registration tests**

Append to `tests/shell/test_busting_scene.py`:

```python
def test_bust_scene_registered() -> None:
    assert isinstance(SCENES[SceneId.BUST], BustingScene)


def test_draw_smoke_in_active_phase(bust_game: Game) -> None:
    _init_video()
    bust = bust_game.bust
    assert bust is not None
    bust.left_x = 200.0
    bust.right_x = 440.0
    bust.snare_x = 320.0
    bust.phase = BustPhase.ACTIVE
    surface = pygame.Surface((640, 400))
    BustingScene().draw(surface, bust_game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 399)) != pygame.Color(16, 14, 24)  # ground drawn


def test_draw_smoke_in_every_phase(bust_game: Game) -> None:
    _init_video()
    surface = pygame.Surface((640, 400))
    scene = BustingScene()
    bust = bust_game.bust
    assert bust is not None
    for phase in BustPhase:
        bust.phase = phase
        scene.draw(surface, bust_game, SpriteFactory(), TextRenderer())
```

- [ ] **Step 10: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_busting_scene.py -v`
Expected: FAIL — `test_bust_scene_registered` fails with `AssertionError` (the stub scene
is still registered) and `test_draw_smoke_in_active_phase` fails on the ground-pixel
assertion (draw only fills the background so far)

- [ ] **Step 11: Implement draw() and register the scene**

(a) In `src/psychic_cleaners/shell/scenes/busting.py`, replace the `draw` method with:

```python
    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((16, 14, 24))
        # Building facade with lit windows.
        pygame.draw.rect(surface, (72, 62, 88), pygame.Rect(60, 40, 520, 320))
        for row_y in range(80, 320, 60):
            for col_x in range(100, 560, 80):
                pygame.draw.rect(surface, (236, 210, 120), pygame.Rect(col_x, row_y, 24, 32))
        # Pavement.
        pygame.draw.rect(surface, (58, 58, 66), pygame.Rect(0, int(BUST_GROUND_Y), 640, 40))
        bust = game.bust
        if bust is None:
            return
        # Placed cleaners.
        for side, x in enumerate((bust.left_x, bust.right_x)):
            if x is not None:
                name = "cleaner.slimed" if bust.slimed_side == side else "cleaner"
                _blit_on_ground(surface, gfx.get(name), x)
        # Cursor: a cleaner while positioning, the snare while aiming it.
        if bust.phase in (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT):
            _blit_on_ground(surface, gfx.get("cleaner"), bust.cursor_x)
        elif bust.phase is BustPhase.SNARE:
            _blit_on_ground(surface, gfx.get("snare"), bust.cursor_x)
        # Laid snare.
        if bust.snare_x is not None:
            _blit_on_ground(surface, gfx.get("snare"), bust.snare_x)
        # The smudge.
        smudge = gfx.get("smudge")
        smudge_pos = (
            int(bust.ghost_x - smudge.get_width() / 2),
            int(bust.ghost_y - smudge.get_height() / 2),
        )
        surface.blit(smudge, smudge_pos)
        # Beams.
        beams = bust.beam_endpoints()
        if beams is not None:
            for start, end in beams:
                pygame.draw.line(surface, (120, 220, 255), start, end, 3)
        text.draw(surface, _HINTS[bust.phase], (20, 12), size=16)
```

and add this module-level helper at the bottom of the file:

```python
def _blit_on_ground(surface: pygame.Surface, sprite: pygame.Surface, x: float) -> None:
    surface.blit(
        sprite,
        (int(x - sprite.get_width() / 2), int(BUST_GROUND_Y - sprite.get_height())),
    )
```

(b) In `src/psychic_cleaners/shell/app.py`, add the import

```python
from psychic_cleaners.shell.scenes.busting import BustingScene
```

(merged into the existing scene imports, keeping alphabetical order for ruff's isort) and
change the `SceneId.BUST` entry in the `SCENES` dict literal to:

```python
    SceneId.BUST: BustingScene(),
```

removing the stub that was registered there.

- [ ] **Step 12: Run test to verify it passes**

Run: `uv run pytest tests/shell/test_busting_scene.py -v`
Expected: PASS — 8 passed. Then run the whole suite: `uv run pytest` — all green
(the existing app smoke test still renders every registered scene).

- [ ] **Step 13: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: clean

- [ ] **Step 14: Commit**

```bash
git add src/psychic_cleaners/shell/scenes/busting.py src/psychic_cleaners/shell/gfx.py \
    src/psychic_cleaners/shell/app.py tests/shell/test_busting_scene.py
git commit -m "feat: add busting scene with beams, snare, and smudge sprites"
```

<!-- CONTRACT-NOTE: MISSED/SLIMED/BACKFIRE waste a snare via direct mutation
loadout.counts["snare"] -= 1, as instructed; Loadout exposes no remove/spend API. -->
<!-- CONTRACT-NOTE: Task 26 assumes a module-level "cleaner" builder function exists in
shell/gfx.py from an earlier milestone (the name is in the contract's sprite list); a
fallback module-level builder is included in Step 3 in case no other task added it. -->







---

## Milestone 8: Mascot events

Goal: implement the Sir Squish threat model (`core/giant.py`) — a pure state machine that rolls
random rampages against city PSI, raises a timed alert when a mascot sensor is carried, and
expires into a stomp — then wire it into `Game.tick` (stomp fines, PSI spikes, the `DeployBait`
command) and all three world scenes — city map, driving, busting (flashing alert banner, B key).

When this lands: while playing on the city map (or driving/busting), Sir Squish periodically
stomps a random building for a $4,000 fine and a 500 PSI spike; with a mascot sensor equipped a
flashing "MASCOT INBOUND" banner gives you 10 seconds to press B and spend one gummy bait charge
to avert him.

### Task 27: Mascot threat model

**Files:**
- Create: src/psychic_cleaners/core/giant.py
- Test: tests/core/test_giant.py

**Interfaces:**
- Consumes: `MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI`, `MASCOT_ALERT_WINDOW` from
  `core/constants.py`; `Event`, `MascotAlert(window_seconds: float)`, `StompTriggered()` from
  `core/events.py`; `Rng` protocol and `make_rng(seed: int) -> Rng` from `core/rng.py`.
- Produces: `MascotState` enum (`CALM`, `ALERT`) and
  `MascotModel(state: MascotState = CALM, alert_remaining: float = 0.0)` with
  `tick(dt_seconds: float, psi_value: int, has_sensor: bool, rng: Rng) -> list[Event]` and
  `deploy_bait() -> bool` — consumed by Task 28.

- [ ] **Step 1: Write the failing tests for CALM-state triggering**

Create `tests/core/test_giant.py`:

```python
"""Tests for the Sir Squish threat model (core/giant.py)."""

from psychic_cleaners.core.constants import MASCOT_ALERT_WINDOW
from psychic_cleaners.core.events import Event, MascotAlert, StompTriggered
from psychic_cleaners.core.giant import MascotModel, MascotState
from psychic_cleaners.core.rng import make_rng


def _tick_until_event(mascot: MascotModel, psi: int, *, sensor: bool, seed: int) -> list[Event]:
    """Tick 1-second steps until the model emits something (10 simulated minutes max)."""
    rng = make_rng(seed)
    for _ in range(600):
        events = mascot.tick(1.0, psi, sensor, rng)
        if events:
            return events
    raise AssertionError("mascot never triggered within 10 simulated minutes")


def test_psi_zero_never_triggers() -> None:
    mascot = MascotModel()
    rng = make_rng(101)
    for _ in range(10_000):
        assert mascot.tick(1.0, 0, True, rng) == []
    assert mascot.state is MascotState.CALM
    assert mascot.alert_remaining == 0.0


def test_max_psi_with_sensor_raises_alert() -> None:
    mascot = MascotModel()
    events = _tick_until_event(mascot, 9_999, sensor=True, seed=102)
    assert events == [MascotAlert(MASCOT_ALERT_WINDOW)]
    assert mascot.state is MascotState.ALERT
    assert mascot.alert_remaining == MASCOT_ALERT_WINDOW


def test_max_psi_without_sensor_stomps_directly() -> None:
    mascot = MascotModel()
    events = _tick_until_event(mascot, 9_999, sensor=False, seed=103)
    assert events == [StompTriggered()]
    assert mascot.state is MascotState.CALM
    assert mascot.alert_remaining == 0.0
```

(At 9,999 PSI the trigger rate is `0.15 * 9.999 ≈ 1.5` per minute — a per-1s-tick probability of
about 0.025 — so 600 ticks make a trigger a statistical certainty for any fixed seed; the seeds
just make the run reproducible.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_giant.py -v`

Expected: FAIL — collection error
`ModuleNotFoundError: No module named 'psychic_cleaners.core.giant'`.

- [ ] **Step 3: Write the minimal implementation (CALM branch)**

Create `src/psychic_cleaners/core/giant.py`:

```python
"""Sir Squish threat model: PSI-driven rampage rolls, sensor alerts, bait aversion."""

import enum
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    MASCOT_ALERT_WINDOW,
    MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI,
)
from psychic_cleaners.core.events import Event, MascotAlert, StompTriggered
from psychic_cleaners.core.rng import Rng


class MascotState(enum.Enum):
    CALM = enum.auto()
    ALERT = enum.auto()


@dataclass
class MascotModel:
    """Pure mascot state machine; Game translates StompTriggered into world damage."""

    state: MascotState = MascotState.CALM
    alert_remaining: float = 0.0

    def tick(self, dt_seconds: float, psi_value: int, has_sensor: bool, rng: Rng) -> list[Event]:
        events: list[Event] = []
        if self.state is MascotState.ALERT:
            return events
        rate_per_minute = MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI * (psi_value / 1000)
        if rng.random() < rate_per_minute * (dt_seconds / 60.0):
            if has_sensor:
                self.state = MascotState.ALERT
                self.alert_remaining = MASCOT_ALERT_WINDOW
                events.append(MascotAlert(MASCOT_ALERT_WINDOW))
            else:
                events.append(StompTriggered())
        return events
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_giant.py -v`

Expected: PASS — 3 passed.

- [ ] **Step 5: Add the failing test for ALERT countdown and expiry**

Append to `tests/core/test_giant.py` (and add `import pytest` at the top of the file, above the
`psychic_cleaners` imports):

```python
def test_alert_counts_down_and_expires_to_stomp() -> None:
    mascot = MascotModel(state=MascotState.ALERT, alert_remaining=MASCOT_ALERT_WINDOW)
    rng = make_rng(104)
    collected: list[Event] = []
    for _ in range(9):
        collected += mascot.tick(1.0, 9_999, True, rng)
    assert collected == []  # no re-alerts, no early stomp while the window is open
    assert mascot.state is MascotState.ALERT
    assert mascot.alert_remaining == pytest.approx(MASCOT_ALERT_WINDOW - 9.0)
    final = mascot.tick(1.5, 9_999, True, rng)
    assert final == [StompTriggered()]
    assert mascot.state is MascotState.CALM
    assert mascot.alert_remaining == 0.0
```

- [ ] **Step 6: Run the new test to verify it fails**

Run: `uv run pytest tests/core/test_giant.py::test_alert_counts_down_and_expires_to_stomp -v`

Expected: FAIL — `assert 10.0 == 1.0 ± ...` (the ALERT branch currently returns without counting
down, so `alert_remaining` is still `MASCOT_ALERT_WINDOW`).

- [ ] **Step 7: Implement the ALERT countdown**

In `src/psychic_cleaners/core/giant.py`, replace the ALERT early-return inside `tick` so the
whole method reads:

```python
    def tick(self, dt_seconds: float, psi_value: int, has_sensor: bool, rng: Rng) -> list[Event]:
        events: list[Event] = []
        if self.state is MascotState.ALERT:
            self.alert_remaining -= dt_seconds
            if self.alert_remaining <= 0.0:
                self.alert_remaining = 0.0
                self.state = MascotState.CALM
                events.append(StompTriggered())
            return events
        rate_per_minute = MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI * (psi_value / 1000)
        if rng.random() < rate_per_minute * (dt_seconds / 60.0):
            if has_sensor:
                self.state = MascotState.ALERT
                self.alert_remaining = MASCOT_ALERT_WINDOW
                events.append(MascotAlert(MASCOT_ALERT_WINDOW))
            else:
                events.append(StompTriggered())
        return events
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_giant.py -v`

Expected: PASS — 4 passed.

- [ ] **Step 9: Add the failing tests for deploy_bait**

Append to `tests/core/test_giant.py`:

```python
def test_deploy_bait_in_calm_returns_false() -> None:
    mascot = MascotModel()
    assert mascot.deploy_bait() is False
    assert mascot.state is MascotState.CALM
    assert mascot.alert_remaining == 0.0


def test_deploy_bait_in_alert_averts_and_resets() -> None:
    mascot = MascotModel(state=MascotState.ALERT, alert_remaining=5.0)
    assert mascot.deploy_bait() is True
    assert mascot.state is MascotState.CALM
    assert mascot.alert_remaining == 0.0
    # the cancelled alert must never expire into a stomp (psi 0 -> no new rolls either)
    rng = make_rng(105)
    assert mascot.tick(20.0, 0, True, rng) == []
    assert mascot.deploy_bait() is False  # back in CALM, bait does nothing now
```

- [ ] **Step 10: Run the new tests to verify they fail**

Run: `uv run pytest tests/core/test_giant.py -v -k deploy_bait`

Expected: FAIL — `AttributeError: 'MascotModel' object has no attribute 'deploy_bait'` (2 failed).

- [ ] **Step 11: Implement deploy_bait**

Append this method to `MascotModel` in `src/psychic_cleaners/core/giant.py` (below `tick`):

```python
    def deploy_bait(self) -> bool:
        """True iff currently in ALERT; averts the pending stomp and resets to CALM."""
        if self.state is MascotState.ALERT:
            self.state = MascotState.CALM
            self.alert_remaining = 0.0
            return True
        return False
```

- [ ] **Step 12: Run the full module tests to verify they pass**

Run: `uv run pytest tests/core/test_giant.py -v`

Expected: PASS — 6 passed.

- [ ] **Step 13: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean — `All checks passed!`, no files reformatted, `Success: no issues found`.

- [ ] **Step 14: Commit**

```bash
git add src/psychic_cleaners/core/giant.py tests/core/test_giant.py
git commit -m "feat: mascot threat model with sensor alerts and bait aversion"
```

### Task 28: Mascot events in Game plus world-scene alert overlay

**Files:**
- Modify: src/psychic_cleaners/core/game.py (add `mascot` field + `_reset` entry, tick
  `MascotModel` in the world advance, post-tick translation of `StompTriggered` into
  fines/PSI/`BuildingStomped`, handle the `DeployBait` command)
- Modify: src/psychic_cleaners/shell/scenes/__init__.py (shared `_draw_mascot_banner` helper)
- Modify: src/psychic_cleaners/shell/scenes/city_map.py, src/psychic_cleaners/shell/scenes/driving.py
  (Task 22), src/psychic_cleaners/shell/scenes/busting.py (Task 26) — flashing alert banner and
  B key -> `DeployBait` in each world scene
- Test: tests/core/test_game_mascot.py, tests/shell/test_mascot_overlay.py

**Interfaces:**
- Consumes: `MascotModel`, `MascotState` from Task 27; `Game`, `SceneId`, `new_game` from
  `core/game.py`; `City.stompable_positions()`, `Wallet.fine(amount)`, `PsiModel.spike(amount)`,
  `Loadout` (`has`, `bait_charges`, `use_bait`, `add`), `VEHICLES`; constants `STOMP_FINE`,
  `STOMP_PSI_SPIKE`, `BAIT_PACK_SIZE`, `MASCOT_ALERT_WINDOW`, `PSI_MAX`; events `DeployBait`,
  `BaitDeployed`, `BuildingStomped(pos, fine)`, `MascotAlert`, `StompTriggered`; shell
  `CityMapScene`, `DrivingScene` (Task 22), `BustingScene` (Task 26), the `Scene` protocol from
  `shell/scenes/__init__.py`, `SpriteFactory`, `TextRenderer`; `DriveSim`, `BustSim` (test
  fixtures for the DRIVE/BUST draw smokes).
- Produces: `Game.mascot: MascotModel` populated and ticked; `DeployBait` command semantics;
  `BuildingStomped`/`BaitDeployed` emitted from `Game.tick` (the finale/polish milestones map
  them to sounds via `EVENT_SOUNDS`); private helper
  `_draw_mascot_banner(surface, game, text)` in `shell/scenes/__init__.py`, called by all three
  world scenes' `draw`.

- [ ] **Step 1: Write the failing stomp-integration tests**

Create `tests/core/test_game_mascot.py`:

```python
"""Game-level mascot integration: stomp fines, PSI spikes, event translation."""

import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import PSI_MAX, STOMP_FINE, STOMP_PSI_SPIKE
from psychic_cleaners.core.events import BuildingStomped, Event, MascotAlert, StompTriggered
from psychic_cleaners.core.game import Game, SceneId, new_game
from psychic_cleaners.core.loadout import Loadout


def _world_game(seed: int, *, sensor: bool, bait: bool) -> Game:
    """A Game dropped straight into MAP with a hot city, bypassing title/shop."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")  # keep the no-snares game-over rule out of these tests
    if sensor:
        game.loadout.add("sensor")
    if bait:
        game.loadout.add("bait")
    game.scene = SceneId.MAP
    game.psi.spike(5_000.0)
    return game


def _tick_until_stomp(game: Game) -> tuple[list[Event], int, int]:
    """Tick until BuildingStomped; return (that tick's events, psi before, balance before)."""
    for _ in range(2_000):
        psi_before = game.psi.value
        balance_before = game.wallet.balance
        events = game.tick([], 1.0)
        if any(isinstance(e, BuildingStomped) for e in events):
            return events, psi_before, balance_before
    pytest.fail("no stomp within 2000 simulated seconds")


def test_stomp_fines_wallet_spikes_psi_and_reports_position() -> None:
    game = _world_game(201, sensor=False, bait=False)
    events, psi_before, balance_before = _tick_until_stomp(game)
    stomp = next(e for e in events if isinstance(e, BuildingStomped))
    assert stomp.fine == STOMP_FINE  # bankroll started at 10,000 so the full fine is charged
    assert game.wallet.balance == balance_before - STOMP_FINE
    assert stomp.pos in game.city.stompable_positions()
    # growth only adds on top of the spike, so >= holds; min() handles the 9,999 clamp
    assert game.psi.value >= min(PSI_MAX, psi_before + STOMP_PSI_SPIKE)
    # the internal trigger event must be translated away, not surfaced to the shell
    assert not any(isinstance(e, StompTriggered) for e in events)


def test_no_sensor_means_no_alert_but_stomps_still_happen() -> None:
    game = _world_game(202, sensor=False, bait=False)
    seen: list[Event] = []
    stomped = False
    for _ in range(2_000):
        events = game.tick([], 1.0)
        seen += events
        if any(isinstance(e, BuildingStomped) for e in events):
            stomped = True
            break
    assert stomped
    assert not any(isinstance(e, MascotAlert) for e in seen)
    assert not any(isinstance(e, StompTriggered) for e in seen)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_game_mascot.py -v`

Expected: FAIL — both tests end with `Failed: no stomp within 2000 simulated seconds` / a falsy
`stomped` assertion, because `Game.tick` never advances a mascot model yet. (If `game.py` does
not have the `mascot` field yet, that is still the failure you see — the tests only touch it
indirectly.)

- [ ] **Step 3: Implement the mascot wiring in core/game.py**

All edits are to `src/psychic_cleaners/core/game.py` (written in Milestones 2–7; adapt local
variable names to what is already there, everything else is exact):

3a. Ensure these imports are present (merge into the existing import lines for each module):

```python
from psychic_cleaners.core.constants import STOMP_FINE, STOMP_PSI_SPIKE
from psychic_cleaners.core.events import BuildingStomped, StompTriggered
from psychic_cleaners.core.giant import MascotModel
```

3b. Ensure the `Game` dataclass has the mascot field, declared between `city` and `scene` to
match the contract's field order (add it if a previous milestone has not already):

```python
    mascot: MascotModel = field(default_factory=MascotModel)
```

3c. `NewGame` and `Continue` both route through `Game._reset()`, and the Task 7 convention says
every task that adds a `Game` field extends `_reset()` in the same task. In `_reset()`, where
the other models are reinitialized (wallet, psi, city, ...), add:

```python
        self.mascot = MascotModel()
```

3d. Mascot ticking is part of world ticking (step 2 of the canonical `Game.tick` shape, after
the command-dispatch loop). The world-advance block for scenes MAP, DRIVE, and BUST exists from
Milestones 5–7 (clock.advance, psi.advance, city.tick). Immediately after the `city.tick(...)`
call in that block, append the mascot's raw events to the block's event-accumulator list (shown
here as `events`; adapt the local name):

```python
        has_sensor = self.loadout.has("sensor") if self.loadout is not None else False
        events.extend(self.mascot.tick(dt_seconds, self.psi.value, has_sensor, self.rng))
```

Because it sits inside the world-advance block, stomps keep firing while busting, as the
contract requires, and never fire in TITLE/SHOP/FINALE/GAME_OVER.

3e. `StompTriggered` is internal and must be translated in post-tick resolution (step 3 of the
canonical shape), not surfaced to the shell. Add this private method to `Game` (place it near
the other private tick helpers):

```python
    def _resolve_stomps(self, events: list[Event]) -> list[Event]:
        """Post-tick: translate internal StompTriggered into world consequences."""
        resolved: list[Event] = []
        for event in events:
            if isinstance(event, StompTriggered):
                pos = self.rng.choice(self.city.stompable_positions())
                fine = self.wallet.fine(STOMP_FINE)
                self.psi.spike(STOMP_PSI_SPIKE)
                resolved.append(BuildingStomped(pos, fine))
            else:
                resolved.append(event)
        return resolved
```

Then, in `Game.tick`, make this the FIRST action of the post-tick resolution block — before the
existing `WispReachedTower` handling and the one-shot `FinaleUnlocked` check (adapt `events` to
the accumulator's local name):

```python
        events = self._resolve_stomps(events)
```

Ordering it first means a stomp's `psi.spike` lands before the one-shot `FinaleUnlocked` check,
so a stomp that pins PSI at max unlocks the finale on the same tick.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_game_mascot.py -v`

Expected: PASS — 2 passed.

- [ ] **Step 5: Add the failing bait-command tests**

In `tests/core/test_game_mascot.py`, replace the import block at the top of the file with:

```python
import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import (
    BAIT_PACK_SIZE,
    MASCOT_ALERT_WINDOW,
    PSI_MAX,
    STOMP_FINE,
    STOMP_PSI_SPIKE,
)
from psychic_cleaners.core.events import (
    BaitDeployed,
    BuildingStomped,
    DeployBait,
    Event,
    MascotAlert,
    StompTriggered,
)
from psychic_cleaners.core.game import Game, SceneId, new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.core.pk import PsiModel
```

then append these helpers and tests:

```python
def _tick_until_alert(game: Game) -> None:
    for _ in range(2_000):
        if any(isinstance(e, MascotAlert) for e in game.tick([], 1.0)):
            return
    pytest.fail("no mascot alert within 2000 simulated seconds")


def _quiet_tick(game: Game, dt: float) -> list[Event]:
    """Tick with psi pinned to zero so no NEW mascot trigger can fire during the window."""
    game.psi = PsiModel()
    return game.tick([], dt)


def test_bait_is_consumed_and_averts_the_stomp() -> None:
    game = _world_game(203, sensor=True, bait=True)
    _tick_until_alert(game)
    assert game.mascot.state is MascotState.ALERT
    game.psi = PsiModel()
    events = game.tick([DeployBait()], 0.1)
    assert any(isinstance(e, BaitDeployed) for e in events)
    assert game.loadout is not None
    assert game.loadout.bait_charges == BAIT_PACK_SIZE - 1
    assert game.mascot.state is MascotState.CALM
    seen: list[Event] = []
    for _ in range(int(MASCOT_ALERT_WINDOW) + 5):
        seen += _quiet_tick(game, 1.0)
    assert not any(isinstance(e, BuildingStomped | StompTriggered) for e in seen)


def test_without_deploy_the_alert_expires_into_a_stomp() -> None:
    # contrast case proving the previous test's aversion is real
    game = _world_game(203, sensor=True, bait=True)
    _tick_until_alert(game)
    seen: list[Event] = []
    for _ in range(int(MASCOT_ALERT_WINDOW) + 5):
        seen += _quiet_tick(game, 1.0)
    assert any(isinstance(e, BuildingStomped) for e in seen)
    assert game.mascot.state is MascotState.CALM


def test_deploy_bait_without_charges_is_ignored() -> None:
    game = _world_game(204, sensor=True, bait=False)
    _tick_until_alert(game)
    events = game.tick([DeployBait()], 0.1)
    assert not any(isinstance(e, BaitDeployed) for e in events)
    # charges are checked FIRST, so the press must NOT cancel the alert
    assert game.mascot.state is MascotState.ALERT
```

- [ ] **Step 6: Run the new tests to verify they fail**

Run: `uv run pytest tests/core/test_game_mascot.py -v -k "bait or expires"`

Expected: `test_without_deploy_the_alert_expires_into_a_stomp` PASSES (expiry was wired in
Step 3); `test_bait_is_consumed_and_averts_the_stomp` FAILS on
`assert any(isinstance(e, BaitDeployed) ...)` and `test_deploy_bait_without_charges_is_ignored`
FAILS only if `Game.tick` raises on the unknown command — otherwise it passes vacuously. Net:
at least 1 failed.

- [ ] **Step 7: Implement the DeployBait command**

In `src/psychic_cleaners/core/game.py`:

7a. Extend the events import from 3a with the two command/event names:

```python
from psychic_cleaners.core.events import BaitDeployed, BuildingStomped, DeployBait, StompTriggered
```

7b. Add this private method to `Game` next to `_resolve_stomps`:

```python
    def _handle_deploy_bait(self) -> list[Event]:
        """Charges are checked FIRST so a chargeless press never cancels the alert."""
        if self.loadout is None or self.loadout.bait_charges <= 0:
            return []
        if self.mascot.deploy_bait() and self.loadout.use_bait():
            return [BaitDeployed()]
        return []
```

7c. In `Game.tick`'s command dispatch, handle `DeployBait` in any world scene. If dispatch is a
single loop over commands, add this branch (adapting `command`/`events` to the local names); if
dispatch is per-scene, add the same two lines to each of the MAP, DRIVE, and BUST handlers:

```python
            world_scenes = (SceneId.MAP, SceneId.DRIVE, SceneId.BUST)
            if isinstance(command, DeployBait) and self.scene in world_scenes:
                events.extend(self._handle_deploy_bait())
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_game_mascot.py -v`

Expected: PASS — 5 passed.

- [ ] **Step 9: Write the failing shell tests (overlay + B key in all three world scenes)**

Create `tests/shell/test_mascot_overlay.py` (tests/conftest.py already exports
`SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`):

```python
"""World-scene mascot overlay: flashing banner and B-key bait mapping in MAP, DRIVE, BUST."""

from collections.abc import Callable, Iterator

import pygame
import pytest

from psychic_cleaners.core.bust import BustSim
from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.drive import DriveSim
from psychic_cleaners.core.events import DeployBait
from psychic_cleaners.core.game import Game, SceneId, new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import Scene, _draw_mascot_banner
from psychic_cleaners.shell.scenes.busting import BustingScene
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.scenes.driving import DrivingScene
from psychic_cleaners.shell.text import TextRenderer


@pytest.fixture(autouse=True)
def _pygame() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((640, 400))
    yield
    pygame.quit()


WORLD_SCENES: list[tuple[SceneId, Callable[[], Scene]]] = [
    (SceneId.MAP, CityMapScene),
    (SceneId.DRIVE, DrivingScene),
    (SceneId.BUST, BustingScene),
]


def _world_game(scene_id: SceneId) -> Game:
    """A Game dropped into the given world scene with the state its scene draws from."""
    game = new_game(301)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("bait")
    game.scene = scene_id
    if scene_id is SceneId.DRIVE:
        game.drive = DriveSim(
            distance_total=800.0, speed=140.0, has_vacuum=False, has_lens=False
        )
    elif scene_id is SceneId.BUST:
        game.bust = BustSim()
    return game


@pytest.mark.parametrize(("scene_id", "make_scene"), WORLD_SCENES)
def test_b_key_maps_to_deploy_bait(scene_id: SceneId, make_scene: Callable[[], Scene]) -> None:
    scene = make_scene()
    key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
    commands = scene.commands([key_event], _world_game(scene_id))
    assert any(isinstance(c, DeployBait) for c in commands)


@pytest.mark.parametrize(("scene_id", "make_scene"), WORLD_SCENES)
def test_alert_overlay_full_scene_draw_smoke(
    scene_id: SceneId, make_scene: Callable[[], Scene]
) -> None:
    scene = make_scene()
    game = _world_game(scene_id)
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = 10.0
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())  # must not raise


def test_banner_visible_only_in_alert_and_flash_on_phase() -> None:
    text = TextRenderer()
    game = _world_game(SceneId.MAP)

    def banner_bytes() -> bytes:
        surface = pygame.Surface((640, 400))
        surface.fill((0, 0, 0))
        _draw_mascot_banner(surface, game, text)
        return pygame.image.tobytes(surface, "RGB")

    blank = banner_bytes()  # CALM: helper draws nothing
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = 10.0  # int(20.0) % 2 == 0 -> visible phase
    visible = banner_bytes()
    game.mascot.alert_remaining = 9.5  # int(19.0) % 2 == 1 -> hidden phase
    hidden = banner_bytes()
    assert visible != blank
    assert hidden == blank
```

- [ ] **Step 10: Run shell tests to verify they fail**

Run: `uv run pytest tests/shell/test_mascot_overlay.py -v`

Expected: FAIL — collection error:
`ImportError: cannot import name '_draw_mascot_banner' from 'psychic_cleaners.shell.scenes'`
(the shared helper does not exist yet).

- [ ] **Step 11: Implement the shared banner and the B-key mapping in all three world scenes**

11a. In `src/psychic_cleaners/shell/scenes/__init__.py` (holds the `Scene` protocol), ensure
these imports are present (`pygame`, `Game`, and `TextRenderer` are already imported for the
protocol — merge, don't duplicate):

```python
import pygame

from psychic_cleaners.core.game import Game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.shell.text import TextRenderer
```

then add this module-level helper below the `Scene` protocol — the single banner implementation
shared by all three world scenes:

```python
def _draw_mascot_banner(surface: pygame.Surface, game: Game, text: TextRenderer) -> None:
    """Flashing mascot-alert banner; draws nothing unless the mascot is in ALERT."""
    if game.mascot.state is not MascotState.ALERT:
        return
    if int(game.mascot.alert_remaining * 2) % 2 != 0:
        return  # off phase of the flash
    charges = game.loadout.bait_charges if game.loadout is not None else 0
    banner = f"MASCOT INBOUND — B: BAIT ({charges} left)"
    text.draw(surface, banner, (150, 8), size=20, color=(255, 96, 96))
```

11b. In `src/psychic_cleaners/shell/scenes/city_map.py` (written in Milestone 5; adapt local
variable names, everything else is exact), ensure these imports are present (merge `DeployBait`
into the existing `core.events` import line):

```python
from psychic_cleaners.core.events import DeployBait
from psychic_cleaners.shell.scenes import _draw_mascot_banner
```

Add the banner call as the LAST statement of `CityMapScene.draw`, so it overlays the map and
HUD:

```python
        _draw_mascot_banner(surface, game, text)
```

And in `CityMapScene.commands`, inside the existing loop over pygame events, add this branch
alongside the existing `KEYDOWN` mappings (rename `event` and `commands` to match the method's
local loop variable and result list):

```python
            if event.type == pygame.KEYDOWN and event.key == pygame.K_b:
                commands.append(DeployBait())
```

11c. Make the SAME three edits to `src/psychic_cleaners/shell/scenes/driving.py` (Task 22): the
two imports, `_draw_mascot_banner(surface, game, text)` as the LAST statement of
`DrivingScene.draw`, and the B-key branch inside the existing event loop of
`DrivingScene.commands`, alongside the `Steer` mappings.

11d. Make the SAME three edits to `src/psychic_cleaners/shell/scenes/busting.py` (Task 26): the
two imports, `_draw_mascot_banner(surface, game, text)` as the LAST statement of
`BustingScene.draw`, and the B-key branch inside the existing event loop of
`BustingScene.commands`, alongside the cleaner/snare key mappings.

- [ ] **Step 12: Run shell tests to verify they pass**

Run: `uv run pytest tests/shell/test_mascot_overlay.py -v`

Expected: PASS — 7 passed (3 B-key tests, 3 draw smokes, 1 flash-phase test).

- [ ] **Step 13: Run the full suite and quality gates**

Run: `uv run pytest -v`

Expected: PASS — every test in tests/core, tests/integration, and tests/shell passes (earlier
milestones' suites must not regress).

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`

Expected: clean — `All checks passed!`, no files reformatted, `Success: no issues found`.

- [ ] **Step 14: Commit**

```bash
git add src/psychic_cleaners/core/game.py src/psychic_cleaners/shell/scenes/__init__.py \
    src/psychic_cleaners/shell/scenes/city_map.py src/psychic_cleaners/shell/scenes/driving.py \
    src/psychic_cleaners/shell/scenes/busting.py \
    tests/core/test_game_mascot.py tests/shell/test_mascot_overlay.py
git commit -m "feat: wire mascot events into game with world-scene alert overlay and bait key"
```

---

## Milestone 9: Finale & endgame — Tower run, win/lose, account carry-over

Goal: implement the endgame — the deterministic door-run simulation in front of Threshold
Tower (`core/finale.py`), the `Game` wiring that routes a Tower arrival into it and resolves
win/lose with account-code issuance, and the two closing scenes (`FinaleScene`,
`GameOverScene`). When this milestone lands, a complete game is playable from title to the
Tower door run, ending on a WON screen showing a reusable account code or a LOST screen
showing the reason, with Enter returning to a fresh title screen.

### Task 29: Finale simulation (`core/finale.py`)

**Files:**
- Create: `src/psychic_cleaners/core/finale.py`
- Test: `tests/core/test_finale.py`

**Interfaces:**
- Consumes (from the contract, all existing by Milestone 2):
  - `core/constants.py`: `DOOR_X = 560.0`, `GIANT_MIN_X = 180.0`, `GIANT_MAX_X = 460.0`,
    `GIANT_SPEED = 220.0`, `GIANT_HOP_PERIOD = 1.2`, `GIANT_AIR_FRACTION = 0.6`,
    `RUNNER_START_X = 40.0`, `RUNNER_SPEED = 260.0`, `SQUASH_RANGE = 36.0`,
    `FINALE_NEEDED_INSIDE = 2`
  - `core/events.py`: `Event`, `RunnerEntered(total_inside: int)`, `RunnerSquashed()`
- Produces (Task 30 and Task 31 rely on these exact names):
  - `class FinaleOutcome(enum.Enum)` with members `WON`, `LOST`
  - `@dataclass class FinaleSim` with fields `able_cleaners: int`,
    `giant_x: float = GIANT_MIN_X`, `giant_dir: int = 1`, `hop_time: float = 0.0`,
    `runner_x: float | None = None`, `inside: int = 0`, `squashed: int = 0`;
    methods `start_run() -> None`, `tick(dt_seconds: float) -> list[Event]`;
    properties `remaining_outside: int`, `airborne: bool`, `outcome: FinaleOutcome | None`

The sim is pure and takes NO rng: identical inputs replay identically. The giant is a
triangle wave: `giant_x` moves at `GIANT_SPEED` in direction `giant_dir` and reflects off
`GIANT_MIN_X`/`GIANT_MAX_X` (flipping `giant_dir`), handling multiple bounces in one large
`dt`. All the numbers in the tests below were computed from the constants and verified:
trust them exactly.

Why the hop exists (do not remove it): the runner starts behind the giant's patrol zone
(40 < 180) and the door lies beyond it (560 > 460), so the runner's and giant's paths MUST
cross at some instant (intermediate value theorem) — with a distance-only squash rule the
finale is unwinnable at ANY runner speed. The giant therefore hops on a fixed cycle
(`GIANT_HOP_PERIOD = 1.2` s, airborne for the first `GIANT_AIR_FRACTION = 0.6` of each
cycle, i.e. airborne 0.72 s then grounded 0.48 s) and squashes only while GROUNDED. The
player's skill is timing the run so the crossing happens under an airborne giant. At the
crossing the closing speed is 480 px/s, so the |gap| < 36 window lasts 72/480 = 0.15 s —
comfortably inside one airborne window, and also fully coverable by one grounded window.

- [ ] **Step 1: Write the failing tests for the giant's triangle wave and `start_run`**

Create `tests/core/test_finale.py`:

```python
"""Unit tests for the finale door-run simulation. Pure and rng-free: no fixtures."""

from __future__ import annotations

from psychic_cleaners.core.constants import GIANT_MIN_X, RUNNER_START_X
from psychic_cleaners.core.finale import FinaleSim


def test_giant_advances_at_giant_speed() -> None:
    sim = FinaleSim(able_cleaners=3)
    assert sim.giant_x == GIANT_MIN_X
    assert sim.giant_dir == 1
    assert sim.tick(0.5) == []
    assert sim.giant_x == 290.0  # 180 + 220 * 0.5
    assert sim.giant_dir == 1


def test_giant_reflects_at_max_bound() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.tick(2.0)  # raw 180 + 440 = 620 -> reflects off 460 to 300, now heading left
    assert sim.giant_x == 300.0
    assert sim.giant_dir == -1


def test_giant_reflects_at_min_bound() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.giant_x = 200.0
    sim.giant_dir = -1
    sim.tick(0.5)  # raw 200 - 110 = 90 -> reflects off 180 to 270, now heading right
    assert sim.giant_x == 270.0
    assert sim.giant_dir == 1


def test_start_run_launches_from_start_x() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    assert sim.runner_x == RUNNER_START_X


def test_start_run_ignored_when_nobody_left_outside() -> None:
    sim = FinaleSim(able_cleaners=2, inside=1, squashed=1)
    assert sim.remaining_outside == 0
    sim.start_run()
    assert sim.runner_x is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/core/test_finale.py -v`
Expected: collection ERROR — `ModuleNotFoundError: No module named 'psychic_cleaners.core.finale'`

- [ ] **Step 3: Write the minimal implementation (giant motion + run launching)**

Create `src/psychic_cleaners/core/finale.py`:

```python
"""Finale door-run simulation: triangle-wave giant, runners, the 2-of-3 rule.

Pure and deterministic — no rng, no clock. The shell/Game decide when to tick.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    GIANT_MAX_X,
    GIANT_MIN_X,
    GIANT_SPEED,
    RUNNER_START_X,
)
from psychic_cleaners.core.events import Event


class FinaleOutcome(enum.Enum):
    WON = enum.auto()
    LOST = enum.auto()


@dataclass
class FinaleSim:
    able_cleaners: int
    giant_x: float = GIANT_MIN_X
    giant_dir: int = 1
    runner_x: float | None = None
    inside: int = 0
    squashed: int = 0

    @property
    def remaining_outside(self) -> int:
        return self.able_cleaners - self.inside - self.squashed

    def start_run(self) -> None:
        if self.runner_x is None and self.remaining_outside > 0:
            self.runner_x = RUNNER_START_X

    def tick(self, dt_seconds: float) -> list[Event]:
        self._advance_giant(dt_seconds)
        return []

    def _advance_giant(self, dt_seconds: float) -> None:
        self.giant_x += self.giant_dir * GIANT_SPEED * dt_seconds
        while self.giant_x > GIANT_MAX_X or self.giant_x < GIANT_MIN_X:
            if self.giant_x > GIANT_MAX_X:
                self.giant_x = 2 * GIANT_MAX_X - self.giant_x
                self.giant_dir = -1
            else:
                self.giant_x = 2 * GIANT_MIN_X - self.giant_x
                self.giant_dir = 1
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_finale.py -v`
Expected: `5 passed`

- [ ] **Step 5: Write the failing tests for the runner, squash, door entry and outcome**

Replace the import block at the top of `tests/core/test_finale.py` with:

```python
from psychic_cleaners.core.constants import (
    DOOR_X,
    FINALE_NEEDED_INSIDE,
    GIANT_AIR_FRACTION,
    GIANT_HOP_PERIOD,
    GIANT_MIN_X,
    RUNNER_START_X,
)
from psychic_cleaners.core.events import Event, RunnerEntered, RunnerSquashed
from psychic_cleaners.core.finale import FinaleOutcome, FinaleSim
```

then append these tests to the file:

```python
def test_start_run_ignored_while_runner_active() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    sim.tick(0.05)  # runner advances to 40 + 260 * 0.05 = 53; giant at 191, far away
    sim.start_run()  # must NOT reset the active runner back to the start
    assert sim.runner_x == 53.0


def test_hop_cycle_airborne_windows() -> None:
    sim = FinaleSim(able_cleaners=3)
    assert sim.airborne  # each cycle starts airborne
    sim.hop_time = GIANT_HOP_PERIOD * GIANT_AIR_FRACTION  # 0.72: first grounded instant
    assert not sim.airborne
    sim.hop_time = GIANT_HOP_PERIOD - 1e-9  # end of the grounded window
    assert not sim.airborne
    sim.hop_time = GIANT_HOP_PERIOD  # wraps into the next cycle
    assert sim.airborne


def test_airborne_giant_does_not_squash() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    sim.runner_x = sim.giant_x  # directly underneath the giant
    assert sim.airborne  # fresh cycle: he is in the air
    assert sim.tick(1 / 600) == []  # passes under safely
    assert sim.squashed == 0


def test_runner_dodges_airborne_giant_and_enters() -> None:
    # Honest 60 fps run from the fresh phase (giant at 180 heading right,
    # hop_time 0). Closed forms: runner r(t) = 40 + 260t reaches the door at
    # t = 2.0; the giant turns at 460 at t ~ 1.273, after which the gap
    # closes at 480 px/s and |gap| < 36 only during t in (1.383, 1.533) —
    # entirely inside the second airborne window [1.2, 1.92). The only
    # grounded windows before the door, [0.72, 1.2) and [1.92, 2.0], have
    # gaps > 90 px. The runner is never squashed and enters at tick ~120.
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    events: list[Event] = []
    ticks = 0
    while not events and ticks < 150:
        events = sim.tick(1 / 60)
        ticks += 1
    assert events == [RunnerEntered(1)]
    assert 115 <= ticks <= 125  # door at t = 520 / 260 = 2.0 s
    assert sim.inside == 1
    assert sim.squashed == 0
    assert sim.runner_x is None


def test_runner_into_grounded_giant_is_squashed() -> None:
    # Pre-tick one full hop cycle (1.2 s) before launching: the crossing then
    # falls at t in (2.033, 2.183) — inside the grounded window [1.92, 2.4).
    # Closed forms: r(t) = 260t - 272; giant (post-turn) g(t) = 740 - 220t;
    # gap = 480t - 1012 hits +/-36 at t = 2.033 / 2.183. The giant lands on
    # the runner at the first sampled grounded instant with |gap| < 36.
    sim = FinaleSim(able_cleaners=3)
    for _ in range(72):  # 72 ticks of 1/60 s = 1.2 s
        sim.tick(1 / 60)
    sim.start_run()
    events: list[Event] = []
    ticks = 0
    while not events and ticks < 150:
        events = sim.tick(1 / 60)
        ticks += 1
    assert events == [RunnerSquashed()]
    assert sim.squashed == 1
    assert sim.inside == 0
    assert sim.runner_x is None


def test_outcome_is_none_at_start() -> None:
    assert FinaleSim(able_cleaners=3).outcome is None


def test_outcome_won_at_needed_inside() -> None:
    sim = FinaleSim(able_cleaners=3, inside=FINALE_NEEDED_INSIDE)
    assert sim.outcome is FinaleOutcome.WON


def test_two_able_both_squashed_is_lost() -> None:
    sim = FinaleSim(able_cleaners=2)
    for _ in range(2):
        sim.start_run()
        sim.runner_x = sim.giant_x  # park the runner under the giant...
        sim.hop_time = GIANT_HOP_PERIOD * GIANT_AIR_FRACTION  # ...at a grounded instant
        assert sim.tick(1 / 600) == [RunnerSquashed()]
    assert sim.squashed == 2
    assert sim.inside == 0
    assert sim.outcome is FinaleOutcome.LOST


def test_three_able_one_squashed_two_entered_is_won() -> None:
    sim = FinaleSim(able_cleaners=3)
    sim.start_run()
    sim.runner_x = sim.giant_x  # forced squash: grounded giant, runner underneath
    sim.hop_time = GIANT_HOP_PERIOD * GIANT_AIR_FRACTION
    assert sim.tick(1 / 600) == [RunnerSquashed()]
    assert sim.outcome is None  # two able cleaners left: still winnable
    for expected_inside in (1, 2):
        sim.start_run()
        assert sim.runner_x == RUNNER_START_X
        sim.runner_x = DOOR_X - 1.0  # one step from the door
        sim.hop_time = 0.0  # airborne, and the giant is far away regardless
        assert sim.tick(1 / 60) == [RunnerEntered(expected_inside)]
    assert sim.inside == 2
    assert sim.outcome is FinaleOutcome.WON
```

- [ ] **Step 6: Run the tests to verify the new ones fail**

Run: `uv run pytest tests/core/test_finale.py -v`
Expected: 9 FAILED, 5 passed — e.g. `test_start_run_ignored_while_runner_active` fails with
`assert 40.0 == 53.0` (runner never advances), `test_hop_cycle_airborne_windows` with
`AttributeError: 'FinaleSim' object has no attribute 'hop_time'`,
`test_runner_dodges_airborne_giant_and_enters` with `assert [] == [RunnerEntered(...)]`,
and the outcome tests with `AttributeError: 'FinaleSim' object has no attribute 'outcome'`.

- [ ] **Step 7: Implement the runner and the outcome property**

Replace `src/psychic_cleaners/core/finale.py` in full with:

```python
"""Finale door-run simulation: triangle-wave giant, runners, the 2-of-3 rule.

Pure and deterministic — no rng, no clock. The shell/Game decide when to tick.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    DOOR_X,
    FINALE_NEEDED_INSIDE,
    GIANT_AIR_FRACTION,
    GIANT_HOP_PERIOD,
    GIANT_MAX_X,
    GIANT_MIN_X,
    GIANT_SPEED,
    RUNNER_SPEED,
    RUNNER_START_X,
    SQUASH_RANGE,
)
from psychic_cleaners.core.events import Event, RunnerEntered, RunnerSquashed


class FinaleOutcome(enum.Enum):
    WON = enum.auto()
    LOST = enum.auto()


@dataclass
class FinaleSim:
    able_cleaners: int
    giant_x: float = GIANT_MIN_X
    giant_dir: int = 1
    hop_time: float = 0.0
    runner_x: float | None = None
    inside: int = 0
    squashed: int = 0

    @property
    def remaining_outside(self) -> int:
        return self.able_cleaners - self.inside - self.squashed

    @property
    def airborne(self) -> bool:
        # The giant hops continuously: airborne for the first GIANT_AIR_FRACTION
        # of each GIANT_HOP_PERIOD cycle. Runners pass safely UNDER him while he
        # is up — without this the finale is unwinnable (the runner's and the
        # giant's paths must cross; see the milestone intro).
        return (self.hop_time % GIANT_HOP_PERIOD) < GIANT_HOP_PERIOD * GIANT_AIR_FRACTION

    def start_run(self) -> None:
        if self.runner_x is None and self.remaining_outside > 0:
            self.runner_x = RUNNER_START_X

    def tick(self, dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        self.hop_time += dt_seconds
        self._advance_giant(dt_seconds)
        if self.runner_x is not None:
            self.runner_x += RUNNER_SPEED * dt_seconds
            if not self.airborne and abs(self.runner_x - self.giant_x) < SQUASH_RANGE:
                self.squashed += 1
                self.runner_x = None
                events.append(RunnerSquashed())
            elif self.runner_x >= DOOR_X:
                self.inside += 1
                self.runner_x = None
                events.append(RunnerEntered(self.inside))
        return events

    def _advance_giant(self, dt_seconds: float) -> None:
        self.giant_x += self.giant_dir * GIANT_SPEED * dt_seconds
        while self.giant_x > GIANT_MAX_X or self.giant_x < GIANT_MIN_X:
            if self.giant_x > GIANT_MAX_X:
                self.giant_x = 2 * GIANT_MAX_X - self.giant_x
                self.giant_dir = -1
            else:
                self.giant_x = 2 * GIANT_MIN_X - self.giant_x
                self.giant_dir = 1

    @property
    def outcome(self) -> FinaleOutcome | None:
        if self.inside >= FINALE_NEEDED_INSIDE:
            return FinaleOutcome.WON
        active = 1 if self.runner_x is not None else 0
        if self.inside + self.remaining_outside + active < FINALE_NEEDED_INSIDE:
            return FinaleOutcome.LOST
        return None
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_finale.py -v`
Expected: `14 passed`

- [ ] **Step 9: Run quality gates**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: all tests pass, ruff clean (format may rewrite nothing), mypy `Success: no issues found`

- [ ] **Step 10: Commit**

```bash
git add src/psychic_cleaners/core/finale.py tests/core/test_finale.py
git commit -m "feat: add deterministic finale door-run simulation"
```

### Task 30: Endgame wiring — tower routing, win/lose, account issuance

**Files:**
- Modify: `src/psychic_cleaners/core/game.py` (Tower arrival routing, FINALE scene branch,
  endgame resolution, account-code issuance)
- Test: `tests/core/test_game_finale.py` (new)
- Test: `tests/integration/test_full_game.py` (new — full win and full loss playthroughs)

**Interfaces:**
- Consumes:
  - `FinaleSim`, `FinaleOutcome` from Task 29
  - `encode_account(name: str, bankroll: int) -> str` / `decode_account(name: str, code: str) -> int`
    from `core/codec.py` (Milestone 4)
  - `Game` FSM plumbing from Milestones 2–8: `Game.tick(commands, dt_seconds)`, the arrival
    router from Task 25 (depot → tower → haunted → MAP order), `_world_scenes` (the
    world-advance gate covering MAP/DRIVE/BUST only), `able_cleaners()`, `free_snares()`,
    `finale_unlocked`, `starting_bankroll`, `player_name`, `result`
  - Events/commands: `StartRun`, `Continue`, `GameWon(account_code)`, `GameLost(reason)`,
    `SceneChanged(scene)`, `RunnerEntered`, `RunnerSquashed`, `FinaleUnlocked`
- Produces (Task 31 relies on):
  - `Game.finale: FinaleSim | None` populated on Tower arrival, cleared on resolution
  - endgame resolution behaviour: `result` set to `"won"`/`"lost"`, `GameWon`/`GameLost`
    emitted, scene `GAME_OVER`
  - the private hook `_tick_finale` (Task 31 edits it to record the account code / reason)

Winnability note: the giant's hop cycle (Task 29) is what makes the door run winnable —
squash applies only while he is grounded, so a well-timed launch crosses him mid-air. The
fresh finale phase (giant at `GIANT_MIN_X` heading right, `hop_time` 0) is a verified safe
launch; the full-game win test below re-aligns the giant before each run and uses sampled
strides whose gaps never enter the squash range at all, making it hop-phase-independent.

- [ ] **Step 1: Write the failing tests for Tower arrival routing**

Create `tests/core/test_game_finale.py`:

```python
"""Game-level finale wiring: tower routing, FINALE scene, endgame resolution."""

from __future__ import annotations

from psychic_cleaners.core.codec import decode_account
from psychic_cleaners.core.constants import RUNNER_START_X, TOWER_POS
from psychic_cleaners.core.events import (
    BuyItem,
    Event,
    FinishShopping,
    GameLost,
    GameWon,
    NewGame,
    RunnerEntered,
    RunnerSquashed,
    SceneChanged,
    SceneId,
    SelectVehicle,
    SetDestination,
    StartRun,
)
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import Game, new_game


def _game_at_tower(name: str = "Alex") -> Game:
    """A game parked on the Tower square with the finale unlocked, still in MAP."""
    game = new_game(1)
    game.tick([NewGame(name)], 0.0)
    game.tick([SelectVehicle("compact")], 0.0)
    game.tick([BuyItem("snare")], 0.0)  # keeps the bankruptcy rule out of play
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP
    game.finale_unlocked = True
    game.position = TOWER_POS
    return game


def test_tower_arrival_enters_finale_with_able_cleaners() -> None:
    game = _game_at_tower()
    events = game.tick([SetDestination(TOWER_POS)], 0.0)  # arrival on the spot
    assert game.scene is SceneId.FINALE
    assert isinstance(game.finale, FinaleSim)
    assert game.finale.able_cleaners == 3
    assert SceneChanged(SceneId.FINALE) in events


def test_tower_arrival_with_too_few_able_cleaners_loses() -> None:
    game = _game_at_tower()
    game.slimed.update({0, 1})  # only one able cleaner: cannot get two inside
    events = game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.GAME_OVER
    assert game.result == "lost"
    assert GameLost("not enough able cleaners") in events
    assert game.finale is None


def test_tower_arrival_without_unlock_stays_on_map() -> None:
    game = _game_at_tower()
    game.finale_unlocked = False
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.MAP
    assert game.finale is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: the first two tests FAIL — either `AttributeError: 'Game' object has no attribute
'finale'` (if Milestone 2 omitted the field) or `AssertionError: assert <SceneId.MAP> is
<SceneId.FINALE>` (Task 25's router currently falls through to MAP). The third test may
already pass — it pins the guard so this task cannot regress it.

- [ ] **Step 3: Implement Tower routing in `core/game.py`**

Three edits, all in `src/psychic_cleaners/core/game.py`:

1. Ensure these names are imported (merge into the existing import statements — most are
   already there from earlier milestones):

```python
from psychic_cleaners.core.codec import encode_account
from psychic_cleaners.core.constants import FINALE_NEEDED_INSIDE, TOWER_POS
from psychic_cleaners.core.events import (
    Event,
    GameLost,
    GameWon,
    SceneChanged,
    SceneId,
    StartRun,
)
from psychic_cleaners.core.finale import FinaleOutcome, FinaleSim
```

2. Ensure the `Game` dataclass has the contract field, placed with the other sim fields
   (`drive`, `bust`) — add it if Milestone 2 left it out:

```python
    finale: FinaleSim | None = None
```

3. Add this method to `Game`, and wire it into Task 21's `_arrive_at` if/elif chain as a
   new `elif` branch inserted between the depot branch and the haunted-building branch
   (ABOVE the chain's final `else`, which routes to MAP). The chain then reads:

```python
        if pos == DEPOT_POS:
            ...  # Task 19's depot services, unchanged
        elif pos == TOWER_POS and self.finale_unlocked:
            self._arrive_at_tower(events)
        elif ...:  # Task 25's haunted-building branch, unchanged
            ...
        else:
            ...  # MAP fallback, unchanged
        return events
```

```python
    def _arrive_at_tower(self, events: list[Event]) -> None:
        """Tower arrival with the finale unlocked: enter the door run or lose."""
        if self.able_cleaners() >= FINALE_NEEDED_INSIDE:
            self.finale = FinaleSim(able_cleaners=self.able_cleaners())
            self.scene = SceneId.FINALE
            events.append(SceneChanged(SceneId.FINALE))
        else:
            self.result = "lost"
            events.append(GameLost("not enough able cleaners"))
            self.scene = SceneId.GAME_OVER
            events.append(SceneChanged(SceneId.GAME_OVER))
```

Do NOT add `SceneId.FINALE` to `_world_scenes`: the world (clock, psi, city, mascot) stays
frozen during the door run.

The `else:` (immediate-loss) branch and its `"not enough able cleaners"` reason string go
beyond the shared contract, which routes every finale-unlocked Tower arrival to FINALE and
enumerates only three GameLost reasons — see the CONTRACT-NOTE at the end of this file.
The behaviour itself is required by spec section 4.7 ("entering the finale with fewer than
2 able cleaners loses immediately").

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: `3 passed`

- [ ] **Step 5: Write the failing tests for the FINALE scene branch and resolution**

Append to `tests/core/test_game_finale.py`:

```python
def _game_in_finale(name: str = "Alex") -> Game:
    game = _game_at_tower(name)
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.FINALE
    return game


def test_start_run_command_launches_runner() -> None:
    game = _game_in_finale()
    game.tick([StartRun()], 0.0)
    assert game.finale is not None
    assert game.finale.runner_x == RUNNER_START_X


def test_squashed_runner_does_not_slime_cleaners() -> None:
    game = _game_in_finale()
    # One full hop cycle before launching: the crossing then falls in the
    # giant's grounded window [1.92, 2.4) and the runner is squashed
    # (verified schedule — see tests/core/test_finale.py).
    game.tick([], 1.2)
    game.tick([StartRun()], 0.0)
    squashed = False
    for _ in range(100):
        if any(isinstance(e, RunnerSquashed) for e in game.tick([], 0.05)):
            squashed = True
            break
    assert squashed
    assert game.slimed == set()  # finale casualties are NOT game-level slime
    assert game.finale is not None
    assert game.finale.squashed == 1
    assert game.scene is SceneId.FINALE  # two able cleaners left: not over yet


def test_finale_win_with_profit_issues_account_code() -> None:
    game = _game_in_finale()
    game.wallet.earn(5_000)  # compact + snare cost 2_600, so balance 12_400 > 10_000
    assert game.finale is not None
    game.finale.inside = 1  # one cleaner already through the door
    game.tick([StartRun()], 0.0)
    events = game.tick([], 3.25)  # one long stride to the door; giant never sampled close
    assert RunnerEntered(2) in events
    won = [e for e in events if isinstance(e, GameWon)]
    assert len(won) == 1
    assert decode_account("Alex", won[0].account_code) == game.wallet.balance
    assert game.result == "won"
    assert game.scene is SceneId.GAME_OVER
    assert SceneChanged(SceneId.GAME_OVER) in events
    assert game.finale is None


def test_finale_win_without_profit_still_loses() -> None:
    game = _game_in_finale()  # balance 7_400 <= starting 10_000: no profit
    assert game.finale is not None
    game.finale.inside = 1
    game.tick([StartRun()], 0.0)
    events = game.tick([], 3.25)
    assert RunnerEntered(2) in events
    assert GameLost("the franchise never turned a profit") in events
    assert game.result == "lost"
    assert game.scene is SceneId.GAME_OVER
    assert game.finale is None


def test_finale_squash_below_needed_loses_the_city() -> None:
    game = _game_at_tower()
    game.slimed.add(2)  # exactly two able cleaners enter the finale
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.finale is not None and game.finale.able_cleaners == 2
    game.tick([], 1.2)  # one hop cycle: the crossing falls in a grounded window
    game.tick([StartRun()], 0.0)
    events: list[Event] = []
    for _ in range(100):
        evs = game.tick([], 0.05)
        events.extend(evs)
        if any(isinstance(e, RunnerSquashed) for e in evs):
            break
    # ONE squash suffices: inside 0 + remaining_outside 1 + active 0 = 1 < 2,
    # so _tick_finale resolves LOST on that same tick and clears the finale.
    assert sum(isinstance(e, RunnerSquashed) for e in events) == 1
    assert GameLost("the Tower claimed the city") in events
    assert game.result == "lost"
    assert game.scene is SceneId.GAME_OVER
    assert game.finale is None
```

- [ ] **Step 6: Run the tests to verify the new ones fail**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: the 5 new tests FAIL (first three from Step 1 still pass), e.g.
`test_start_run_command_launches_runner` with `assert None == 40.0` — the FINALE branch of
`Game.tick` does not exist yet, so `StartRun` is ignored and the sim never ticks.

- [ ] **Step 7: Implement the FINALE branch and endgame resolution in `core/game.py`**

Three edits in `src/psychic_cleaners/core/game.py`, slotting into the canonical tick
shape (Task 7: dispatch loop -> scene ticking -> post-tick resolution):

1. In `_dispatch` (the per-command handler), add the FINALE branch alongside the
   existing scene-gated branches:

```python
        elif self.scene is SceneId.FINALE:
            if isinstance(command, StartRun) and self.finale is not None:
                self.finale.start_run()
```

2. In `Game.tick`'s scene-ticking section (AFTER the dispatch loop), the scene value must
   be the one captured into a local `scene` variable at the TOP of the call — an arrival
   that switches to FINALE mid-tick must not also finale-tick in the same call. Add:

```python
        if scene is SceneId.FINALE:
            events.extend(self._tick_finale(dt_seconds))
```

   FINALE is NOT in `_world_scenes()`, so the world (clock, psi, city, mascot) stays
   frozen while this branch runs — only the door-run sim advances. Add this method:

```python
    def _tick_finale(self, dt_seconds: float) -> list[Event]:
        """FINALE scene ticking and resolution: the world is frozen."""
        events: list[Event] = []
        if self.finale is None:
            return events
        # RunnerSquashed passes through untouched: a squashed runner is a
        # finale-local casualty and must NOT be added to self.slimed.
        events.extend(self.finale.tick(dt_seconds))
        outcome = self.finale.outcome
        if outcome is FinaleOutcome.WON:
            if self.wallet.balance > self.starting_bankroll:
                self.result = "won"
                events.append(GameWon(encode_account(self.player_name, self.wallet.balance)))
            else:
                self.result = "lost"
                events.append(GameLost("the franchise never turned a profit"))
        elif outcome is FinaleOutcome.LOST:
            self.result = "lost"
            events.append(GameLost("the Tower claimed the city"))
        if outcome is not None:
            self.finale = None
            self.scene = SceneId.GAME_OVER
            events.append(SceneChanged(SceneId.GAME_OVER))
        return events
```

3. Extend `Game._reset()` (Task 7 convention: every field-adding task resets its field
   there) with:

```python
        self.finale = None
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: `8 passed`

- [ ] **Step 9: Write the full-game integration playthroughs**

Create `tests/integration/test_full_game.py`. The win test threads the giant's wave with a
verified deterministic schedule: realign the giant to `GIANT_MIN_X` with one closed-form
tick, launch, then step in 0.4 s ticks — the sampled runner positions are 144, 248, 352,
456, 560 against giant positions 268, 356, 444, 388, 300, so the sampled gaps are 124,
108, 92, 68 px (all > `SQUASH_RANGE` = 36, making the schedule hop-phase-independent) and
the fifth tick reaches the door.

```python
"""Scripted full-game playthroughs of core.game: one win, one loss. No pygame."""

from __future__ import annotations

import pytest

from psychic_cleaners.core.codec import decode_account
from psychic_cleaners.core.constants import (
    GIANT_MAX_X,
    GIANT_MIN_X,
    GIANT_SPEED,
    PSI_MAX,
    STARTING_BANKROLL,
    TOWER_POS,
)
from psychic_cleaners.core.events import (
    BuyItem,
    Continue,
    Event,
    FinaleUnlocked,
    FinishShopping,
    GameLost,
    GameWon,
    NewGame,
    RunnerEntered,
    RunnerSquashed,
    SceneId,
    SelectVehicle,
    SetDestination,
    StartRun,
)
from psychic_cleaners.core.game import Game, new_game


def _drive_until_arrival(game: Game, max_ticks: int = 1000) -> None:
    for _ in range(max_ticks):
        game.tick([], 0.1)
        if game.scene is not SceneId.DRIVE:
            return
    raise AssertionError("drive never arrived")


def _align_giant(game: Game) -> None:
    """One closed-form tick that parks the giant exactly on GIANT_MIN_X.

    It lands heading left, which the reflection turns into 'rising from the
    min bound' on the next tick — a reproducible phase for the run schedule.
    """
    sim = game.finale
    assert sim is not None
    if sim.giant_dir == -1:
        t = (sim.giant_x - GIANT_MIN_X) / GIANT_SPEED
    else:
        t = ((GIANT_MAX_X - sim.giant_x) + (GIANT_MAX_X - GIANT_MIN_X)) / GIANT_SPEED
    if t > 0:
        game.tick([], t)
    assert sim.giant_x == pytest.approx(GIANT_MIN_X)


def _run_one_cleaner_through(game: Game) -> list[Event]:
    """Verified dodge: from the aligned phase, launch at once and step 0.4 s.

    Sampled gaps stay >= 68 px (never inside SQUASH_RANGE, so the giant's
    hop phase is irrelevant); the 5th tick crosses DOOR_X.
    """
    _align_giant(game)
    events = list(game.tick([StartRun()], 0.0))
    for _ in range(9):
        evs = game.tick([], 0.4)
        events.extend(evs)
        if any(isinstance(e, RunnerEntered | RunnerSquashed) for e in evs):
            break
    assert not any(isinstance(e, RunnerSquashed) for e in events)
    assert any(isinstance(e, RunnerEntered) for e in events)
    return events


def test_full_win_playthrough() -> None:
    game = new_game(2026)
    game.tick([NewGame("Alex")], 0.0)
    assert game.scene is SceneId.SHOP

    # Test-level top-up: scripted busts would be the purist route, but the
    # profit rule only compares wallet.balance to starting_bankroll, and the
    # loadout below costs 14_500 against the 10_000 start. Headroom also
    # absorbs any seed-determined stomp fines during the drive.
    game.wallet.earn(60_000)

    for command in (
        SelectVehicle("hearse"),
        BuyItem("vacuum"),
        BuyItem("snare"),
        BuyItem("snare"),
        BuyItem("rig"),
    ):
        game.tick([command], 0.0)
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP

    game.psi.spike(PSI_MAX)
    events = game.tick([], 0.001)  # one world tick latches the unlock
    assert any(isinstance(e, FinaleUnlocked) for e in events)
    assert game.finale_unlocked

    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.scene is SceneId.DRIVE
    _drive_until_arrival(game)
    assert game.scene is SceneId.FINALE
    assert game.finale is not None and game.finale.able_cleaners == 3
    assert game.wallet.balance > game.starting_bankroll  # profit secured pre-run

    _run_one_cleaner_through(game)
    assert game.finale is not None and game.finale.inside == 1
    events = _run_one_cleaner_through(game)  # second entry resolves the game

    won = [e for e in events if isinstance(e, GameWon)]
    assert len(won) == 1
    assert game.result == "won"
    assert game.scene is SceneId.GAME_OVER
    assert decode_account("Alex", won[0].account_code) == game.wallet.balance
    assert game.wallet.balance > STARTING_BANKROLL


def test_full_loss_playthrough() -> None:
    game = new_game(7)
    game.tick([NewGame("Morgan")], 0.0)
    game.tick([SelectVehicle("compact")], 0.0)
    game.tick([BuyItem("snare")], 0.0)  # keeps the bankruptcy rule out of play
    game.tick([FinishShopping()], 0.0)
    assert game.scene is SceneId.MAP

    game.slimed.add(0)  # exactly two able cleaners will enter the finale
    game.psi.spike(PSI_MAX)
    game.tick([], 0.001)
    assert game.finale_unlocked

    game.tick([SetDestination(TOWER_POS)], 0.0)
    _drive_until_arrival(game)
    assert game.scene is SceneId.FINALE
    assert game.finale is not None and game.finale.able_cleaners == 2

    game.tick([], 1.2)  # one hop cycle: the crossing falls in a grounded window
    game.tick([StartRun()], 0.0)  # straight into the landing giant
    events: list[Event] = []
    for _ in range(100):
        evs = game.tick([], 0.05)
        events.extend(evs)
        if any(isinstance(e, RunnerSquashed) for e in evs):
            break
    # With two able cleaners the first squash already leaves
    # inside 0 + remaining_outside 1 + active 0 = 1 < FINALE_NEEDED_INSIDE,
    # so the game resolves LOST on that tick — only one runner ever falls.
    assert sum(isinstance(e, RunnerSquashed) for e in events) == 1
    lost = [e for e in events if isinstance(e, GameLost)]
    assert lost == [GameLost("the Tower claimed the city")]
    assert game.result == "lost"
    assert game.scene is SceneId.GAME_OVER

    game.tick([Continue()], 0.0)  # back to a fresh title screen
    assert game.scene is SceneId.TITLE
    assert game.result is None
    assert game.finale is None
    assert game.wallet.balance == STARTING_BANKROLL
```

- [ ] **Step 10: Run the integration tests**

Run: `uv run pytest tests/integration/test_full_game.py -v`
Expected: `2 passed` — no new implementation belongs to this step; these are acceptance
tests over the wiring from Steps 3/7 plus earlier milestones. If one fails, the failing
assertion pinpoints which contract behaviour is missing (e.g. `FinaleUnlocked` never
emitted means the MAP world tick from Task 25 skips the `psi.at_max` latch) — fix it in
`core/game.py` where that behaviour lives, not by weakening the test.

- [ ] **Step 11: Run quality gates**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: all tests pass, ruff clean, mypy `Success: no issues found`

- [ ] **Step 12: Commit**

```bash
git add src/psychic_cleaners/core/game.py tests/core/test_game_finale.py tests/integration/test_full_game.py
git commit -m "feat: wire finale routing, endgame resolution and account issuance"
```

### Task 31: Finale and game-over scenes

**Files:**
- Create: `src/psychic_cleaners/shell/scenes/finale.py`
- Create: `src/psychic_cleaners/shell/scenes/gameover.py`
- Modify: `src/psychic_cleaners/core/game.py` (add the contract fields
  `last_account_code` / `lose_reason`, record them at endgame resolution)
- Modify: `src/psychic_cleaners/shell/gfx.py` (add the `"mascot"` sprite builder, 48x64)
- Modify: `src/psychic_cleaners/shell/app.py` (point the `SCENES` registry entries for
  FINALE and GAME_OVER at the real scene classes)
- Test: `tests/shell/test_endgame_scenes.py` (new)
- Test: `tests/core/test_game_finale.py` (extend with field-recording tests)

**Interfaces:**
- Consumes: `FinaleSim` (Task 29); `Game.finale`, `Game.result` and `_tick_finale` /
  `_arrive_at_tower` (Task 30); `StartRun`, `Continue`, `SceneId`; the `Scene` protocol
  (`commands(events, game)` / `draw(surface, game, gfx, text)`), `SpriteFactory.get`,
  `TextRenderer.draw` from Milestone 1/2 shell tasks
- Produces: `FinaleScene`, `GameOverScene` (registered in `SCENES`); `Game.last_account_code:
  str | None` and `Game.lose_reason: str | None`; sprite name `"mascot"` (48x64)

- [ ] **Step 1: Write the failing tests for the new `Game` fields**

Append to `tests/core/test_game_finale.py` (all names used are already imported there):

```python
def test_win_records_last_account_code_field() -> None:
    game = _game_in_finale()
    game.wallet.earn(5_000)  # balance 12_400 > starting 10_000
    assert game.finale is not None
    game.finale.inside = 1
    game.tick([StartRun()], 0.0)
    game.tick([], 3.25)
    assert game.result == "won"
    assert game.last_account_code is not None
    assert decode_account("Alex", game.last_account_code) == game.wallet.balance
    assert game.lose_reason is None


def test_no_profit_records_lose_reason_field() -> None:
    game = _game_in_finale()  # balance 7_400: no profit
    assert game.finale is not None
    game.finale.inside = 1
    game.tick([StartRun()], 0.0)
    game.tick([], 3.25)
    assert game.result == "lost"
    assert game.lose_reason == "the franchise never turned a profit"
    assert game.last_account_code is None


def test_too_few_cleaners_records_lose_reason_field() -> None:
    game = _game_at_tower()
    game.slimed.update({0, 1})
    game.tick([SetDestination(TOWER_POS)], 0.0)
    assert game.result == "lost"
    assert game.lose_reason == "not enough able cleaners"


def test_squash_loss_records_lose_reason_field() -> None:
    game = _game_at_tower()
    game.slimed.add(2)  # two able cleaners: the first squash resolves LOST
    game.tick([SetDestination(TOWER_POS)], 0.0)
    game.tick([StartRun()], 0.0)
    for _ in range(100):
        if any(isinstance(e, RunnerSquashed) for e in game.tick([], 0.05)):
            break
    assert game.result == "lost"
    assert game.lose_reason == "the Tower claimed the city"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: the 4 new tests FAIL with
`AttributeError: 'Game' object has no attribute 'last_account_code'`
(the 8 tests from Task 30 still pass).

- [ ] **Step 3: Add the fields and record them in `core/game.py`**

1. Add two contract fields to the `Game` dataclass, directly after
   `result: str | None = None`, and extend `Game._reset()` (Task 7 convention) with their
   reinitialization:

```python
    # Set at endgame resolution so GameOverScene can render the outcome
    # without replaying events.
    last_account_code: str | None = None
    lose_reason: str | None = None
```

```python
        # in Game._reset():
        self.last_account_code = None
        self.lose_reason = None
```

2. In `_arrive_at_tower` (Task 30), replace the loss branch body so it also records the
   reason — the `else:` block becomes:

```python
        else:
            reason = "not enough able cleaners"
            self.result = "lost"
            self.lose_reason = reason
            events.append(GameLost(reason))
            self.scene = SceneId.GAME_OVER
            events.append(SceneChanged(SceneId.GAME_OVER))
```

3. In `_tick_finale` (Task 30), replace the resolution block (from `if outcome is
   FinaleOutcome.WON:` through the `elif`) with:

```python
        if outcome is FinaleOutcome.WON:
            if self.wallet.balance > self.starting_bankroll:
                code = encode_account(self.player_name, self.wallet.balance)
                self.result = "won"
                self.last_account_code = code
                events.append(GameWon(code))
            else:
                reason = "the franchise never turned a profit"
                self.result = "lost"
                self.lose_reason = reason
                events.append(GameLost(reason))
        elif outcome is FinaleOutcome.LOST:
            reason = "the Tower claimed the city"
            self.result = "lost"
            self.lose_reason = reason
            events.append(GameLost(reason))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: `12 passed`

- [ ] **Step 5: Write the failing test for the mascot sprite**

Create `tests/shell/test_endgame_scenes.py` (tests/conftest.py already exports
`SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` at import time):

```python
"""Key-mapping and draw-smoke tests for the finale and game-over scenes."""

from __future__ import annotations

from collections.abc import Iterator

import pygame
import pytest

from psychic_cleaners.shell.gfx import SpriteFactory


@pytest.fixture(autouse=True)
def _display() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((640, 400))
    yield
    pygame.quit()


@pytest.fixture
def surface() -> pygame.Surface:
    return pygame.Surface((640, 400))


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_mascot_sprite_is_48_by_64() -> None:
    assert SpriteFactory().get("mascot").get_size() == (48, 64)
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_endgame_scenes.py -v`
Expected: `test_mascot_sprite_is_48_by_64` FAILS — a `KeyError: 'mascot'` (or the
factory's equivalent unknown-sprite error) from `SpriteFactory.get`.

- [ ] **Step 7: Add the mascot builder to `shell/gfx.py`**

`shell/gfx.py` (Milestone 1, extended by each scene milestone) maps sprite names to
zero-argument builder functions that `SpriteFactory.get` calls once and caches. Add this
builder function to the module:

```python
def _build_mascot() -> pygame.Surface:
    """Sir Squish: a 48x64 pale-green gummy giant."""
    surface = pygame.Surface((48, 64), pygame.SRCALPHA)
    body = (150, 230, 160, 255)
    shade = (104, 186, 120, 255)
    ink = (30, 30, 40, 255)
    pygame.draw.ellipse(surface, body, pygame.Rect(4, 22, 40, 42))  # torso
    pygame.draw.ellipse(surface, shade, pygame.Rect(0, 30, 10, 18))  # left arm
    pygame.draw.ellipse(surface, shade, pygame.Rect(38, 30, 10, 18))  # right arm
    pygame.draw.ellipse(surface, shade, pygame.Rect(10, 54, 12, 10))  # left foot
    pygame.draw.ellipse(surface, shade, pygame.Rect(26, 54, 12, 10))  # right foot
    pygame.draw.circle(surface, body, (24, 16), 14)  # head
    pygame.draw.circle(surface, ink, (18, 14), 3)  # left eye
    pygame.draw.circle(surface, ink, (30, 14), 3)  # right eye
    pygame.draw.line(surface, ink, (18, 22), (30, 22), 2)  # grin
    return surface
```

and register it under the name `"mascot"` in the factory's name→builder registry, i.e. add
the entry `"mascot": _build_mascot,` to the registry dict. (If Milestone 1's factory
dispatches with an `if`/`elif` chain inside `get` instead of a dict, add the equivalent
branch returning `_build_mascot()` in that chain — the test pins the observable behaviour.)

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run pytest tests/shell/test_endgame_scenes.py -v`
Expected: `1 passed`

- [ ] **Step 9: Write the failing tests for `FinaleScene`**

Add these imports to `tests/shell/test_endgame_scenes.py` (merge into the import block):

```python
from psychic_cleaners.core.events import SceneId, StartRun
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.shell.scenes.finale import FinaleScene
from psychic_cleaners.shell.text import TextRenderer
```

then append:

```python
def test_finale_space_sends_start_run() -> None:
    game = new_game(1)
    assert FinaleScene().commands([_key(pygame.K_SPACE)], game) == [StartRun()]


def test_finale_ignores_other_keys() -> None:
    game = new_game(1)
    events = [_key(pygame.K_RETURN), pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE)]
    assert FinaleScene().commands(events, game) == []


def _finale_game() -> Game:
    game = new_game(1)
    game.scene = SceneId.FINALE
    game.finale = FinaleSim(able_cleaners=3)
    game.finale.start_run()
    return game


def test_finale_draw_smoke_with_active_runner(surface: pygame.Surface) -> None:
    FinaleScene().draw(surface, _finale_game(), SpriteFactory(), TextRenderer())


def test_finale_draw_smoke_without_runner(surface: pygame.Surface) -> None:
    game = _finale_game()
    assert game.finale is not None
    game.finale.runner_x = None
    FinaleScene().draw(surface, game, SpriteFactory(), TextRenderer())
```

- [ ] **Step 10: Run the tests to verify they fail**

Run: `uv run pytest tests/shell/test_endgame_scenes.py -v`
Expected: collection ERROR — `ModuleNotFoundError: No module named
'psychic_cleaners.shell.scenes.finale'`

- [ ] **Step 11: Implement `FinaleScene`**

Create `src/psychic_cleaners/shell/scenes/finale.py`:

```python
"""Finale scene: send cleaners past the bouncing mascot into the Tower door."""

from __future__ import annotations

from typing import Final

import pygame

from psychic_cleaners.core.constants import DOOR_X
from psychic_cleaners.core.events import Command, StartRun
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_GROUND_Y: Final[int] = 336
_SKY: Final[tuple[int, int, int]] = (18, 12, 44)
_GROUND: Final[tuple[int, int, int]] = (44, 40, 52)
_DOOR: Final[tuple[int, int, int]] = (94, 62, 30)


class FinaleScene:
    """The Tower door run: the giant bounces, cleaners dash for the door."""

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                out.append(StartRun())
        return out

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill(_SKY)
        pygame.draw.rect(
            surface,
            _GROUND,
            pygame.Rect(0, _GROUND_Y, surface.get_width(), surface.get_height() - _GROUND_Y),
        )
        tower = gfx.get("tower")
        surface.blit(tower, (int(DOOR_X) - tower.get_width() // 2, _GROUND_Y - tower.get_height()))
        pygame.draw.rect(surface, _DOOR, pygame.Rect(int(DOOR_X) - 12, _GROUND_Y - 48, 24, 48))
        sim = game.finale
        if sim is not None:
            mascot = gfx.get("mascot")
            hop = 28 if sim.airborne else 0  # readable hop: run under him while he's up
            surface.blit(
                mascot,
                (
                    int(sim.giant_x) - mascot.get_width() // 2,
                    _GROUND_Y - mascot.get_height() - hop,
                ),
            )
            if sim.runner_x is not None:
                runner = gfx.get("cleaner")
                surface.blit(
                    runner,
                    (int(sim.runner_x) - runner.get_width() // 2, _GROUND_Y - runner.get_height()),
                )
            text.draw(surface, f"INSIDE: {sim.inside}", (16, 12))
            text.draw(surface, f"SQUASHED: {sim.squashed}", (16, 32))
            text.draw(surface, f"REMAINING: {sim.remaining_outside}", (16, 52))
        text.draw(surface, "SPACE: send cleaner", (16, 380))
```

- [ ] **Step 12: Run the tests to verify they pass**

Run: `uv run pytest tests/shell/test_endgame_scenes.py -v`
Expected: `5 passed`

- [ ] **Step 13: Write the failing tests for `GameOverScene` and the registry**

Add these imports to `tests/shell/test_endgame_scenes.py` (merge into the import block):

```python
from psychic_cleaners.core.events import Continue
from psychic_cleaners.shell.scenes.gameover import GameOverScene
```

then append:

```python
def test_gameover_return_sends_continue() -> None:
    game = new_game(1)
    assert GameOverScene().commands([_key(pygame.K_RETURN)], game) == [Continue()]


def test_gameover_ignores_other_keys() -> None:
    game = new_game(1)
    assert GameOverScene().commands([_key(pygame.K_SPACE)], game) == []


def test_gameover_draw_smoke_won_with_code(surface: pygame.Surface) -> None:
    game = new_game(1)
    game.scene = SceneId.GAME_OVER
    game.result = "won"
    game.last_account_code = "ABCDEFG"
    GameOverScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_gameover_draw_smoke_lost_with_reason(surface: pygame.Surface) -> None:
    game = new_game(1)
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    game.lose_reason = "the Tower claimed the city"
    GameOverScene().draw(surface, game, SpriteFactory(), TextRenderer())


def test_scene_registry_uses_endgame_scenes() -> None:
    from psychic_cleaners.shell.app import SCENES

    assert isinstance(SCENES[SceneId.FINALE], FinaleScene)
    assert isinstance(SCENES[SceneId.GAME_OVER], GameOverScene)
```

- [ ] **Step 14: Run the tests to verify they fail**

Run: `uv run pytest tests/shell/test_endgame_scenes.py -v`
Expected: collection ERROR — `ModuleNotFoundError: No module named
'psychic_cleaners.shell.scenes.gameover'`

- [ ] **Step 15: Implement `GameOverScene` and update the `SCENES` registry**

Create `src/psychic_cleaners/shell/scenes/gameover.py`:

```python
"""Game-over scene: verdict, account code or loss reason, Enter back to title."""

from __future__ import annotations

from typing import Final

import pygame

from psychic_cleaners.core.events import Command, Continue
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_BG: Final[tuple[int, int, int]] = (12, 10, 18)
_WIN: Final[tuple[int, int, int]] = (240, 214, 90)
_LOSE: Final[tuple[int, int, int]] = (222, 84, 84)
_CODE: Final[tuple[int, int, int]] = (120, 240, 160)


class GameOverScene:
    """Shows WON/LOST, the new account code on a win, the reason on a loss."""

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                out.append(Continue())
        return out

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill(_BG)
        won = game.result == "won"
        text.draw(surface, "WON" if won else "LOST", (280, 100), size=48,
                  color=_WIN if won else _LOSE)
        if won and game.last_account_code is not None:
            text.draw(surface, "FRANCHISE APPROVED - YOUR NEW ACCOUNT CODE:", (150, 190))
            text.draw(surface, game.last_account_code, (270, 220), size=32, color=_CODE)
        elif game.lose_reason is not None:
            text.draw(surface, game.lose_reason, (190, 200))
        text.draw(surface, "Enter: title", (280, 340))
```

Then in `src/psychic_cleaners/shell/app.py`, add the imports:

```python
from psychic_cleaners.shell.scenes.finale import FinaleScene
from psychic_cleaners.shell.scenes.gameover import GameOverScene
```

and in the `SCENES` registry replace the FINALE and GAME_OVER entries (currently the
Milestone 2 stub scenes) with:

```python
    SceneId.FINALE: FinaleScene(),
    SceneId.GAME_OVER: GameOverScene(),
```

Remove the now-unused stub-scene imports for those two entries if nothing else uses them.

- [ ] **Step 16: Run the tests to verify they pass**

Run: `uv run pytest tests/shell/test_endgame_scenes.py -v`
Expected: `10 passed`

- [ ] **Step 17: Run quality gates**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: all tests pass, ruff clean, mypy `Success: no issues found`

- [ ] **Step 18: Commit**

```bash
git add src/psychic_cleaners/shell/scenes/finale.py src/psychic_cleaners/shell/scenes/gameover.py \
        src/psychic_cleaners/shell/gfx.py src/psychic_cleaners/shell/app.py \
        src/psychic_cleaners/core/game.py \
        tests/shell/test_endgame_scenes.py tests/core/test_game_finale.py
git commit -m "feat: add finale and game-over scenes with account-code display"
```

<!-- CONTRACT-NOTE: Task 30's _arrive_at_tower adds a fourth GameLost reason string
beyond the contract's enumerated three: "not enough able cleaners", for a
finale-unlocked Tower arrival with able_cleaners() < FINALE_NEEDED_INSIDE (mandated
by spec section 4.7: "entering the finale with fewer than 2 able cleaners loses
immediately"). -->

---

## Milestone 10: Audio & polish — tasks 32 to 35

Goal: give the game a voice and a face — synthesized SFX driven by core events, an original
chiptune theme with karaoke on the title screen, a deliberate final sprite set — then lock quality
in with a CI coverage gate, a README, and a final verification gauntlet. This milestone does not
change `core.Game` behaviour; when it lands, the same game is playable but every event has a
sound, the title screen sings, and every sprite looks intentional.

### Task 32: Synthesized audio and event-driven SFX

**Files:**
- Create: `src/psychic_cleaners/shell/audio.py` (new module — nothing exists at this path
  before this task; the code below is the complete module)
- Modify: `src/psychic_cleaners/shell/app.py` (add `EVENT_SOUNDS` and `self.audio` — both
  appear here for the first time; play sounds for events returned by `game.tick`)
- Test: `tests/shell/test_audio.py`

**Interfaces:**
- Consumes: `Event` subclasses from `psychic_cleaners.core.events` (`GhostTrapped`,
  `WispCaptured`, `BustMissed`, `BeamsCrossed`, `CleanerSlimed`, `BuildingStomped`,
  `MascotAlert`, `BaitDeployed`, `RunnerEntered`, `RunnerSquashed`, `GameWon`, `GameLost`,
  `ItemBought`, `PurchaseRejected`, `AccountRejected`); `App` from `shell/app.py` per contract
  (`step` gathers commands, calls `self.game.tick(commands, dt)`).
- Produces: `synth_square(freq: float, ms: int, volume: float = 0.5) -> bytes`,
  `synth_noise(ms: int, volume: float = 0.5) -> bytes`,
  `class AudioBank` with `__init__(enabled: bool = True)` and `play(name: str) -> None`,
  module constants `SAMPLE_RATE` and `_RECIPES` (private registry), and
  `EVENT_SOUNDS: Final[dict[type[Event], str]]` in `shell/app.py`. Task 33 extends this module.

- [ ] **Step 1: Write the failing synth/bank test**

Create `tests/shell/test_audio.py`:

```python
"""Synthesized audio: waveform shape, byte lengths, graceful no-ops."""

from psychic_cleaners.shell.audio import SAMPLE_RATE, AudioBank, synth_noise, synth_square


def _samples(raw: bytes) -> list[int]:
    return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)]


def test_square_byte_length() -> None:
    assert len(synth_square(440.0, 100)) == round(100 / 1000 * SAMPLE_RATE) * 2


def test_noise_byte_length_and_reproducible() -> None:
    assert len(synth_noise(50)) == round(50 / 1000 * SAMPLE_RATE) * 2
    assert synth_noise(50) == synth_noise(50)


def test_square_alternates_at_expected_period() -> None:
    # 2205 Hz at 22050 Hz sample rate -> half-period of exactly 5 samples.
    samples = _samples(synth_square(2205.0, 10))
    assert all(s > 0 for s in samples[0:5])
    assert all(s < 0 for s in samples[5:10])
    assert all(s > 0 for s in samples[10:15])


def test_disabled_bank_play_is_noop() -> None:
    bank = AudioBank(enabled=False)
    bank.play("trap")  # must not raise


def test_unknown_name_is_noop() -> None:
    bank = AudioBank(enabled=False)
    bank.play("definitely-not-a-sound")  # must not raise
    enabled_bank = AudioBank()
    enabled_bank.play("definitely-not-a-sound")  # must not raise even when mixer is live
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_audio.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psychic_cleaners.shell.audio'`
(this milestone introduces the module; earlier milestones do not touch audio).

- [ ] **Step 3: Write `shell/audio.py`**

Create `src/psychic_cleaners/shell/audio.py` with exactly:

```python
"""Synthesized sound effects. All audio is generated in code — no asset files."""

import random
from collections.abc import Callable
from typing import Final

import pygame

SAMPLE_RATE: Final[int] = 22050
_MAX_AMPLITUDE: Final[int] = 32767


def _sample_count(ms: int) -> int:
    return round(ms / 1000 * SAMPLE_RATE)


def synth_square(freq: float, ms: int, volume: float = 0.5) -> bytes:
    """Raw 16-bit signed little-endian mono square wave at SAMPLE_RATE."""
    amplitude = int(volume * _MAX_AMPLITUDE)
    out = bytearray()
    for i in range(_sample_count(ms)):
        high = int(i * 2.0 * freq / SAMPLE_RATE) % 2 == 0
        sample = amplitude if high else -amplitude
        out += sample.to_bytes(2, "little", signed=True)
    return bytes(out)


def synth_noise(ms: int, volume: float = 0.5) -> bytes:
    """Raw 16-bit signed little-endian mono white noise, seeded for reproducibility."""
    amplitude = int(volume * _MAX_AMPLITUDE)
    rng = random.Random(0)
    out = bytearray()
    for _ in range(_sample_count(ms)):
        out += rng.randint(-amplitude, amplitude).to_bytes(2, "little", signed=True)
    return bytes(out)


def _seq(*parts: bytes) -> bytes:
    return b"".join(parts)


_RECIPES: Final[dict[str, Callable[[], bytes]]] = {
    "catch": lambda: _seq(synth_square(660.0, 60), synth_square(880.0, 90)),
    "trap": lambda: _seq(
        synth_square(440.0, 60), synth_square(660.0, 60), synth_square(880.0, 120)
    ),
    "miss": lambda: _seq(synth_square(330.0, 80), synth_square(220.0, 140)),
    "backfire": lambda: _seq(synth_noise(120, 0.6), synth_square(110.0, 180)),
    "slime": lambda: _seq(
        synth_square(180.0, 60), synth_square(140.0, 60), synth_square(180.0, 80)
    ),
    "stomp": lambda: _seq(synth_noise(60, 0.8), synth_square(70.0, 200, 0.7)),
    "alert": lambda: _seq(
        synth_square(880.0, 70),
        synth_square(660.0, 70),
        synth_square(880.0, 70),
        synth_square(660.0, 70),
    ),
    "bait": lambda: _seq(synth_square(520.0, 50), synth_square(520.0, 50, 0.3)),
    "enter": lambda: _seq(synth_square(660.0, 50), synth_square(990.0, 90)),
    "squash": lambda: _seq(synth_noise(80, 0.7), synth_square(150.0, 130)),
    "win": lambda: _seq(
        synth_square(523.0, 90),
        synth_square(659.0, 90),
        synth_square(784.0, 90),
        synth_square(1046.0, 220),
    ),
    "lose": lambda: _seq(
        synth_square(392.0, 140), synth_square(330.0, 140), synth_square(262.0, 260)
    ),
    "buy": lambda: _seq(synth_square(988.0, 40), synth_square(1319.0, 70)),
    "reject": lambda: synth_square(160.0, 140, 0.6),
    "theme": lambda: synth_square(440.0, 300, 0.3),
}


class AudioBank:
    """Owns the mixer and all generated sounds; degrades to silence gracefully."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        if not enabled:
            return
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
        except pygame.error:
            return
        self._enabled = True
        for name, recipe in _RECIPES.items():
            self._sounds[name] = pygame.mixer.Sound(buffer=recipe())

    def play(self, name: str) -> None:
        sound = self._sounds.get(name)
        if sound is not None:
            sound.play()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/shell/test_audio.py -v`
Expected: PASS (5 tests). `tests/conftest.py` sets `SDL_AUDIODRIVER=dummy`, so the mixer
initializes headlessly and the enabled-bank path is exercised for real.

- [ ] **Step 5: Write the failing event-map test**

Append to `tests/shell/test_audio.py`:

```python
def test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe() -> None:
    from psychic_cleaners.core.events import (
        AccountRejected,
        BaitDeployed,
        BeamsCrossed,
        BuildingStomped,
        BustMissed,
        CleanerSlimed,
        Event,
        GameLost,
        GameWon,
        GhostTrapped,
        ItemBought,
        MascotAlert,
        PurchaseRejected,
        RunnerEntered,
        RunnerSquashed,
        WispCaptured,
    )
    from psychic_cleaners.shell.app import EVENT_SOUNDS
    from psychic_cleaners.shell.audio import _RECIPES

    # Subset assertions by design (per contract): each mapping below must be
    # PRESENT, but future additions to EVENT_SOUNDS must not break this test —
    # never assert exact dict equality here.
    expected: dict[type[Event], str] = {
        GhostTrapped: "trap",
        WispCaptured: "catch",
        BustMissed: "miss",
        BeamsCrossed: "backfire",
        CleanerSlimed: "slime",
        BuildingStomped: "stomp",
        MascotAlert: "alert",
        BaitDeployed: "bait",
        RunnerEntered: "enter",
        RunnerSquashed: "squash",
        GameWon: "win",
        GameLost: "lose",
        ItemBought: "buy",
        PurchaseRejected: "reject",
        AccountRejected: "reject",
    }
    for event_type, sound_name in expected.items():
        assert EVENT_SOUNDS.get(event_type) == sound_name, event_type
    assert set(EVENT_SOUNDS.values()) <= set(_RECIPES)
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_audio.py::test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe -v`
Expected: FAIL — `ImportError: cannot import name 'EVENT_SOUNDS' from 'psychic_cleaners.shell.app'`.

- [ ] **Step 7: Wire `EVENT_SOUNDS` and playback into `shell/app.py`**

Three edits to `src/psychic_cleaners/shell/app.py`:

1. Merge these names into the existing imports (ruff's isort will order them; the module
   already imports `Final` and core names — extend, do not duplicate):

```python
from psychic_cleaners.core.events import (
    AccountRejected,
    BaitDeployed,
    BeamsCrossed,
    BuildingStomped,
    BustMissed,
    CleanerSlimed,
    Event,
    GameLost,
    GameWon,
    GhostTrapped,
    ItemBought,
    MascotAlert,
    PurchaseRejected,
    RunnerEntered,
    RunnerSquashed,
    WispCaptured,
)
from psychic_cleaners.shell.audio import AudioBank
```

2. At module level, next to `LOGICAL_SIZE` / `WINDOW_SCALE` / `FPS`, add:

```python
EVENT_SOUNDS: Final[dict[type[Event], str]] = {
    GhostTrapped: "trap",
    WispCaptured: "catch",
    BustMissed: "miss",
    BeamsCrossed: "backfire",
    CleanerSlimed: "slime",
    BuildingStomped: "stomp",
    MascotAlert: "alert",
    BaitDeployed: "bait",
    RunnerEntered: "enter",
    RunnerSquashed: "squash",
    GameWon: "win",
    GameLost: "lose",
    ItemBought: "buy",
    PurchaseRejected: "reject",
    AccountRejected: "reject",
}
```

3. In `App.__init__`, add this line after `self.text = TextRenderer()` — `self.audio` first
   appears here (per contract, App is game/gfx/text-only before this milestone):

```python
        self.audio = AudioBank()
```

   In `App.step`, bind the return value of the tick call (if the current code discards it,
   rename accordingly) and play mapped sounds immediately after it:

```python
        game_events = self.game.tick(commands, dt)
        for game_event in game_events:
            sound_name = EVENT_SOUNDS.get(type(game_event))
            if sound_name is not None:
                self.audio.play(sound_name)
```

   If `step` already consumes the tick result for other purposes (it does — scenes draw from
   state, and Task 33 adds music tracking), keep a single `game_events` variable and reuse it.

- [ ] **Step 8: Run the full audio test file and the app smoke tests**

Run: `uv run pytest tests/shell/test_audio.py tests/shell -v`
Expected: PASS — all 6 audio tests plus every pre-existing shell smoke test (App constructs,
scenes render) still green.

- [ ] **Step 9: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: `All checks passed!`, no files reformatted (or reformats applied cleanly),
`Success: no issues found`.

- [ ] **Step 10: Commit**

```bash
git add src/psychic_cleaners/shell/audio.py src/psychic_cleaners/shell/app.py tests/shell/test_audio.py
git commit -m "feat: synthesized SFX bank and event-driven sound playback"
```

### Task 33: Theme chiptune and title karaoke

**Files:**
- Modify: `src/psychic_cleaners/shell/audio.py` (add `NOTE_HZ`, `THEME`, `build_theme`,
  `AudioBank.play_music_loop` / `stop_music`; point the `"theme"` recipe at `build_theme`)
- Modify: `src/psychic_cleaners/shell/scenes/title.py` (add `KARAOKE_WORDS` and karaoke drawing)
- Modify: `src/psychic_cleaners/shell/app.py` (start/stop the music loop on TITLE enter/leave)
- Test: `tests/shell/test_theme.py`

**Interfaces:**
- Consumes: `synth_square`, `SAMPLE_RATE`, `AudioBank`, `_RECIPES` from Task 32;
  `TitleScene` in `shell/scenes/title.py` and the `SCENES` registry, `App`, `SceneId` per contract;
  `TextRenderer.draw(surface, message, pos, size=16, color=(230, 230, 230))`.
- Produces: `NOTE_HZ: Final[dict[str, float]]` (C4..C6), `THEME: Final[list[tuple[str, int]]]`
  (16 entries, `("", ms)` = rest), `build_theme() -> bytes`,
  `AudioBank.play_music_loop() -> None`, `AudioBank.stop_music() -> None`,
  `KARAOKE_WORDS: Final[tuple[str, ...]]` in `title.py`.

- [ ] **Step 1: Write the failing theme test**

Create `tests/shell/test_theme.py`:

```python
"""Theme chiptune: note table, hook length, music no-ops when disabled."""

import pytest

from psychic_cleaners.shell.audio import NOTE_HZ, SAMPLE_RATE, THEME, AudioBank, build_theme


def test_a4_is_440_equal_temperament() -> None:
    assert NOTE_HZ["A4"] == pytest.approx(440.0, abs=1e-6)
    assert NOTE_HZ["A5"] == pytest.approx(880.0, abs=1e-6)
    assert NOTE_HZ["C6"] == pytest.approx(2.0 * NOTE_HZ["C5"], abs=1e-6)


def test_theme_is_a_sixteen_note_hook() -> None:
    assert len(THEME) == 16
    assert all(name == "" or name in NOTE_HZ for name, _ in THEME)


def test_build_theme_byte_length() -> None:
    expected = sum(round(ms / 1000 * SAMPLE_RATE) * 2 for _, ms in THEME)
    assert len(build_theme()) == expected


def test_music_calls_are_noops_when_disabled() -> None:
    bank = AudioBank(enabled=False)
    bank.play_music_loop()  # must not raise
    bank.stop_music()  # must not raise
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_theme.py -v`
Expected: FAIL — `ImportError: cannot import name 'NOTE_HZ' from 'psychic_cleaners.shell.audio'`.

- [ ] **Step 3: Extend `shell/audio.py` with the note table, hook, and music loop**

In `src/psychic_cleaners/shell/audio.py`, insert the following block between `def _seq(...)`
and the `_RECIPES` dict:

```python
_NOTE_NAMES: Final[tuple[str, ...]] = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)


def _note_freq(semitones_above_c0: int) -> float:
    a4 = 9 + 12 * 4  # A4 in semitones above C0
    return 440.0 * 2.0 ** ((semitones_above_c0 - a4) / 12.0)


NOTE_HZ: Final[dict[str, float]] = {
    f"{name}{octave}": _note_freq(_NOTE_NAMES.index(name) + 12 * octave)
    for octave in (4, 5)
    for name in _NOTE_NAMES
} | {"C6": _note_freq(12 * 6)}

# Original 16-note hook, call (bars 1-2) and answer (bars 3-4). "" = rest.
THEME: Final[list[tuple[str, int]]] = [
    ("C5", 150), ("E5", 150), ("G5", 150), ("E5", 150),
    ("A5", 300), ("G5", 150), ("", 150), ("E5", 300),
    ("F5", 150), ("E5", 150), ("D5", 150), ("F5", 150),
    ("E5", 300), ("D5", 150), ("C5", 150), ("", 300),
]


def _silence(ms: int) -> bytes:
    return b"\x00\x00" * _sample_count(ms)


def build_theme() -> bytes:
    parts: list[bytes] = []
    for note, ms in THEME:
        parts.append(synth_square(NOTE_HZ[note], ms, 0.35) if note else _silence(ms))
    return b"".join(parts)
```

Change the `"theme"` entry of `_RECIPES` from
`"theme": lambda: synth_square(440.0, 300, 0.3),` to:

```python
    "theme": build_theme,
```

In `AudioBank.__init__`, add this line immediately after `self._sounds: dict[...] = {}`
(before the `if not enabled: return`):

```python
        self._music: pygame.mixer.Sound | None = None
```

Add these two methods to `AudioBank` after `play`:

```python
    def play_music_loop(self) -> None:
        if not self._enabled:
            return
        if self._music is None:
            self._music = pygame.mixer.Sound(buffer=build_theme())
        self._music.play(loops=-1)

    def stop_music(self) -> None:
        if self._music is not None:
            self._music.stop()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/shell/test_theme.py tests/shell/test_audio.py -v`
Expected: PASS — all theme tests and all Task 32 tests (the `"theme"` recipe is still a valid
recipe, now the real hook).

- [ ] **Step 5: Write the failing karaoke test**

Append to `tests/shell/test_theme.py`:

```python
def test_title_karaoke_words_and_draw_smoke() -> None:
    import pygame

    from psychic_cleaners.core.game import SceneId, new_game
    from psychic_cleaners.shell.app import SCENES
    from psychic_cleaners.shell.gfx import SpriteFactory
    from psychic_cleaners.shell.scenes.title import KARAOKE_WORDS
    from psychic_cleaners.shell.text import TextRenderer

    assert KARAOKE_WORDS == ("WHEN", "THE", "STAINS", "COME", "CREEPING", "CALL", "THE", "CLEANERS")
    pygame.init()
    surface = pygame.Surface((640, 400))
    SCENES[SceneId.TITLE].draw(surface, new_game(seed=1), SpriteFactory(), TextRenderer())
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_theme.py::test_title_karaoke_words_and_draw_smoke -v`
Expected: FAIL — `ImportError: cannot import name 'KARAOKE_WORDS' from
'psychic_cleaners.shell.scenes.title'`.

- [ ] **Step 7: Add the karaoke line to `title.py`**

In `src/psychic_cleaners/shell/scenes/title.py`: ensure `import pygame`, and add
`from typing import Final` and the import of `TextRenderer` if not already present (the `draw`
signature already uses it). Add at module level:

```python
KARAOKE_WORDS: Final[tuple[str, ...]] = (
    "WHEN", "THE", "STAINS", "COME", "CREEPING", "CALL", "THE", "CLEANERS",
)


def _draw_karaoke(surface: pygame.Surface, text: TextRenderer) -> None:
    """Bouncing-ball lyric line — pure presentation, no game state."""
    ball_index = int(pygame.time.get_ticks() / 500) % len(KARAOKE_WORDS)
    x = 48
    y = 330
    for i, word in enumerate(KARAOKE_WORDS):
        text.draw(surface, word, (x, y), size=14, color=(250, 220, 120))
        if i == ball_index:
            pygame.draw.circle(surface, (255, 255, 255), (x + 4 * len(word), y - 10), 4)
        x += 8 * len(word) + 12
```

Then add exactly one line at the end of `TitleScene.draw`:

```python
        _draw_karaoke(surface, text)
```

- [ ] **Step 8: Run the karaoke test and the pre-existing title smoke**

Run: `uv run pytest tests/shell/test_theme.py tests/shell -v`
Expected: PASS — karaoke test green and every pre-existing title-scene smoke test unchanged
and green.

- [ ] **Step 9: Write the failing music-on-title test**

Append to `tests/shell/test_theme.py`:

```python
def test_app_starts_title_music() -> None:
    from psychic_cleaners.shell.app import App

    app = App(seed=1)
    if not app.audio._enabled:  # mixer genuinely unavailable on this machine
        pytest.skip("mixer unavailable")
    assert app.audio._music is not None  # theme loop started on TITLE
    for _ in range(3):
        app.step(1 / 60)
```

- [ ] **Step 10: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_theme.py::test_app_starts_title_music -v`
Expected: FAIL — `AssertionError` on `app.audio._music is not None` (the loop is never started).

- [ ] **Step 11: Start/stop music on scene transitions in `app.py`**

In `src/psychic_cleaners/shell/app.py`, ensure `SceneId` is imported
(`from psychic_cleaners.core.game import SceneId` — it already is if `SCENES` is typed).

In `App.__init__`, after `self.audio = AudioBank()`, add:

```python
        self._prev_scene: SceneId = self.game.scene
        if self._prev_scene is SceneId.TITLE:
            self.audio.play_music_loop()
```

In `App.step`, immediately after the Task 32 sound-playback loop, add:

```python
        if self.game.scene is not self._prev_scene:
            if self.game.scene is SceneId.TITLE:
                self.audio.play_music_loop()
            elif self._prev_scene is SceneId.TITLE:
                self.audio.stop_music()
            self._prev_scene = self.game.scene
```

- [ ] **Step 12: Run all shell tests to verify green**

Run: `uv run pytest tests/shell -v`
Expected: PASS — music test green, app smoke and every scene smoke still green.

- [ ] **Step 13: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: `All checks passed!`, no unexpected reformats, `Success: no issues found`.

- [ ] **Step 14: Commit**

```bash
git add src/psychic_cleaners/shell/audio.py src/psychic_cleaners/shell/app.py \
  src/psychic_cleaners/shell/scenes/title.py tests/shell/test_theme.py
git commit -m "feat: original theme chiptune with title-screen bouncing-ball karaoke"
```

### Task 34: Sprite polish pass

**Files:**
- Modify: `src/psychic_cleaners/shell/gfx.py` (full replacement — every contract sprite name
  gets a distinct, deliberate builder; the public API `SpriteFactory.get(name)` is unchanged)
- Test: `tests/shell/test_gfx_polish.py`
- Modify: `tests/shell/test_foundation.py`, `tests/shell/test_city_sprites.py`,
  `tests/shell/test_driving_scene.py`, `tests/shell/test_busting_scene.py` (these files hold
  the earlier pinned `get_size()` assertions — reconcile them to the SIZES table below)

**Interfaces:**
- Consumes: contract sprite names: `"car.compact" "car.hearse" "car.wagon" "car.performance"
  "wisp" "wisp.faint" "smudge" "cleaner" "cleaner.slimed" "building" "building.haunted"
  "tower" "depot" "mascot" "snare" "logo"`.
- Produces: `SpriteFactory.get(name: str) -> pygame.Surface` (cached, generated on demand,
  `KeyError` on unknown names) with the exact sizes in the SIZES table; scenes from earlier
  milestones keep working because they only call `get` and blit.

- [ ] **Step 1: Write the failing polish test**

Create `tests/shell/test_gfx_polish.py`:

```python
"""Every contract sprite exists, has its documented size, and is visually distinct."""

from typing import Final

import pygame
import pytest

from psychic_cleaners.shell.gfx import SpriteFactory

SIZES: Final[dict[str, tuple[int, int]]] = {
    "car.compact": (48, 28),
    "car.hearse": (48, 28),
    "car.wagon": (48, 28),
    "car.performance": (48, 28),
    "wisp": (24, 24),
    "wisp.faint": (24, 24),
    "smudge": (48, 48),
    "cleaner": (24, 40),
    "cleaner.slimed": (24, 40),
    "building": (48, 56),
    "building.haunted": (48, 56),
    "tower": (56, 96),
    "depot": (56, 48),
    "mascot": (72, 96),
    "snare": (32, 16),
    "logo": (320, 96),
}


@pytest.fixture(autouse=True, scope="module")
def _pygame() -> None:
    pygame.init()


def test_all_sixteen_sprites_have_expected_sizes() -> None:
    factory = SpriteFactory()
    assert len(SIZES) == 16
    for name, size in SIZES.items():
        assert factory.get(name).get_size() == size, name


def test_no_two_sprites_are_byte_identical() -> None:
    factory = SpriteFactory()
    encoded = [
        (factory.get(name).get_size(), pygame.image.tobytes(factory.get(name), "RGBA"))
        for name in SIZES
    ]
    assert len(set(encoded)) == len(encoded)


def test_get_is_cached() -> None:
    factory = SpriteFactory()
    assert factory.get("wisp") is factory.get("wisp")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/shell/test_gfx_polish.py -v`
Expected: FAIL — size assertions or `KeyError`, depending on the placeholder builders the
earlier milestones left in `gfx.py`.

- [ ] **Step 3: Replace `shell/gfx.py` with the full deliberate sprite set**

Replace the entire contents of `src/psychic_cleaners/shell/gfx.py` with:

```python
"""Code-generated sprite factory: every sprite is drawn deterministically and cached."""

import math
from collections.abc import Callable
from typing import Final

import pygame

type Color = tuple[int, int, int]
type ColorA = tuple[int, int, int, int]


def _surface(width: int, height: int) -> pygame.Surface:
    return pygame.Surface((width, height), pygame.SRCALPHA)


def _car(body: Color, cabin: Color, cabin_rect: pygame.Rect) -> pygame.Surface:
    surf = _surface(48, 28)
    pygame.draw.rect(surf, cabin, cabin_rect, border_radius=3)
    pygame.draw.rect(surf, body, pygame.Rect(2, 10, 44, 10), border_radius=4)
    for wheel_x in (10, 36):
        pygame.draw.circle(surf, (25, 25, 30), (wheel_x, 21), 5)
        pygame.draw.circle(surf, (140, 140, 150), (wheel_x, 21), 2)
    pygame.draw.rect(surf, (255, 240, 170), pygame.Rect(44, 12, 3, 4))  # headlight
    return surf


def _build_car_compact() -> pygame.Surface:
    return _car((200, 60, 50), (240, 230, 220), pygame.Rect(14, 4, 18, 8))


def _build_car_hearse() -> pygame.Surface:
    return _car((40, 40, 48), (200, 200, 210), pygame.Rect(8, 4, 30, 8))


def _build_car_wagon() -> pygame.Surface:
    return _car((70, 120, 190), (220, 230, 240), pygame.Rect(10, 4, 28, 8))


def _build_car_performance() -> pygame.Surface:
    surf = _car((250, 200, 40), (30, 30, 35), pygame.Rect(18, 5, 16, 7))
    pygame.draw.rect(surf, (30, 30, 35), pygame.Rect(2, 14, 44, 2))  # racing stripe
    return surf


def _build_wisp() -> pygame.Surface:
    surf = _surface(24, 24)
    pygame.draw.polygon(surf, (150, 200, 255), [(5, 12), (12, 23), (19, 12)])  # tail
    pygame.draw.circle(surf, (150, 200, 255), (12, 10), 9)
    pygame.draw.circle(surf, (235, 245, 255), (12, 10), 6)
    pygame.draw.circle(surf, (20, 20, 40), (9, 9), 1)
    pygame.draw.circle(surf, (20, 20, 40), (15, 9), 1)
    return surf


def _build_wisp_faint() -> pygame.Surface:
    surf = _surface(24, 24)
    # Alpha 90 is pinned by the contract: an earlier driving-scene test asserts `90 in alphas`.
    ghost: ColorA = (150, 200, 255, 90)
    pygame.draw.polygon(surf, ghost, [(5, 12), (12, 23), (19, 12)])
    pygame.draw.circle(surf, ghost, (12, 10), 9)
    pygame.draw.circle(surf, (235, 245, 255, 110), (12, 10), 6)
    return surf


def _build_smudge() -> pygame.Surface:
    surf = _surface(48, 48)
    body: Color = (150, 150, 90)
    dark: Color = (105, 105, 60)
    pygame.draw.circle(surf, body, (24, 18), 16)
    pygame.draw.rect(surf, body, pygame.Rect(8, 18, 32, 12))
    for drip_x, drip_len in ((11, 8), (21, 14), (33, 6)):  # greasy drips
        pygame.draw.rect(surf, dark, pygame.Rect(drip_x, 28, 5, drip_len))
        pygame.draw.circle(surf, dark, (drip_x + 2, 28 + drip_len), 3)
    pygame.draw.circle(surf, (250, 250, 250), (18, 14), 5)
    pygame.draw.circle(surf, (250, 250, 250), (30, 14), 5)
    pygame.draw.circle(surf, (30, 30, 30), (19, 15), 2)
    pygame.draw.circle(surf, (30, 30, 30), (31, 15), 2)
    return surf


def _cleaner(suit: Color, drip: Color | None) -> pygame.Surface:
    surf = _surface(24, 40)
    pygame.draw.rect(surf, (120, 90, 60), pygame.Rect(1, 12, 6, 14), border_radius=2)  # pack
    pygame.draw.rect(surf, suit, pygame.Rect(7, 12, 12, 16), border_radius=3)  # torso
    pygame.draw.circle(surf, (235, 200, 170), (13, 7), 5)  # head
    pygame.draw.rect(surf, suit, pygame.Rect(8, 1, 10, 3))  # cap
    pygame.draw.rect(surf, (40, 40, 55), pygame.Rect(8, 28, 4, 10))  # legs
    pygame.draw.rect(surf, (40, 40, 55), pygame.Rect(14, 28, 4, 10))
    pygame.draw.line(surf, suit, (19, 16), (23, 22), 3)  # arm with wand
    if drip is not None:
        pygame.draw.circle(surf, drip, (13, 12), 6)
        for drip_x in (9, 13, 17):
            pygame.draw.rect(surf, drip, pygame.Rect(drip_x, 12, 3, 8))
    return surf


def _build_cleaner() -> pygame.Surface:
    return _cleaner((210, 180, 90), None)


def _build_cleaner_slimed() -> pygame.Surface:
    return _cleaner((210, 180, 90), (90, 220, 90))


def _building(window: Color, halo: ColorA | None) -> pygame.Surface:
    surf = _surface(48, 56)
    pygame.draw.rect(surf, (100, 100, 115), pygame.Rect(2, 6, 44, 50))
    pygame.draw.rect(surf, (70, 70, 85), pygame.Rect(0, 0, 48, 8))  # roofline
    for row in range(3):
        for col in range(3):
            window_rect = pygame.Rect(8 + col * 13, 13 + row * 11, 8, 6)
            if halo is not None:
                pygame.draw.rect(surf, halo, window_rect.inflate(4, 4))
            pygame.draw.rect(surf, window, window_rect)
    pygame.draw.rect(surf, (50, 40, 35), pygame.Rect(20, 44, 8, 12))  # door
    return surf


def _build_building() -> pygame.Surface:
    return _building((225, 210, 140), None)


def _build_building_haunted() -> pygame.Surface:
    return _building((215, 140, 255), (140, 60, 200, 160))


def _build_tower() -> pygame.Surface:
    surf = _surface(56, 96)
    pygame.draw.circle(surf, (120, 60, 180, 70), (28, 20), 18)  # ambient glow
    pygame.draw.polygon(surf, (60, 55, 80), [(28, 2), (44, 40), (44, 94), (12, 94), (12, 40)])
    pygame.draw.polygon(surf, (90, 80, 120), [(28, 2), (36, 40), (36, 94), (20, 94), (20, 40)])
    for slit_y in range(48, 90, 12):
        pygame.draw.rect(surf, (200, 120, 255), pygame.Rect(24, slit_y, 8, 6))
    pygame.draw.circle(surf, (230, 180, 255), (28, 14), 4)  # beacon
    return surf


def _build_depot() -> pygame.Surface:
    surf = _surface(56, 48)
    pygame.draw.rect(surf, (150, 60, 60), pygame.Rect(2, 14, 52, 34))
    pygame.draw.polygon(surf, (110, 45, 45), [(0, 16), (28, 0), (56, 16)])  # gable roof
    pygame.draw.rect(surf, (90, 90, 100), pygame.Rect(12, 22, 32, 26))  # garage door
    for slat_y in range(24, 46, 5):
        pygame.draw.line(surf, (60, 60, 70), (12, slat_y), (44, slat_y), 1)
    pygame.draw.rect(surf, (230, 220, 200), pygame.Rect(22, 16, 12, 5))  # sign
    return surf


def _build_mascot() -> pygame.Surface:
    surf = _surface(72, 96)
    body: Color = (255, 120, 160)
    dark: Color = (220, 80, 130)
    pygame.draw.rect(surf, body, pygame.Rect(14, 30, 44, 54), border_radius=18)  # gummy body
    pygame.draw.circle(surf, body, (36, 22), 18)  # head
    pygame.draw.circle(surf, body, (10, 46), 8)  # stubby arms
    pygame.draw.circle(surf, body, (62, 46), 8)
    pygame.draw.rect(surf, dark, pygame.Rect(20, 80, 12, 14), border_radius=6)  # legs
    pygame.draw.rect(surf, dark, pygame.Rect(40, 80, 12, 14), border_radius=6)
    pygame.draw.circle(surf, (40, 20, 30), (30, 20), 3)  # eyes
    pygame.draw.circle(surf, (40, 20, 30), (42, 20), 3)
    pygame.draw.arc(surf, (40, 20, 30), pygame.Rect(28, 22, 16, 12), math.pi, 2 * math.pi, 2)
    pygame.draw.circle(surf, (255, 170, 200), (28, 48), 7)  # belly sheen
    return surf


def _build_snare() -> pygame.Surface:
    surf = _surface(32, 16)
    pygame.draw.rect(surf, (60, 60, 70), pygame.Rect(2, 6, 28, 9), border_radius=2)
    for stripe_x in range(4, 28, 8):  # hazard stripes
        pygame.draw.rect(surf, (250, 210, 60), pygame.Rect(stripe_x, 6, 4, 9))
    pygame.draw.rect(surf, (90, 90, 105), pygame.Rect(4, 2, 11, 5))  # lid halves
    pygame.draw.rect(surf, (90, 90, 105), pygame.Rect(17, 2, 11, 5))
    pygame.draw.rect(surf, (255, 80, 80), pygame.Rect(14, 8, 4, 4))  # indicator lamp
    return surf


def _build_logo() -> pygame.Surface:
    surf = _surface(320, 96)
    pygame.draw.rect(surf, (30, 25, 55), pygame.Rect(0, 8, 320, 80), border_radius=16)
    pygame.draw.rect(surf, (150, 110, 255), pygame.Rect(0, 8, 320, 80), width=4, border_radius=16)
    pygame.draw.line(surf, (200, 160, 90), (40, 24), (64, 64), 5)  # broom handle
    pygame.draw.polygon(surf, (240, 200, 90), [(58, 58), (76, 70), (66, 82), (48, 68)])  # head
    star = [
        (96, 20), (101, 34), (116, 34), (104, 43), (109, 58),
        (96, 48), (83, 58), (88, 43), (76, 34), (91, 34),
    ]
    pygame.draw.polygon(surf, (255, 230, 120), star)
    white: Color = (235, 235, 255)
    p_letter = [(140, 74), (140, 24), (166, 24), (166, 48), (140, 48)]
    c_letter = [(210, 24), (184, 24), (184, 74), (210, 74)]
    pygame.draw.lines(surf, white, False, p_letter, 6)  # "P"
    pygame.draw.lines(surf, white, False, c_letter, 6)  # "C"
    pygame.draw.rect(surf, (150, 110, 255), pygame.Rect(228, 34, 64, 8))  # wordmark bars
    pygame.draw.rect(surf, (150, 110, 255), pygame.Rect(228, 54, 48, 8))
    return surf


_BUILDERS: Final[dict[str, Callable[[], pygame.Surface]]] = {
    "car.compact": _build_car_compact,
    "car.hearse": _build_car_hearse,
    "car.wagon": _build_car_wagon,
    "car.performance": _build_car_performance,
    "wisp": _build_wisp,
    "wisp.faint": _build_wisp_faint,
    "smudge": _build_smudge,
    "cleaner": _build_cleaner,
    "cleaner.slimed": _build_cleaner_slimed,
    "building": _build_building,
    "building.haunted": _build_building_haunted,
    "tower": _build_tower,
    "depot": _build_depot,
    "mascot": _build_mascot,
    "snare": _build_snare,
    "logo": _build_logo,
}


class SpriteFactory:
    """Generates sprites on demand and caches them by name."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = _BUILDERS[name]()
        return self._cache[name]
```

- [ ] **Step 4: Run the polish test to verify it passes**

Run: `uv run pytest tests/shell/test_gfx_polish.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Reconcile earlier size-pinning tests and run the whole shell suite**

Run: `uv run pytest tests/shell -v`
The earlier pinned sprite-size assertions live in `tests/shell/test_foundation.py`,
`tests/shell/test_city_sprites.py`, `tests/shell/test_driving_scene.py`, and
`tests/shell/test_busting_scene.py`. In each of those files, delete or update ONLY the
`get_size()` assertions, so that any that remain match the SIZES table from Step 1 —
`test_gfx_polish.py`'s SIZES table is now the single, exhaustive source of truth for sprite
dimensions. Keep every non-size assertion in those files (caching, distinctness, KeyError
checks, alpha checks) exactly as-is — in particular, the faint-wisp `90 in alphas` assertion
in `tests/shell/test_driving_scene.py` now passes unchanged against the Step 3 builder.
Scenes only call `get` and blit, so no scene code changes. Re-run until:
Expected: PASS — entire `tests/shell` suite green.

- [ ] **Step 6: Run quality gates**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: `All checks passed!`, clean format, `Success: no issues found`.

- [ ] **Step 7: Commit**

```bash
git add src/psychic_cleaners/shell/gfx.py tests/shell/test_gfx_polish.py tests/shell
git commit -m "feat: deliberate sprite set for all sixteen contract sprites"
```

### Task 35: Coverage gate, README, final verification

**Files:**
- Modify: `.github/workflows/ci.yml` (pytest step becomes the coverage-gated command)
- Modify: `README.md` (full replacement with real content)

**Interfaces:**
- Consumes: everything — this task verifies the finished project.
- Produces: CI gate
  `uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90 --override-ini="addopts=--cov-report=term-missing"`;
  user-facing README. No code API changes.

- [ ] **Step 1: Verify the coverage gate passes locally before wiring it into CI**

Run:

```bash
uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90 \
  --override-ini="addopts=--cov-report=term-missing"
```

The `--override-ini` is load-bearing: pyproject's addopts already include
`--cov=psychic_cleaners`, and pytest-cov unions repeated `--cov` targets, so without the
override the `--cov-fail-under=90` would gate the whole-package (core + shell) total instead
of the spec's core-only gate. The override drops the package-wide `--cov` while keeping the
`term-missing` report.
Expected: all tests pass and the summary ends with
`Required test coverage of 90% reached.` The coverage table must list only
`psychic_cleaners/core/` files. If coverage is below 90%, the missing lines are
listed by `--cov-report=term-missing` — add core unit tests for
those lines before proceeding. Do NOT add `--cov-fail-under` to `pyproject.toml` addopts;
local dev keeps fast, ungated runs.

- [ ] **Step 2: Add the gated step to CI**

In `.github/workflows/ci.yml`, replace the existing pytest step with:

```yaml
      - name: Tests with core coverage gate
        env:
          SDL_VIDEODRIVER: dummy
          SDL_AUDIODRIVER: dummy
        run: >-
          uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90
          --override-ini="addopts=--cov-report=term-missing"
```

Keep every other step (uv sync, ruff check, ruff format --check, mypy) exactly as it was.

- [ ] **Step 3: Write the README**

Replace the entire contents of `README.md` with:

```markdown
# Psychic Cleaners

A clean-room [pygame-ce](https://pyga.me) homage to a 1984 Activision C64 classic about
running a paranormal-removal franchise: buy a vehicle and gear, watch the city map, drive
to hauntings, snare stain-ghosts between two beams, dodge a rampaging gummy mascot, and —
when the city's psychic residue maxes out — storm Threshold Tower. Mechanics and pacing
follow the original; every name, sprite, sound, and melody is an original work. The full
concept-by-concept theme mapping is in
[docs/superpowers/specs/2026-07-13-psychic-cleaners-design.md](docs/superpowers/specs/2026-07-13-psychic-cleaners-design.md)
(section 3).

## Install

Requires Python >= 3.14 and [uv](https://docs.astral.sh/uv/).

    uv sync

## Play

    uv run psychic-cleaners

Win condition: end the finale with a bankroll strictly greater than the one you started
with. Your account code carries the bankroll into the next game.

## Controls

| Scene     | Keys                                                                         |
|-----------|------------------------------------------------------------------------------|
| Title     | Type your name; `Tab` toggles new-franchise / account-code entry; `Enter` confirms |
| Shop      | `Up`/`Down` select; `Enter` buy vehicle or item; `F` finish shopping           |
| City map  | Arrow keys move the cursor; `Enter` travel; `B` deploy gummy bait on an alert  |
| Driving   | `Up`/`Down` change lane; `B` deploy gummy bait on an alert                     |
| Busting   | `Left`/`Right` move cleaner or snare cursor; `Enter` place / lay snare; `Space` spring it; `B` deploy gummy bait on an alert |
| Finale    | `Space` send the next runner past the mascot                                   |
| Game over | `Enter` back to the title                                                      |

## Development

    uv run pytest                 # full suite (SDL dummy drivers set by tests/conftest.py)
    uv run ruff check .           # lint
    uv run ruff format .          # format
    uv run mypy                   # strict type-check of src and tests
    uv run pre-commit install     # ruff + mypy on every commit

CI additionally enforces >= 90% coverage on the pure-logic core:
`uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90
--override-ini="addopts=--cov-report=term-missing"` (the override drops the package-wide
`--cov` from pyproject addopts so the gate measures `core/` only).

## Project layout

    src/psychic_cleaners/
      core/    # pure deterministic game logic — zero pygame imports
               # constants.py is the single tuning point for every gameplay number
      shell/   # all pygame-ce code: app loop, generated sprites/audio, one module per scene
    tests/
      core/         # fast unit + Hypothesis property tests
      integration/  # scripted full-playthrough tests of core.game (no pygame)
      shell/        # SDL dummy-driver smoke tests

The shell feeds `Command` objects into `core.game.Game.tick`, which returns `Event`
objects; the shell draws state and plays a sound per event. Same seed + same commands =
same game, which is what makes the playthrough tests deterministic.
```

- [ ] **Step 4: Gauntlet — lint**

Run: `uv run ruff check .`
Expected output: `All checks passed!`

- [ ] **Step 5: Gauntlet — format check**

Run: `uv run ruff format --check .`
Expected output: `N files already formatted` (no `Would reformat` lines). If any file would
be reformatted, run `uv run ruff format .` and re-check.

- [ ] **Step 6: Gauntlet — types**

Run: `uv run mypy`
Expected output: `Success: no issues found in N source files`

- [ ] **Step 7: Gauntlet — tests with the coverage gate**

Run (the exact command CI runs):

```bash
uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90 \
  --override-ini="addopts=--cov-report=term-missing"
```

Expected output: every test passes, a coverage table listing only
`psychic_cleaners/core/` files prints, final line includes
`Required test coverage of 90% reached.`

- [ ] **Step 8: Gauntlet — headless soak**

Run:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run python -c \
  'from psychic_cleaners.shell.app import App; a=App(seed=1); [a.step(1/60) for _ in range(120)]'
```

Expected: exits with status 0 and no traceback — two simulated seconds of the real app
(window, sprites, audio bank, title music path) under dummy drivers.

- [ ] **Step 9: Commit**

```bash
git add .github/workflows/ci.yml README.md
git commit -m "chore: core coverage gate in CI, player-facing README"
```

<!-- CONTRACT-NOTE: Most per-scene key bindings are not in the contract; the contract does pin the B key (DeployBait on a mascot alert) in all three world scenes — map, driving, AND busting. The README documents Tab (title account toggle), Up/Down+Enter+F (shop), arrows+Enter+B (map), Up/Down+B (drive), Left/Right+Enter+Space+B (bust), Space (finale), Enter (game over); if the scene tasks bound the non-contract keys differently, only the README controls table needs editing. -->
<!-- CONTRACT-NOTE: pyproject addopts already include `--cov=psychic_cleaners`, and pytest-cov unions repeated `--cov` targets, so a bare `--cov=psychic_cleaners.core --cov-fail-under=90` would apply fail-under to the whole-package total rather than the spec's core-only gate. Task 35 therefore appends `--override-ini="addopts=--cov-report=term-missing"` to the gate command in Steps 1, 2, and 7 (and the README), dropping the package-wide --cov while keeping the term-missing report. -->
<!-- CONTRACT-NOTE: Private/auxiliary names introduced (allowed as non-contract): audio._RECIPES, audio._seq, audio._silence, App._prev_scene, title.KARAOKE_WORDS. -->

---

## Appendix: Shared Interface Contract

This contract is the single source of truth for names, signatures, types, and
gameplay constants across all plan tasks. Plan writers MUST use these exact
names and signatures. If a needed name is missing, choose minimally, mark it
with `<!-- CONTRACT-NOTE: ... -->` at the end of your file.

Python >= 3.14. `core/` never imports pygame. `shell/` is the only place
pygame (the pygame-ce package) may be imported. mypy --strict everywhere.
All gameplay numbers live in `core/constants.py`.

## Package layout

```
src/psychic_cleaners/
  __init__.py
  __main__.py            # runs shell.app.main()
  core/
    __init__.py
    constants.py  events.py  rng.py  clock.py  economy.py  codec.py
    catalog.py  loadout.py  pk.py  city.py  drive.py  geometry.py
    bust.py  giant.py  finale.py  game.py
  shell/
    __init__.py
    app.py  gfx.py  audio.py  text.py
    scenes/
      __init__.py
      title.py  shop.py  city_map.py  driving.py  busting.py
      finale.py  gameover.py
tests/
  __init__.py absent — tests use plain pytest discovery
  core/          # pure fast tests
  integration/   # scripted playthroughs of core.game (no pygame)
  shell/         # SDL dummy-driver smoke tests
  conftest.py    # sets SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy for shell tests; provides fixed-seed rng fixture
```

## core/constants.py — every value, exact

```python
from typing import Final

# economy (documented values from the original)
STARTING_BANKROLL: Final[int] = 10_000
STOMP_FINE: Final[int] = 4_000
VACUUM_BOUNTY: Final[int] = 100
BUST_BASE_FEE: Final[int] = 300
BUST_FEE_PER_1000_PSI: Final[int] = 100
MAX_BANKROLL: Final[int] = 9_999_999

# psi
PSI_MAX: Final[int] = 9_999
PSI_GROWTH_PER_MINUTE: Final[float] = 250.0
PSI_HAUNT_GROWTH_PER_MINUTE: Final[float] = 100.0   # per active haunting
WISP_TOWER_PSI_JUMP: Final[int] = 100
STOMP_PSI_SPIKE: Final[int] = 500

# time
GAME_MINUTES_PER_REAL_SECOND: Final[float] = 1.0

# cleaners
CLEANER_COUNT: Final[int] = 3
FINALE_NEEDED_INSIDE: Final[int] = 2

# items
BAIT_PACK_SIZE: Final[int] = 5
CONTAINMENT_RIG_CAPACITY: Final[int] = 10

# city grid
GRID_WIDTH: Final[int] = 10
GRID_HEIGHT: Final[int] = 6
TOWER_POS: Final[tuple[int, int]] = (5, 3)
DEPOT_POS: Final[tuple[int, int]] = (0, 5)
BLOCK_LENGTH: Final[float] = 400.0            # travel units per manhattan step
HAUNT_CHANCE_PER_MINUTE: Final[float] = 0.8   # scaled by (1 + psi/PSI_MAX)
MAX_ACTIVE_HAUNTS: Final[int] = 4
WISP_SPAWN_PER_MINUTE: Final[float] = 0.6
WISP_MAP_SPEED: Final[float] = 0.05           # grid cells per real second

# drive scene
DRIVE_LANES: Final[int] = 3
CAR_X: Final[float] = 80.0
ROAD_WISP_SPAWN_PER_SECOND: Final[float] = 0.5
ROAD_WISP_SPEED: Final[float] = 120.0         # toward the car, units/sec
CATCH_RANGE: Final[float] = 24.0
FAINT_WISP_CHANCE: Final[float] = 0.3
ROAD_LENGTH_VISIBLE: Final[float] = 640.0

# bust scene (logical coordinates, 640x400 space)
BEAM_CROSS_GHOST_Y: Final[float] = 320.0
BUST_GROUND_Y: Final[float] = 360.0
BEAM_TOP_Y: Final[float] = 120.0
BEAM_MAX_TILT: Final[float] = 140.0
GHOST_DRIFT_SPEED: Final[float] = 60.0
GHOST_SINK_SPEED: Final[float] = 8.0
GHOST_REPEL_SPEED: Final[float] = 90.0
SLIME_RANGE: Final[float] = 28.0
SNARE_WIDTH: Final[float] = 48.0
SNARE_TRIGGER_Y: Final[float] = 280.0
CLEANER_SPEED: Final[float] = 180.0           # px/sec while positioning
BUST_MIN_X: Final[float] = 40.0
BUST_MAX_X: Final[float] = 600.0

# mascot (Sir Squish)
MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI: Final[float] = 0.15
MASCOT_ALERT_WINDOW: Final[float] = 10.0      # real seconds to deploy bait

# finale
DOOR_X: Final[float] = 560.0
GIANT_MIN_X: Final[float] = 180.0
GIANT_MAX_X: Final[float] = 460.0
GIANT_SPEED: Final[float] = 220.0             # triangle-wave patrol, px/sec
GIANT_HOP_PERIOD: Final[float] = 1.2          # seconds per hop cycle
GIANT_AIR_FRACTION: Final[float] = 0.6        # first 60% of each cycle is airborne
RUNNER_START_X: Final[float] = 40.0
RUNNER_SPEED: Final[float] = 260.0
SQUASH_RANGE: Final[float] = 36.0             # squash only while the giant is GROUNDED
```

## core/rng.py

```python
from typing import Protocol
from collections.abc import Sequence

class Rng(Protocol):
    def random(self) -> float: ...                       # [0.0, 1.0)
    def randint(self, a: int, b: int) -> int: ...        # inclusive
    def uniform(self, a: float, b: float) -> float: ...
    def choice[T](self, seq: Sequence[T]) -> T: ...

def make_rng(seed: int) -> Rng:   # returns random.Random(seed)
```

Probability-per-time pattern used everywhere:
`if rng.random() < rate_per_minute * (dt_seconds / 60.0): ...`

## core/clock.py

```python
from dataclasses import dataclass

@dataclass
class GameClock:
    minutes: float = 0.0
    def advance(self, dt_seconds: float) -> None:
        # minutes += dt_seconds * GAME_MINUTES_PER_REAL_SECOND
```

## core/events.py

`GridPos` lives HERE: `type GridPos = tuple[int, int]`

Bases (frozen dataclasses):
```python
@dataclass(frozen=True)
class Command: pass

@dataclass(frozen=True)
class Event: pass
```

Commands (all frozen dataclasses subclassing Command; fields exactly as shown):
```python
NewGame(name: str)
EnterAccount(name: str, code: str)
SelectVehicle(vehicle_id: str)
BuyItem(item_id: str)
FinishShopping()
SetDestination(pos: GridPos)
BuyItem is also valid in MAP scene when position == DEPOT_POS, for item_id "snare" only
Steer(delta: int)              # -1 = lane up, +1 = lane down
MoveCleaner(dx: float)         # signed px this frame
PlaceCleaner()
LaySnare()
SpringSnare()
DeployBait()
StartRun()
Continue()                     # advance past overlays / gameover -> title
```

Events (all frozen dataclasses subclassing Event):
```python
SceneChanged(scene: SceneId)                 # SceneId imported from core.game under TYPE_CHECKING or defined here — SceneId LIVES IN events.py to avoid cycles
AccountAccepted(name: str, bankroll: int)
AccountRejected(reason: str)
VehicleSelected(vehicle_id: str)
ItemBought(item_id: str)
PurchaseRejected(reason: str)
CommandRejected(reason: str)                 # invalid non-purchase command, e.g. "no snare laid"
TravelStarted(dest: GridPos, distance: float)
Arrived(pos: GridPos)
WispCaptured(bounty: int)
HauntStarted(pos: GridPos)
HauntCleared(pos: GridPos)
WispReachedTower()
GhostTrapped(fee: int)
BustMissed()
BeamsCrossed()
CleanerSlimed(cleaner: int)                  # 0..2 game-level index
SnaresEmptied()
CleanersRestored()
MascotAlert(window_seconds: float)
BaitDeployed()
StompTriggered()                             # internal, from MascotModel
BuildingStomped(pos: GridPos, fine: int)
FinaleUnlocked()
RunnerEntered(total_inside: int)
RunnerSquashed()
GameWon(account_code: str)
GameLost(reason: str)
```

`SceneId` is defined in `core/events.py`:
```python
class SceneId(enum.Enum):
    TITLE = auto(); SHOP = auto(); MAP = auto(); DRIVE = auto()
    BUST = auto(); FINALE = auto(); GAME_OVER = auto()
```
(`core/game.py` re-exports it: `from psychic_cleaners.core.events import SceneId`.)

## core/economy.py

```python
@dataclass
class Wallet:
    balance: int = STARTING_BANKROLL
    def can_afford(self, amount: int) -> bool
    def spend(self, amount: int) -> bool      # False and unchanged if insufficient; never negative
    def earn(self, amount: int) -> None       # amount >= 0; clamp total at MAX_BANKROLL
    def fine(self, amount: int) -> int        # charges min(amount, balance), returns amount charged

def bust_fee(psi_value: int) -> int:
    # BUST_BASE_FEE + BUST_FEE_PER_1000_PSI * (psi_value // 1000)
```

## core/codec.py

```python
class AccountCodeError(ValueError): pass

ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"   # 30 chars, no confusables

def encode_account(name: str, bankroll: int) -> str    # 7-char code
def decode_account(name: str, code: str) -> int        # returns bankroll or raises AccountCodeError
```
Exact algorithm (both directions must implement this):
- decode normalizes the incoming code with `.strip().upper()` before any validation
- `_norm(name) = " ".join(name.split()).casefold()`; empty normalized name → AccountCodeError
- `key = zlib.crc32(_norm(name).encode()) & 0xFFFFFF`
- require `0 <= bankroll <= MAX_BANKROLL` else AccountCodeError
- `mixed = bankroll ^ key` (24 bits)
- `check = zlib.crc32(f"{_norm(name)}:{bankroll}".encode()) & 0xFF`
- `raw = (mixed << 8) | check` (32 bits)
- encode raw as exactly 7 base-30 digits (most significant first) using ALPHABET
- decode: reject wrong length/characters, reverse, verify checksum, else AccountCodeError

## core/catalog.py

```python
@dataclass(frozen=True)
class Vehicle:
    id: str; name: str; price: int; speed: float; capacity: int

@dataclass(frozen=True)
class Item:
    id: str; name: str; price: int; slots: int

VEHICLES: Final[dict[str, Vehicle]]  # insertion order = display order
ITEMS: Final[dict[str, Item]]
```
Exact data:
| id | name | price | speed | capacity |
|---|---|---|---|---|
| compact | Compact | 2000 | 100.0 | 7 |
| hearse | Hearse | 4800 | 140.0 | 9 |
| wagon | Wagon | 6000 | 140.0 | 11 |
| performance | Performance | 15000 | 200.0 | 14 |

| id | name | price | slots |
|---|---|---|---|
| detector | Residue detector | 400 | 1 |
| lens | Spectral lens | 800 | 1 |
| sensor | Mascot sensor | 800 | 1 |
| bait | Gummy bait (5) | 400 | 1 |
| snare | Spirit snare | 600 | 1 |
| rig | Containment rig | 8000 | 3 |
| vacuum | Roof vacuum | 500 | 1 |

## core/loadout.py

```python
@dataclass
class Loadout:
    vehicle: Vehicle
    counts: dict[str, int] = field(default_factory=dict)   # item_id -> count owned
    bait_charges: int = 0            # BAIT_PACK_SIZE per bait pack bought
    def slots_used(self) -> int      # sum(ITEMS[i].slots * n)
    def can_add(self, item_id: str) -> bool     # capacity check
    def add(self, item_id: str) -> None         # raises ValueError if not can_add; bait adds charges
    def count(self, item_id: str) -> int
    def has(self, item_id: str) -> bool         # count > 0
    def use_bait(self) -> bool                  # decrement charge, False if none
```
Only one of each non-snare item is purchasable (`can_add` returns False for
duplicates), except `snare` (unlimited by capacity) and `bait` (re-buyable
packs; capacity slot counted once per pack).

## core/pk.py

```python
@dataclass
class PsiModel:
    psi: float = 0.0
    def advance(self, dt_seconds: float, active_haunts: int) -> None
    def spike(self, amount: float) -> None      # clamp to [0, PSI_MAX]
    @property
    def value(self) -> int                      # int(self.psi), 0..PSI_MAX
    @property
    def at_max(self) -> bool                    # value >= PSI_MAX
```

## core/city.py

```python
@dataclass
class Building:
    pos: GridPos
    haunted: bool = False

@dataclass
class Wisp:
    x: float          # grid coords, float
    y: float

@dataclass
class City:
    buildings: dict[GridPos, Building]
    wisps: list[Wisp] = field(default_factory=list)
    @classmethod
    def new(cls) -> "City"      # building at every cell except TOWER_POS and DEPOT_POS
    def tick(self, dt_seconds: float, psi_value: int, rng: Rng) -> list[Event]
        # haunt spawning (HauntStarted), wisp spawning, wisp drift toward
        # TOWER_POS; wisp reaching within 0.5 cells of tower -> remove, WispReachedTower()
    def haunted_positions(self) -> list[GridPos]
    def active_haunts(self) -> int
    def clear_haunt(self, pos: GridPos) -> None       # emits nothing; Game emits HauntCleared
    def stompable_positions(self) -> list[GridPos]    # all building positions
    def distance(self, a: GridPos, b: GridPos) -> float   # manhattan * BLOCK_LENGTH
```

## core/drive.py

```python
@dataclass
class RoadWisp:
    x: float          # 0..ROAD_LENGTH_VISIBLE, moves toward 0 (toward car)
    lane: int         # 0..DRIVE_LANES-1
    faint: bool

@dataclass
class DriveSim:
    distance_total: float
    speed: float
    has_vacuum: bool
    has_lens: bool
    distance_done: float = 0.0
    lane: int = 1
    wisps: list[RoadWisp] = field(default_factory=list)
    def steer(self, delta: int) -> None      # clamp 0..DRIVE_LANES-1
    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]
        # advance distance_done by speed*dt; spawn wisps (lane=randint, faint per chance)
        # at x=ROAD_LENGTH_VISIBLE; move wisps toward 0 at ROAD_WISP_SPEED + speed
        # catch: has_vacuum and wisp.lane == self.lane and |wisp.x - CAR_X| <= CATCH_RANGE
        #        and (not wisp.faint or has_lens)  -> remove, WispCaptured(VACUUM_BOUNTY)
        # wisps with x < -CATCH_RANGE removed silently
    @property
    def arrived(self) -> bool                # distance_done >= distance_total
```

## core/geometry.py

```python
type Vec = tuple[float, float]
def segments_cross(a1: Vec, a2: Vec, b1: Vec, b2: Vec) -> bool
    # strict proper intersection of open segments (shared endpoints do NOT count)
```

## core/bust.py

```python
class BustPhase(enum.Enum):
    POSITION_LEFT = auto(); POSITION_RIGHT = auto(); SNARE = auto()
    ACTIVE = auto(); RESOLVED = auto()

class BustOutcome(enum.Enum):
    CAUGHT = auto(); MISSED = auto(); BACKFIRE = auto(); SLIMED = auto()

@dataclass
class BustSim:
    phase: BustPhase = BustPhase.POSITION_LEFT
    cursor_x: float = 320.0
    left_x: float | None = None
    right_x: float | None = None
    snare_x: float | None = None
    ghost_x: float = 320.0
    ghost_y: float = 160.0
    outcome: BustOutcome | None = None
    slimed_side: int | None = None     # 0 = left cleaner, 1 = right cleaner
    def move(self, dx: float) -> None  # cursor during POSITION_*/SNARE, clamp BUST_MIN_X..BUST_MAX_X
    def place(self) -> None            # POSITION_LEFT->POSITION_RIGHT->SNARE; in SNARE: lays snare at cursor -> ACTIVE
    def spring(self) -> None           # in ACTIVE: CAUGHT if |ghost_x-snare_x| <= SNARE_WIDTH/2 and ghost_y >= SNARE_TRIGGER_Y else MISSED
    def beam_endpoints(self) -> tuple[tuple[Vec, Vec], tuple[Vec, Vec]] | None
        # for each placed cleaner in ACTIVE: from (x, BUST_GROUND_Y) to
        # (x + clamp(ghost_x - x, -BEAM_MAX_TILT, BEAM_MAX_TILT), BEAM_TOP_Y)
    def tick(self, dt_seconds: float, rng: Rng) -> list[Event]
        # ACTIVE only: ghost drifts (rng.uniform(-1,1)*GHOST_DRIFT_SPEED*dt),
        # sinks GHOST_SINK_SPEED*dt, repelled horizontally away from the nearer
        # beam at GHOST_REPEL_SPEED*dt when a beam is within SNARE_WIDTH;
        # clamp ghost to BUST_MIN_X..BUST_MAX_X, BEAM_TOP_Y..BUST_GROUND_Y.
        # BACKFIRE check (either condition, checked every ACTIVE tick):
        #   (a) segments_cross(*beams)  — defensive geometric check, or
        #   (b) min(left_x, right_x) < ghost_x < max(left_x, right_x)
        #       and ghost_y >= BEAM_CROSS_GHOST_Y
        #       (the ghost has sunk low BETWEEN the cleaners: both beams angle
        #       steeply down at it and cross — the reachable, player-caused
        #       hazard: spring the snare before the ghost sinks too low)
        #   -> outcome=BACKFIRE, phase=RESOLVED, [BeamsCrossed()]
        # if ghost within SLIME_RANGE of a cleaner: outcome=SLIMED, slimed_side set
```
`BustSim` emits geometry-level events only (BeamsCrossed). Money, snare
accounting, and CleanerSlimed(game index) are Game's job (task: bust wiring).
Note SNARE_TRIGGER_Y (280) < BEAM_CROSS_GHOST_Y (320): there is a 40px band
where the ghost is springable but not yet backfiring — the skill window.

## core/giant.py

```python
class MascotState(enum.Enum):
    CALM = auto(); ALERT = auto()

@dataclass
class MascotModel:
    state: MascotState = MascotState.CALM
    alert_remaining: float = 0.0
    def tick(self, dt_seconds: float, psi_value: int, has_sensor: bool, rng: Rng) -> list[Event]
        # CALM: p = MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI * (psi_value/1000) per minute
        #   triggered & has_sensor -> state=ALERT, alert_remaining=MASCOT_ALERT_WINDOW, [MascotAlert(MASCOT_ALERT_WINDOW)]
        #   triggered & not has_sensor -> [StompTriggered()]
        # ALERT: countdown; on expiry -> CALM, [StompTriggered()]
    def deploy_bait(self) -> bool      # True iff state==ALERT; resets to CALM
```

## core/finale.py

```python
class FinaleOutcome(enum.Enum):
    WON = auto(); LOST = auto()

@dataclass
class FinaleSim:
    able_cleaners: int                # cleaners available at start
    giant_x: float = GIANT_MIN_X
    giant_dir: int = 1
    hop_time: float = 0.0             # accumulated sim time, drives the hop cycle
    runner_x: float | None = None
    inside: int = 0
    squashed: int = 0
    def start_run(self) -> None       # only if runner_x is None and remaining_outside > 0
    @property
    def remaining_outside(self) -> int    # able_cleaners - inside - squashed
    @property
    def airborne(self) -> bool
        # (hop_time % GIANT_HOP_PERIOD) < GIANT_HOP_PERIOD * GIANT_AIR_FRACTION
        # The giant hops continuously; runners pass safely UNDER him while he
        # is airborne. This is the timing skill — without it the finale is
        # provably unwinnable (runner starts behind the patrol zone, door lies
        # beyond it, so runner and giant paths must cross by IVT).
    def tick(self, dt_seconds: float) -> list[Event]
        # hop_time += dt
        # giant: triangle wave between GIANT_MIN_X..GIANT_MAX_X at GIANT_SPEED
        # runner (if any): advance RUNNER_SPEED*dt toward DOOR_X;
        #   (not airborne) and |runner_x - giant_x| < SQUASH_RANGE
        #     -> squashed += 1, runner_x=None, [RunnerSquashed()]
        #   runner_x >= DOOR_X -> inside += 1, runner_x=None, [RunnerEntered(inside)]
    @property
    def outcome(self) -> FinaleOutcome | None
        # WON if inside >= FINALE_NEEDED_INSIDE
        # LOST if inside + remaining_outside + (1 if runner active else 0) < FINALE_NEEDED_INSIDE
```

## core/game.py

```python
from psychic_cleaners.core.events import SceneId   # re-export

@dataclass
class Game:
    rng: Rng
    clock: GameClock = field(default_factory=GameClock)
    wallet: Wallet = field(default_factory=Wallet)
    psi: PsiModel = field(default_factory=PsiModel)
    city: City = field(default_factory=City.new)
    mascot: MascotModel = field(default_factory=MascotModel)
    scene: SceneId = SceneId.TITLE
    player_name: str = ""
    starting_bankroll: int = STARTING_BANKROLL
    loadout: Loadout | None = None
    drive: DriveSim | None = None
    bust: BustSim | None = None
    finale: FinaleSim | None = None
    slimed: set[int] = field(default_factory=set)   # cleaner indices 0..2
    contained: int = 0            # ghosts in rig
    snares_full: int = 0
    position: GridPos = DEPOT_POS
    destination: GridPos | None = None
    finale_unlocked: bool = False
    result: str | None = None             # None | "won" | "lost"
    notice: str | None = None             # last rejection message, drawn by title/shop scenes
    last_account_code: str | None = None  # set on win, drawn by GameOverScene
    lose_reason: str | None = None        # set on loss, drawn by GameOverScene

    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]

    # helpers other tasks rely on:
    def free_snares(self) -> int          # loadout.count("snare") - snares_full; 0 if loadout is None
    def able_cleaners(self) -> int        # CLEANER_COUNT - len(self.slimed)
    def _reset(self) -> None              # reinitialize EVERY field except rng.
        # CONVENTION: NewGame and Continue both route through _reset(); every
        # task that adds a Game field MUST add that field's reinitialization
        # to _reset() in the same task. Rejection handlers set self.notice;
        # AccountAccepted/ItemBought/VehicleSelected clear it to None.

def new_game(seed: int) -> Game           # Game(rng=make_rng(seed))
```

Canonical `Game.tick` internal order (all tasks slot into this exact shape):
1. Command dispatch: `for command in commands: self._dispatch(command, events)`
   (per-command, scene-gated handlers; invalid commands are ignored or answered
   with PurchaseRejected/CommandRejected).
2. Scene ticking, AFTER the dispatch loop, using the CURRENT scene:
   world scenes (MAP, DRIVE, BUST): clock.advance, psi.advance(dt, pre-tick
   active_haunts), city.tick, mascot.tick; DRIVE additionally ticks drive;
   BUST additionally ticks bust (ACTIVE phase only); FINALE ticks ONLY finale
   (world frozen).
3. Post-tick resolution: WispReachedTower -> psi.spike; one-shot
   FinaleUnlocked; drive arrival -> _arrive_at routing; bust RESOLVED
   handling; finale outcome handling; bankruptcy check.

Behavioural contract for `Game.tick` (implemented incrementally across tasks):
- Every SceneChanged transition appends `SceneChanged(new_scene)`.
- World time (clock, psi, city, mascot) advances ONLY in scenes MAP, DRIVE, BUST.
- TITLE: `NewGame(name)` -> fresh state, SHOP. `EnterAccount(name, code)` ->
  decode; ok -> AccountAccepted + bankroll restored + SHOP; bad -> AccountRejected, stay.
- SHOP: SelectVehicle (deduct price, create Loadout) -> VehicleSelected or
  PurchaseRejected("cannot afford"). BuyItem -> checks vehicle chosen, funds,
  capacity -> ItemBought or PurchaseRejected(reason). FinishShopping: requires
  vehicle -> MAP.
- MAP: SetDestination(pos) -> if pos == position: handle arrival immediately;
  else create DriveSim(distance=city.distance(position, pos), speed=vehicle.speed,
  has_vacuum=loadout.has("vacuum"), has_lens=loadout.has("lens")) -> DRIVE,
  TravelStarted. WispReachedTower events from city.tick -> psi.spike(WISP_TOWER_PSI_JUMP).
  psi.at_max first time -> finale_unlocked=True, FinaleUnlocked event.
  BuyItem("snare") accepted while position == DEPOT_POS (wallet + capacity
  checks as in SHOP) -> ItemBought or PurchaseRejected — the mid-game restock
  the bankruptcy rule presupposes. BuyItem for any other item or away from
  the Depot -> PurchaseRejected("snares only, at the Depot").
- Arrival routing is ONE method, `_arrive_at(pos)`, an if/elif chain ending in
  an `else` that routes to MAP. Later tasks insert their `elif` branches
  (tower before haunted before the else). Every arrival emits Arrived(pos).
- DRIVE: Steer; drive.tick; each WispCaptured -> wallet.earn(VACUUM_BOUNTY)
  AND removes one wisp from city.wisps if any remain (road wisps represent
  the city population);
  arrived -> position=destination, Arrived(pos); route via _arrive_at:
  pos == DEPOT_POS -> snares_full=0, contained=0, slimed.clear(),
  SnaresEmptied + CleanersRestored, -> MAP;
  pos == TOWER_POS and finale_unlocked -> FINALE (FinaleSim(able_cleaners=able_cleaners()));
  pos haunted and free_snares() > 0 and able_cleaners() >= 2 -> BUST (new BustSim);
  else -> MAP.
- BUST: MoveCleaner/PlaceCleaner/LaySnare(=place in SNARE phase)/SpringSnare;
  SpringSnare outside the ACTIVE phase -> CommandRejected("no snare laid");
  bust.tick; on RESOLVED: CAUGHT -> snare accounting (rig with space: contained+=1
  else snares_full+=1), fee=bust_fee(psi.value), wallet.earn(fee), GhostTrapped(fee),
  city.clear_haunt(position), HauntCleared; MISSED -> snares_full accounting
  unchanged but one snare spent (snares_full += 1 only on catch — a missed
  snare is spent: model as snares_full += 1? NO — exact rule: a snare is
  consumed on CAUGHT (holds ghost) and on MISSED/BACKFIRE it is wasted:
  loadout.counts["snare"] -= 1). SLIMED -> CleanerSlimed(idx) where idx is the
  lowest unslimed index for side; BACKFIRE -> both participating cleaners slimed,
  BeamsCrossed already emitted, snare wasted. After resolution -> MAP.
  If a stomp fires while busting, it still applies.
- Mascot handling in world tick: StompTriggered from mascot.tick ->
  pick rng.choice(city.stompable_positions()), fine=wallet.fine(STOMP_FINE),
  psi.spike(STOMP_PSI_SPIKE), BuildingStomped(pos, fine). MascotAlert only
  fires when loadout.has("sensor"). DeployBait command: if mascot ALERT and
  loadout.use_bait() -> BaitDeployed (no stomp).
- FINALE: StartRun; finale.tick (world frozen); outcome WON ->
  if wallet.balance > starting_bankroll: result="won",
  GameWon(encode_account(player_name, wallet.balance)) else result="lost",
  GameLost("the franchise never turned a profit"); LOST -> result="lost",
  GameLost("the Tower claimed the city"). -> GAME_OVER.
  Endgame resolution also records last_account_code (on win) and
  lose_reason (on any loss) for GameOverScene to draw.
- Bankruptcy check (post-tick resolution step, world scenes, only once
  loadout is not None): the franchise folds when it cannot field a snare by
  ANY means: free_snares() == 0 AND snares_full == 0 AND
  wallet.balance < ITEMS["snare"].price (snares are re-buyable at the Depot,
  and full snares are emptied there). When all three hold:
  result="lost", lose_reason="no snares left — the franchise folds",
  GameLost(lose_reason) -> GAME_OVER.
- GAME_OVER: Continue -> fresh TITLE state (new_game keeps rng).

## Shell contracts

```python
# shell/app.py
LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)
WINDOW_SCALE: Final[int] = 2
FPS: Final[int] = 60

class App:
    def __init__(self, seed: int | None = None) -> None
        # pygame.init(); window LOGICAL_SIZE*WINDOW_SCALE; logical Surface;
        # game = new_game(seed if seed is not None else int.from_bytes(os.urandom(4)))
        # gfx = SpriteFactory(); text = TextRenderer(); audio = AudioBank()
    def step(self, dt: float) -> None       # one frame: gather pygame events ->
        # scene.commands() -> game.tick -> audio cues -> scene.draw -> scale-blit
    def run(self) -> None                   # clock loop at FPS until QUIT
def main() -> None
    # console entry. MUST be exception-safe:
    #   app = App()
    #   try: app.run()
    #   finally: pygame.quit()

SCENES: Final[dict[SceneId, Scene]]
    # module-level registry, written as an EXPLICIT dict literal with one
    # entry per SceneId (placeholders first; later tasks change one entry's
    # value in place, e.g. `SceneId.SHOP: ShopScene(),`)
```

```python
# shell/scenes/* — each module exposes one class implementing:
class Scene(Protocol):                       # defined in shell/scenes/__init__.py
    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]: ...
    def draw(self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer) -> None: ...
```
Class names: TitleScene, ShopScene, CityMapScene, DrivingScene, BustingScene,
FinaleScene, GameOverScene.

Scene behaviour notes:
- TitleScene and ShopScene draw `game.notice` (rejection feedback) when set.
- CityMapScene, residue detector effect: wisps are drawn and haunted
  buildings FLASH (alternate normal/haunted sprite at ~2 Hz) only when
  loadout.has("detector"); without it, haunted buildings render as the
  static haunted sprite and wisps are invisible.
- Mascot alert UI (flashing banner + B-key -> DeployBait) exists in ALL
  three world scenes: CityMapScene, DrivingScene, BustingScene — alerts can
  fire during any of them.
- Sprite builders are module-level zero-argument functions registered in a
  module-level `_BUILDERS: dict[str, Callable[[], pygame.Surface]]` in
  shell/gfx.py; never instance methods.

```python
# shell/gfx.py
class SpriteFactory:
    def get(self, name: str) -> pygame.Surface   # cached, generated on demand
```
Sprite names used by scenes, with FINAL pixel sizes (the polish milestone
lands these exact sizes; earlier placeholder sizes may differ, and earlier
tests must not pin sprite sizes): cars 48x28 ("car.compact" "car.hearse"
"car.wagon" "car.performance"), "wisp"/"wisp.faint" 24x24 (faint variant
must include alpha value 90), "smudge" 48x48, "cleaner"/"cleaner.slimed"
24x40, "building"/"building.haunted" 48x56, "tower" 56x96, "depot" 56x48,
"mascot" 72x96, "snare" 32x16, "logo" 320x96.

```python
# shell/audio.py
SAMPLE_RATE: Final[int] = 22050
class AudioBank:
    def __init__(self, enabled: bool = True) -> None   # disabled or mixer-init failure -> all methods are no-ops
    def play(self, name: str) -> None
    def play_music_loop(self) -> None      # loops build_theme() with loops=-1
    def stop_music(self) -> None
def synth_square(freq: float, ms: int, volume: float = 0.5) -> bytes   # raw 16-bit signed mono LE @ SAMPLE_RATE
def synth_noise(ms: int, volume: float = 0.5) -> bytes
NOTE_HZ: Final[dict[str, float]]           # C4..C6 equal temperament, A4=440
THEME: Final[list[tuple[str, int]]]        # (note name or "" rest, ms) — original composition
def build_theme() -> bytes
```
Sound names: "catch" "trap" "miss" "backfire" "slime" "stomp" "alert" "bait"
"enter" "squash" "win" "lose" "buy" "reject" "theme".
Event->sound map lives in app.py: `EVENT_SOUNDS: Final[dict[type[Event], str]]`.
EVENT_SOUNDS is built once in the audio milestone; earlier milestones must
NOT define it. Tests assert specific mappings are present (subset), never
exact dict equality. App and its step() gain `self.audio` only in the audio
milestone (App is game/gfx/text-only before that).

```python
# shell/text.py
class TextRenderer:
    def __init__(self) -> None                  # pygame.font.Font(None, ...) cache per size
    def draw(self, surface: pygame.Surface, message: str, pos: tuple[int, int],
             size: int = 16, color: tuple[int, int, int] = (230, 230, 230)) -> None
```

## Tooling contract

- pyproject: `[dependency-groups] dev = ["pytest", "pytest-cov", "hypothesis", "ruff", "mypy", "pre-commit"]`
- `[project.scripts] psychic-cleaners = "psychic_cleaners.shell.app:main"`
- ruff: `line-length = 100`, `target-version = "py314"`, lint select
  `["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF"]`
- mypy: `strict = true`, `files = ["src", "tests"]`, `mypy_path = ["src"]`,
  `explicit_package_bases = true` (tests tree has no __init__.py files)
- pytest: `testpaths = ["tests"]`; coverage via `--cov=psychic_cleaners --cov-report=term-missing`
  (fail-under added only in the final task)
- tests/conftest.py sets `os.environ.setdefault("SDL_VIDEODRIVER", "dummy")`
  and `SDL_AUDIODRIVER=dummy` at import time, provides `rng` fixture = `make_rng(1234)`
- Every command in plan steps runs through uv: `uv run pytest ...`, `uv run ruff check .`,
  `uv run mypy`.
- Commit style: conventional commits (`feat:`, `test:`, `chore:`, `ci:`).
- The strings "Ghostbusters", "Slimer", "Stay-Puft", "Zuul", "Ecto" must never
  appear in code, tests, assets, or comments — theme names only.

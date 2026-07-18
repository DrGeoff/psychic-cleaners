# In-Game Quit Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the player press Escape in any scene to open a "Quit? (Y/N)" overlay that pauses the simulation, and confirm or cancel with Y/Enter or N/Escape.

**Architecture:** A single `_quit_confirm: bool` flag lives on `App` (`src/psychic_cleaners/shell/app.py`). `App.step()` intercepts `KEYDOWN` events for Escape/Y/Return/N before they reach the active scene, decides whether to call `Game.tick()` at all this frame, and draws a small overlay box after the scene's own `draw()` when the flag is set. No new `Command`/`Event` types, no scene-level changes — this is purely a shell/meta concern.

**Tech Stack:** Python, pygame (existing `TextRenderer` for overlay text, existing `pygame.draw.rect` for the overlay box). Tests use pytest with pygame's dummy SDL drivers (already configured for this repo's headless test suite — see existing `tests/shell/test_app_smoke.py` for the pattern of posting synthetic `pygame.event.Event`s and calling `App.step()` directly).

## Global Constraints

- Escape opens the overlay in every scene (Title, Shop, Map, Drive, Bust, Finale, Game Over) — this is app-global, not per-scene.
- While the overlay is open, `Game.tick()` must not be called (simulation pauses) and no events reach `scene.commands()`.
- `Y` or `Enter` confirms quit → `App.running = False`. `N` or `Escape` cancels → overlay closes, next frame's input reaches the scene normally again.
- `pygame.QUIT` (window close) keeps working unconditionally, overlay open or not.
- No new `Command`/`Event` types in `core/events.py` — this stays entirely inside `App`.

---

## File Structure

- **Modify:** `src/psychic_cleaners/shell/app.py` — add the `_quit_confirm` flag, the interception logic in `step()`, and the overlay draw call.
- **Test:** `tests/shell/test_quit_confirm.py` — new file, following the `App`-driving pattern already used in `tests/shell/test_app_smoke.py` and `tests/shell/test_app_transitions.py`.

---

### Task 1: Escape opens the overlay and pauses the tick

**Files:**
- Modify: `src/psychic_cleaners/shell/app.py`
- Test: `tests/shell/test_quit_confirm.py`

**Interfaces:**
- Consumes: `App.__init__` (existing), `App.step(dt: float) -> None` (existing), `pygame.event.Event` with `type=pygame.KEYDOWN, key=pygame.K_ESCAPE`.
- Produces: `App._quit_confirm: bool` attribute, initialized `False` in `__init__`. Later tasks (2, 3, 4) read and mutate this same attribute — do not rename it.

- [ ] **Step 1: Write the failing test**

Create `tests/shell/test_quit_confirm.py`:

```python
"""Escape-to-quit confirmation overlay: App.step intercepts input while it's open."""

import pygame

from psychic_cleaners.core.events import NewGame, SceneId
from psychic_cleaners.shell.app import App


def test_escape_opens_quit_confirm_and_pauses_tick() -> None:
    app = App(seed=1)
    try:
        app.game.tick([NewGame("Ada")], 0.0)  # TITLE -> SHOP, so a tick would be visible
        scene_before = app.game.scene
        assert app._quit_confirm is False
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        app.step(1 / 60)
        assert app._quit_confirm is True
        assert app.game.scene is scene_before  # tick was skipped, not just a no-op transition
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_quit_confirm.py::test_escape_opens_quit_confirm_and_pauses_tick -v`
Expected: FAIL with `AttributeError: 'App' object has no attribute '_quit_confirm'`

- [ ] **Step 3: Add the flag and interception to `App`**

In `src/psychic_cleaners/shell/app.py`, add `_quit_confirm` to `__init__` (right after `self.running = True`):

```python
        self.running = True
        self._quit_confirm = False
```

Replace the body of `step()` (currently starting `events = pygame.event.get()` through the `scene = SCENES[self.game.scene]` / `commands = scene.commands(...)` / `game_events = self.game.tick(...)` block) with:

```python
    def step(self, dt: float) -> None:
        events = pygame.event.get()
        quit_confirmed = False
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if not self._quit_confirm and event.key == pygame.K_ESCAPE:
                    self._quit_confirm = True
                elif self._quit_confirm:
                    if event.key in (pygame.K_y, pygame.K_RETURN):
                        quit_confirmed = True
                    elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                        self._quit_confirm = False
        if quit_confirmed:
            self.running = False
        if self._quit_confirm:
            SCENES[self.game.scene].draw(self.logical, self.game, self.gfx, self.text)
            self._draw_quit_overlay()
            pygame.transform.scale(self.logical, self.window.get_size(), self.window)
            pygame.display.flip()
            return
        scene = SCENES[self.game.scene]
        commands = scene.commands(events, self.game, dt)
        game_events = self.game.tick(commands, dt)
        for game_event in game_events:
            sound_name = EVENT_SOUNDS.get(type(game_event))
            if sound_name is not None:
                self.audio.play(sound_name)
        if self.game.scene is not self._prev_scene:
            if self.game.scene is SceneId.TITLE:
                self.audio.play_music_loop()
                _reset_scene_singletons()
            elif self._prev_scene is SceneId.TITLE:
                self.audio.stop_music()
            self._prev_scene = self.game.scene
        # Re-resolve after the tick: when a tick changes the scene, the
        # transition frame must draw the NEW scene against the new game state,
        # not the pre-tick scene that gathered this frame's commands.
        SCENES[self.game.scene].draw(self.logical, self.game, self.gfx, self.text)
        pygame.transform.scale(self.logical, self.window.get_size(), self.window)
        pygame.display.flip()
```

Note: `quit_confirmed` is intentionally applied (`self.running = False`) *before* the early-return overlay draw, so a confirmed quit still renders one last frame instead of leaving stale state — matching `App.run()`'s `while self.running:` loop, which will exit before the next `step()` call.

`_draw_quit_overlay` is added in Task 2; leave it undefined for now — this step alone will fail at runtime once `_quit_confirm` is `True`, but Task 1's test only exercises the opening frame, and the overlay draw only executes when `_quit_confirm` is already `True` *before* this frame's events are processed... actually re-check: in Step 1's test, Escape is posted and processed in the same `step()` call that flips `_quit_confirm` to `True`, and the `if self._quit_confirm:` branch below runs in that same call. So `_draw_quit_overlay` must exist by the end of this task. Add a minimal version now (a full version lands in Task 2 without changing its signature):

```python
    def _draw_quit_overlay(self) -> None:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/shell/test_quit_confirm.py::test_escape_opens_quit_confirm_and_pauses_tick -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest -q`
Expected: All tests pass (existing `test_step_handles_quit_event` and friends in `test_app_smoke.py` must still pass — `pygame.QUIT` handling is unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/shell/app.py tests/shell/test_quit_confirm.py
git commit -m "feat: pause simulation and open quit-confirm state on Escape"
```

---

### Task 2: Draw the confirmation overlay

**Files:**
- Modify: `src/psychic_cleaners/shell/app.py`
- Test: `tests/shell/test_quit_confirm.py`

**Interfaces:**
- Consumes: `App._quit_confirm` (Task 1), `App.text: TextRenderer` (existing), `App.logical: pygame.Surface` (existing), `TextRenderer.draw(surface, message, pos, size=16, color=(230,230,230)) -> None` (existing, `src/psychic_cleaners/shell/text.py`).
- Produces: `App._draw_quit_overlay(self) -> None` — fully implemented, replacing Task 1's stub. No other task depends on its internals, only that it draws the box+text onto `self.logical`.

- [ ] **Step 1: Write the failing test**

Add to `tests/shell/test_quit_confirm.py`:

```python
def test_quit_overlay_draws_prompt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(seed=1)
    try:
        drawn: list[str] = []
        original_draw = app.text.draw

        def _recording_draw(surface, message, pos, size=16, color=(230, 230, 230)):
            drawn.append(message)
            return original_draw(surface, message, pos, size=size, color=color)

        monkeypatch.setattr(app.text, "draw", _recording_draw)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        app.step(1 / 60)
        assert any("Quit" in message for message in drawn)
    finally:
        pygame.quit()
```

Add `import pytest` to the top of `tests/shell/test_quit_confirm.py` alongside the existing `import pygame`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_quit_confirm.py::test_quit_overlay_draws_prompt_text -v`
Expected: FAIL with `assert False` (the stub `_draw_quit_overlay` draws nothing, so `drawn` is empty)

- [ ] **Step 3: Implement `_draw_quit_overlay`**

Replace the Task 1 stub in `src/psychic_cleaners/shell/app.py`:

```python
    def _draw_quit_overlay(self) -> None:
        box = pygame.Rect(0, 0, 260, 60)
        box.center = (LOGICAL_SIZE[0] // 2, LOGICAL_SIZE[1] // 2)
        pygame.draw.rect(self.logical, (14, 10, 38), box)
        pygame.draw.rect(self.logical, (255, 214, 90), box, width=2)
        self.text.draw(
            self.logical,
            "Quit Psychic Cleaners? (Y/N)",
            (box.left + 18, box.top + 22),
            size=16,
            color=(230, 230, 230),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/shell/test_quit_confirm.py -v`
Expected: Both tests in the file PASS

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest -q`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/shell/app.py tests/shell/test_quit_confirm.py
git commit -m "feat: draw the quit-confirm overlay box and prompt text"
```

---

### Task 3: Y/Enter confirms, N/Escape cancels, other keys are swallowed

**Files:**
- Modify: none (interception logic already written in Task 1's `step()` rewrite — this task is test-only, verifying the branches already implemented)
- Test: `tests/shell/test_quit_confirm.py`

**Interfaces:**
- Consumes: `App._quit_confirm`, `App.running`, `App.step` — all from Task 1. No production code changes; Task 1's `step()` already implements the Y/N/other-key branching. This task's job is to pin that behavior down with tests so a future refactor can't silently break it.

- [ ] **Step 1: Write the failing/passing tests**

Add to `tests/shell/test_quit_confirm.py`:

```python
def _open_quit_confirm(app: App) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app.step(1 / 60)
    assert app._quit_confirm is True


def test_y_confirms_quit() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()


def test_return_confirms_quit() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()


def test_n_cancels_and_resumes_scene_input() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
        app.step(1 / 60)
        assert app._quit_confirm is False
        assert app.running is True
        # Next frame's input must reach the scene again: TITLE -> SHOP via NewGame
        # requires TitleScene.commands to see the Enter keypress and a non-empty name.
        from psychic_cleaners.core.events import SceneId

        assert app.game.scene is SceneId.TITLE
    finally:
        pygame.quit()


def test_escape_again_cancels() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        app.step(1 / 60)
        assert app._quit_confirm is False
        assert app.running is True
    finally:
        pygame.quit()


def test_other_key_is_swallowed_while_confirming() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        app.step(1 / 60)
        assert app._quit_confirm is True
        assert app.running is True
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/shell/test_quit_confirm.py -v`
Expected: All PASS immediately — Task 1's `step()` rewrite already implements this branching. If any fail, fix `step()`'s `KEYDOWN` branch (added in Task 1) to match: `K_y`/`K_RETURN` → `quit_confirmed = True`; `K_n`/`K_ESCAPE` → `self._quit_confirm = False`; anything else while `self._quit_confirm` is `True` → no state change.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/shell/test_quit_confirm.py
git commit -m "test: pin down quit-confirm Y/N/cancel/swallow behavior"
```

---

### Task 4: Verify no scene sees input while the overlay is open, and window-close still works

**Files:**
- Modify: none
- Test: `tests/shell/test_quit_confirm.py`

**Interfaces:**
- Consumes: `App._quit_confirm`, `App.step`, `SCENES` dict (existing, from `psychic_cleaners.shell.app`), `monkeypatch.setattr` on a scene's `commands` method (same pattern as `test_app_smoke.py::test_step_plays_sound_for_mapped_game_event`).

- [ ] **Step 1: Write the test**

Add to `tests/shell/test_quit_confirm.py`:

```python
def test_scene_commands_not_called_while_confirming(monkeypatch: pytest.MonkeyPatch) -> None:
    from psychic_cleaners.core.events import SceneId
    from psychic_cleaners.shell.app import SCENES

    app = App(seed=1)
    try:
        title_scene = SCENES[SceneId.TITLE]
        calls: list[object] = []
        original_commands = title_scene.commands
        monkeypatch.setattr(
            title_scene,
            "commands",
            lambda events, game, dt: (calls.append(1), original_commands(events, game, dt))[1],
        )
        _open_quit_confirm(app)
        assert calls == []  # the Escape keydown itself must not reach scene.commands
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        app.step(1 / 60)
        assert calls == []  # still swallowed on the following frame
    finally:
        pygame.quit()


def test_window_close_still_works_while_confirming() -> None:
    app = App(seed=1)
    try:
        _open_quit_confirm(app)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/shell/test_quit_confirm.py -v`
Expected: All PASS — Task 1's `step()` already returns early (skipping `scene.commands()`) whenever `self._quit_confirm` is `True` after processing events, and the `pygame.QUIT` check runs unconditionally at the top of the event loop regardless of `_quit_confirm`.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: All tests pass, zero failures, zero errors.

- [ ] **Step 4: Lint and type-check**

Run: `uv run ruff check src/psychic_cleaners/shell/app.py tests/shell/test_quit_confirm.py`
Run: `uv run ruff format --check src/psychic_cleaners/shell/app.py tests/shell/test_quit_confirm.py`
Run: `uv run mypy src/psychic_cleaners/shell/app.py`
Expected: No errors from any of the three. Fix any reported issues (e.g. missing type annotations on new test helpers — `_open_quit_confirm(app: App) -> None` already annotated above) before proceeding.

- [ ] **Step 5: Commit**

```bash
git add tests/shell/test_quit_confirm.py
git commit -m "test: confirm scene input is swallowed and window-close still works during quit-confirm"
```

---

## Manual Verification (optional but recommended)

After all four tasks are committed, use the `run` skill or `uv run psychic-cleaners` (check `pyproject.toml` for the actual entry point script name) to launch the real app and confirm by hand:
- Escape during the Title screen's name entry does NOT type into the name field, and opens the overlay.
- Escape during Driving/Busting freezes the action; Y quits the process; N resumes exactly where it was.
- Escape twice in a row (open, then cancel) leaves normal play completely unaffected.

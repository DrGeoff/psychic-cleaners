# In-game quit confirmation

## Problem

The only ways to exit Psychic Cleaners are closing the window (`pygame.QUIT`)
or Ctrl-C in the terminal. There is no in-game key to quit, and no
confirmation step to guard against an accidental exit mid-game.

## Behavior

Pressing `Escape` in any scene opens a "Quit? (Y)es / (N)o" overlay drawn on
top of the current scene. While the overlay is open:

- `Game.tick` is skipped — the simulation pauses. Driving, busting, and any
  timers freeze until the player answers.
- `Y` or `Enter` confirms: the app stops (`App.running = False`), the same
  clean-exit path as closing the window.
- `N` or `Escape` again cancels: the overlay closes and play resumes exactly
  where it left off.
- All other input is swallowed while the overlay is open — it never reaches
  the active scene, so e.g. driving controls or the Title screen's text
  entry can't leak through underneath the overlay.

This applies globally, in every scene (Title, Shop, Map, Drive, Bust,
Finale, Game Over) — it is a shell-level "meta" action, not part of any
scene's own flow.

## Implementation

Lives entirely in `App` (`src/psychic_cleaners/shell/app.py`) — not in
`core/` and not in individual scene modules. It needs no new `Command` or
`Event` type since it never touches game state; it only decides whether to
call `Game.tick` this frame.

Add `_quit_confirm: bool = False` to `App.__init__`. In `App.step()`, before
dispatching events to the active scene:

1. Pull `KEYDOWN` events out of this frame's event list.
2. If `_quit_confirm` is `False` and `Escape` was pressed: set it `True`.
   Skip `scene.commands()` / `Game.tick()` this frame.
3. If `_quit_confirm` is `True`: check this frame's `KEYDOWN` events for
   `Y`/`Return` (quit — set `App.running = False`) or `N`/`Escape` (cancel —
   set `_quit_confirm` back to `False`). Skip `scene.commands()` /
   `Game.tick()` regardless of which key was pressed, or none.
4. In both cases (opening or already open), no events reach
   `scene.commands()` this frame — the scene's own input handling is fully
   paused while the overlay is up.
5. `pygame.QUIT` (window close) is still handled unconditionally, overlay or
   not.

Draw order: run the active scene's normal `draw()` first (so the frozen
game state is visible underneath), then if `_quit_confirm` is `True`, draw
a centered semi-transparent box (~200x50px) with the text
`"Quit Psychic Cleaners? (Y/N)"` using the existing `TextRenderer`.

## Testing

Add a test (new file `tests/shell/test_quit_confirm.py`, following the
existing `tests/shell/test_app_*.py` pattern of driving `App` with synthetic
`pygame.event.Event` objects):

- Escape opens the overlay; `Game.tick` is not invoked that frame (game
  state, e.g. the current scene or a counter, is unchanged from before the
  keypress).
- With the overlay open, `Y` sets `App.running` to `False`.
- With the overlay open, `N` closes the overlay and a subsequent frame's
  input reaches the scene normally again (game state resumes changing).
- Any other key while the overlay is open is swallowed: it doesn't reach
  the scene and doesn't close the overlay.

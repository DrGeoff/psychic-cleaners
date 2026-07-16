# Scripted playtests

Self-checking end-to-end playtests that drive the **real `App`** (headless, via
posted pygame events) rather than the core API. They caught most of the bugs the
unit suite couldn't: scene-transition state leaks, notice lifetimes, draw-order
regressions, economy balance problems.

pytest does **not** collect these (they don't match `test_*.py` on purpose —
each takes seconds to minutes). Run them by hand when touching scene routing,
the economy, or App-level behavior:

```sh
uv run python tests/playtests/playtest.py 12345 --inject-profit
uv run python tests/playtests/playtest2.py
uv run python tests/playtests/playtest3.py
uv run python tests/playtests/drive3.py
uv run python tests/playtests/playtest_beam_crossing.py
```

Each prints `[PASS]`/`[FAIL]` per check and exits non-zero on any failure.

| Script | Covers | ~Runtime |
| --- | --- | --- |
| `playtest.py` | Full playthrough: title → shop → depot → drive → bust (catch + miss) → mascot → finale → restart/restore, with an independent economy ledger asserted every tick. `--inject-profit` exercises the win + account-code path; omit it for the loss path. | 2–4 min |
| `playtest2.py` | Failure scenarios the happy path can't stage: backfire, turn-aways, containment rig, fold, profit boundary, codec fuzz (round-trips, typos, wrong name), pixel checks (banner, wisp visibility). | 1–2 min |
| `playtest3.py` | Round-2 fix verification: name clamp, bait stacking, notice expiry, haunt visible under the tower, immediate arrival on the current cell, faint-wisp lens rules, wallet clamp. | ~1 min |
| `drive3.py` | Round-1 fix verification through the real UI: rejected-code field survival, notice scoping, slimed turn-aways, tower turn-away vs. loss, depot restore. | ~1 min |
| `playtest_beam_crossing.py` | Beam-crossing backfire mechanic (2026-07-16): narrow cleaner gap + off-center ghost sunk to the ground fires `BeamsCrossed` independently of `sunk_between`; wide cleaner gap (≥300px) stays immune at the same depth. Ghost position is injected directly on the real `BustSim` after real input reaches `ACTIVE`, isolating the geometry check from drift/sink timing. | ~10 s |

Notes:

- Seeded and deterministic; screenshots land in `tests/playtests/shots*/`
  (gitignored).
- `SDL_NO_SIGNAL_HANDLERS=1` is set by the scripts so `timeout N ...` can kill
  a wedged run (SDL otherwise swallows SIGTERM as an unpolled SDL_QUIT event).
- The suites share one process-wide pygame; `playtest2.py`/`playtest3.py`
  import helpers from `playtest.py`, so run them from this directory or via
  the repo-root commands above.
- These scripts are exempt from mypy (see `pyproject.toml`); keep them
  ruff-clean.

# Audio polish: SFX pass, chord synthesis, karaoke sync — design

Date: 2026-07-16
Status: Approved pending user review

## 1. Background

The design doc's milestone 10 ("Polish") lists three items: "chiptune theme
with karaoke ball, SFX pass, balance calibration". The chiptune theme and a
bouncing-ball karaoke lyric line already exist (`shell/audio.py`,
`shell/scenes/title.py`, commit `c69c749`), but two gaps remain:

- The karaoke ball advances on a flat 500ms-per-word clock
  (`_draw_karaoke` in `title.py`) while the theme it's meant to track is a
  3000ms loop built from 16 notes of uneven length (150/300ms) — the ball
  drifts out of sync with the music on every loop.
- Several gameplay events carry no sound at all (`RentCharged`, `LoanTaken`,
  `LoanRepaid`, `TravelStarted`, `Arrived`, `HauntStarted`, `HauntCleared`,
  `WispReachedTower`, `SnaresEmptied`, `CleanersRestored`,
  `ConvergenceStarted`, `FinaleUnlocked`, `VehicleSelected`,
  `AccountAccepted`), and the 14 sounds that do exist are single-voice
  square/noise tones with instant on/off (audible clicks, no envelope,
  no chords) — a first pass, not the intended quality bar.

This spec covers both remaining polish items: the SFX pass (fill the gaps,
raise synthesis quality, rebalance volumes) and the karaoke-ball sync fix.

## 2. Goals

- Every gameplay event the shell can plausibly react to has a distinct,
  audible sound (excluding events that never reach the shell or would fire
  too often to be meaningful — see Non-goals).
- Synthesized sounds sound closer to an actual SID-chip voice: shaped
  ADSR envelopes (no more clicks), more than one waveform, and multi-voice
  chords where a single tone reads thin.
- Volumes are rebalanced as a deliberate pass, not left at each recipe's
  original ad hoc guess.
- The karaoke ball tracks the theme's actual note timing, so the highlighted
  word always lines up with the notes playing under it, indefinitely (no
  drift across loop boundaries).

## 3. Non-goals

- No new audio assets/files — synthesis stays 100% code-generated per the
  project's clean-room constraint (README, design doc §2).
- No sound for `StompTriggered` (internal-only event; `Game` consumes and
  converts it to `BuildingStomped` before the shell ever sees it —
  `core/game.py:311-314`) or `SceneChanged` (fires on every scene
  transition; a blanket sound here would be noise, not signal).
- No numpy or other new dependency — buffers stay small (sub-second,
  built once at `AudioBank.__init__`) and pure-Python generation is already
  the established pattern.
- No changes to *which* events the core game emits — this spec only adds
  shell-side sound reactions to events that already exist.

## 4. Mechanism

### 4.1 Synthesis engine (`shell/audio.py`)

Add:

- `synth_voice(wave, freq_hz, ms, volume, *, attack_ms=5, decay_ms=10, sustain=0.7, release_ms=15) -> bytes`
  — one enveloped voice. `wave` is one of `"square" | "triangle" |
  "sawtooth" | "noise"`. The envelope is a straightforward linear
  attack → linear decay to `sustain` level → hold → linear release,
  applied as a multiplier over the raw waveform sample-by-sample.
- `mix(*voices: bytes) -> bytes` — sums same-channel int16 buffers
  sample-by-sample (zero-padding shorter buffers to the longest one),
  clamped to `[-32767, 32767]` to avoid wraparound distortion. This is
  what makes chords (e.g. a root+fifth dyad) possible without a second
  mixer channel.
- `synth_square(freq, ms, volume=0.5)` and `synth_noise(ms, volume=0.5)`
  become thin wrappers: `synth_voice("square", ...)` /
  `synth_voice("noise", ...)` with the engine's default envelope. Existing
  call sites (`_seq`, `_RECIPES`, `build_theme`) keep their signatures.
- `MASTER_VOLUME: Final[float] = 0.6` applied once when each
  `pygame.mixer.Sound` is constructed in `AudioBank.__init__`, so the
  rebalance pass has one global knob plus per-recipe relative volumes.

### 4.2 Sound catalogue

All 14 existing recipes (`catch`, `trap`, `miss`, `backfire`, `slime`,
`stomp`, `alert`, `bait`, `enter`, `squash`, `win`, `lose`, `buy`, `reject`)
are rebuilt on the new engine: enveloped, and — where a single tone reads
thin (`catch`, `win`, `trap`) — voiced as a `mix()` chord rather than a
monophonic run. Relative volumes are reviewed together so impact/danger
sounds (`stomp`, `backfire`, `squash`) read louder than transient
confirmations (`buy`, `select`).

New recipes, added to `_RECIPES` and `EVENT_SOUNDS` (`shell/app.py`):

| Event | Recipe | Character |
|---|---|---|
| `AccountAccepted` | `login` | Warm rising dyad |
| `VehicleSelected` | `select` | Short confirm blip, quiet |
| `TravelStarted` | `depart` | Two-note engine-rev square |
| `RentCharged` | `rent` | Descending minor stab |
| `LoanTaken` | `loan` | Bright ascending arpeggio |
| `LoanRepaid` | `repay` | Short descending confirm, brighter than `rent` |
| `Arrived` | `arrive` | Soft double-blip |
| `HauntStarted` | `haunt` | Detuned triangle+square beat, eerie |
| `HauntCleared` | `clear` | Resolving triad |
| `WispReachedTower` | `breach` | Descending noise+square, ominous |
| `SnaresEmptied` and `CleanersRestored` | `dayroll` (shared) | Day-rollover chime — both events always fire together on a day boundary (`core/game.py:528-529`), so one recipe covers both mapping entries |
| `ConvergenceStarted` | `converge` | Low drone swell |
| `FinaleUnlocked` | `unlock` | Fanfare stinger |

### 4.3 Karaoke-ball sync (`shell/scenes/title.py`)

Replace the flat-clock word index with real note-timing boundaries derived
from `audio.THEME`:

- At module load, group `THEME`'s 16 `(note, ms)` entries into 8 pairs (one
  pair per `KARAOKE_WORDS` entry, matching the theme's existing "2 bars per
  word" structure) and compute cumulative-ms boundaries, e.g.
  `WORD_BOUNDARIES_MS: Final[tuple[int, ...]]` — the end-time of each word's
  window, and `THEME_TOTAL_MS` (the sum, currently 3000).
- `_draw_karaoke` looks up the active word via
  `elapsed_ms = int(elapsed * 1000) % THEME_TOTAL_MS`, then finds which
  boundary bracket it falls into (linear scan over 8 entries — cheap, no
  need for bisect).
- Behavior stays pure-presentation / simulated-time only, consistent with
  the existing docstring's determinism requirement (no wall-clock reads).

## 5. Rejected alternatives

- **Numpy-based mixing.** Would simplify `mix()`'s sample summation, but
  the project has zero numpy dependency today and these buffers are small
  enough that pure-Python sample loops (already the established pattern in
  `synth_square`/`synth_noise`) stay fast enough at startup-only
  generation time.
- **Per-word independent audio splice instead of boundary math.** Slicing
  the actual theme audio into 8 labeled segments and driving the ball off
  playback position was considered, but `pygame.mixer.Sound` doesn't expose
  frame-accurate playback position, and simulated-time determinism (the
  existing constraint) is easier to keep with a precomputed boundary table
  than with any form of playback introspection.
- **Sound for every event including `StompTriggered`/`SceneChanged`.**
  Rejected per Non-goals — one is unreachable from the shell, the other
  fires too often to carry meaning.

## 6. Compatibility and testing plan

- `tests/shell/test_audio.py`:
  - Update `test_square_alternates_at_expected_period` to assert alternation
    in the envelope's steady-state region, not from sample 0 (the new
    default envelope has a short attack ramp).
  - New tests: `synth_voice` produces correct byte length and envelope
    shape (near-zero at sample 0, ramping up) for each waveform; `mix()`
    sums and clamps correctly (e.g. two full-amplitude voices don't wrap
    around int16); `MASTER_VOLUME` scaling is applied.
  - New test for karaoke boundaries: `WORD_BOUNDARIES_MS` sums to
    `THEME_TOTAL_MS`; spot-check a few `elapsed` values map to the expected
    word index.
- `tests/shell/test_audio.py`'s
  `test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe`:
  extend the `expected` subset dict with the 13 new mappings (contract
  stays "must be present", not exact-equality, per its existing docstring).
- Full suite (`uv run pytest`), `ruff check .`, `mypy` must stay clean.
- Use the `verify` skill to smoke-test the title screen (karaoke ball
  visibly synced) and a scripted playthrough segment hitting a handful of
  the newly-sounded events, before calling this done.

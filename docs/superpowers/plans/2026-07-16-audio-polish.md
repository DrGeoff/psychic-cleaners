# Audio Polish (SFX Pass + Chord Synthesis + Karaoke Sync) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `shell/audio.py` an ADSR-enveloped, multi-waveform, chord-capable
synthesis engine; use it to rebalance the 14 existing SFX and add 13 new
event-sound mappings for currently-silent gameplay events; and fix the
title-screen karaoke ball so it tracks the chiptune theme's real note timing
instead of drifting on a flat clock.

**Architecture:** All changes are additive inside two existing files
(`shell/audio.py`, `shell/scenes/title.py`) plus one dict extension in
`shell/app.py`. No new files, no new dependency — synthesis stays pure
Python, generated once at `AudioBank.__init__` / module import time.

**Tech Stack:** Python 3.14, pygame-ce (`pygame.mixer.Sound(buffer=...)`),
pytest.

## Global Constraints

- No new audio asset files — all sound stays 100% code-generated (README,
  design doc §2; spec §3 Non-goals).
- No new dependency (no numpy) — pure-Python sample generation, matching
  the existing `synth_square`/`synth_noise` pattern (spec §3, §5).
- `synth_square`/`synth_noise` keep their existing call signatures — other
  code in the repo may call them directly (spec §4.1).
- `StompTriggered` and `SceneChanged` get no sound mapping (spec §3).
- `SnaresEmptied` and `CleanersRestored` share one `"dayroll"` recipe (spec
  §4.2 — both always fire together on a day boundary, `core/game.py:528-529`).
- Karaoke-ball timing must stay driven by simulated `elapsed` time only, no
  wall-clock reads (existing `_draw_karaoke` docstring constraint, spec §4.3).

---

### Task 1: Enveloped multi-waveform synthesis primitives

**Files:**
- Modify: `src/psychic_cleaners/shell/audio.py`
- Test: `tests/shell/test_audio.py`

**Interfaces:**
- Consumes: nothing new (uses existing `SAMPLE_RATE`, `_MAX_AMPLITUDE`,
  `_sample_count`).
- Produces: `synth_voice(wave: Waveform, freq: float, ms: int, volume: float = 0.5, *, attack_ms: int = 5, decay_ms: int = 10, sustain: float = 0.7, release_ms: int = 15) -> bytes`,
  `mix(*voices: bytes) -> bytes`, both used by Task 2/3. `synth_square`
  and `synth_noise` keep their existing signatures but become wrappers
  around `synth_voice`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/shell/test_audio.py`, replacing the existing
`test_square_alternates_at_expected_period` test (it currently asserts
alternation from sample 0, which the new default envelope's attack ramp
breaks) and adding new coverage:

```python
def test_synth_voice_raw_square_alternates_at_expected_period() -> None:
    # 2205 Hz at 22050 Hz sample rate -> half-period of exactly 5 samples.
    # Envelope disabled (attack/decay/release=0, sustain=1.0) to isolate
    # waveform shape from envelope shaping.
    samples = _samples(
        synth_voice(
            "square", 2205.0, 10, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
        )
    )
    assert all(s > 0 for s in samples[0:5])
    assert all(s < 0 for s in samples[5:10])
    assert all(s > 0 for s in samples[10:15])


def test_synth_voice_default_envelope_ramps_up_from_zero() -> None:
    samples = _samples(synth_voice("square", 440.0, 100, 0.8, attack_ms=5))
    assert samples[0] == 0
    assert 0 < abs(samples[10]) < round(0.8 * 32767)


def test_synth_voice_triangle_and_sawtooth_produce_distinct_shapes() -> None:
    triangle = _samples(
        synth_voice(
            "triangle", 220.0, 20, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
        )
    )
    sawtooth = _samples(
        synth_voice(
            "sawtooth", 220.0, 20, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
        )
    )
    assert triangle != sawtooth
    assert max(triangle) > 0 and min(triangle) < 0
    assert max(sawtooth) > 0 and min(sawtooth) < 0


def test_synth_square_and_synth_noise_are_synth_voice_wrappers() -> None:
    assert len(synth_square(440.0, 100)) == round(100 / 1000 * SAMPLE_RATE) * 2
    assert len(synth_noise(50)) == round(50 / 1000 * SAMPLE_RATE) * 2
    assert synth_noise(50) == synth_noise(50)  # still reproducible (seeded)


def test_mix_sums_and_clamps_to_int16_range() -> None:
    a = synth_voice(
        "square", 440.0, 10, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
    )
    b = synth_voice(
        "square", 440.0, 10, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
    )
    mixed = _samples(mix(a, b))
    # Two identical full-amplitude voices summed must clamp, never wrap around.
    assert all(s in (32767, -32768) for s in mixed)


def test_mix_pads_shorter_voice_with_silence() -> None:
    long_voice = synth_voice(
        "square", 440.0, 20, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
    )
    short_voice = synth_voice(
        "square", 440.0, 10, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
    )
    mixed = mix(long_voice, short_voice)
    assert len(mixed) == len(long_voice)
```

Update the `test_audio.py` imports to add `mix`, `synth_voice`:

```python
from psychic_cleaners.shell.audio import (
    SAMPLE_RATE,
    AudioBank,
    mix,
    synth_noise,
    synth_square,
    synth_voice,
)
```

Delete the old `test_square_alternates_at_expected_period` function (its
behavior is now covered by `test_synth_voice_raw_square_alternates_at_expected_period`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_audio.py -v`
Expected: FAIL — `ImportError: cannot import name 'synth_voice'` (and `mix`).

- [ ] **Step 3: Implement `synth_voice` and `mix` in `audio.py`**

Add near the top of `src/psychic_cleaners/shell/audio.py`, after the
`_sample_count` function and before `synth_square`:

```python
from typing import Literal

Waveform = Literal["square", "triangle", "sawtooth", "noise"]


def _wave_sample(wave: Waveform, phase: float, rng: random.Random | None) -> float:
    """Raw waveform value in [-1.0, 1.0] at the given phase (cycles, not radians)."""
    if wave == "square":
        return 1.0 if (phase % 1.0) < 0.5 else -1.0
    if wave == "triangle":
        p = phase % 1.0
        return 4.0 * abs(p - 0.5) - 1.0
    if wave == "sawtooth":
        p = phase % 1.0
        return 2.0 * p - 1.0
    assert rng is not None  # wave == "noise"
    return rng.uniform(-1.0, 1.0)


def _envelope_gain(
    i: int, total: int, attack: int, decay: int, sustain: float, release: int
) -> float:
    """Linear attack -> linear decay to sustain -> hold -> linear release.

    When attack/decay/release are 0, their trigger conditions (i < 0, etc.)
    are never true for i >= 0, so those stages are skipped naturally —
    no zero-length-window special-casing needed, and no division by zero.
    """
    if i < attack:
        return i / attack
    if i < attack + decay:
        d = i - attack
        return 1.0 - (1.0 - sustain) * (d / decay)
    release_start = total - release
    if i >= release_start:
        r = i - release_start
        return sustain * (1.0 - r / release)
    return sustain


def synth_voice(
    wave: Waveform,
    freq: float,
    ms: int,
    volume: float = 0.5,
    *,
    attack_ms: int = 5,
    decay_ms: int = 10,
    sustain: float = 0.7,
    release_ms: int = 15,
) -> bytes:
    """Raw 16-bit signed little-endian mono voice, envelope-shaped."""
    total = _sample_count(ms)
    attack = _sample_count(attack_ms)
    decay = _sample_count(decay_ms)
    release = _sample_count(release_ms)
    rng = random.Random(0) if wave == "noise" else None
    out = bytearray()
    for i in range(total):
        raw = _wave_sample(wave, i * freq / SAMPLE_RATE, rng)
        gain = _envelope_gain(i, total, attack, decay, sustain, release)
        sample = int(raw * gain * volume * _MAX_AMPLITUDE)
        sample = max(-_MAX_AMPLITUDE - 1, min(_MAX_AMPLITUDE, sample))
        out += sample.to_bytes(2, "little", signed=True)
    return bytes(out)


def mix(*voices: bytes) -> bytes:
    """Sum simultaneous voices sample-by-sample, clamped to int16 range.

    Shorter voices are zero-padded to the longest voice's length.
    """
    if not voices:
        return b""
    sample_lists = [
        [int.from_bytes(v[i : i + 2], "little", signed=True) for i in range(0, len(v), 2)]
        for v in voices
    ]
    total = max(len(s) for s in sample_lists)
    out = bytearray()
    for i in range(total):
        total_sample = sum(s[i] for s in sample_lists if i < len(s))
        clamped = max(-_MAX_AMPLITUDE - 1, min(_MAX_AMPLITUDE, total_sample))
        out += clamped.to_bytes(2, "little", signed=True)
    return bytes(out)
```

Then replace the existing `synth_square` and `synth_noise` definitions with
wrappers:

```python
def synth_square(freq: float, ms: int, volume: float = 0.5) -> bytes:
    """Raw 16-bit signed little-endian mono square wave, envelope-shaped."""
    return synth_voice("square", freq, ms, volume)


def synth_noise(ms: int, volume: float = 0.5) -> bytes:
    """Raw 16-bit signed little-endian mono white noise, seeded for reproducibility."""
    return synth_voice("noise", 0.0, ms, volume)
```

Remove the old bodies of `synth_square`/`synth_noise` (the manual
sample-generation loops) — they're now fully replaced by the
`synth_voice` calls above. Keep the module docstring's opening line
(`"""Synthesized sound effects. All audio is generated in code — no asset files."""`)
unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_audio.py -v`
Expected: PASS (all tests, including the pre-existing ones lower in the
file — `AudioBank`/degradation tests are unaffected by this task).

- [ ] **Step 5: Run lint and type-check**

Run: `uv run ruff check . && uv run mypy`
Expected: clean (fix any typing issues, e.g. `Waveform` literal usage, before
proceeding).

- [ ] **Step 6: Commit**

```bash
git add src/psychic_cleaners/shell/audio.py tests/shell/test_audio.py
git commit -m "feat(audio): add enveloped multi-waveform synth_voice and mix() chord engine"
```

---

### Task 2: Rebuild the 14 existing recipes on the new engine + master volume

**Files:**
- Modify: `src/psychic_cleaners/shell/audio.py`
- Test: `tests/shell/test_audio.py`

**Interfaces:**
- Consumes: `synth_voice`, `mix` from Task 1.
- Produces: `MASTER_VOLUME: Final[float]` constant and a `_scale(raw: bytes, factor: float) -> bytes`
  helper, both used unchanged by Task 3. `_RECIPES` keeps its existing
  `dict[str, Callable[[], bytes]]` type and all 14 existing keys — Task 3
  adds more keys to the same dict, it does not replace it.

- [ ] **Step 1: Write the failing test**

Add to `tests/shell/test_audio.py`:

```python
def test_all_recipes_produce_nonempty_even_length_audio() -> None:
    from psychic_cleaners.shell.audio import _RECIPES

    for name, recipe in _RECIPES.items():
        raw = recipe()
        assert len(raw) > 0, name
        assert len(raw) % 2 == 0, name


def test_master_volume_is_applied_to_built_sounds() -> None:
    from psychic_cleaners.shell.audio import _RECIPES, MASTER_VOLUME, _scale

    bank = AudioBank()
    if not bank._enabled:
        pytest.skip("mixer unavailable")
    expected = _scale(_RECIPES["buy"](), MASTER_VOLUME)
    assert bank._sounds["buy"].get_raw() == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_audio.py -k "master_volume or nonempty" -v`
Expected: FAIL — `ImportError: cannot import name 'MASTER_VOLUME'`.

- [ ] **Step 3: Add `MASTER_VOLUME`, `_scale`, and rebuild the 14 recipes**

Add near the top of `audio.py`, alongside the other `Final` constants:

```python
MASTER_VOLUME: Final[float] = 0.6
```

Add after `mix`:

```python
def _scale(raw: bytes, factor: float) -> bytes:
    """Scale a raw buffer's samples by factor, clamped to int16 range."""
    out = bytearray()
    for i in range(0, len(raw), 2):
        sample = int.from_bytes(raw[i : i + 2], "little", signed=True)
        scaled = max(-_MAX_AMPLITUDE - 1, min(_MAX_AMPLITUDE, int(sample * factor)))
        out += scaled.to_bytes(2, "little", signed=True)
    return bytes(out)
```

Replace the 14 existing entries in `_RECIPES` (leave the `"theme": build_theme`
entry untouched) with:

```python
_RECIPES: Final[dict[str, Callable[[], bytes]]] = {
    "catch": lambda: _seq(
        mix(synth_voice("square", 660.0, 60, 0.5), synth_voice("triangle", 660.0, 60, 0.3)),
        mix(synth_voice("square", 880.0, 90, 0.5), synth_voice("square", 1320.0, 90, 0.25)),
    ),
    "trap": lambda: _seq(
        synth_voice("square", 440.0, 60, 0.5),
        synth_voice("square", 660.0, 60, 0.5),
        mix(synth_voice("square", 880.0, 120, 0.5), synth_voice("square", 1108.0, 120, 0.3)),
    ),
    "miss": lambda: _seq(
        synth_voice("square", 330.0, 80, 0.5), synth_voice("square", 220.0, 140, 0.5)
    ),
    "backfire": lambda: _seq(
        synth_voice("noise", 0.0, 120, 0.7), synth_voice("sawtooth", 110.0, 180, 0.6)
    ),
    "slime": lambda: _seq(
        synth_voice("triangle", 180.0, 60, 0.5),
        synth_voice("triangle", 140.0, 60, 0.5),
        synth_voice("triangle", 180.0, 80, 0.5),
    ),
    "stomp": lambda: _seq(
        synth_voice("noise", 0.0, 60, 0.85), synth_voice("sawtooth", 70.0, 200, 0.75)
    ),
    "alert": lambda: _seq(
        synth_voice("square", 880.0, 70, 0.5),
        synth_voice("square", 660.0, 70, 0.5),
        synth_voice("square", 880.0, 70, 0.5),
        synth_voice("square", 660.0, 70, 0.5),
    ),
    "bait": lambda: _seq(
        synth_voice("square", 520.0, 50, 0.5), synth_voice("square", 520.0, 50, 0.3)
    ),
    "enter": lambda: _seq(
        synth_voice("square", 660.0, 50, 0.4), synth_voice("square", 990.0, 90, 0.4)
    ),
    "squash": lambda: _seq(
        synth_voice("noise", 0.0, 80, 0.75), synth_voice("sawtooth", 150.0, 130, 0.7)
    ),
    "win": lambda: _seq(
        mix(synth_voice("square", 523.0, 90, 0.45), synth_voice("square", 659.0, 90, 0.35)),
        mix(synth_voice("square", 659.0, 90, 0.45), synth_voice("square", 784.0, 90, 0.35)),
        mix(synth_voice("square", 784.0, 90, 0.45), synth_voice("square", 988.0, 90, 0.35)),
        mix(synth_voice("square", 1046.0, 220, 0.5), synth_voice("square", 1318.0, 220, 0.35)),
    ),
    "lose": lambda: _seq(
        synth_voice("sawtooth", 392.0, 140, 0.5),
        synth_voice("sawtooth", 330.0, 140, 0.5),
        synth_voice("sawtooth", 262.0, 260, 0.5),
    ),
    "buy": lambda: _seq(
        synth_voice("square", 988.0, 40, 0.35), synth_voice("square", 1319.0, 70, 0.35)
    ),
    "reject": lambda: synth_voice("square", 160.0, 140, 0.55),
    "theme": build_theme,
}
```

- [ ] **Step 4: Apply `MASTER_VOLUME` in `AudioBank.__init__`**

In `AudioBank.__init__`, change:

```python
        for name, recipe in _RECIPES.items():
            self._sounds[name] = pygame.mixer.Sound(buffer=recipe())
```

to:

```python
        for name, recipe in _RECIPES.items():
            self._sounds[name] = pygame.mixer.Sound(buffer=_scale(recipe(), MASTER_VOLUME))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_audio.py -v`
Expected: PASS.

- [ ] **Step 6: Run full suite, lint, type-check**

Run: `uv run pytest && uv run ruff check . && uv run mypy`
Expected: clean — this also confirms nothing outside `shell/audio.py`
depended on the old recipe internals.

- [ ] **Step 7: Commit**

```bash
git add src/psychic_cleaners/shell/audio.py tests/shell/test_audio.py
git commit -m "feat(audio): rebuild SFX recipes as enveloped chords, add MASTER_VOLUME"
```

---

### Task 3: Add 13 new recipes and wire them to previously-silent events

**Files:**
- Modify: `src/psychic_cleaners/shell/audio.py`
- Modify: `src/psychic_cleaners/shell/app.py`
- Test: `tests/shell/test_audio.py`

**Interfaces:**
- Consumes: `synth_voice`, `mix`, `_seq`, `_RECIPES` from Tasks 1-2;
  `EVENT_SOUNDS: Final[dict[type[Event], str]]` from `app.py` (existing).
- Produces: 13 new `_RECIPES` keys (`login`, `select`, `depart`, `rent`,
  `loan`, `repay`, `arrive`, `haunt`, `clear`, `breach`, `dayroll`,
  `converge`, `unlock`) and 14 new `EVENT_SOUNDS` entries (two events share
  `dayroll`). No later task depends on new names beyond this list.

- [ ] **Step 1: Write the failing test**

Extend the `expected` dict inside
`test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe` in
`tests/shell/test_audio.py`. Update its import block and the dict:

```python
def test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe() -> None:
    from psychic_cleaners.core.events import (
        AccountAccepted,
        AccountRejected,
        Arrived,
        BaitDeployed,
        BeamsCrossed,
        BuildingStomped,
        BustMissed,
        CleanerSlimed,
        CleanersRestored,
        CommandRejected,
        ConvergenceStarted,
        Event,
        FinaleUnlocked,
        GameLost,
        GameWon,
        GhostTrapped,
        HauntCleared,
        HauntStarted,
        ItemBought,
        LoanRepaid,
        LoanTaken,
        MascotAlert,
        PurchaseRejected,
        RentCharged,
        RunnerEntered,
        RunnerSquashed,
        SnaresEmptied,
        TravelStarted,
        VehicleSelected,
        WispCaptured,
        WispReachedTower,
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
        CommandRejected: "reject",
        AccountAccepted: "login",
        VehicleSelected: "select",
        TravelStarted: "depart",
        RentCharged: "rent",
        LoanTaken: "loan",
        LoanRepaid: "repay",
        Arrived: "arrive",
        HauntStarted: "haunt",
        HauntCleared: "clear",
        WispReachedTower: "breach",
        SnaresEmptied: "dayroll",
        CleanersRestored: "dayroll",
        ConvergenceStarted: "converge",
        FinaleUnlocked: "unlock",
    }
    for event_type, sound_name in expected.items():
        assert EVENT_SOUNDS.get(event_type) == sound_name, event_type
    assert set(EVENT_SOUNDS.values()) <= set(_RECIPES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_audio.py -k event_sounds -v`
Expected: FAIL — `AssertionError` on the first new event type (`EVENT_SOUNDS.get(AccountAccepted)` is `None`).

- [ ] **Step 3: Add the 13 new recipes to `_RECIPES` in `audio.py`**

Insert before the `"theme": build_theme,` line in `_RECIPES`:

```python
    "login": lambda: _seq(
        synth_voice("triangle", 440.0, 90, 0.4), synth_voice("triangle", 660.0, 140, 0.45)
    ),
    "select": lambda: synth_voice("square", 784.0, 40, 0.3),
    "depart": lambda: _seq(
        synth_voice("sawtooth", 220.0, 70, 0.4), synth_voice("sawtooth", 330.0, 90, 0.4)
    ),
    "rent": lambda: _seq(
        synth_voice("square", 392.0, 90, 0.45), synth_voice("square", 294.0, 160, 0.45)
    ),
    "loan": lambda: _seq(
        synth_voice("square", 523.0, 60, 0.4),
        synth_voice("square", 659.0, 60, 0.4),
        synth_voice("square", 784.0, 100, 0.45),
    ),
    "repay": lambda: _seq(
        synth_voice("square", 659.0, 60, 0.4), synth_voice("square", 523.0, 90, 0.4)
    ),
    "arrive": lambda: _seq(
        synth_voice("square", 587.0, 40, 0.3), synth_voice("square", 587.0, 60, 0.35)
    ),
    "haunt": lambda: mix(
        synth_voice("triangle", 233.0, 220, 0.4), synth_voice("square", 247.0, 220, 0.3)
    ),
    "clear": lambda: _seq(
        mix(synth_voice("square", 523.0, 80, 0.4), synth_voice("square", 659.0, 80, 0.3)),
        mix(synth_voice("square", 659.0, 80, 0.4), synth_voice("square", 784.0, 80, 0.3)),
        mix(synth_voice("square", 784.0, 140, 0.45), synth_voice("square", 988.0, 140, 0.3)),
    ),
    "breach": lambda: _seq(
        synth_voice("noise", 0.0, 100, 0.6),
        synth_voice("sawtooth", 196.0, 220, 0.55),
        synth_voice("sawtooth", 147.0, 260, 0.55),
    ),
    "dayroll": lambda: _seq(
        synth_voice("triangle", 880.0, 60, 0.35), synth_voice("triangle", 1046.0, 90, 0.35)
    ),
    "converge": lambda: mix(
        synth_voice("sawtooth", 98.0, 400, 0.5), synth_voice("square", 110.0, 400, 0.3)
    ),
    "unlock": lambda: _seq(
        synth_voice("square", 523.0, 70, 0.45),
        synth_voice("square", 659.0, 70, 0.45),
        synth_voice("square", 784.0, 70, 0.45),
        mix(synth_voice("square", 1046.0, 200, 0.5), synth_voice("square", 1318.0, 200, 0.35)),
    ),
```

- [ ] **Step 4: Wire the new events in `app.py`**

In `src/psychic_cleaners/shell/app.py`, extend the `from psychic_cleaners.core.events import (...)` block (currently lines 8-27) to also import:
`AccountAccepted`, `Arrived`, `CleanersRestored`, `ConvergenceStarted`,
`FinaleUnlocked`, `HauntCleared`, `HauntStarted`, `LoanRepaid`, `LoanTaken`,
`RentCharged`, `SnaresEmptied`, `TravelStarted`, `VehicleSelected`,
`WispReachedTower` — keep the existing alphabetical ordering (this project's
`ruff` `I` import-sort rule enforces it, so insert each name in
alphabetical position within the existing tuple of names).

Then extend `EVENT_SOUNDS` (currently lines 50-67) by adding these entries
before the closing `}`:

```python
    AccountAccepted: "login",
    VehicleSelected: "select",
    TravelStarted: "depart",
    RentCharged: "rent",
    LoanTaken: "loan",
    LoanRepaid: "repay",
    Arrived: "arrive",
    HauntStarted: "haunt",
    HauntCleared: "clear",
    WispReachedTower: "breach",
    SnaresEmptied: "dayroll",
    CleanersRestored: "dayroll",
    ConvergenceStarted: "converge",
    FinaleUnlocked: "unlock",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_audio.py -v`
Expected: PASS.

- [ ] **Step 6: Run full suite, lint, type-check**

Run: `uv run pytest && uv run ruff check . && uv run mypy`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add src/psychic_cleaners/shell/audio.py src/psychic_cleaners/shell/app.py tests/shell/test_audio.py
git commit -m "feat(audio): add SFX for rent, loans, travel, haunts, and finale events"
```

---

### Task 4: Sync the karaoke ball to the theme's real note timing

**Files:**
- Modify: `src/psychic_cleaners/shell/scenes/title.py`
- Test: `tests/shell/test_title.py` (create if it does not already exist —
  check with `ls tests/shell/test_title.py` first; if present, add to it
  following its existing import/style conventions instead of duplicating
  a header)

**Interfaces:**
- Consumes: `THEME: Final[list[tuple[str, int]]]` from
  `psychic_cleaners.shell.audio` (existing, unchanged).
- Produces: `WORD_BOUNDARIES_MS: Final[tuple[int, ...]]`,
  `THEME_TOTAL_MS: Final[int]`, `_ball_index(elapsed: float) -> int` in
  `title.py`. No later task depends on these.

- [ ] **Step 1: Write the failing test**

Check whether `tests/shell/test_title.py` exists:

Run: `ls tests/shell/test_title.py`

If it does not exist, create it with:

```python
"""Title scene: karaoke-ball word-boundary sync."""

from psychic_cleaners.shell.audio import THEME
from psychic_cleaners.shell.scenes.title import (
    KARAOKE_WORDS,
    THEME_TOTAL_MS,
    WORD_BOUNDARIES_MS,
    _ball_index,
)


def test_word_boundaries_count_matches_karaoke_words() -> None:
    assert len(WORD_BOUNDARIES_MS) == len(KARAOKE_WORDS)


def test_word_boundaries_sum_to_theme_total() -> None:
    assert WORD_BOUNDARIES_MS[-1] == sum(ms for _, ms in THEME)
    assert THEME_TOTAL_MS == WORD_BOUNDARIES_MS[-1]


def test_word_boundaries_are_strictly_increasing() -> None:
    assert list(WORD_BOUNDARIES_MS) == sorted(set(WORD_BOUNDARIES_MS))


def test_ball_index_tracks_known_elapsed_values() -> None:
    # THEME's 16 notes, paired 2-per-word, give boundaries at
    # 300, 600, 1050, 1500, 1800, 2100, 2550, 3000 ms.
    assert _ball_index(0.0) == 0
    assert _ball_index(0.29) == 0
    assert _ball_index(0.35) == 1
    assert _ball_index(0.65) == 2
    assert _ball_index(2.99) == 7


def test_ball_index_wraps_at_theme_loop_boundary() -> None:
    # elapsed == exactly one theme loop must wrap back to word 0, not drift.
    assert _ball_index(THEME_TOTAL_MS / 1000) == _ball_index(0.0)
```

If `tests/shell/test_title.py` already exists, append these same test
functions (adjusting the import block to merge with existing imports)
instead of overwriting the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_title.py -v`
Expected: FAIL — `ImportError: cannot import name 'WORD_BOUNDARIES_MS'`.

- [ ] **Step 3: Implement the boundary table and `_ball_index`**

In `src/psychic_cleaners/shell/scenes/title.py`, add the import and new
module-level code after the existing `KARAOKE_WORDS` definition:

```python
from psychic_cleaners.shell.audio import THEME
```

(Add this to the existing import block at the top of the file, keeping
alphabetical order among the `psychic_cleaners.shell` imports.)

Then, immediately after the `KARAOKE_WORDS` tuple definition:

```python
def _word_boundaries_ms() -> tuple[int, ...]:
    """Cumulative end-time (ms) of each KARAOKE_WORDS entry within THEME.

    THEME has 16 (note, ms) entries for 8 words -> 2 theme entries per word,
    matching the theme's "call bars 1-2, answer bars 3-4" structure.
    """
    notes_per_word = len(THEME) // len(KARAOKE_WORDS)
    boundaries: list[int] = []
    cumulative = 0
    for i in range(len(KARAOKE_WORDS)):
        window = THEME[i * notes_per_word : (i + 1) * notes_per_word]
        cumulative += sum(ms for _, ms in window)
        boundaries.append(cumulative)
    return tuple(boundaries)


WORD_BOUNDARIES_MS: Final[tuple[int, ...]] = _word_boundaries_ms()
THEME_TOTAL_MS: Final[int] = WORD_BOUNDARIES_MS[-1]


def _ball_index(elapsed: float) -> int:
    """Which KARAOKE_WORDS entry is active at simulated time `elapsed` seconds.

    Wraps at THEME_TOTAL_MS so the ball re-syncs every theme loop instead
    of drifting, since the theme itself loops via play(loops=-1).
    """
    elapsed_ms = int(elapsed * 1000) % THEME_TOTAL_MS
    for i, boundary in enumerate(WORD_BOUNDARIES_MS):
        if elapsed_ms < boundary:
            return i
    return len(KARAOKE_WORDS) - 1
```

- [ ] **Step 4: Update `_draw_karaoke` to use `_ball_index`**

Replace the existing line in `_draw_karaoke`:

```python
    ball_index = int(elapsed / 0.5) % len(KARAOKE_WORDS)
```

with:

```python
    ball_index = _ball_index(elapsed)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_title.py -v`
Expected: PASS.

- [ ] **Step 6: Run full suite, lint, type-check**

Run: `uv run pytest && uv run ruff check . && uv run mypy`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add src/psychic_cleaners/shell/scenes/title.py tests/shell/test_title.py
git commit -m "fix(title): sync karaoke ball to the theme's real note timing"
```

---

### Task 5: Full-suite verification and coverage gate

**Files:** none modified — verification only.

**Interfaces:**
- Consumes: everything from Tasks 1-4.
- Produces: nothing (terminal task).

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -q`
Expected: all tests pass, 0 failures.

- [ ] **Step 2: Run the core coverage gate**

Run: `uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90 --override-ini="addopts=--cov-report=term-missing"`
Expected: passes at >= 90% (this task touches no `core/` files, so this
gate should be unaffected, but confirm rather than assume).

- [ ] **Step 3: Run lint and type-check**

Run: `uv run ruff check . && uv run ruff format --check . && uv run mypy`
Expected: clean.

- [ ] **Step 4: Confirm no leftover TODOs or debug code**

Run: `git diff main --stat` (or the relevant base branch) and eyeball the
diff for stray `print()`/debug leftovers.
Expected: clean diff, only the intended files from Tasks 1-4.

No commit for this task — it's a checkpoint, not a change.

---

## Post-plan verification (not a plan task — done by the orchestrating session)

After all 5 tasks are complete, use the `verify` skill to drive the real
app headless and confirm: the title screen's karaoke ball visibly tracks
the theme without drift across a full loop, and a scripted playthrough
segment triggers a sample of the newly-sounded events (e.g. `LoanTaken`,
`RentCharged`, `HauntStarted`) without error.

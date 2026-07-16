"""Synthesized sound effects. All audio is generated in code — no asset files."""

import random
from collections.abc import Callable
from typing import Final, Literal

import pygame

SAMPLE_RATE: Final[int] = 22050
_MAX_AMPLITUDE: Final[int] = 32767


def _sample_count(ms: int) -> int:
    return round(ms / 1000 * SAMPLE_RATE)


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


def synth_square(freq: float, ms: int, volume: float = 0.5) -> bytes:
    """Raw 16-bit signed little-endian mono square wave, envelope-shaped."""
    return synth_voice("square", freq, ms, volume)


def synth_noise(ms: int, volume: float = 0.5) -> bytes:
    """Raw 16-bit signed little-endian mono white noise, seeded for reproducibility."""
    return synth_voice("noise", 0.0, ms, volume)


def _seq(*parts: bytes) -> bytes:
    return b"".join(parts)


_NOTE_NAMES: Final[tuple[str, ...]] = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)


def _note_freq(semitones_above_c0: int) -> float:
    a4 = 9 + 12 * 4  # A4 in semitones above C0
    return float(440.0 * 2.0 ** ((semitones_above_c0 - a4) / 12.0))


NOTE_HZ: Final[dict[str, float]] = {
    f"{name}{octave}": _note_freq(_NOTE_NAMES.index(name) + 12 * octave)
    for octave in (4, 5)
    for name in _NOTE_NAMES
} | {"C6": _note_freq(12 * 6)}

# Original 16-note hook, call (bars 1-2) and answer (bars 3-4). "" = rest.
THEME: Final[list[tuple[str, int]]] = [
    ("C5", 150),
    ("E5", 150),
    ("G5", 150),
    ("E5", 150),
    ("A5", 300),
    ("G5", 150),
    ("", 150),
    ("E5", 300),
    ("F5", 150),
    ("E5", 150),
    ("D5", 150),
    ("F5", 150),
    ("E5", 300),
    ("D5", 150),
    ("C5", 150),
    ("", 300),
]


def _silence(ms: int) -> bytes:
    return b"\x00\x00" * _sample_count(ms)


def build_theme() -> bytes:
    parts: list[bytes] = []
    for note, ms in THEME:
        parts.append(synth_square(NOTE_HZ[note], ms, 0.35) if note else _silence(ms))
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
    "theme": build_theme,
}


class AudioBank:
    """Owns the mixer and all generated sounds; degrades to silence gracefully."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music: pygame.mixer.Sound | None = None
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

    def play_music_loop(self) -> None:
        if not self._enabled:
            return
        if self._music is None:
            # Reuse the "theme" Sound built once in __init__ instead of
            # re-synthesizing build_theme() a second time.
            self._music = self._sounds["theme"]
        self._music.play(loops=-1)

    def stop_music(self) -> None:
        if self._music is not None:
            self._music.stop()

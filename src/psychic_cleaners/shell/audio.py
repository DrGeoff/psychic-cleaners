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

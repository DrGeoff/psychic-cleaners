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

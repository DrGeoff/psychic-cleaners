"""Game-time model: real seconds in, game minutes accumulated."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import GAME_MINUTES_PER_REAL_SECOND


@dataclass
class GameClock:
    minutes: float = 0.0

    def advance(self, dt_seconds: float) -> None:
        self.minutes += dt_seconds * GAME_MINUTES_PER_REAL_SECOND

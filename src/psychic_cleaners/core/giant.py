"""Sir Squish threat model: PSI-driven rampage rolls, sensor alerts, bait aversion."""

import enum
from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    MASCOT_ALERT_WINDOW,
    MASCOT_CHANCE_PER_REAL_MINUTE_PER_1000_PSI,
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
            self.alert_remaining -= dt_seconds
            if self.alert_remaining <= 0.0:
                self.alert_remaining = 0.0
                self.state = MascotState.CALM
                events.append(StompTriggered())
            return events
        rate_per_minute = MASCOT_CHANCE_PER_REAL_MINUTE_PER_1000_PSI * (psi_value / 1000)
        if rng.random() < rate_per_minute * (dt_seconds / 60.0):
            if has_sensor:
                self.state = MascotState.ALERT
                self.alert_remaining = MASCOT_ALERT_WINDOW
                events.append(MascotAlert(MASCOT_ALERT_WINDOW))
            else:
                events.append(StompTriggered())
        return events

    def deploy_bait(self) -> bool:
        """True iff currently in ALERT; averts the pending stomp and resets to CALM."""
        if self.state is MascotState.ALERT:
            self.state = MascotState.CALM
            self.alert_remaining = 0.0
            return True
        return False

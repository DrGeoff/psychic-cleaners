"""Tests for the Sir Squish threat model (core/giant.py)."""

import pytest

from psychic_cleaners.core.constants import MASCOT_ALERT_WINDOW
from psychic_cleaners.core.events import Event, MascotAlert, StompTriggered
from psychic_cleaners.core.giant import MascotModel, MascotState
from psychic_cleaners.core.rng import make_rng


def _tick_until_event(mascot: MascotModel, psi: int, *, sensor: bool, seed: int) -> list[Event]:
    """Tick 1-second steps until the model emits something (10 simulated minutes max)."""
    rng = make_rng(seed)
    for _ in range(600):
        events = mascot.tick(1.0, psi, sensor, rng)
        if events:
            return events
    raise AssertionError("mascot never triggered within 10 simulated minutes")


def test_psi_zero_never_triggers() -> None:
    mascot = MascotModel()
    rng = make_rng(101)
    for _ in range(10_000):
        assert mascot.tick(1.0, 0, True, rng) == []
    assert mascot.state == MascotState.CALM
    assert mascot.alert_remaining == 0.0


def test_max_psi_with_sensor_raises_alert() -> None:
    mascot = MascotModel()
    events = _tick_until_event(mascot, 9_999, sensor=True, seed=102)
    assert events == [MascotAlert(MASCOT_ALERT_WINDOW)]
    assert mascot.state is MascotState.ALERT
    assert mascot.alert_remaining == MASCOT_ALERT_WINDOW


def test_max_psi_without_sensor_stomps_directly() -> None:
    mascot = MascotModel()
    events = _tick_until_event(mascot, 9_999, sensor=False, seed=103)
    assert events == [StompTriggered()]
    assert mascot.state == MascotState.CALM
    assert mascot.alert_remaining == 0.0


def test_alert_counts_down_and_expires_to_stomp() -> None:
    mascot = MascotModel(state=MascotState.ALERT, alert_remaining=MASCOT_ALERT_WINDOW)
    rng = make_rng(104)
    collected: list[Event] = []
    for _ in range(9):
        collected += mascot.tick(1.0, 9_999, True, rng)
    assert collected == []  # no re-alerts, no early stomp while the window is open
    assert mascot.alert_remaining == pytest.approx(MASCOT_ALERT_WINDOW - 9.0)
    final = mascot.tick(1.5, 9_999, True, rng)
    assert final == [StompTriggered()]
    assert mascot.state == MascotState.CALM
    assert mascot.alert_remaining == 0.0


def test_deploy_bait_in_calm_returns_false() -> None:
    mascot = MascotModel()
    assert mascot.deploy_bait() is False
    assert mascot.state == MascotState.CALM
    assert mascot.alert_remaining == 0.0


def test_deploy_bait_in_alert_averts_and_resets() -> None:
    mascot = MascotModel(state=MascotState.ALERT, alert_remaining=5.0)
    assert mascot.deploy_bait() is True
    assert mascot.state == MascotState.CALM
    assert mascot.alert_remaining == 0.0
    # the cancelled alert must never expire into a stomp (psi 0 -> no new rolls either)
    rng = make_rng(105)
    assert mascot.tick(20.0, 0, True, rng) == []
    assert mascot.deploy_bait() is False  # back in CALM, bait does nothing now

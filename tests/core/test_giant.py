"""Tests for the Sir Squish threat model (core/giant.py)."""

from collections.abc import Sequence

import pytest

from psychic_cleaners.core.constants import MASCOT_ALERT_WINDOW
from psychic_cleaners.core.events import Event, MascotAlert, StompTriggered
from psychic_cleaners.core.giant import MascotModel, MascotState
from psychic_cleaners.core.rng import make_rng


class _FixedRng:
    """Rng stub whose random() always returns a fixed value."""

    def __init__(self, value: float) -> None:
        self._value = value

    def random(self) -> float:
        return self._value

    def randint(self, a: int, b: int) -> int:
        return a

    def uniform(self, a: float, b: float) -> float:
        return a

    def choice[T](self, seq: Sequence[T]) -> T:
        return seq[0]


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


def test_mid_psi_rate_formula_is_exact() -> None:
    # psi=1000 -> rate_per_minute = 0.10 * (1000/1000) = 0.10/min. Over a full
    # 60s tick that's chance == 0.10 exactly. The psi=0/9999 extremes pass
    # under almost any scaling error (0 stays 0 regardless, 9999 fires
    # "eventually" regardless); this pins the /1000 psi-normalization term.
    assert MascotModel().tick(60.0, 1_000, True, _FixedRng(0.099999)) == [
        MascotAlert(MASCOT_ALERT_WINDOW)
    ]
    assert MascotModel().tick(60.0, 1_000, True, _FixedRng(0.1)) == []  # strict <: at-threshold


def test_mid_psi_rate_scales_with_dt() -> None:
    # Same psi, half the dt: chance halves to 0.05. Pins the dt_seconds/60.0
    # per-minute-to-per-tick conversion specifically.
    assert MascotModel().tick(30.0, 1_000, True, _FixedRng(0.0499)) == [
        MascotAlert(MASCOT_ALERT_WINDOW)
    ]
    assert MascotModel().tick(30.0, 1_000, True, _FixedRng(0.05)) == []


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

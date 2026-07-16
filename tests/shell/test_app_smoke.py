"""Headless smoke test: the app constructs and renders frames under SDL dummy drivers."""

import pygame
import pytest

from psychic_cleaners.core.events import BuyItem, NewGame, SceneId, SelectVehicle
from psychic_cleaners.shell.app import FPS, LOGICAL_SIZE, SCENES, WINDOW_SCALE, App


def test_shell_constants() -> None:
    assert LOGICAL_SIZE == (640, 400)
    assert WINDOW_SCALE == 2
    assert FPS == 60


def test_app_constructs_and_steps() -> None:
    app = App(seed=1)
    try:
        app.step(1 / 60)
        app.step(1 / 60)
        assert app.logical.get_size() == LOGICAL_SIZE
    finally:
        pygame.quit()


def test_step_handles_quit_event() -> None:
    app = App(seed=1)
    try:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.step(1 / 60)
        assert app.running is False
    finally:
        pygame.quit()


def test_step_plays_sound_for_mapped_game_event(monkeypatch: pytest.MonkeyPatch) -> None:
    # test_audio.py's test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe
    # only checks the static EVENT_SOUNDS dict; this drives an actual game
    # event through App.step and confirms the per-frame loop really calls
    # AudioBank.play with the mapped name, not just that the mapping exists.
    app = App(seed=1)
    try:
        app.game.tick([NewGame("Ada")], 0.0)  # TITLE -> SHOP
        app.game.tick([SelectVehicle("compact")], 0.0)
        assert app.game.scene is SceneId.SHOP
        played: list[str] = []
        monkeypatch.setattr(app.audio, "play", played.append)
        shop_scene = SCENES[SceneId.SHOP]
        monkeypatch.setattr(shop_scene, "commands", lambda events, game, dt: [BuyItem("snare")])
        app.step(1 / 60)
        assert "buy" in played
    finally:
        pygame.quit()


class _FakeClock:
    """pygame.time.Clock stand-in returning a fixed frame time in ms."""

    def __init__(self, tick_ms: int) -> None:
        self.tick_ms = tick_ms

    def tick(self, fps: int) -> int:
        return self.tick_ms


def _run_one_frame(app: App, monkeypatch: pytest.MonkeyPatch, tick_ms: int) -> float:
    """Run App.run() for exactly one frame with a stubbed clock; return the dt stepped."""
    received: list[float] = []

    def fake_step(dt: float) -> None:
        received.append(dt)
        app.running = False

    monkeypatch.setattr(app, "step", fake_step)
    monkeypatch.setattr(app, "clock", _FakeClock(tick_ms))
    app.running = True
    app.run()
    assert len(received) == 1
    return received[0]


def test_run_clamps_lag_spikes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wall-clock hitch (window drag, sleep-resume) must not become one giant
    physics step: at dt >= ~0.15 finale runners tunnel through the giant and the
    bust ghost jumps the slime band. run() caps the step at 0.1s."""
    app = App(seed=1)
    try:
        assert _run_one_frame(app, monkeypatch, tick_ms=2000) == pytest.approx(0.1)
    finally:
        pygame.quit()


def test_run_passes_normal_frames_through(monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(seed=1)
    try:
        assert _run_one_frame(app, monkeypatch, tick_ms=16) == pytest.approx(0.016)
    finally:
        pygame.quit()

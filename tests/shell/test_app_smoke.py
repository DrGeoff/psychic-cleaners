"""Headless smoke test: the app constructs and renders frames under SDL dummy drivers."""

import pygame

from psychic_cleaners.shell.app import FPS, LOGICAL_SIZE, WINDOW_SCALE, App


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

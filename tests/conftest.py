"""Shared pytest configuration.

Sets SDL dummy drivers at import time, before any test module imports
pygame, so shell tests run headless. Provides a fixed-seed rng fixture
for deterministic core tests.
"""

import os

import pytest

from psychic_cleaners.core.rng import Rng, make_rng

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def rng() -> Rng:
    return make_rng(1234)

"""Global test configuration.

Sets SDL dummy drivers at import time, BEFORE any test module can import
pygame, so shell tests run headless on any machine and in CI.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

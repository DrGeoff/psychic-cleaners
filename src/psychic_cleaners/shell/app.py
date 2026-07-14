"""Application shell: window, logical surface, fixed-timestep main loop.

Minimal version. Later tasks add the Game, scene registry, sprite factory,
text renderer, and audio bank; the names below are contract-fixed.
"""

from typing import Final

import pygame

LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)
WINDOW_SCALE: Final[int] = 2
FPS: Final[int] = 60

_BACKGROUND: Final[tuple[int, int, int]] = (16, 16, 32)
_FPS_COLOR: Final[tuple[int, int, int]] = (230, 230, 230)


class App:
    """Owns the window, the 640x400 logical surface, and the main loop."""

    def __init__(self, seed: int | None = None) -> None:
        pygame.init()
        self.seed = seed
        self.window = pygame.display.set_mode(
            (LOGICAL_SIZE[0] * WINDOW_SCALE, LOGICAL_SIZE[1] * WINDOW_SCALE)
        )
        pygame.display.set_caption("Psychic Cleaners")
        self.logical = pygame.Surface(LOGICAL_SIZE)
        self._font = pygame.font.Font(None, 20)

    def step(self, dt: float) -> None:
        """Render one frame: clear, draw FPS, scale the logical surface up, flip."""
        fps = 0.0 if dt <= 0.0 else 1.0 / dt
        self.logical.fill(_BACKGROUND)
        fps_surface = self._font.render(f"FPS: {fps:.0f}", True, _FPS_COLOR)
        self.logical.blit(fps_surface, (4, 4))
        pygame.transform.scale(self.logical, self.window.get_size(), self.window)
        pygame.display.flip()

    def run(self) -> None:
        """Fixed-timestep loop at FPS until the window is closed."""
        clock = pygame.time.Clock()
        running = True
        while running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.step(dt)


def main() -> None:
    """Console entry point (see [project.scripts] in pyproject.toml).

    Exception-safe per the contract: pygame.quit() runs exactly once, in the
    finally, even if run() raises.
    """
    app = App()
    try:
        app.run()
    finally:
        pygame.quit()

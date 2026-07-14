"""Code-generated sprite factory. All art is drawn in code; no asset files."""

from collections.abc import Callable

import pygame


def _build_logo() -> pygame.Surface:
    """Drawn wordmark rectangle used on the title screen."""
    surface = pygame.Surface((200, 48), pygame.SRCALPHA)
    surface.fill((30, 30, 60))
    pygame.draw.rect(surface, (120, 220, 160), surface.get_rect(), width=3)
    pygame.draw.rect(surface, (120, 220, 160), pygame.Rect(12, 20, 176, 8))
    return surface


def _build_cleaner() -> pygame.Surface:
    """Simple 24x32 figure: head, overalls, boots."""
    surface = pygame.Surface((24, 32), pygame.SRCALPHA)
    pygame.draw.rect(surface, (210, 180, 90), pygame.Rect(6, 12, 12, 16))
    pygame.draw.circle(surface, (240, 210, 170), (12, 7), 5)
    pygame.draw.rect(surface, (90, 90, 100), pygame.Rect(4, 28, 6, 4))
    pygame.draw.rect(surface, (90, 90, 100), pygame.Rect(14, 28, 6, 4))
    return surface


_BUILDERS: dict[str, Callable[[], pygame.Surface]] = {
    "logo": _build_logo,
    "cleaner": _build_cleaner,
}


class SpriteFactory:
    """Generates and caches sprites by name. Unknown names raise KeyError."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = _BUILDERS[name]()
        return self._cache[name]

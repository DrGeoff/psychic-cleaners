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


def _build_building() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    surface.fill((70, 80, 110))
    pygame.draw.rect(surface, (40, 45, 70), pygame.Rect(0, 0, 48, 48), width=2)
    for wx in range(8, 41, 12):
        for wy in range(8, 41, 12):
            pygame.draw.rect(surface, (240, 220, 140), pygame.Rect(wx, wy, 6, 8))
    return surface


def _build_building_haunted() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    surface.fill((60, 105, 75))
    pygame.draw.rect(surface, (30, 60, 40), pygame.Rect(0, 0, 48, 48), width=2)
    for wx in range(8, 41, 12):
        for wy in range(8, 41, 12):
            pygame.draw.rect(surface, (180, 255, 130), pygame.Rect(wx, wy, 6, 8))
    pygame.draw.circle(surface, (200, 255, 160), (24, 6), 5)
    return surface


def _build_tower() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.rect(surface, (90, 60, 130), pygame.Rect(8, 16, 32, 32))
    pygame.draw.polygon(surface, (120, 80, 170), [(8, 16), (24, 0), (40, 16)])
    pygame.draw.rect(surface, (240, 230, 120), pygame.Rect(21, 34, 6, 14))
    return surface


def _build_depot() -> pygame.Surface:
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    surface.fill((150, 70, 60))
    pygame.draw.rect(surface, (90, 40, 35), pygame.Rect(0, 0, 48, 48), width=2)
    pygame.draw.rect(surface, (230, 230, 230), pygame.Rect(16, 22, 16, 26))
    pygame.draw.rect(surface, (250, 250, 200), pygame.Rect(6, 6, 36, 10))
    return surface


def _build_wisp() -> pygame.Surface:
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.circle(surface, (180, 240, 255), (8, 8), 7)
    pygame.draw.circle(surface, (255, 255, 255), (6, 6), 3)
    return surface


_BUILDERS: dict[str, Callable[[], pygame.Surface]] = {
    "logo": _build_logo,
    "cleaner": _build_cleaner,
    "building": _build_building,
    "building.haunted": _build_building_haunted,
    "tower": _build_tower,
    "depot": _build_depot,
    "wisp": _build_wisp,
}


class SpriteFactory:
    """Generates and caches sprites by name. Unknown names raise KeyError."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = _BUILDERS[name]()
        return self._cache[name]

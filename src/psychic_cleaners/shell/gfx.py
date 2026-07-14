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


def _build_car(
    body: tuple[int, int, int],
    roof: tuple[int, int, int],
    roof_rect: tuple[int, int, int, int],
    stripe: bool = False,
) -> pygame.Surface:
    surf = pygame.Surface((48, 24), pygame.SRCALPHA)
    pygame.draw.rect(surf, body, pygame.Rect(2, 8, 44, 10), border_radius=4)
    pygame.draw.rect(surf, roof, pygame.Rect(*roof_rect), border_radius=3)
    if stripe:
        pygame.draw.rect(surf, (250, 250, 250), pygame.Rect(2, 15, 44, 2))
    for wheel_x in (12, 36):
        pygame.draw.circle(surf, (25, 25, 30), (wheel_x, 20), 4)
        pygame.draw.circle(surf, (190, 190, 200), (wheel_x, 20), 2)
    return surf


def _build_car_compact() -> pygame.Surface:
    return _build_car((90, 175, 160), (140, 215, 205), (14, 3, 20, 8))


def _build_car_hearse() -> pygame.Surface:
    return _build_car((72, 62, 96), (52, 44, 70), (8, 3, 34, 8))


def _build_car_wagon() -> pygame.Surface:
    return _build_car((155, 110, 70), (120, 82, 50), (10, 3, 30, 8))


def _build_car_performance() -> pygame.Surface:
    return _build_car((205, 55, 55), (150, 30, 30), (18, 4, 16, 7), stripe=True)


def _build_wisp_faint() -> pygame.Surface:
    surf = pygame.Surface((24, 24), pygame.SRCALPHA)
    pygame.draw.circle(surf, (180, 240, 255, 90), (12, 10), 8)
    pygame.draw.circle(surf, (235, 255, 255, 90), (12, 10), 4)
    pygame.draw.rect(surf, (180, 240, 255, 90), pygame.Rect(6, 14, 12, 6), border_radius=3)
    return surf


def _build_smudge() -> pygame.Surface:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(surf, (146, 188, 92), (16, 19), 12)  # greasy body
    pygame.draw.circle(surf, (186, 222, 124), (13, 15), 8)  # highlight
    pygame.draw.circle(surf, (32, 32, 32), (12, 14), 2)  # eyes
    pygame.draw.circle(surf, (32, 32, 32), (20, 14), 2)
    return surf


def _build_cleaner_slimed() -> pygame.Surface:
    surf = _build_cleaner()  # fresh surface from the module-level cleaner builder
    tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    tint.fill((110, 210, 110, 255))
    surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)  # green tint
    return surf


def _build_snare() -> pygame.Surface:
    surf = pygame.Surface((24, 12), pygame.SRCALPHA)
    pygame.draw.rect(surf, (58, 58, 70), pygame.Rect(0, 0, 24, 12))
    pygame.draw.rect(surf, (250, 208, 84), pygame.Rect(0, 0, 24, 12), width=2)
    pygame.draw.line(surf, (250, 208, 84), (11, 2), (11, 9), width=2)
    return surf


def _build_mascot() -> pygame.Surface:
    """Sir Squish: a 48x64 pale-green gummy giant."""
    surface = pygame.Surface((48, 64), pygame.SRCALPHA)
    body = (150, 230, 160, 255)
    shade = (104, 186, 120, 255)
    ink = (30, 30, 40, 255)
    pygame.draw.ellipse(surface, body, pygame.Rect(4, 22, 40, 42))  # torso
    pygame.draw.ellipse(surface, shade, pygame.Rect(0, 30, 10, 18))  # left arm
    pygame.draw.ellipse(surface, shade, pygame.Rect(38, 30, 10, 18))  # right arm
    pygame.draw.ellipse(surface, shade, pygame.Rect(10, 54, 12, 10))  # left foot
    pygame.draw.ellipse(surface, shade, pygame.Rect(26, 54, 12, 10))  # right foot
    pygame.draw.circle(surface, body, (24, 16), 14)  # head
    pygame.draw.circle(surface, ink, (18, 14), 3)  # left eye
    pygame.draw.circle(surface, ink, (30, 14), 3)  # right eye
    pygame.draw.line(surface, ink, (18, 22), (30, 22), 2)  # grin
    return surface


_BUILDERS: dict[str, Callable[[], pygame.Surface]] = {
    "logo": _build_logo,
    "cleaner": _build_cleaner,
    "cleaner.slimed": _build_cleaner_slimed,
    "building": _build_building,
    "building.haunted": _build_building_haunted,
    "tower": _build_tower,
    "depot": _build_depot,
    "wisp": _build_wisp,
    "car.compact": _build_car_compact,
    "car.hearse": _build_car_hearse,
    "car.wagon": _build_car_wagon,
    "car.performance": _build_car_performance,
    "wisp.faint": _build_wisp_faint,
    "smudge": _build_smudge,
    "snare": _build_snare,
    "mascot": _build_mascot,
}


class SpriteFactory:
    """Generates and caches sprites by name. Unknown names raise KeyError."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = _BUILDERS[name]()
        return self._cache[name]

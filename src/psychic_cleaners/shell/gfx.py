"""Code-generated sprite factory: every sprite is drawn deterministically and cached."""

import math
from collections.abc import Callable
from typing import Final

import pygame

type Color = tuple[int, int, int]
type ColorA = tuple[int, int, int, int]


def _surface(width: int, height: int) -> pygame.Surface:
    return pygame.Surface((width, height), pygame.SRCALPHA)


def _car(body: Color, cabin: Color, cabin_rect: pygame.Rect) -> pygame.Surface:
    surf = _surface(48, 28)
    pygame.draw.rect(surf, cabin, cabin_rect, border_radius=3)
    pygame.draw.rect(surf, body, pygame.Rect(2, 10, 44, 10), border_radius=4)
    for wheel_x in (10, 36):
        pygame.draw.circle(surf, (25, 25, 30), (wheel_x, 21), 5)
        pygame.draw.circle(surf, (140, 140, 150), (wheel_x, 21), 2)
    pygame.draw.rect(surf, (255, 240, 170), pygame.Rect(44, 12, 3, 4))  # headlight
    return surf


def _build_car_compact() -> pygame.Surface:
    return _car((200, 60, 50), (240, 230, 220), pygame.Rect(14, 4, 18, 8))


def _build_car_hearse() -> pygame.Surface:
    return _car((40, 40, 48), (200, 200, 210), pygame.Rect(8, 4, 30, 8))


def _build_car_wagon() -> pygame.Surface:
    return _car((70, 120, 190), (220, 230, 240), pygame.Rect(10, 4, 28, 8))


def _build_car_performance() -> pygame.Surface:
    surf = _car((250, 200, 40), (30, 30, 35), pygame.Rect(18, 5, 16, 7))
    pygame.draw.rect(surf, (30, 30, 35), pygame.Rect(2, 14, 44, 2))  # racing stripe
    return surf


def _build_wisp() -> pygame.Surface:
    surf = _surface(24, 24)
    pygame.draw.polygon(surf, (150, 200, 255), [(5, 12), (12, 23), (19, 12)])  # tail
    pygame.draw.circle(surf, (150, 200, 255), (12, 10), 9)
    pygame.draw.circle(surf, (235, 245, 255), (12, 10), 6)
    pygame.draw.circle(surf, (20, 20, 40), (9, 9), 1)
    pygame.draw.circle(surf, (20, 20, 40), (15, 9), 1)
    return surf


def _build_wisp_faint() -> pygame.Surface:
    surf = _surface(24, 24)
    # Alpha 90 is pinned by the contract: an earlier driving-scene test asserts `90 in alphas`.
    ghost: ColorA = (150, 200, 255, 90)
    pygame.draw.polygon(surf, ghost, [(5, 12), (12, 23), (19, 12)])
    pygame.draw.circle(surf, ghost, (12, 10), 9)
    pygame.draw.circle(surf, (235, 245, 255, 110), (12, 10), 6)
    return surf


def _build_smudge() -> pygame.Surface:
    surf = _surface(48, 48)
    body: Color = (150, 150, 90)
    dark: Color = (105, 105, 60)
    pygame.draw.circle(surf, body, (24, 18), 16)
    pygame.draw.rect(surf, body, pygame.Rect(8, 18, 32, 12))
    for drip_x, drip_len in ((11, 8), (21, 14), (33, 6)):  # greasy drips
        pygame.draw.rect(surf, dark, pygame.Rect(drip_x, 28, 5, drip_len))
        pygame.draw.circle(surf, dark, (drip_x + 2, 28 + drip_len), 3)
    pygame.draw.circle(surf, (250, 250, 250), (18, 14), 5)
    pygame.draw.circle(surf, (250, 250, 250), (30, 14), 5)
    pygame.draw.circle(surf, (30, 30, 30), (19, 15), 2)
    pygame.draw.circle(surf, (30, 30, 30), (31, 15), 2)
    return surf


def _cleaner(suit: Color, drip: Color | None) -> pygame.Surface:
    surf = _surface(24, 40)
    pygame.draw.rect(surf, (120, 90, 60), pygame.Rect(1, 12, 6, 14), border_radius=2)  # pack
    pygame.draw.rect(surf, suit, pygame.Rect(7, 12, 12, 16), border_radius=3)  # torso
    pygame.draw.circle(surf, (235, 200, 170), (13, 7), 5)  # head
    pygame.draw.rect(surf, suit, pygame.Rect(8, 1, 10, 3))  # cap
    pygame.draw.rect(surf, (40, 40, 55), pygame.Rect(8, 28, 4, 10))  # legs
    pygame.draw.rect(surf, (40, 40, 55), pygame.Rect(14, 28, 4, 10))
    pygame.draw.line(surf, suit, (19, 16), (23, 22), 3)  # arm with wand
    if drip is not None:
        pygame.draw.circle(surf, drip, (13, 12), 6)
        for drip_x in (9, 13, 17):
            pygame.draw.rect(surf, drip, pygame.Rect(drip_x, 12, 3, 8))
    return surf


def _build_cleaner() -> pygame.Surface:
    return _cleaner((210, 180, 90), None)


def _build_cleaner_slimed() -> pygame.Surface:
    return _cleaner((210, 180, 90), (90, 220, 90))


def _building(window: Color, halo: ColorA | None) -> pygame.Surface:
    surf = _surface(48, 56)
    pygame.draw.rect(surf, (100, 100, 115), pygame.Rect(2, 6, 44, 50))
    pygame.draw.rect(surf, (70, 70, 85), pygame.Rect(0, 0, 48, 8))  # roofline
    for row in range(3):
        for col in range(3):
            window_rect = pygame.Rect(8 + col * 13, 13 + row * 11, 8, 6)
            if halo is not None:
                pygame.draw.rect(surf, halo, window_rect.inflate(4, 4))
            pygame.draw.rect(surf, window, window_rect)
    pygame.draw.rect(surf, (50, 40, 35), pygame.Rect(20, 44, 8, 12))  # door
    return surf


def _build_building() -> pygame.Surface:
    return _building((225, 210, 140), None)


def _build_building_haunted() -> pygame.Surface:
    return _building((215, 140, 255), (140, 60, 200, 160))


def _build_tower() -> pygame.Surface:
    surf = _surface(56, 96)
    pygame.draw.circle(surf, (120, 60, 180, 70), (28, 20), 18)  # ambient glow
    pygame.draw.polygon(surf, (60, 55, 80), [(28, 2), (44, 40), (44, 94), (12, 94), (12, 40)])
    pygame.draw.polygon(surf, (90, 80, 120), [(28, 2), (36, 40), (36, 94), (20, 94), (20, 40)])
    for slit_y in range(48, 90, 12):
        pygame.draw.rect(surf, (200, 120, 255), pygame.Rect(24, slit_y, 8, 6))
    pygame.draw.circle(surf, (230, 180, 255), (28, 14), 4)  # beacon
    return surf


def _build_tower_map() -> pygame.Surface:
    # The map cell is only 48px tall; the full 56x96 tower would spill into
    # the cell below it, hiding a haunting there. Scale it down to fit its
    # own cell (aspect preserved: 56x96 -> 28x48) for the map view only.
    return pygame.transform.scale(_build_tower(), (28, 48))


def _build_depot() -> pygame.Surface:
    surf = _surface(56, 48)
    pygame.draw.rect(surf, (150, 60, 60), pygame.Rect(2, 14, 52, 34))
    pygame.draw.polygon(surf, (110, 45, 45), [(0, 16), (28, 0), (56, 16)])  # gable roof
    pygame.draw.rect(surf, (90, 90, 100), pygame.Rect(12, 22, 32, 26))  # garage door
    for slat_y in range(24, 46, 5):
        pygame.draw.line(surf, (60, 60, 70), (12, slat_y), (44, slat_y), 1)
    pygame.draw.rect(surf, (230, 220, 200), pygame.Rect(22, 16, 12, 5))  # sign
    return surf


def _build_mascot() -> pygame.Surface:
    surf = _surface(72, 96)
    body: Color = (255, 120, 160)
    dark: Color = (220, 80, 130)
    pygame.draw.rect(surf, body, pygame.Rect(14, 30, 44, 54), border_radius=18)  # gummy body
    pygame.draw.circle(surf, body, (36, 22), 18)  # head
    pygame.draw.circle(surf, body, (10, 46), 8)  # stubby arms
    pygame.draw.circle(surf, body, (62, 46), 8)
    pygame.draw.rect(surf, dark, pygame.Rect(20, 80, 12, 14), border_radius=6)  # legs
    pygame.draw.rect(surf, dark, pygame.Rect(40, 80, 12, 14), border_radius=6)
    pygame.draw.circle(surf, (40, 20, 30), (30, 20), 3)  # eyes
    pygame.draw.circle(surf, (40, 20, 30), (42, 20), 3)
    pygame.draw.arc(surf, (40, 20, 30), pygame.Rect(28, 22, 16, 12), math.pi, 2 * math.pi, 2)
    pygame.draw.circle(surf, (255, 170, 200), (28, 48), 7)  # belly sheen
    return surf


def _walker(robe: Color, trim: Color) -> pygame.Surface:
    surf = _surface(20, 28)
    pygame.draw.polygon(surf, robe, [(10, 4), (17, 26), (3, 26)])  # hooded robe
    pygame.draw.circle(surf, trim, (10, 5), 4)  # hood rim
    pygame.draw.circle(surf, (20, 18, 30), (10, 5), 2)  # shadowed face
    pygame.draw.line(surf, trim, (6, 26), (14, 26), 2)  # hem
    return surf


def _build_warden() -> pygame.Surface:
    surf = _walker((120, 60, 160), (200, 140, 240))
    pygame.draw.circle(surf, (255, 150, 90), (8, 5), 1)  # ember eyes
    pygame.draw.circle(surf, (255, 150, 90), (12, 5), 1)
    return surf


def _build_locksmith() -> pygame.Surface:
    surf = _walker((60, 90, 140), (140, 190, 240))
    pygame.draw.line(surf, (250, 210, 60), (16, 10), (16, 18), 2)  # raised key
    pygame.draw.circle(surf, (250, 210, 60), (16, 9), 2)
    return surf


def _build_snare() -> pygame.Surface:
    surf = _surface(32, 16)
    pygame.draw.rect(surf, (60, 60, 70), pygame.Rect(2, 6, 28, 9), border_radius=2)
    for stripe_x in range(4, 28, 8):  # hazard stripes
        pygame.draw.rect(surf, (250, 210, 60), pygame.Rect(stripe_x, 6, 4, 9))
    pygame.draw.rect(surf, (90, 90, 105), pygame.Rect(4, 2, 11, 5))  # lid halves
    pygame.draw.rect(surf, (90, 90, 105), pygame.Rect(17, 2, 11, 5))
    pygame.draw.rect(surf, (255, 80, 80), pygame.Rect(14, 8, 4, 4))  # indicator lamp
    return surf


def _build_logo() -> pygame.Surface:
    surf = _surface(320, 96)
    pygame.draw.rect(surf, (30, 25, 55), pygame.Rect(0, 8, 320, 80), border_radius=16)
    pygame.draw.rect(surf, (150, 110, 255), pygame.Rect(0, 8, 320, 80), width=4, border_radius=16)
    pygame.draw.line(surf, (200, 160, 90), (40, 24), (64, 64), 5)  # broom handle
    pygame.draw.polygon(surf, (240, 200, 90), [(58, 58), (76, 70), (66, 82), (48, 68)])  # head
    star = [
        (96, 20),
        (101, 34),
        (116, 34),
        (104, 43),
        (109, 58),
        (96, 48),
        (83, 58),
        (88, 43),
        (76, 34),
        (91, 34),
    ]
    pygame.draw.polygon(surf, (255, 230, 120), star)
    white: Color = (235, 235, 255)
    p_letter = [(140, 74), (140, 24), (166, 24), (166, 48), (140, 48)]
    c_letter = [(210, 24), (184, 24), (184, 74), (210, 74)]
    pygame.draw.lines(surf, white, False, p_letter, 6)  # "P"
    pygame.draw.lines(surf, white, False, c_letter, 6)  # "C"
    pygame.draw.rect(surf, (150, 110, 255), pygame.Rect(228, 34, 64, 8))  # wordmark bars
    pygame.draw.rect(surf, (150, 110, 255), pygame.Rect(228, 54, 48, 8))
    return surf


_BUILDERS: Final[dict[str, Callable[[], pygame.Surface]]] = {
    "car.compact": _build_car_compact,
    "car.hearse": _build_car_hearse,
    "car.wagon": _build_car_wagon,
    "car.performance": _build_car_performance,
    "wisp": _build_wisp,
    "wisp.faint": _build_wisp_faint,
    "smudge": _build_smudge,
    "cleaner": _build_cleaner,
    "cleaner.slimed": _build_cleaner_slimed,
    "building": _build_building,
    "building.haunted": _build_building_haunted,
    "tower": _build_tower,
    "tower.map": _build_tower_map,
    "depot": _build_depot,
    "warden": _build_warden,
    "locksmith": _build_locksmith,
    "mascot": _build_mascot,
    "snare": _build_snare,
    "logo": _build_logo,
}


class SpriteFactory:
    """Generates sprites on demand and caches them by name."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = _BUILDERS[name]()
        return self._cache[name]

"""Driving scene: three-lane road, steerable car, road wisps, progress bar."""

from typing import Final

import pygame

from psychic_cleaners.core.constants import CAR_X, DRIVE_LANES
from psychic_cleaners.core.events import Command, Steer
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_ROAD_TOP: Final[int] = 110
_LANE_HEIGHT: Final[int] = 60
_GRASS: Final[tuple[int, int, int]] = (24, 44, 30)
_LANE_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (52, 52, 60),
    (62, 62, 70),
    (52, 52, 60),
)
_LANE_MARK: Final[tuple[int, int, int]] = (205, 205, 95)
_BAR_RECT: Final[pygame.Rect] = pygame.Rect(120, 24, 400, 12)
_BAR_BACK: Final[tuple[int, int, int]] = (40, 40, 48)
_BAR_FILL: Final[tuple[int, int, int]] = (120, 220, 140)
_BAR_EDGE: Final[tuple[int, int, int]] = (205, 205, 210)


def _lane_center_y(lane: int) -> int:
    return _ROAD_TOP + lane * _LANE_HEIGHT + _LANE_HEIGHT // 2


class DrivingScene:
    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    out.append(Steer(delta=-1))
                elif event.key == pygame.K_DOWN:
                    out.append(Steer(delta=1))
        return out

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill(_GRASS)
        width = surface.get_width()
        for lane in range(DRIVE_LANES):
            band = pygame.Rect(0, _ROAD_TOP + lane * _LANE_HEIGHT, width, _LANE_HEIGHT)
            pygame.draw.rect(surface, _LANE_COLORS[lane % len(_LANE_COLORS)], band)
        for boundary in range(1, DRIVE_LANES):
            y = _ROAD_TOP + boundary * _LANE_HEIGHT
            for x in range(0, width, 40):
                pygame.draw.line(surface, _LANE_MARK, (x, y), (x + 20, y), 2)
        drive = game.drive
        loadout = game.loadout
        if drive is None or loadout is None:
            return
        has_lens = loadout.has("lens")
        for wisp in drive.wisps:
            if wisp.faint and not has_lens:
                continue
            sprite = gfx.get("wisp.faint" if wisp.faint else "wisp")
            rect = sprite.get_rect(center=(int(wisp.x), _lane_center_y(wisp.lane)))
            surface.blit(sprite, rect)
        car = gfx.get(f"car.{loadout.vehicle.id}")
        car_rect = car.get_rect(center=(int(CAR_X), _lane_center_y(drive.lane)))
        surface.blit(car, car_rect)
        fraction = min(1.0, drive.distance_done / max(drive.distance_total, 1.0))
        pygame.draw.rect(surface, _BAR_BACK, _BAR_RECT)
        fill_width = int(_BAR_RECT.width * fraction)
        fill = pygame.Rect(_BAR_RECT.x, _BAR_RECT.y, fill_width, _BAR_RECT.height)
        pygame.draw.rect(surface, _BAR_FILL, fill)
        pygame.draw.rect(surface, _BAR_EDGE, _BAR_RECT, 1)
        text.draw(surface, f"${game.wallet.balance}", (16, 16), size=20)

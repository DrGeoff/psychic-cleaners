"""City map scene: pick destinations, watch hauntings and wisps, read the HUD."""

import pygame

from psychic_cleaners.core.constants import (
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    PSI_MAX,
    TOWER_POS,
)
from psychic_cleaners.core.events import Command, DeployBait, GridPos, SetDestination
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import _draw_mascot_banner
from psychic_cleaners.shell.text import TextRenderer

_CELL: int = 56
_ORIGIN_X: int = 40
_ORIGIN_Y: int = 12
_HUD_Y: int = 356


def _cell_rect(pos: GridPos) -> pygame.Rect:
    return pygame.Rect(_ORIGIN_X + pos[0] * _CELL + 4, _ORIGIN_Y + pos[1] * _CELL + 4, 48, 48)


class CityMapScene:
    """Scene registered under SceneId.MAP."""

    def __init__(self) -> None:
        self.cursor: GridPos = DEPOT_POS

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        commands: list[Command] = []
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            x, y = self.cursor
            if event.key == pygame.K_LEFT:
                self.cursor = (max(x - 1, 0), y)
            elif event.key == pygame.K_RIGHT:
                self.cursor = (min(x + 1, GRID_WIDTH - 1), y)
            elif event.key == pygame.K_UP:
                self.cursor = (x, max(y - 1, 0))
            elif event.key == pygame.K_DOWN:
                self.cursor = (x, min(y + 1, GRID_HEIGHT - 1))
            elif event.key == pygame.K_RETURN:
                commands.append(SetDestination(self.cursor))
            elif event.key == pygame.K_b:
                commands.append(DeployBait())
        return commands

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((24, 26, 34))
        detector = game.loadout is not None and game.loadout.has("detector")
        flash = int(pygame.time.get_ticks() / 250) % 2 == 0  # ~2 Hz toggle
        for pos, building in game.city.buildings.items():
            if not building.haunted:
                name = "building"
            elif detector:
                # residue detector: haunted buildings flash between the sprites
                name = "building.haunted" if flash else "building"
            else:
                name = "building.haunted"
            surface.blit(gfx.get(name), _cell_rect(pos).topleft)
        surface.blit(gfx.get("tower"), _cell_rect(TOWER_POS).topleft)
        surface.blit(gfx.get("depot"), _cell_rect(DEPOT_POS).topleft)
        if detector:
            # wisps are invisible without the residue detector
            wisp_sprite = gfx.get("wisp")
            for wisp in game.city.wisps:
                px = int(_ORIGIN_X + wisp.x * _CELL + _CELL / 2) - 8
                py = int(_ORIGIN_Y + wisp.y * _CELL + _CELL / 2) - 8
                surface.blit(wisp_sprite, (px, py))
        car = _cell_rect(game.position)
        car_rect = pygame.Rect(car.left + 16, car.top + 36, 16, 10)
        pygame.draw.rect(surface, (250, 250, 250), car_rect)
        cursor_rect = _cell_rect(self.cursor).inflate(6, 6)
        pygame.draw.rect(surface, (255, 230, 90), cursor_rect, width=2)
        self._draw_hud(surface, game, text)
        _draw_mascot_banner(surface, game, text)

    def _draw_hud(self, surface: pygame.Surface, game: Game, text: TextRenderer) -> None:
        pygame.draw.rect(surface, (12, 12, 18), pygame.Rect(0, _HUD_Y, 640, 400 - _HUD_Y))
        text.draw(surface, f"${game.wallet.balance}", (10, _HUD_Y + 6), size=16)
        text.draw(surface, f"PSI {game.psi.value:>4}", (10, _HUD_Y + 24), size=16)
        bar = pygame.Rect(90, _HUD_Y + 26, 120, 10)
        pygame.draw.rect(surface, (60, 60, 70), bar)
        fill_width = int(bar.width * game.psi.value / PSI_MAX)
        pygame.draw.rect(surface, (170, 90, 220), pygame.Rect(bar.left, bar.top, fill_width, 10))
        snares = f"snares {game.free_snares()} free / {game.snares_full} full"
        text.draw(surface, snares, (240, _HUD_Y + 6), size=16)
        text.draw(surface, f"contained {game.contained}", (240, _HUD_Y + 24), size=16)
        text.draw(surface, f"slimed {len(game.slimed)}", (430, _HUD_Y + 6), size=16)

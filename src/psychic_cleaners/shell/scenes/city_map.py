"""City map scene: pick destinations, watch hauntings and wisps, read the HUD."""

import pygame

from psychic_cleaners.core.catalog import ITEMS
from psychic_cleaners.core.constants import (
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    PSI_MAX,
    TOWER_POS,
)
from psychic_cleaners.core.events import BuyItem, Command, DeployBait, GridPos, SetDestination
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import _draw_mascot_banner
from psychic_cleaners.shell.text import TextRenderer

_CELL: int = 56
_ORIGIN_X: int = 40
_ORIGIN_Y: int = 12
_HUD_Y: int = 356
_RED: tuple[int, int, int] = (240, 120, 120)
_CAR_MARKER: tuple[int, int, int] = (250, 250, 250)
_CAR_MARKER_OUTLINE: tuple[int, int, int] = (30, 30, 40)
_CONTROL_HINT: str = "Arrows: move cursor - Enter: travel - B: bait"


def _cell_rect(pos: GridPos) -> pygame.Rect:
    return pygame.Rect(_ORIGIN_X + pos[0] * _CELL + 4, _ORIGIN_Y + pos[1] * _CELL + 4, 48, 48)


class CityMapScene:
    """Scene registered under SceneId.MAP."""

    def __init__(self) -> None:
        self.cursor: GridPos = DEPOT_POS

    def reset(self) -> None:
        """Return the cursor to the Depot.

        Called by the shell on every transition INTO TITLE, so a new game's
        map opens with the cursor on the Depot rather than wherever the
        previous game left it.
        """
        self.cursor = DEPOT_POS

    def commands(
        self, events: list[pygame.event.Event], game: Game, dt_seconds: float
    ) -> list[Command]:
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
            elif event.key == pygame.K_s:
                commands.append(BuyItem("snare"))
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
        # "tower.map" is scaled to fit the tower's own cell (28x48, aspect
        # preserved) so it doesn't spill into the building cell below and
        # hide a haunting there; centered horizontally, flush with the cell
        # top since the sprite height already matches the cell height.
        tower_rect = _cell_rect(TOWER_POS)
        tower_sprite = gfx.get("tower.map")
        tower_x = tower_rect.left + (tower_rect.width - tower_sprite.get_width()) // 2
        surface.blit(tower_sprite, (tower_x, tower_rect.top))
        surface.blit(gfx.get("depot"), _cell_rect(DEPOT_POS).topleft)
        if detector:
            # wisps are invisible without the residue detector
            wisp_sprite = gfx.get("wisp")
            for wisp in game.city.wisps:
                px = int(_ORIGIN_X + wisp.x * _CELL + _CELL / 2) - 8
                py = int(_ORIGIN_Y + wisp.y * _CELL + _CELL / 2) - 8
                surface.blit(wisp_sprite, (px, py))
        if game.convergence is not None:
            # The Warden and the Locksmith are visible without any detector:
            # their walk toward the Tower is the endgame telegraph.
            for name, walker in (
                ("warden", game.convergence.warden),
                ("locksmith", game.convergence.locksmith),
            ):
                sprite = gfx.get(name)
                px = int(_ORIGIN_X + walker.x * _CELL + _CELL / 2) - sprite.get_width() // 2
                py = int(_ORIGIN_Y + walker.y * _CELL + _CELL / 2) - sprite.get_height() // 2
                surface.blit(sprite, (px, py))
        # Player marker: drawn AFTER every cell sprite (buildings, tower,
        # depot, wisps) so it stays visible even when parked on the Depot
        # tile, with a dark outline for contrast against any cell colour.
        car = _cell_rect(game.position)
        outline_rect = pygame.Rect(car.left + 13, car.top + 35, 22, 12)
        pygame.draw.rect(surface, _CAR_MARKER_OUTLINE, outline_rect, border_radius=2)
        car_rect = pygame.Rect(car.left + 14, car.top + 36, 20, 10)
        pygame.draw.rect(surface, _CAR_MARKER, car_rect, border_radius=2)
        cursor_rect = _cell_rect(self.cursor).inflate(6, 6)
        pygame.draw.rect(surface, (255, 230, 90), cursor_rect, width=2)
        self._draw_hud(surface, game, text)
        _draw_mascot_banner(surface, game, text)

    def _draw_hud(self, surface: pygame.Surface, game: Game, text: TextRenderer) -> None:
        pygame.draw.rect(surface, (12, 12, 18), pygame.Rect(0, _HUD_Y, 640, 400 - _HUD_Y))
        text.draw(surface, f"${game.wallet.balance}", (10, _HUD_Y + 4), size=16)
        text.draw(surface, f"PSI {game.psi.value:>4}", (10, _HUD_Y + 18), size=16)
        bar = pygame.Rect(90, _HUD_Y + 20, 120, 10)
        pygame.draw.rect(surface, (60, 60, 70), bar)
        fill_width = int(bar.width * game.psi.value / PSI_MAX)
        pygame.draw.rect(surface, (170, 90, 220), pygame.Rect(bar.left, bar.top, fill_width, 10))
        snares = f"snares {game.free_snares()} free / {game.snares_full} full"
        text.draw(surface, snares, (240, _HUD_Y + 4), size=16)
        text.draw(surface, f"contained {game.contained}", (240, _HUD_Y + 18), size=16)
        text.draw(surface, f"slimed {len(game.slimed)}", (430, _HUD_Y + 4), size=16)
        if game.position == DEPOT_POS:
            hint = f"S: buy snare (${ITEMS['snare'].price})"
            text.draw(surface, hint, (430, _HUD_Y + 18), size=16)
        if game.notice is not None:
            text.draw(surface, game.notice, (10, _HUD_Y + 32), size=16, color=_RED)
        else:
            # A first-time player never trips a notice, so this row would
            # otherwise stay blank for the whole game.
            text.draw(surface, _CONTROL_HINT, (10, _HUD_Y + 32), size=16)

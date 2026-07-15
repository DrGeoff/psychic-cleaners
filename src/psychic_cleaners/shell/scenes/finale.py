"""Finale scene: send cleaners past the bouncing mascot into the Tower door."""

from __future__ import annotations

from typing import Final

import pygame

from psychic_cleaners.core.constants import DOOR_X
from psychic_cleaners.core.events import Command, StartRun
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import _blit_bottom_aligned
from psychic_cleaners.shell.text import TextRenderer

_GROUND_Y: Final[int] = 336
_SKY: Final[tuple[int, int, int]] = (18, 12, 44)
_GROUND: Final[tuple[int, int, int]] = (44, 40, 52)
_DOOR: Final[tuple[int, int, int]] = (94, 62, 30)


class FinaleScene:
    """The Tower door run: the giant bounces, cleaners dash for the door."""

    def commands(
        self, events: list[pygame.event.Event], game: Game, dt_seconds: float
    ) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                out.append(StartRun())
        return out

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill(_SKY)
        pygame.draw.rect(
            surface,
            _GROUND,
            pygame.Rect(0, _GROUND_Y, surface.get_width(), surface.get_height() - _GROUND_Y),
        )
        tower = gfx.get("tower")
        surface.blit(tower, (int(DOOR_X) - tower.get_width() // 2, _GROUND_Y - tower.get_height()))
        pygame.draw.rect(surface, _DOOR, pygame.Rect(int(DOOR_X) - 12, _GROUND_Y - 48, 24, 48))
        sim = game.finale
        if sim is not None:
            mascot = gfx.get("mascot")
            hop = 28 if sim.airborne else 0  # readable hop: run under him while he's up
            _blit_bottom_aligned(surface, mascot, sim.giant_x, _GROUND_Y, hop)
            if sim.runner_x is not None:
                runner = gfx.get("cleaner")
                _blit_bottom_aligned(surface, runner, sim.runner_x, _GROUND_Y)
            text.draw(surface, f"INSIDE: {sim.inside}", (16, 12))
            text.draw(surface, f"SQUASHED: {sim.squashed}", (16, 32))
            text.draw(surface, f"REMAINING: {sim.remaining_outside}", (16, 52))
            if sim.runner_x is None and sim.remaining_outside > 0:
                # Only prompt when SPACE would actually send someone.
                text.draw(surface, "SPACE: send cleaner", (16, 380))

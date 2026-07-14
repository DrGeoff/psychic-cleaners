"""Finale scene: send cleaners past the bouncing mascot into the Tower door."""

from __future__ import annotations

from typing import Final

import pygame

from psychic_cleaners.core.constants import DOOR_X
from psychic_cleaners.core.events import Command, StartRun
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_GROUND_Y: Final[int] = 336
_SKY: Final[tuple[int, int, int]] = (18, 12, 44)
_GROUND: Final[tuple[int, int, int]] = (44, 40, 52)
_DOOR: Final[tuple[int, int, int]] = (94, 62, 30)


class FinaleScene:
    """The Tower door run: the giant bounces, cleaners dash for the door."""

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
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
            surface.blit(
                mascot,
                (
                    int(sim.giant_x) - mascot.get_width() // 2,
                    _GROUND_Y - mascot.get_height() - hop,
                ),
            )
            if sim.runner_x is not None:
                runner = gfx.get("cleaner")
                surface.blit(
                    runner,
                    (int(sim.runner_x) - runner.get_width() // 2, _GROUND_Y - runner.get_height()),
                )
            text.draw(surface, f"INSIDE: {sim.inside}", (16, 12))
            text.draw(surface, f"SQUASHED: {sim.squashed}", (16, 32))
            text.draw(surface, f"REMAINING: {sim.remaining_outside}", (16, 52))
        text.draw(surface, "SPACE: send cleaner", (16, 380))

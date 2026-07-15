"""Bust scene: position cleaners, lay the snare, steer the smudge, spring it."""

import pygame

from psychic_cleaners.core.bust import BustPhase
from psychic_cleaners.core.constants import BUST_GROUND_Y, CLEANER_SPEED
from psychic_cleaners.core.events import (
    Command,
    DeployBait,
    LaySnare,
    MoveCleaner,
    PlaceCleaner,
    SpringSnare,
)
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import _blit_bottom_aligned, _draw_mascot_banner
from psychic_cleaners.shell.text import TextRenderer

_POSITIONING = (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT, BustPhase.SNARE)

_HINTS: dict[BustPhase, str] = {
    BustPhase.POSITION_LEFT: "Arrows: move first cleaner - Enter: place",
    BustPhase.POSITION_RIGHT: "Arrows: move second cleaner - Enter: place",
    BustPhase.SNARE: "Arrows: move snare - Enter: lay it down",
    BustPhase.ACTIVE: "Space: spring the snare when the smudge is above it",
    BustPhase.RESOLVED: "",
}


class BustingScene:
    def commands(
        self, events: list[pygame.event.Event], game: Game, dt_seconds: float
    ) -> list[Command]:
        bust = game.bust
        if bust is None:
            return []
        cmds: list[Command] = []
        if bust.phase in _POSITIONING:
            pressed = pygame.key.get_pressed()
            step = CLEANER_SPEED * dt_seconds
            if pressed[pygame.K_LEFT]:
                cmds.append(MoveCleaner(-step))
            if pressed[pygame.K_RIGHT]:
                cmds.append(MoveCleaner(step))
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_RETURN:
                if bust.phase in (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT):
                    cmds.append(PlaceCleaner())
                elif bust.phase is BustPhase.SNARE:
                    cmds.append(LaySnare())
            elif event.key == pygame.K_SPACE:
                cmds.append(SpringSnare())
            elif event.key == pygame.K_b:
                cmds.append(DeployBait())
        return cmds

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((16, 14, 24))
        # Building facade with lit windows.
        pygame.draw.rect(surface, (72, 62, 88), pygame.Rect(60, 40, 520, 320))
        for row_y in range(80, 320, 60):
            for col_x in range(100, 560, 80):
                pygame.draw.rect(surface, (236, 210, 120), pygame.Rect(col_x, row_y, 24, 32))
        # Pavement.
        pygame.draw.rect(surface, (58, 58, 66), pygame.Rect(0, int(BUST_GROUND_Y), 640, 40))
        bust = game.bust
        if bust is None:
            return
        # Placed cleaners.
        for side, x in enumerate((bust.left_x, bust.right_x)):
            if x is not None:
                name = "cleaner.slimed" if bust.slimed_side == side else "cleaner"
                _blit_bottom_aligned(surface, gfx.get(name), x, BUST_GROUND_Y)
        # Cursor: a cleaner while positioning, the snare while aiming it.
        if bust.phase in (BustPhase.POSITION_LEFT, BustPhase.POSITION_RIGHT):
            _blit_bottom_aligned(surface, gfx.get("cleaner"), bust.cursor_x, BUST_GROUND_Y)
        elif bust.phase is BustPhase.SNARE:
            _blit_bottom_aligned(surface, gfx.get("snare"), bust.cursor_x, BUST_GROUND_Y)
        # Laid snare.
        if bust.snare_x is not None:
            _blit_bottom_aligned(surface, gfx.get("snare"), bust.snare_x, BUST_GROUND_Y)
        # The smudge.
        smudge = gfx.get("smudge")
        smudge_pos = (
            int(bust.ghost_x - smudge.get_width() / 2),
            int(bust.ghost_y - smudge.get_height() / 2),
        )
        surface.blit(smudge, smudge_pos)
        # Beams.
        beams = bust.beam_endpoints()
        if beams is not None:
            for start, end in beams:
                pygame.draw.line(surface, (120, 220, 255), start, end, 3)
        # Hint sits on the bottom pavement strip (like the finale's prompt) so
        # the top-of-screen mascot banner can never overprint it.
        text.draw(surface, _HINTS[bust.phase], (20, 380), size=16)
        _draw_mascot_banner(surface, game, text)

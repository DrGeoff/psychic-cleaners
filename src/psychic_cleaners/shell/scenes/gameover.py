"""Game-over scene: verdict, account code or loss reason, Enter back to title."""

from __future__ import annotations

from typing import Final

import pygame

from psychic_cleaners.core.events import Command, Continue
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_BG: Final[tuple[int, int, int]] = (12, 10, 18)
_WIN: Final[tuple[int, int, int]] = (240, 214, 90)
_LOSE: Final[tuple[int, int, int]] = (222, 84, 84)
_CODE: Final[tuple[int, int, int]] = (120, 240, 160)


class GameOverScene:
    """Shows WON/LOST, the new account code on a win, the reason on a loss."""

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                out.append(Continue())
        return out

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill(_BG)
        won = game.result == "won"
        text.draw(
            surface,
            "WON" if won else "LOST",
            (280, 100),
            size=48,
            color=_WIN if won else _LOSE,
        )
        if won and game.last_account_code is not None:
            text.draw(surface, "FRANCHISE APPROVED - YOUR NEW ACCOUNT CODE:", (150, 190))
            text.draw(surface, game.last_account_code, (270, 220), size=32, color=_CODE)
        elif game.lose_reason is not None:
            text.draw(surface, game.lose_reason, (190, 200))
        text.draw(surface, "Enter: title", (280, 340))

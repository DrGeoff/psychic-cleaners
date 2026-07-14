"""Title scene: name entry and account-code restore."""

import enum
from typing import Final

import pygame

from psychic_cleaners.core.events import Command, EnterAccount, NewGame
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_NAME_MAX: Final[int] = 20
_CODE_MAX: Final[int] = 7


class _Field(enum.Enum):
    NAME = enum.auto()
    CODE = enum.auto()


class TitleScene:
    """Two text fields (name, account code); Enter starts the game.

    A non-empty code field means "restore my account" (EnterAccount);
    an empty one starts a fresh franchise (NewGame).
    """

    def __init__(self) -> None:
        self._name: str = ""
        self._code: str = ""
        self._focus: _Field = _Field.NAME

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        out: list[Command] = []
        for event in events:
            if event.type == pygame.TEXTINPUT:
                self._append(str(event.text))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self._focus = _Field.CODE if self._focus is _Field.NAME else _Field.NAME
                elif event.key == pygame.K_BACKSPACE:
                    if self._focus is _Field.NAME:
                        self._name = self._name[:-1]
                    else:
                        self._code = self._code[:-1]
                elif event.key == pygame.K_RETURN and self._name.strip():
                    if self._code:
                        out.append(EnterAccount(self._name, self._code))
                    else:
                        out.append(NewGame(self._name))
        return out

    def _append(self, text: str) -> None:
        printable = "".join(ch for ch in text if ch.isprintable())
        if self._focus is _Field.NAME:
            self._name = (self._name + printable)[:_NAME_MAX]
        else:
            self._code = (self._code + printable.upper())[:_CODE_MAX]

    def draw(
        self,
        surface: pygame.Surface,
        game: Game,
        gfx: SpriteFactory,
        text: TextRenderer,
    ) -> None:
        surface.fill((14, 10, 38))
        logo = gfx.get("logo")
        surface.blit(logo, ((surface.get_width() - logo.get_width()) // 2, 32))
        name_focused = self._focus is _Field.NAME
        self._draw_field(surface, text, "Name", self._name, 200, focused=name_focused)
        self._draw_field(surface, text, "Account code", self._code, 250, focused=not name_focused)
        if game.notice is not None:
            text.draw(surface, game.notice, (110, 305), size=16, color=(255, 96, 96))
        text.draw(
            surface,
            "Tab switches fields. Enter starts. Blank code = new $10,000 franchise.",
            (110, 340),
            size=14,
            color=(160, 160, 190),
        )

    def _draw_field(
        self,
        surface: pygame.Surface,
        text: TextRenderer,
        label: str,
        value: str,
        y: int,
        *,
        focused: bool,
    ) -> None:
        color = (255, 214, 90) if focused else (110, 110, 140)
        text.draw(surface, label, (110, y + 6), size=16, color=color)
        box = pygame.Rect(250, y, 280, 28)
        pygame.draw.rect(surface, color, box, width=2)
        cursor = "_" if focused else ""
        text.draw(surface, value + cursor, (258, y + 6), size=16)

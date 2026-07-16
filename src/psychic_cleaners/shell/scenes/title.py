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

KARAOKE_WORDS: Final[tuple[str, ...]] = (
    "WHEN",
    "THE",
    "STAINS",
    "COME",
    "CREEPING",
    "CALL",
    "THE",
    "CLEANERS",
)


def _draw_karaoke(surface: pygame.Surface, text: TextRenderer, elapsed: float) -> None:
    """Bouncing-ball lyric line — pure presentation, no game state.

    `elapsed` is simulated seconds accumulated from dt, not wall-clock time:
    real time would make this (and any screenshot of it) non-deterministic
    under fast-forwarded or injected dt.
    """
    ball_index = int(elapsed / 0.5) % len(KARAOKE_WORDS)
    x = 48
    y = 330
    for i, word in enumerate(KARAOKE_WORDS):
        text.draw(surface, word, (x, y), size=14, color=(250, 220, 120))
        if i == ball_index:
            pygame.draw.circle(surface, (255, 255, 255), (x + 4 * len(word), y - 10), 4)
        x += 8 * len(word) + 12


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
        self._elapsed: float = 0.0

    def commands(
        self, events: list[pygame.event.Event], game: Game, dt_seconds: float
    ) -> list[Command]:
        self._elapsed += dt_seconds
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

    def reset(self) -> None:
        """Clear both buffers and return focus to the name field.

        Called by the shell on every transition INTO TITLE (fresh game or a
        return from GAME_OVER), so a REJECTED account code doesn't wipe the
        player's name mid-edit, but a later trip back to TITLE still starts
        from blank fields rather than the previous game's leftovers.
        """
        self._name = ""
        self._code = ""
        self._focus = _Field.NAME
        self._elapsed = 0.0

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
        _draw_karaoke(surface, text, self._elapsed)

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

"""Interactive store: pick one vehicle, fill it with gear, F to finish."""

from __future__ import annotations

from typing import Final

import pygame

from psychic_cleaners.core.catalog import ITEMS, VEHICLES, Item, Vehicle
from psychic_cleaners.core.events import BuyItem, Command, FinishShopping, SelectVehicle
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

_ROWS: list[Vehicle | Item] = [*VEHICLES.values(), *ITEMS.values()]

_WHITE = (235, 235, 235)
_GREY = (110, 110, 110)
_RED = (240, 120, 120)

_MARKER_X: Final[int] = 24
_NAME_X: Final[int] = 44
_PRICE_X: Final[int] = 280
_SUFFIX_X: Final[int] = 380


class ShopScene:
    """Vertical menu: 4 vehicles then 7 items. Up/Down moves, Enter buys, F finishes."""

    def __init__(self) -> None:
        self.cursor = 0

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        commands: list[Command] = []
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self.cursor = (self.cursor - 1) % len(_ROWS)
            elif event.key == pygame.K_DOWN:
                self.cursor = (self.cursor + 1) % len(_ROWS)
            elif event.key == pygame.K_RETURN:
                row = _ROWS[self.cursor]
                if isinstance(row, Vehicle):
                    commands.append(SelectVehicle(row.id))
                else:
                    commands.append(BuyItem(row.id))
            elif event.key == pygame.K_f:
                commands.append(FinishShopping())
        return commands

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None:
        surface.fill((18, 14, 28))
        text.draw(surface, "PSYCHIC CLEANERS OUTFITTERS", (24, 16), size=24)
        text.draw(surface, f"Balance: ${game.wallet.balance}", (24, 44), size=16)
        if game.loadout is None:
            text.draw(surface, "Choose a vehicle (Enter). F when done.", (24, 62), size=16)
        else:
            loadout = game.loadout
            status = (
                f"Vehicle: {loadout.vehicle.name}   "
                f"Slots: {loadout.slots_used()}/{loadout.vehicle.capacity}"
            )
            text.draw(surface, status, (24, 62), size=16)
        for index, row in enumerate(_ROWS):
            y = 96 + index * 22
            marker = ">" if index == self.cursor else ""
            color = _WHITE if game.wallet.can_afford(row.price) else _GREY
            if isinstance(row, Vehicle):
                chosen = game.loadout is not None and game.loadout.vehicle.id == row.id
                suffix = "[chosen]" if chosen else ""
            else:
                owned = game.loadout.count(row.id) if game.loadout is not None else 0
                suffix = f"x{owned}" if owned else ""
            text.draw(surface, marker, (_MARKER_X, y), size=16, color=color)
            text.draw(surface, row.name, (_NAME_X, y), size=16, color=color)
            text.draw(surface, f"${row.price}", (_PRICE_X, y), size=16, color=color)
            if suffix:
                text.draw(surface, suffix, (_SUFFIX_X, y), size=16, color=color)
        if game.notice is not None:
            text.draw(surface, game.notice, (24, 376), size=16, color=_RED)

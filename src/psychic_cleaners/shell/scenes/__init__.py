"""Scene protocol and the placeholder scene used before real scenes land."""

from typing import Protocol

import pygame

from psychic_cleaners.core.events import Command, Continue
from psychic_cleaners.core.game import Game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer


class Scene(Protocol):
    """One thin shell module per core mechanic: input -> Commands, state -> pixels."""

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]: ...

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None: ...


class PlaceholderScene:
    """Labelled stand-in scene: shows its name, turns Return into Continue()."""

    def __init__(self, name: str) -> None:
        self.name = name

    def commands(self, events: list[pygame.event.Event], game: Game) -> list[Command]:
        return [
            Continue()
            for event in events
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        ]

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None:
        surface.fill((16, 16, 24))
        width, height = surface.get_size()
        text.draw(surface, self.name, (width // 2 - 5 * len(self.name), height // 2 - 12), size=24)
        text.draw(surface, "press Enter", (width // 2 - 40, height // 2 + 16), size=16)

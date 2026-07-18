"""Scene protocol and helpers shared by the scene modules."""

from typing import Protocol

import pygame

from psychic_cleaners.core.constants import MASCOT_ALERT_WINDOW
from psychic_cleaners.core.events import Command
from psychic_cleaners.core.game import Game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.text import TextRenderer

# Shared by every scene that draws game.notice as a rejection message.
_NOTICE_RED: tuple[int, int, int] = (240, 120, 120)


class Scene(Protocol):
    """One thin shell module per core mechanic: input -> Commands, state -> pixels.

    ``dt_seconds`` is the clamped frame dt the app will feed to ``Game.tick``,
    so held-key movement can scale with real time instead of frame count.
    """

    def commands(
        self, events: list[pygame.event.Event], game: Game, dt_seconds: float
    ) -> list[Command]: ...

    def draw(
        self, surface: pygame.Surface, game: Game, gfx: SpriteFactory, text: TextRenderer
    ) -> None: ...


def _blit_bottom_aligned(
    surface: pygame.Surface,
    sprite: pygame.Surface,
    x: float,
    ground_y: float,
    y_offset: float = 0.0,
) -> None:
    """Blit `sprite` centered on x, bottom-aligned to ground_y, raised by y_offset."""
    surface.blit(
        sprite,
        (int(x - sprite.get_width() / 2), int(ground_y - sprite.get_height() - y_offset)),
    )


def _draw_mascot_banner(surface: pygame.Surface, game: Game, text: TextRenderer) -> None:
    """Flashing mascot-alert banner; draws nothing unless the mascot is in ALERT."""
    if game.mascot.state is not MascotState.ALERT:
        return
    # clamp: a hypothetical alert_remaining > MASCOT_ALERT_WINDOW must never
    # drive elapsed negative and desync the flash parity
    elapsed = max(0.0, MASCOT_ALERT_WINDOW - game.mascot.alert_remaining)
    if int(elapsed * 2) % 2 != 0:
        return  # off phase of the flash
    charges = game.loadout.bait_charges if game.loadout is not None else 0
    banner = f"MASCOT INBOUND — B: BAIT ({charges} left)"
    text.draw(surface, banner, (150, 8), size=20, color=(255, 96, 96))


def _bait_control_hint(game: Game) -> str:
    """ "B: bait" control text, or an explanation of what's still missing.

    Deploying bait needs BOTH the Mascot sensor (to ever see an alert
    instead of an unwarned stomp) and Gummy bait charges — without both,
    pressing B silently does nothing, so the always-on hint must say why.
    """
    has_sensor = game.loadout is not None and game.loadout.has("sensor")
    has_bait = game.loadout is not None and game.loadout.bait_charges > 0
    if has_sensor and has_bait:
        return "B: bait"
    missing = []
    if not has_sensor:
        missing.append("sensor")
    if not has_bait:
        missing.append("bait")
    return f"B: bait (buy {' + '.join(missing)} at the shop first)"

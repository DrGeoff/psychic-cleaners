"""Main loop: fixed-rate stepping, logical surface scaled to the window."""

import os
from typing import Final

import pygame

from psychic_cleaners.core.events import SceneId
from psychic_cleaners.core.game import new_game
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import PlaceholderScene, Scene
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.scenes.shop import ShopScene
from psychic_cleaners.shell.scenes.title import TitleScene
from psychic_cleaners.shell.text import TextRenderer

LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)
WINDOW_SCALE: Final[int] = 2
FPS: Final[int] = 60

SCENES: Final[dict[SceneId, Scene]] = {
    SceneId.TITLE: TitleScene(),
    SceneId.SHOP: ShopScene(),
    SceneId.MAP: CityMapScene(),
    SceneId.DRIVE: PlaceholderScene("DRIVE"),
    SceneId.BUST: PlaceholderScene("BUST"),
    SceneId.FINALE: PlaceholderScene("FINALE"),
    SceneId.GAME_OVER: PlaceholderScene("GAME_OVER"),
}


class App:
    """Owns the window, the Game, and the per-frame pipeline."""

    def __init__(self, seed: int | None = None) -> None:
        pygame.init()
        window_size = (LOGICAL_SIZE[0] * WINDOW_SCALE, LOGICAL_SIZE[1] * WINDOW_SCALE)
        self.window = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Psychic Cleaners")
        self.logical = pygame.Surface(LOGICAL_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.game = new_game(seed if seed is not None else int.from_bytes(os.urandom(4)))
        self.gfx = SpriteFactory()
        self.text = TextRenderer()

    def step(self, dt: float) -> None:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
        scene = SCENES[self.game.scene]
        commands = scene.commands(events, self.game)
        self.game.tick(commands, dt)
        scene.draw(self.logical, self.game, self.gfx, self.text)
        pygame.transform.scale(self.logical, self.window.get_size(), self.window)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)


def main() -> None:
    app = App()
    try:
        app.run()
    finally:
        pygame.quit()

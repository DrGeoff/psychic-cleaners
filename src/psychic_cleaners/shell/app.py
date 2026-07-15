"""Main loop: fixed-rate stepping, logical surface scaled to the window."""

import os
from typing import Final

import pygame

from psychic_cleaners.core.events import (
    AccountRejected,
    BaitDeployed,
    BeamsCrossed,
    BuildingStomped,
    BustMissed,
    CleanerSlimed,
    CommandRejected,
    Event,
    GameLost,
    GameWon,
    GhostTrapped,
    ItemBought,
    MascotAlert,
    PurchaseRejected,
    RunnerEntered,
    RunnerSquashed,
    SceneId,
    WispCaptured,
)
from psychic_cleaners.core.game import new_game
from psychic_cleaners.shell.audio import AudioBank
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import Scene
from psychic_cleaners.shell.scenes.busting import BustingScene
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.scenes.driving import DrivingScene
from psychic_cleaners.shell.scenes.finale import FinaleScene
from psychic_cleaners.shell.scenes.gameover import GameOverScene
from psychic_cleaners.shell.scenes.shop import ShopScene
from psychic_cleaners.shell.scenes.title import TitleScene
from psychic_cleaners.shell.text import TextRenderer

LOGICAL_SIZE: Final[tuple[int, int]] = (640, 400)
WINDOW_SCALE: Final[int] = 2
FPS: Final[int] = 60

EVENT_SOUNDS: Final[dict[type[Event], str]] = {
    GhostTrapped: "trap",
    WispCaptured: "catch",
    BustMissed: "miss",
    BeamsCrossed: "backfire",
    CleanerSlimed: "slime",
    BuildingStomped: "stomp",
    MascotAlert: "alert",
    BaitDeployed: "bait",
    RunnerEntered: "enter",
    RunnerSquashed: "squash",
    GameWon: "win",
    GameLost: "lose",
    ItemBought: "buy",
    PurchaseRejected: "reject",
    AccountRejected: "reject",
    CommandRejected: "reject",
}

SCENES: Final[dict[SceneId, Scene]] = {
    SceneId.TITLE: TitleScene(),
    SceneId.SHOP: ShopScene(),
    SceneId.MAP: CityMapScene(),
    SceneId.DRIVE: DrivingScene(),
    SceneId.BUST: BustingScene(),
    SceneId.FINALE: FinaleScene(),
    SceneId.GAME_OVER: GameOverScene(),
}


def _reset_scene_singletons() -> None:
    """Return the stateful scene singletons to their new-game state.

    SCENES is module-level, so without this a second App in the same
    process (tests, scripted playtests) would inherit the previous game's
    shop/map cursors and title fields.
    """
    title_scene = SCENES[SceneId.TITLE]
    if isinstance(title_scene, TitleScene):
        title_scene.reset()
    shop_scene = SCENES[SceneId.SHOP]
    if isinstance(shop_scene, ShopScene):
        shop_scene.reset()
    map_scene = SCENES[SceneId.MAP]
    if isinstance(map_scene, CityMapScene):
        map_scene.reset()


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
        _reset_scene_singletons()
        self.game = new_game(seed if seed is not None else int.from_bytes(os.urandom(4)))
        self.gfx = SpriteFactory()
        self.text = TextRenderer()
        self.audio = AudioBank()
        self._prev_scene: SceneId = self.game.scene
        if self._prev_scene is SceneId.TITLE:
            self.audio.play_music_loop()

    def step(self, dt: float) -> None:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
        scene = SCENES[self.game.scene]
        commands = scene.commands(events, self.game)
        game_events = self.game.tick(commands, dt)
        for game_event in game_events:
            sound_name = EVENT_SOUNDS.get(type(game_event))
            if sound_name is not None:
                self.audio.play(sound_name)
        if self.game.scene is not self._prev_scene:
            if self.game.scene is SceneId.TITLE:
                self.audio.play_music_loop()
                _reset_scene_singletons()
            elif self._prev_scene is SceneId.TITLE:
                self.audio.stop_music()
            self._prev_scene = self.game.scene
        # Re-resolve after the tick: when a tick changes the scene, the
        # transition frame must draw the NEW scene against the new game state,
        # not the pre-tick scene that gathered this frame's commands.
        SCENES[self.game.scene].draw(self.logical, self.game, self.gfx, self.text)
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

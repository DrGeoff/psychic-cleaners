"""Top-level game state and scene FSM.

This is the skeleton: fields and handlers for TITLE and GAME_OVER only.
Later tasks ADD fields to Game (wallet, psi, city, mascot, loadout, drive,
bust, finale, ...) plus per-scene command handlers in _dispatch, and MUST
extend _reset() with every added field in the same task.

Game.tick keeps the contract's canonical three-step shape:
1. command dispatch, 2. scene ticking, 3. post-tick resolution.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from psychic_cleaners.core.clock import GameClock
from psychic_cleaners.core.constants import STARTING_BANKROLL
from psychic_cleaners.core.events import (
    Command,
    Continue,
    Event,
    NewGame,
    SceneChanged,
    SceneId,
)
from psychic_cleaners.core.rng import Rng, make_rng

__all__ = ["Game", "SceneId", "new_game"]


@dataclass
class Game:
    rng: Rng
    clock: GameClock = field(default_factory=GameClock)
    scene: SceneId = SceneId.TITLE
    player_name: str = ""
    starting_bankroll: int = STARTING_BANKROLL
    result: str | None = None

    def tick(self, commands: Sequence[Command], dt_seconds: float) -> list[Event]:
        events: list[Event] = []
        # 1. Command dispatch: per-command, scene-gated handlers.
        for command in commands:
            self._dispatch(command, events)
        # 2. Scene ticking, AFTER the dispatch loop, on the CURRENT scene.
        if self.scene in self._world_scenes():
            # World time passes only here; psi/city/mascot ticks join in
            # later tasks at this same point.
            self.clock.advance(dt_seconds)
        # 3. Post-tick resolution: empty for now; later tasks extend it here
        #    (tower psi spikes, finale unlock, arrival routing, bankruptcy).
        return events

    def _dispatch(self, command: Command, events: list[Event]) -> None:
        # Unknown or invalid commands for the current scene are ignored silently.
        if self.scene is SceneId.TITLE and isinstance(command, NewGame):
            self._reset()
            self.player_name = command.name
            self._change_scene(SceneId.SHOP, events)
        elif self.scene is SceneId.GAME_OVER and isinstance(command, Continue):
            self._reset()
            self._change_scene(SceneId.TITLE, events)

    def _change_scene(self, s: SceneId, events: list[Event]) -> None:
        self.scene = s
        events.append(SceneChanged(s))

    def _world_scenes(self) -> frozenset[SceneId]:
        return frozenset({SceneId.MAP, SceneId.DRIVE, SceneId.BUST})

    def _reset(self) -> None:
        """Reinitialize every field except rng to a fresh TITLE state.

        CONVENTION: every later task that adds a Game field MUST extend
        this method in the same task.
        """
        self.clock = GameClock()
        self.scene = SceneId.TITLE
        self.player_name = ""
        self.starting_bankroll = STARTING_BANKROLL
        self.result = None


def new_game(seed: int) -> Game:
    return Game(rng=make_rng(seed))

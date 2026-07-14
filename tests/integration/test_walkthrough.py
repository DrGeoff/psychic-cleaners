"""Scripted FSM walkthrough: title -> shop -> (forced) map -> (forced)
game over -> title.

Forced scene assignments below are placeholders; Milestones 3-9 replace
them one by one with real command-driven transitions.
"""

from psychic_cleaners.core.events import Continue, NewGame, SceneChanged
from psychic_cleaners.core.game import SceneId, new_game


def test_walkthrough_title_to_gameover_and_back() -> None:
    game = new_game(99)
    assert game.scene is SceneId.TITLE

    # Title: start a new franchise.
    events = game.tick([NewGame(name="Ada")], dt_seconds=1.0)
    assert events == [SceneChanged(SceneId.SHOP)]
    assert game.clock.minutes == 0.0  # SHOP is not a world scene

    # Shop -> map (forced until Milestone 3 wires FinishShopping).
    game.scene = SceneId.MAP
    game.tick([], dt_seconds=2.0)
    assert game.clock.minutes > 0.0  # world time flows on the map

    # Map -> game over (forced until Milestone 9 wires the finale).
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    events = game.tick([Continue()], dt_seconds=0.0)
    assert events == [SceneChanged(SceneId.TITLE)]
    assert game.scene is SceneId.TITLE
    assert game.result is None
    assert game.clock.minutes == 0.0

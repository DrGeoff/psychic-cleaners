"""Scripted FSM walkthrough: title -> shop -> (forced) map -> (forced)
game over -> title.

The forced scene/result assignments below are a deliberate FSM-skeleton
shortcut: this test only exercises Game.tick's top-level scene dispatch and
the world-clock gating (SHOP doesn't tick the clock, MAP does), so it jumps
straight to each scene rather than driving the intervening gameplay. For
realistic, fully command-driven playthroughs (shopping, driving, busting,
the finale, winning and losing) see tests/integration/test_full_game.py.
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

    # Shop -> map: forced directly (see module docstring) rather than driving
    # FinishShopping through a real shopping trip.
    game.scene = SceneId.MAP
    game.tick([], dt_seconds=2.0)
    assert game.clock.minutes > 0.0  # world time flows on the map

    # Map -> game over: forced directly (see module docstring) rather than
    # driving a full finale run.
    game.scene = SceneId.GAME_OVER
    game.result = "lost"
    events = game.tick([Continue()], dt_seconds=0.0)
    assert events == [SceneChanged(SceneId.TITLE)]
    assert game.scene is SceneId.TITLE
    assert game.result is None
    assert game.clock.minutes == 0.0

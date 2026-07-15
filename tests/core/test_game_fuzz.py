"""Property tests: Game.tick never raises, whatever the shell throws at it.

Design spec §5: invalid commands produce rejection Events with reasons —
never exceptions. Two angles:

- a lifecycle fuzz that drives a fresh game through a few hundred ticks of
  arbitrary commands (garbage ids, unicode names, out-of-grid positions,
  huge steer/move values), across whatever scenes result;
- a staged fuzz that starts INSIDE the deep scenes (BUST, FINALE) the
  lifecycle fuzz cannot reach by chance — entering BUST needs a bought
  snare AND an arrival on a currently-haunted cell, a conjunction random
  commands never satisfy.

nan floats are excluded (asserting no-raise on nan positions is
meaningless) and inf could stall physics loops, so numbers are bounded to
±10**6 — a separate bounded world, matching what the shell can produce.
"""

from collections.abc import Callable

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from psychic_cleaners.core.bust import BustSim
from psychic_cleaners.core.catalog import ITEMS, VEHICLES
from psychic_cleaners.core.constants import GRID_HEIGHT, GRID_WIDTH
from psychic_cleaners.core.events import (
    BuyItem,
    Command,
    Continue,
    DeployBait,
    EnterAccount,
    FinishShopping,
    LaySnare,
    MoveCleaner,
    NewGame,
    PlaceCleaner,
    SceneId,
    SelectVehicle,
    SetDestination,
    SpringSnare,
    StartRun,
    Steer,
)
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout

_BOUND = 10**6

_ints: st.SearchStrategy[int] = st.integers(min_value=-_BOUND, max_value=_BOUND)
_floats: st.SearchStrategy[float] = st.floats(
    min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
)
# Arbitrary text (empty / whitespace / unicode) MIXED with real catalog ids
# and a plausible name, so lifecycle runs regularly get past TITLE and SHOP
# into MAP / DRIVE / GAME_OVER. BUST and FINALE are out of chance's reach —
# the staged fuzz below starts inside them instead.
_names: st.SearchStrategy[str] = st.one_of(st.just("Pat"), st.text(max_size=20))
_item_ids: st.SearchStrategy[str] = st.one_of(st.sampled_from(sorted(ITEMS)), st.text(max_size=10))
_vehicle_ids: st.SearchStrategy[str] = st.one_of(
    st.sampled_from(sorted(VEHICLES)), st.text(max_size=10)
)
_positions: st.SearchStrategy[tuple[int, int]] = st.one_of(
    st.tuples(
        st.integers(min_value=0, max_value=GRID_WIDTH - 1),
        st.integers(min_value=0, max_value=GRID_HEIGHT - 1),
    ),
    st.tuples(_ints, _ints),
)

_commands: st.SearchStrategy[Command] = st.one_of(
    st.builds(NewGame, name=_names),
    st.builds(EnterAccount, name=_names, code=st.text(max_size=12)),
    st.builds(SelectVehicle, vehicle_id=_vehicle_ids),
    st.builds(BuyItem, item_id=_item_ids),
    st.builds(FinishShopping),
    st.builds(SetDestination, pos=_positions),
    st.builds(Steer, delta=_ints),
    st.builds(MoveCleaner, dx=_floats),
    st.builds(PlaceCleaner),
    st.builds(LaySnare),
    st.builds(SpringSnare),
    st.builds(DeployBait),
    st.builds(StartRun),
    st.builds(Continue),
)


@settings(deadline=None)  # soak-style: a loaded CI runner must not flake per-example
@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    commands=st.lists(_commands, min_size=200, max_size=300),
    dt=st.sampled_from([0.016, 0.1, 0.5, 2.0]),
)
def test_tick_never_raises_on_arbitrary_commands(
    seed: int, commands: list[Command], dt: float
) -> None:
    game = new_game(seed)
    for command in commands:
        game.tick([command], dt)  # design spec §5: rejection Events, never exceptions
        assert isinstance(game.scene, SceneId)


def _staged_bust(seed: int) -> Game:
    """A game dropped straight into an active bust, mid-loadout, on a haunt."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")
    game.city.buildings[(2, 2)].haunted = True
    game.position = (2, 2)
    game.bust = BustSim()
    game.scene = SceneId.BUST
    return game


def _staged_finale(seed: int) -> Game:
    """A game dropped straight into the finale with a full able crew."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")
    game.finale_unlocked = True
    game.finale = FinaleSim(able_cleaners=3)
    game.scene = SceneId.FINALE
    return game


@pytest.mark.parametrize("stage", [_staged_bust, _staged_finale])
@settings(deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    commands=st.lists(_commands, min_size=50, max_size=120),
    dt=st.sampled_from([0.016, 0.1, 0.5, 2.0]),
)
def test_tick_never_raises_from_deep_scenes(
    stage: Callable[[int], Game], seed: int, commands: list[Command], dt: float
) -> None:
    # The deep dispatch arms (BUST positioning/snare/spring, FINALE StartRun)
    # are exercised from the very first tick; the game is then free to wander
    # (resolve -> MAP -> fold/finale/game over) under continued fuzz.
    game = stage(seed)
    for command in commands:
        game.tick([command], dt)
        assert isinstance(game.scene, SceneId)

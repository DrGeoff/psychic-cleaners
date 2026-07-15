"""Task 3: map notices must expire after NOTICE_LIFETIME_SECONDS of world-tick."""

from __future__ import annotations

import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import NOTICE_LIFETIME_SECONDS
from psychic_cleaners.core.events import BuyItem, NewGame, PurchaseRejected, SceneId, SetDestination
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.loadout import Loadout


def _map_game(seed: int) -> Game:
    """A game forced onto the map with a vehicle, skipping title/shop flow."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")  # keeps the bankruptcy rule out of play
    game.scene = SceneId.MAP
    return game


def test_depot_rejection_arms_notice_lifetime() -> None:
    game = _map_game(20)
    game.position = (3, 3)  # away from the Depot
    events = game.tick([BuyItem("snare")], 0.0)
    assert PurchaseRejected("snares only, at the Depot") in events
    assert game.notice == "snares only, at the Depot"
    assert game.notice_remaining == NOTICE_LIFETIME_SECONDS


def test_notice_survives_ticks_just_under_its_lifetime() -> None:
    game = _map_game(21)
    game.position = (3, 3)
    game.tick([BuyItem("snare")], 0.0)
    game.tick([], NOTICE_LIFETIME_SECONDS - 0.1)
    assert game.notice == "snares only, at the Depot"
    assert game.notice_remaining == pytest.approx(0.1)


def test_notice_clears_once_its_lifetime_elapses() -> None:
    game = _map_game(22)
    game.position = (3, 3)
    game.tick([BuyItem("snare")], 0.0)
    game.tick([], NOTICE_LIFETIME_SECONDS - 0.1)
    game.tick([], 0.2)  # crosses zero
    assert game.notice is None
    assert game.notice_remaining == 0.0


def test_scene_change_still_clears_notice_immediately() -> None:
    # Existing behavior (pre-dating this task): a scene change must clear a
    # live notice right away, not wait for it to decay.
    game = _map_game(23)
    game.position = (3, 3)
    game.tick([BuyItem("snare")], 0.0)
    assert game.notice is not None
    assert game.notice_remaining > 0.0
    game.tick([SetDestination((1, 5))], 0.0)  # departs MAP -> DRIVE
    assert game.scene is SceneId.DRIVE
    assert game.notice is None
    assert game.notice_remaining == 0.0


def test_new_game_resets_notice_remaining() -> None:
    game = new_game(24)
    game.notice = "stale notice"
    game.notice_remaining = 3.5
    game.scene = SceneId.TITLE
    game.tick([NewGame("pat")], 0.0)
    assert game.notice is None
    assert game.notice_remaining == 0.0

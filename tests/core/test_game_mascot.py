"""Game-level mascot integration: stomp fines, PSI spikes, event translation."""

import pytest

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import (
    BAIT_PACK_SIZE,
    MASCOT_ALERT_WINDOW,
    PSI_MAX,
    STOMP_FINE,
    STOMP_PSI_SPIKE,
)
from psychic_cleaners.core.events import (
    BaitDeployed,
    BuildingStomped,
    DeployBait,
    Event,
    MascotAlert,
    StompTriggered,
)
from psychic_cleaners.core.game import Game, SceneId, new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.core.pk import PsiModel


def _world_game(seed: int, *, sensor: bool, bait: bool) -> Game:
    """A Game dropped straight into MAP with a hot city, bypassing title/shop."""
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")  # keep the no-snares game-over rule out of these tests
    if sensor:
        game.loadout.add("sensor")
    if bait:
        game.loadout.add("bait")
    game.scene = SceneId.MAP
    game.psi.spike(5_000.0)
    return game


def _tick_until_stomp(game: Game) -> tuple[list[Event], int, int]:
    """Tick until BuildingStomped; return (that tick's events, psi before, balance before)."""
    for _ in range(2_000):
        psi_before = game.psi.value
        balance_before = game.wallet.balance
        events = game.tick([], 1.0)
        if any(isinstance(e, BuildingStomped) for e in events):
            return events, psi_before, balance_before
    pytest.fail("no stomp within 2000 simulated seconds")


def test_stomp_fines_wallet_spikes_psi_and_reports_position() -> None:
    game = _world_game(201, sensor=False, bait=False)
    events, psi_before, balance_before = _tick_until_stomp(game)
    stomp = next(e for e in events if isinstance(e, BuildingStomped))
    assert stomp.fine == STOMP_FINE  # bankroll started at 10,000 so the full fine is charged
    assert game.wallet.balance == balance_before - STOMP_FINE
    assert stomp.pos in game.city.stompable_positions()
    # growth only adds on top of the spike, so >= holds; min() handles the 9,999 clamp
    assert game.psi.value >= min(PSI_MAX, psi_before + STOMP_PSI_SPIKE)
    # the internal trigger event must be translated away, not surfaced to the shell
    assert not any(isinstance(e, StompTriggered) for e in events)


def test_no_sensor_means_no_alert_but_stomps_still_happen() -> None:
    game = _world_game(202, sensor=False, bait=False)
    seen: list[Event] = []
    stomped = False
    for _ in range(2_000):
        events = game.tick([], 1.0)
        seen += events
        if any(isinstance(e, BuildingStomped) for e in events):
            stomped = True
            break
    assert stomped
    assert not any(isinstance(e, MascotAlert) for e in seen)
    assert not any(isinstance(e, StompTriggered) for e in seen)


def _tick_until_alert(game: Game) -> None:
    for _ in range(2_000):
        if any(isinstance(e, MascotAlert) for e in game.tick([], 1.0)):
            return
    pytest.fail("no mascot alert within 2000 simulated seconds")


def _quiet_tick(game: Game, dt: float) -> list[Event]:
    """Tick with psi pinned to zero so no NEW mascot trigger can fire during the window."""
    game.psi = PsiModel()
    return game.tick([], dt)


def test_bait_is_consumed_and_averts_the_stomp() -> None:
    game = _world_game(203, sensor=True, bait=True)
    _tick_until_alert(game)
    state_after_alert = game.mascot.state
    assert state_after_alert is MascotState.ALERT
    game.psi = PsiModel()
    events = game.tick([DeployBait()], 0.1)
    assert any(isinstance(e, BaitDeployed) for e in events)
    assert game.loadout is not None
    assert game.loadout.bait_charges == BAIT_PACK_SIZE - 1
    state_after_bait = game.mascot.state
    assert state_after_bait is MascotState.CALM
    seen: list[Event] = []
    for _ in range(int(MASCOT_ALERT_WINDOW) + 5):
        seen += _quiet_tick(game, 1.0)
    assert not any(isinstance(e, BuildingStomped | StompTriggered) for e in seen)


def test_without_deploy_the_alert_expires_into_a_stomp() -> None:
    # contrast case proving the previous test's aversion is real
    game = _world_game(203, sensor=True, bait=True)
    _tick_until_alert(game)
    seen: list[Event] = []
    for _ in range(int(MASCOT_ALERT_WINDOW) + 5):
        seen += _quiet_tick(game, 1.0)
    assert any(isinstance(e, BuildingStomped) for e in seen)
    assert game.mascot.state is MascotState.CALM


def test_deploy_bait_without_charges_is_ignored() -> None:
    game = _world_game(204, sensor=True, bait=False)
    _tick_until_alert(game)
    events = game.tick([DeployBait()], 0.1)
    assert not any(isinstance(e, BaitDeployed) for e in events)
    # charges are checked FIRST, so the press must NOT cancel the alert
    assert game.mascot.state is MascotState.ALERT

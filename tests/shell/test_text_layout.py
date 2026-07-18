"""Meta rule: on-screen text must never overlap and must stay fully visible.

Regression coverage for two real bugs found by playtesting:
- city_map.py's Depot hint ("S: snare / L: loan / P: repay") used to be drawn
  on the same HUD row as "contained N", overlapping into unreadable text.
- title.py's account-code explanation line used to run off the right edge of
  the 640x400 canvas.

This module renders every scene through a range of representative game
states and asserts, for every string TextRenderer.draw is asked to render,
that its bounding box (a) stays fully inside the 640x400 canvas and (b) never
intersects another string's bounding box drawn in the same frame.
"""

from __future__ import annotations

import itertools

import pygame
import pytest

from psychic_cleaners.core.bust import BustPhase, BustSim
from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.codec import encode_account
from psychic_cleaners.core.constants import DEPOT_POS, MASCOT_ALERT_WINDOW
from psychic_cleaners.core.drive import DriveSim
from psychic_cleaners.core.events import BuyItem, NewGame, SelectVehicle
from psychic_cleaners.core.finale import FinaleSim
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.core.loadout import Loadout
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes import Scene
from psychic_cleaners.shell.scenes.busting import BustingScene
from psychic_cleaners.shell.scenes.city_map import CityMapScene
from psychic_cleaners.shell.scenes.driving import DrivingScene
from psychic_cleaners.shell.scenes.finale import FinaleScene
from psychic_cleaners.shell.scenes.gameover import GameOverScene
from psychic_cleaners.shell.scenes.shop import _ROWS, ShopScene
from psychic_cleaners.shell.scenes.title import TitleScene
from psychic_cleaners.shell.text import TextRenderer

_CANVAS = pygame.Rect(0, 0, 640, 400)


@pytest.fixture(scope="module", autouse=True)
def _display() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))


@pytest.fixture(scope="module")
def gfx() -> SpriteFactory:
    return SpriteFactory()


class _RecordingText(TextRenderer):
    """Records each drawn string's bounding box instead of just blitting it."""

    def __init__(self) -> None:
        super().__init__()
        self.boxes: list[tuple[str, pygame.Rect]] = []

    def draw(
        self,
        surface: pygame.Surface,
        message: str,
        pos: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = (230, 230, 230),
    ) -> None:
        if message:
            width, height = self._font(size).size(message)
            self.boxes.append((message, pygame.Rect(pos[0], pos[1], width, height)))
        super().draw(surface, message, pos, size=size, color=color)


def _render(scene: Scene, game: Game, gfx: SpriteFactory, label: str) -> None:
    """Draw `scene` once and assert every string it drew is legible.

    "Legible" means: fully on-canvas, and not overlapping any other string
    drawn in the same frame.
    """
    surface = pygame.Surface((640, 400))
    text = _RecordingText()
    scene.draw(surface, game, gfx, text)
    for message, box in text.boxes:
        assert _CANVAS.contains(box), (
            f"{label}: {message!r} at {box} is not fully visible on the {_CANVAS} canvas"
        )
    for (msg_a, box_a), (msg_b, box_b) in itertools.combinations(text.boxes, 2):
        assert not box_a.colliderect(box_b), (
            f"{label}: {msg_a!r} {box_a} overlaps {msg_b!r} {box_b}"
        )


# ---------------------------------------------------------------- TITLE ----


def test_title_layout_default(gfx: SpriteFactory) -> None:
    scene = TitleScene()
    game = new_game(1)
    _render(scene, game, gfx, "title/default")


def test_title_layout_full_length_fields(gfx: SpriteFactory) -> None:
    scene = TitleScene()
    scene._name = "X" * 20  # _NAME_MAX
    scene._code = "AB23456"  # _CODE_MAX
    game = new_game(2)
    _render(scene, game, gfx, "title/full-fields")


def test_title_layout_with_notice(gfx: SpriteFactory) -> None:
    scene = TitleScene()
    game = new_game(3)
    game.notice = "invalid account code"
    _render(scene, game, gfx, "title/notice")


# ----------------------------------------------------------------- SHOP ----

_SHOP_STATES = [
    ("empty", None, ()),
    ("loaded", "wagon", ("rig", "bait", "snare", "snare")),
]


@pytest.mark.parametrize("cursor", range(len(_ROWS)))
@pytest.mark.parametrize("state_name,vehicle_id,item_ids", _SHOP_STATES)
def test_shop_layout_every_row(
    gfx: SpriteFactory,
    cursor: int,
    state_name: str,
    vehicle_id: str | None,
    item_ids: tuple[str, ...],
) -> None:
    game = new_game(1)
    game.tick([NewGame("Pat")], 0.0)  # enters SHOP; SelectVehicle is ignored elsewhere
    if vehicle_id is not None:
        game.tick([SelectVehicle(vehicle_id)], 0.0)
        for item_id in item_ids:
            game.tick([BuyItem(item_id)], 0.0)
    scene = ShopScene()
    scene.cursor = cursor
    _render(scene, game, gfx, f"shop/{state_name}/cursor={cursor}")


def test_shop_layout_with_notice(gfx: SpriteFactory) -> None:
    game = new_game(1)
    game.tick([NewGame("Pat")], 0.0)
    game.tick([SelectVehicle("compact")], 0.0)
    game.tick([SelectVehicle("hearse")], 0.0)  # rejected: vehicle already chosen
    assert game.notice == "vehicle already chosen"
    scene = ShopScene()
    _render(scene, game, gfx, "shop/notice")


# ------------------------------------------------------------------ MAP ----


def _map_game(position: tuple[int, int], **overrides: object) -> Game:
    game = new_game(1)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.position = position
    for key, value in overrides.items():
        setattr(game, key, value)
    return game


def test_map_layout_at_depot_default(gfx: SpriteFactory) -> None:
    scene = CityMapScene()
    game = _map_game(DEPOT_POS)
    _render(scene, game, gfx, "map/depot/default")


def test_map_layout_at_depot_with_notice(gfx: SpriteFactory) -> None:
    scene = CityMapScene()
    game = _map_game(DEPOT_POS, notice="snares only, at the Depot")
    _render(scene, game, gfx, "map/depot/notice")


def test_map_layout_at_depot_bait_ready(gfx: SpriteFactory) -> None:
    scene = CityMapScene()
    game = _map_game(DEPOT_POS)
    assert game.loadout is not None
    game.loadout.add("sensor")
    game.loadout.add("bait")
    _render(scene, game, gfx, "map/depot/bait-ready")


def test_map_layout_away_from_depot_with_debt_and_containment(gfx: SpriteFactory) -> None:
    scene = CityMapScene()
    game = _map_game((3, 3), debt=1000, contained=3)
    game.slimed = {0, 1}
    _render(scene, game, gfx, "map/away/debt-and-contained")


def test_map_layout_away_with_notice(gfx: SpriteFactory) -> None:
    scene = CityMapScene()
    game = _map_game((3, 3), notice="no free snare — buy or empty one at the Depot")
    _render(scene, game, gfx, "map/away/notice")


def test_map_layout_bait_missing_hint(gfx: SpriteFactory) -> None:
    scene = CityMapScene()
    game = _map_game((3, 3))  # no sensor, no bait: longest hint variant
    _render(scene, game, gfx, "map/away/bait-missing")


# ---------------------------------------------------------------- DRIVE ----


def _drive_game(items: tuple[str, ...] = ()) -> Game:
    game = new_game(1)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    for item_id in items:
        game.loadout.add(item_id)
    game.drive = DriveSim(distance_total=1000.0, speed=140.0, has_vacuum=False, has_lens=False)
    return game


def test_drive_layout_bait_missing_both(gfx: SpriteFactory) -> None:
    scene = DrivingScene()
    game = _drive_game()
    _render(scene, game, gfx, "drive/bait-missing-both")


def test_drive_layout_bait_missing_bait_only(gfx: SpriteFactory) -> None:
    scene = DrivingScene()
    game = _drive_game(items=("sensor",))
    _render(scene, game, gfx, "drive/bait-missing-bait")


def test_drive_layout_bait_missing_sensor_only(gfx: SpriteFactory) -> None:
    scene = DrivingScene()
    game = _drive_game(items=("bait",))
    _render(scene, game, gfx, "drive/bait-missing-sensor")


def test_drive_layout_bait_ready(gfx: SpriteFactory) -> None:
    scene = DrivingScene()
    game = _drive_game(items=("sensor", "bait"))
    _render(scene, game, gfx, "drive/bait-ready")


def test_drive_layout_mascot_alert_banner(gfx: SpriteFactory) -> None:
    scene = DrivingScene()
    game = _drive_game(items=("sensor", "bait"))
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = MASCOT_ALERT_WINDOW  # elapsed=0: flash is on
    _render(scene, game, gfx, "drive/mascot-alert")


# ----------------------------------------------------------------- BUST ----


def _bust_game(phase: BustPhase) -> Game:
    game = new_game(1)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.bust = BustSim(phase=phase)
    return game


@pytest.mark.parametrize("phase", list(BustPhase))
def test_bust_layout_every_phase(gfx: SpriteFactory, phase: BustPhase) -> None:
    scene = BustingScene()
    game = _bust_game(phase)
    _render(scene, game, gfx, f"bust/{phase.name}")


def test_bust_layout_mascot_alert_banner(gfx: SpriteFactory) -> None:
    scene = BustingScene()
    game = _bust_game(BustPhase.ACTIVE)
    game.mascot.state = MascotState.ALERT
    game.mascot.alert_remaining = MASCOT_ALERT_WINDOW
    _render(scene, game, gfx, "bust/mascot-alert")


# ---------------------------------------------------------------- FINALE ----


def test_finale_layout_no_sim(gfx: SpriteFactory) -> None:
    scene = FinaleScene()
    game = new_game(1)
    _render(scene, game, gfx, "finale/no-sim")


def test_finale_layout_awaiting_runner(gfx: SpriteFactory) -> None:
    scene = FinaleScene()
    game = new_game(1)
    game.finale = FinaleSim(able_cleaners=2)
    _render(scene, game, gfx, "finale/awaiting-runner")


def test_finale_layout_runner_in_transit(gfx: SpriteFactory) -> None:
    scene = FinaleScene()
    game = new_game(1)
    game.finale = FinaleSim(able_cleaners=2, runner_x=300.0)
    _render(scene, game, gfx, "finale/runner-in-transit")


def test_finale_layout_all_cleaners_inside(gfx: SpriteFactory) -> None:
    scene = FinaleScene()
    game = new_game(1)
    game.finale = FinaleSim(able_cleaners=2, inside=2)
    _render(scene, game, gfx, "finale/all-inside")


# ------------------------------------------------------------- GAME_OVER ----

_LOSE_REASONS = [
    "no snares left — the franchise folds",
    "rent due, can't pay — the franchise folds",
    "the franchise never turned a profit",
    "the Tower claimed the city",
]


@pytest.mark.parametrize("reason", _LOSE_REASONS)
def test_gameover_layout_lost(gfx: SpriteFactory, reason: str) -> None:
    scene = GameOverScene()
    game = new_game(1)
    game.result = "lost"
    game.lose_reason = reason
    _render(scene, game, gfx, f"gameover/lost/{reason}")


def test_gameover_layout_won(gfx: SpriteFactory) -> None:
    scene = GameOverScene()
    game = new_game(1)
    game.result = "won"
    game.last_account_code = encode_account("Pat", 20000)
    _render(scene, game, gfx, "gameover/won")

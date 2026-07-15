"""Input mapping and draw smoke tests for the busting scene."""

import pygame
import pytest

from psychic_cleaners.core.bust import BustPhase, BustSim
from psychic_cleaners.core.constants import CLEANER_SPEED, MASCOT_ALERT_WINDOW
from psychic_cleaners.core.events import (
    LaySnare,
    MoveCleaner,
    PlaceCleaner,
    SceneId,
    SpringSnare,
)
from psychic_cleaners.core.game import Game, new_game
from psychic_cleaners.core.giant import MascotState
from psychic_cleaners.shell.app import SCENES
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.busting import _HINTS, BustingScene
from psychic_cleaners.shell.text import TextRenderer


def _init_video() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))


def test_new_sprites_have_expected_sizes() -> None:
    _init_video()
    gfx = SpriteFactory()
    assert gfx.get("smudge").get_size() == (48, 48)
    assert gfx.get("snare").get_size() == (32, 16)
    assert gfx.get("cleaner.slimed").get_size() == gfx.get("cleaner").get_size()


class _Pressed:
    """Stand-in for pygame.key.get_pressed() supporting index access."""

    def __init__(self, *keys: int) -> None:
        self._down = set(keys)

    def __getitem__(self, key: int) -> bool:
        return key in self._down


def _press(monkeypatch: pytest.MonkeyPatch, *keys: int) -> None:
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Pressed(*keys))


@pytest.fixture
def bust_game() -> Game:
    game = new_game(1)
    game.scene = SceneId.BUST
    game.bust = BustSim()
    return game


def test_held_arrows_move_cursor_in_positioning_phases(
    monkeypatch: pytest.MonkeyPatch, bust_game: Game
) -> None:
    scene = BustingScene()
    step = CLEANER_SPEED * (1 / 60)
    _press(monkeypatch, pygame.K_LEFT)
    assert scene.commands([], bust_game, 1 / 60) == [MoveCleaner(-step)]
    _press(monkeypatch, pygame.K_RIGHT)
    assert scene.commands([], bust_game, 1 / 60) == [MoveCleaner(step)]
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.SNARE
    _press(monkeypatch, pygame.K_LEFT)
    assert scene.commands([], bust_game, 1 / 60) == [MoveCleaner(-step)]


def test_held_arrow_movement_is_time_proportional(
    monkeypatch: pytest.MonkeyPatch, bust_game: Game
) -> None:
    """A long (clamped) frame moves the cursor further: dt=1/30 covers twice dt=1/60."""
    scene = BustingScene()
    _press(monkeypatch, pygame.K_RIGHT)
    (fast,) = scene.commands([], bust_game, 1 / 60)
    (slow,) = scene.commands([], bust_game, 1 / 30)
    assert isinstance(fast, MoveCleaner)
    assert isinstance(slow, MoveCleaner)
    assert fast.dx == pytest.approx(CLEANER_SPEED / 60)
    assert slow.dx == pytest.approx(2 * fast.dx)


def test_arrows_ignored_when_active(monkeypatch: pytest.MonkeyPatch, bust_game: Game) -> None:
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.ACTIVE
    _press(monkeypatch, pygame.K_LEFT, pygame.K_RIGHT)
    assert BustingScene().commands([], bust_game, 1 / 60) == []


def test_enter_places_cleaners_then_lays_snare(
    monkeypatch: pytest.MonkeyPatch, bust_game: Game
) -> None:
    scene = BustingScene()
    _press(monkeypatch)  # nothing held
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert bust_game.bust is not None
    assert scene.commands([enter], bust_game, 1 / 60) == [PlaceCleaner()]
    bust_game.bust.phase = BustPhase.POSITION_RIGHT
    assert scene.commands([enter], bust_game, 1 / 60) == [PlaceCleaner()]
    bust_game.bust.phase = BustPhase.SNARE
    assert scene.commands([enter], bust_game, 1 / 60) == [LaySnare()]
    bust_game.bust.phase = BustPhase.ACTIVE
    assert scene.commands([enter], bust_game, 1 / 60) == []


def test_space_springs_snare(bust_game: Game) -> None:
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.ACTIVE
    space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    assert BustingScene().commands([space], bust_game, 1 / 60) == [SpringSnare()]


def test_space_emits_snare_command_in_non_active_phases(
    monkeypatch: pytest.MonkeyPatch, bust_game: Game
) -> None:
    """Scene emits SpringSnare in non-ACTIVE phases; the core's rejection is
    covered by tests/integration/test_bust_flow.py."""
    assert bust_game.bust is not None
    bust_game.bust.phase = BustPhase.POSITION_LEFT
    space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    _press(monkeypatch)  # initialize pygame key system with empty pressed keys
    assert BustingScene().commands([space], bust_game, 1 / 60) == [SpringSnare()]


def test_bust_scene_registered() -> None:
    assert isinstance(SCENES[SceneId.BUST], BustingScene)


def test_draw_smoke_in_active_phase(bust_game: Game) -> None:
    _init_video()
    bust = bust_game.bust
    assert bust is not None
    bust.left_x = 200.0
    bust.right_x = 440.0
    bust.snare_x = 320.0
    bust.phase = BustPhase.ACTIVE
    surface = pygame.Surface((640, 400))
    BustingScene().draw(surface, bust_game, SpriteFactory(), TextRenderer())
    assert surface.get_at((320, 399)) != pygame.Color(16, 14, 24)  # ground drawn


def test_draw_smoke_in_every_phase(bust_game: Game) -> None:
    _init_video()
    surface = pygame.Surface((640, 400))
    scene = BustingScene()
    bust = bust_game.bust
    assert bust is not None
    for phase in BustPhase:
        bust.phase = phase
        scene.draw(surface, bust_game, SpriteFactory(), TextRenderer())


class _RectText(TextRenderer):
    """TextRenderer that records the pixel rect of every message it draws."""

    def __init__(self) -> None:
        super().__init__()
        self.rects: dict[str, pygame.Rect] = {}

    def draw(
        self,
        surface: pygame.Surface,
        message: str,
        pos: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = (230, 230, 230),
    ) -> None:
        width, height = self._font(size).size(message)
        self.rects[message] = pygame.Rect(pos[0], pos[1], width, height)
        super().draw(surface, message, pos, size, color)


def test_mascot_banner_does_not_overlap_the_bust_hint(bust_game: Game) -> None:
    """An alert mid-bust must not overprint the phase hint into a jumble."""
    _init_video()
    bust_game.bust = BustSim(phase=BustPhase.ACTIVE, left_x=250.0, right_x=390.0, snare_x=320.0)
    bust_game.mascot.state = MascotState.ALERT
    bust_game.mascot.alert_remaining = MASCOT_ALERT_WINDOW  # fresh alert: banner ON
    text = _RectText()
    BustingScene().draw(pygame.Surface((640, 400)), bust_game, SpriteFactory(), text)
    hint = text.rects[_HINTS[BustPhase.ACTIVE]]
    banner = next(rect for msg, rect in text.rects.items() if msg.startswith("MASCOT INBOUND"))
    assert not banner.colliderect(hint), (banner, hint)

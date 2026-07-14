"""ShopScene key mapping and draw smoke test (SDL dummy driver)."""

import pygame

from psychic_cleaners.core.events import (
    BuyItem,
    FinishShopping,
    NewGame,
    SceneId,
    SelectVehicle,
)
from psychic_cleaners.core.game import new_game
from psychic_cleaners.shell.app import SCENES
from psychic_cleaners.shell.gfx import SpriteFactory
from psychic_cleaners.shell.scenes.shop import ShopScene
from psychic_cleaners.shell.text import TextRenderer


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_enter_on_first_row_selects_first_vehicle() -> None:
    scene = ShopScene()
    game = new_game(1)
    assert scene.commands([_key(pygame.K_RETURN)], game) == [SelectVehicle("compact")]


def test_cursor_down_reaches_first_item_row() -> None:
    scene = ShopScene()
    game = new_game(1)
    scene.commands([_key(pygame.K_DOWN)] * 4, game)  # past the 4 vehicles
    assert scene.commands([_key(pygame.K_RETURN)], game) == [BuyItem("detector")]


def test_cursor_up_wraps_to_last_row() -> None:
    scene = ShopScene()
    game = new_game(1)
    scene.commands([_key(pygame.K_UP)], game)
    assert scene.commands([_key(pygame.K_RETURN)], game) == [BuyItem("vacuum")]


def test_f_emits_finish_shopping() -> None:
    scene = ShopScene()
    game = new_game(1)
    assert scene.commands([_key(pygame.K_f)], game) == [FinishShopping()]


def test_other_keys_emit_nothing() -> None:
    scene = ShopScene()
    game = new_game(1)
    assert scene.commands([_key(pygame.K_SPACE)], game) == []


def test_shop_scene_registered_in_app() -> None:
    assert isinstance(SCENES[SceneId.SHOP], ShopScene)


def test_draw_smoke_before_and_after_purchases() -> None:
    pygame.init()
    surface = pygame.Surface((640, 400))
    scene = ShopScene()
    gfx = SpriteFactory()
    text = TextRenderer()
    game = new_game(1)
    game.tick([NewGame("Pat")], 0.0)
    scene.draw(surface, game, gfx, text)  # no vehicle chosen yet
    game.tick([SelectVehicle("hearse"), BuyItem("snare")], 0.0)
    scene.draw(surface, game, gfx, text)  # vehicle chosen, one item owned
    game.tick([SelectVehicle("compact")], 0.0)  # second vehicle -> rejected
    assert game.notice == "vehicle already chosen"
    scene.draw(surface, game, gfx, text)  # notice line rendered when set

"""Existence and caching for the Milestone 5 city sprites."""

import pygame

from psychic_cleaners.shell.gfx import SpriteFactory


def test_city_sprites_exist() -> None:
    pygame.init()
    factory = SpriteFactory()
    for name in ("building", "building.haunted", "tower", "depot", "wisp"):
        sprite = factory.get(name)
        assert sprite.get_width() > 0
        assert sprite.get_height() > 0


def test_city_sprites_are_cached() -> None:
    pygame.init()
    factory = SpriteFactory()
    assert factory.get("building") is factory.get("building")

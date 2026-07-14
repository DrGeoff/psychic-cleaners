"""Every contract sprite exists, has its documented size, and is visually distinct."""

from typing import Final

import pygame
import pytest

from psychic_cleaners.shell.gfx import SpriteFactory

SIZES: Final[dict[str, tuple[int, int]]] = {
    "car.compact": (48, 28),
    "car.hearse": (48, 28),
    "car.wagon": (48, 28),
    "car.performance": (48, 28),
    "wisp": (24, 24),
    "wisp.faint": (24, 24),
    "smudge": (48, 48),
    "cleaner": (24, 40),
    "cleaner.slimed": (24, 40),
    "building": (48, 56),
    "building.haunted": (48, 56),
    "tower": (56, 96),
    "depot": (56, 48),
    "mascot": (72, 96),
    "snare": (32, 16),
    "logo": (320, 96),
}


@pytest.fixture(autouse=True, scope="module")
def _pygame() -> None:
    pygame.init()


def test_all_sixteen_sprites_have_expected_sizes() -> None:
    factory = SpriteFactory()
    assert len(SIZES) == 16
    for name, size in SIZES.items():
        assert factory.get(name).get_size() == size, name


def test_no_two_sprites_are_byte_identical() -> None:
    factory = SpriteFactory()
    encoded = [
        (factory.get(name).get_size(), pygame.image.tobytes(factory.get(name), "RGBA"))
        for name in SIZES
    ]
    assert len(set(encoded)) == len(encoded)


def test_get_is_cached() -> None:
    factory = SpriteFactory()
    assert factory.get("wisp") is factory.get("wisp")

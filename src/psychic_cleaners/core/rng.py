"""Seedable RNG protocol. All core randomness is injected through this."""

import random
from collections.abc import Sequence
from typing import Protocol


class Rng(Protocol):
    """The subset of random.Random the core is allowed to use."""

    def random(self) -> float: ...

    def randint(self, a: int, b: int) -> int: ...

    def uniform(self, a: float, b: float) -> float: ...

    def choice[T](self, seq: Sequence[T]) -> T: ...


def make_rng(seed: int) -> Rng:
    """Return a deterministic Rng seeded with `seed`."""
    return random.Random(seed)

"""The seedable RNG: determinism per seed, divergence across seeds."""

from collections.abc import Sequence

from psychic_cleaners.core.rng import Rng, make_rng


def _sample(rng: Rng, seq: Sequence[str]) -> tuple[float, int, float, str]:
    return (rng.random(), rng.randint(1, 100), rng.uniform(0.0, 10.0), rng.choice(seq))


def test_same_seed_gives_identical_sequence() -> None:
    a = make_rng(42)
    b = make_rng(42)
    items = ["wisp", "smudge", "snare"]
    for _ in range(20):
        assert _sample(a, items) == _sample(b, items)


def test_different_seeds_give_different_sequences() -> None:
    a = make_rng(1)
    b = make_rng(2)
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_usable_through_the_rng_protocol() -> None:
    value = _sample(make_rng(7), ["only"])
    assert 0.0 <= value[0] < 1.0
    assert 1 <= value[1] <= 100
    assert 0.0 <= value[2] <= 10.0
    assert value[3] == "only"

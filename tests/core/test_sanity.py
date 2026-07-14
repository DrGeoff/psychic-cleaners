"""Sanity check: the package imports and declares its version."""

import psychic_cleaners


def test_version() -> None:
    assert psychic_cleaners.__version__ == "0.1.0"

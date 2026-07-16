"""Title scene: karaoke-ball word-boundary sync."""

from psychic_cleaners.shell.audio import THEME
from psychic_cleaners.shell.scenes.title import (
    KARAOKE_WORDS,
    THEME_TOTAL_MS,
    WORD_BOUNDARIES_MS,
    _ball_index,
)


def test_word_boundaries_count_matches_karaoke_words() -> None:
    assert len(WORD_BOUNDARIES_MS) == len(KARAOKE_WORDS)


def test_word_boundaries_sum_to_theme_total() -> None:
    assert WORD_BOUNDARIES_MS[-1] == sum(ms for _, ms in THEME)
    assert WORD_BOUNDARIES_MS[-1] == THEME_TOTAL_MS


def test_word_boundaries_are_strictly_increasing() -> None:
    assert list(WORD_BOUNDARIES_MS) == sorted(set(WORD_BOUNDARIES_MS))


def test_ball_index_tracks_known_elapsed_values() -> None:
    # THEME's 16 notes, paired 2-per-word, give boundaries at
    # 300, 600, 1050, 1500, 1800, 2100, 2550, 3000 ms.
    assert _ball_index(0.0) == 0
    assert _ball_index(0.29) == 0
    assert _ball_index(0.35) == 1
    assert _ball_index(0.65) == 2
    assert _ball_index(2.99) == 7


def test_ball_index_wraps_at_theme_loop_boundary() -> None:
    # elapsed == exactly one theme loop must wrap back to word 0, not drift.
    assert _ball_index(THEME_TOTAL_MS / 1000) == _ball_index(0.0)

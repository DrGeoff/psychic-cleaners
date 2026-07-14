"""Theme chiptune: note table, hook length, music no-ops when disabled."""

import pytest

from psychic_cleaners.shell.audio import NOTE_HZ, SAMPLE_RATE, THEME, AudioBank, build_theme


def test_a4_is_440_equal_temperament() -> None:
    assert NOTE_HZ["A4"] == pytest.approx(440.0, abs=1e-6)
    assert NOTE_HZ["A5"] == pytest.approx(880.0, abs=1e-6)
    assert NOTE_HZ["C6"] == pytest.approx(2.0 * NOTE_HZ["C5"], abs=1e-6)


def test_theme_is_a_sixteen_note_hook() -> None:
    assert len(THEME) == 16
    assert all(name == "" or name in NOTE_HZ for name, _ in THEME)


def test_build_theme_byte_length() -> None:
    expected = sum(round(ms / 1000 * SAMPLE_RATE) * 2 for _, ms in THEME)
    assert len(build_theme()) == expected


def test_music_calls_are_noops_when_disabled() -> None:
    bank = AudioBank(enabled=False)
    bank.play_music_loop()  # must not raise
    bank.stop_music()  # must not raise


def test_title_karaoke_words_and_draw_smoke() -> None:
    import pygame

    from psychic_cleaners.core.game import SceneId, new_game
    from psychic_cleaners.shell.app import SCENES
    from psychic_cleaners.shell.gfx import SpriteFactory
    from psychic_cleaners.shell.scenes.title import KARAOKE_WORDS
    from psychic_cleaners.shell.text import TextRenderer

    assert KARAOKE_WORDS == ("WHEN", "THE", "STAINS", "COME", "CREEPING", "CALL", "THE", "CLEANERS")
    pygame.init()
    surface = pygame.Surface((640, 400))
    SCENES[SceneId.TITLE].draw(surface, new_game(seed=1), SpriteFactory(), TextRenderer())


def test_app_starts_title_music() -> None:
    from psychic_cleaners.shell.app import App

    app = App(seed=1)
    if not app.audio._enabled:  # mixer genuinely unavailable on this machine
        pytest.skip("mixer unavailable")
    assert app.audio._music is not None  # theme loop started on TITLE
    for _ in range(3):
        app.step(1 / 60)

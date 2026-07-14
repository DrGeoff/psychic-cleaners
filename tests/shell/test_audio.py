"""Synthesized audio: waveform shape, byte lengths, graceful no-ops."""

import pytest

from psychic_cleaners.shell.audio import SAMPLE_RATE, AudioBank, synth_noise, synth_square


def _samples(raw: bytes) -> list[int]:
    return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)]


def test_square_byte_length() -> None:
    assert len(synth_square(440.0, 100)) == round(100 / 1000 * SAMPLE_RATE) * 2


def test_noise_byte_length_and_reproducible() -> None:
    assert len(synth_noise(50)) == round(50 / 1000 * SAMPLE_RATE) * 2
    assert synth_noise(50) == synth_noise(50)


def test_square_alternates_at_expected_period() -> None:
    # 2205 Hz at 22050 Hz sample rate -> half-period of exactly 5 samples.
    samples = _samples(synth_square(2205.0, 10))
    assert all(s > 0 for s in samples[0:5])
    assert all(s < 0 for s in samples[5:10])
    assert all(s > 0 for s in samples[10:15])


def test_play_music_loop_reuses_prebuilt_theme_sound() -> None:
    bank = AudioBank()
    if not bank._enabled:  # mixer genuinely unavailable on this machine
        pytest.skip("mixer unavailable")
    bank.play_music_loop()
    # play_music_loop must reuse the "theme" Sound built once in __init__,
    # not re-synthesize build_theme() a second time.
    assert bank._music is bank._sounds["theme"]


def test_disabled_bank_play_is_noop() -> None:
    bank = AudioBank(enabled=False)
    bank.play("trap")  # must not raise


def test_unknown_name_is_noop() -> None:
    bank = AudioBank(enabled=False)
    bank.play("definitely-not-a-sound")  # must not raise
    enabled_bank = AudioBank()
    enabled_bank.play("definitely-not-a-sound")  # must not raise even when mixer is live


def test_event_sounds_maps_each_core_event_and_every_value_is_a_recipe() -> None:
    from psychic_cleaners.core.events import (
        AccountRejected,
        BaitDeployed,
        BeamsCrossed,
        BuildingStomped,
        BustMissed,
        CleanerSlimed,
        Event,
        GameLost,
        GameWon,
        GhostTrapped,
        ItemBought,
        MascotAlert,
        PurchaseRejected,
        RunnerEntered,
        RunnerSquashed,
        WispCaptured,
    )
    from psychic_cleaners.shell.app import EVENT_SOUNDS
    from psychic_cleaners.shell.audio import _RECIPES

    # Subset assertions by design (per contract): each mapping below must be
    # PRESENT, but future additions to EVENT_SOUNDS must not break this test —
    # never assert exact dict equality here.
    expected: dict[type[Event], str] = {
        GhostTrapped: "trap",
        WispCaptured: "catch",
        BustMissed: "miss",
        BeamsCrossed: "backfire",
        CleanerSlimed: "slime",
        BuildingStomped: "stomp",
        MascotAlert: "alert",
        BaitDeployed: "bait",
        RunnerEntered: "enter",
        RunnerSquashed: "squash",
        GameWon: "win",
        GameLost: "lose",
        ItemBought: "buy",
        PurchaseRejected: "reject",
        AccountRejected: "reject",
    }
    for event_type, sound_name in expected.items():
        assert EVENT_SOUNDS.get(event_type) == sound_name, event_type
    assert set(EVENT_SOUNDS.values()) <= set(_RECIPES)

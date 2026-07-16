"""Synthesized audio: waveform shape, byte lengths, graceful no-ops."""

import pygame
import pytest

from psychic_cleaners.shell.audio import (
    SAMPLE_RATE,
    AudioBank,
    mix,
    synth_noise,
    synth_square,
    synth_voice,
)


def _samples(raw: bytes) -> list[int]:
    return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)]


def test_square_byte_length() -> None:
    assert len(synth_square(440.0, 100)) == round(100 / 1000 * SAMPLE_RATE) * 2


def test_noise_byte_length_and_reproducible() -> None:
    assert len(synth_noise(50)) == round(50 / 1000 * SAMPLE_RATE) * 2
    assert synth_noise(50) == synth_noise(50)


def test_synth_voice_raw_square_alternates_at_expected_period() -> None:
    # 2205 Hz at 22050 Hz sample rate -> half-period of exactly 5 samples.
    # Envelope disabled (attack/decay/release=0, sustain=1.0) to isolate
    # waveform shape from envelope shaping.
    samples = _samples(
        synth_voice("square", 2205.0, 10, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0)
    )
    assert all(s > 0 for s in samples[0:5])
    assert all(s < 0 for s in samples[5:10])
    assert all(s > 0 for s in samples[10:15])


def test_synth_voice_default_envelope_ramps_up_from_zero() -> None:
    samples = _samples(synth_voice("square", 440.0, 100, 0.8, attack_ms=5))
    assert samples[0] == 0
    assert 0 < abs(samples[10]) < round(0.8 * 32767)


def test_synth_voice_triangle_and_sawtooth_produce_distinct_shapes() -> None:
    triangle = _samples(
        synth_voice("triangle", 220.0, 20, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0)
    )
    sawtooth = _samples(
        synth_voice("sawtooth", 220.0, 20, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0)
    )
    assert triangle != sawtooth
    assert max(triangle) > 0 and min(triangle) < 0
    assert max(sawtooth) > 0 and min(sawtooth) < 0


def test_synth_square_and_synth_noise_are_synth_voice_wrappers() -> None:
    assert len(synth_square(440.0, 100)) == round(100 / 1000 * SAMPLE_RATE) * 2
    assert len(synth_noise(50)) == round(50 / 1000 * SAMPLE_RATE) * 2
    assert synth_noise(50) == synth_noise(50)  # still reproducible (seeded)


def test_mix_sums_and_clamps_to_int16_range() -> None:
    a = synth_voice("square", 440.0, 10, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0)
    b = synth_voice("square", 440.0, 10, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0)
    mixed = _samples(mix(a, b))
    # Two identical full-amplitude voices summed must clamp, never wrap around.
    assert all(s in (32767, -32768) for s in mixed)


def test_mix_pads_shorter_voice_with_silence() -> None:
    long_voice = synth_voice(
        "square", 440.0, 20, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
    )
    short_voice = synth_voice(
        "square", 440.0, 10, 1.0, attack_ms=0, decay_ms=0, release_ms=0, sustain=1.0
    )
    mixed = mix(long_voice, short_voice)
    assert len(mixed) == len(long_voice)


def test_play_music_loop_reuses_prebuilt_theme_sound() -> None:
    bank = AudioBank()
    if not bank._enabled:  # mixer genuinely unavailable on this machine
        pytest.skip("mixer unavailable")
    bank.play_music_loop()
    # play_music_loop must reuse the "theme" Sound built once in __init__,
    # not re-synthesize build_theme() a second time.
    assert bank._music is bank._sounds["theme"]


def test_mixer_init_failure_degrades_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    # Distinct from "real audio playback is untestable": the degradation
    # logic in AudioBank.__init__ (the bare `except pygame.error: return`)
    # is itself fully testable by forcing pygame.mixer.init to raise, without
    # depending on whether this machine actually has a mixer.
    def _raise(*args: object, **kwargs: object) -> None:
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "init", _raise)
    bank = AudioBank()  # must not raise despite mixer.init failing
    assert bank._enabled is False
    bank.play("trap")  # no-op, no exception


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
        CommandRejected,
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
        CommandRejected: "reject",
    }
    for event_type, sound_name in expected.items():
        assert EVENT_SOUNDS.get(event_type) == sound_name, event_type
    assert set(EVENT_SOUNDS.values()) <= set(_RECIPES)

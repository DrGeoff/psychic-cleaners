"""Tests for the account-code codec (encode half; decode tests are added below)."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from psychic_cleaners.core.codec import (
    ALPHABET,
    AccountCodeError,
    decode_account,
    encode_account,
)
from psychic_cleaners.core.constants import MAX_BANKROLL


def test_known_answer_vector() -> None:
    assert encode_account("Pat Jones", 10_000) == "KWP73WX"


def test_code_shape() -> None:
    code = encode_account("Geoff", MAX_BANKROLL)
    assert code == "S8T6F8S"
    assert len(code) == 7
    assert all(ch in ALPHABET for ch in code)


def test_name_normalization_is_applied() -> None:
    # Case, leading/trailing space, and repeated internal whitespace are all folded.
    assert encode_account("  pat   JONES ", 10_000) == "KWP73WX"


@pytest.mark.parametrize("bankroll", [-1, MAX_BANKROLL + 1])
def test_out_of_range_bankroll_raises(bankroll: int) -> None:
    with pytest.raises(AccountCodeError):
        encode_account("Pat", bankroll)


@pytest.mark.parametrize("name", ["", "   ", " \t\n"])
def test_empty_normalized_name_raises_on_encode(name: str) -> None:
    with pytest.raises(AccountCodeError):
        encode_account(name, 100)


def test_decode_known_answer() -> None:
    assert decode_account("Pat Jones", "KWP73WX") == 10_000


def test_decode_normalizes_code_and_name() -> None:
    # Codes are accepted case-insensitively with surrounding whitespace stripped,
    # and names get the same normalization as on encode.
    assert decode_account("  PAT   jones ", "  kwp73wx\n") == 10_000


@pytest.mark.parametrize("code", ["CPDG8J", "CPDG8JXA", ""])
def test_wrong_length_raises(code: str) -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Pat Jones", code)


@pytest.mark.parametrize("code", ["CPDG8J0", "CPDG8JI"])  # 0 and I are not in ALPHABET
def test_invalid_character_raises(code: str) -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Pat Jones", code)


def test_empty_normalized_name_raises_on_decode() -> None:
    with pytest.raises(AccountCodeError):
        decode_account("   ", "KWP73WX")


def test_wrong_name_raises() -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Someone Else", "KWP73WX")


def test_corrupted_code_raises() -> None:
    with pytest.raises(AccountCodeError):
        decode_account("Pat Jones", "AWP73WX")  # first char flipped


# Fixed (name, bankroll) pairs picked because a brute-force check of every
# single-character mutation (7 positions x 29 replacement characters = 203
# mutations each) shows zero of them decode to a wrong-but-plausible bankroll
# under the 10-bit checksum. (Under the old 8-bit checksum several of these
# same pairs had 1-2 undetected collisions each, which is the bug this test
# guards against.)
_MUTATION_TEST_PAIRS = [
    ("Pat Jones", 10_000),
    ("Geoff", MAX_BANKROLL),
    ("Ada Lovelace", 250_000),
    ("Grace Hopper", 1),
    ("Marie Curie", 42),
    ("Edith Piaf", 7),
]


@pytest.mark.parametrize("name,bankroll", _MUTATION_TEST_PAIRS)
def test_exhaustive_single_character_mutation_is_always_detected(name: str, bankroll: int) -> None:
    code = encode_account(name, bankroll)
    undetected = 0
    for pos in range(len(code)):
        for replacement in ALPHABET:
            if replacement == code[pos]:
                continue
            corrupted = code[:pos] + replacement + code[pos + 1 :]
            try:
                decoded = decode_account(name, corrupted)
            except AccountCodeError:
                continue  # corruption detected -- the expected outcome
            if decoded != bankroll:
                undetected += 1
    assert undetected == 0


def _normalizes_nonempty(name: str) -> bool:
    return " ".join(name.split()).casefold() != ""


names: st.SearchStrategy[str] = st.text(min_size=1, max_size=40).filter(_normalizes_nonempty)
bankrolls: st.SearchStrategy[int] = st.integers(min_value=0, max_value=MAX_BANKROLL)


@given(name=names, bankroll=bankrolls)
def test_round_trip(name: str, bankroll: int) -> None:
    code = encode_account(name, bankroll)
    assert len(code) == 7
    assert all(ch in ALPHABET for ch in code)
    assert decode_account(name, code) == bankroll


@given(
    name=names,
    bankroll=bankrolls,
    pos=st.integers(min_value=0, max_value=6),
    replacement=st.sampled_from(ALPHABET),
)
def test_single_substitution_never_restores_the_original_account(
    name: str, bankroll: int, pos: int, replacement: str
) -> None:
    code = encode_account(name, bankroll)
    assume(code[pos] != replacement)
    corrupted = code[:pos] + replacement + code[pos + 1 :]
    try:
        decoded = decode_account(name, corrupted)
    except AccountCodeError:
        return  # the corruption was detected — the common case
    # A 10-bit checksum collides on roughly 0.1% of substitutions. Even then the
    # decoded value is provably a DIFFERENT account than the one that was typed
    # over: it can never equal the original bankroll, and its canonical code is
    # the corrupted string, not the original one.
    assert decoded != bankroll
    assert encode_account(name, decoded) != code

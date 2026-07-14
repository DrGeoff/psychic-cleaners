"""Account-code codec.

Encodes (player name, bankroll) into a 7-character code over a 30-letter
alphabet with no easily-confused glyphs. The bankroll is xor-mixed with a
CRC-derived key of the normalized name, and an 8-bit CRC checksum of
"name:bankroll" is appended, so a code only decodes for the name it was
issued to and single-character typos are (almost always) rejected.
"""

import zlib
from typing import Final

from psychic_cleaners.core.constants import MAX_BANKROLL


class AccountCodeError(ValueError):
    """Raised for an invalid name, bankroll, or account code."""


ALPHABET: Final[str] = "ABCDEFGHJKMNPQRSTVWXYZ23456789"

_CODE_LENGTH: Final[int] = 7
_BASE: Final[int] = len(ALPHABET)  # 30; 30**7 > 2**32, so 7 digits hold any raw value
_CHAR_VALUES: Final[dict[str, int]] = {ch: i for i, ch in enumerate(ALPHABET)}


def _norm(name: str) -> str:
    normalized = " ".join(name.split()).casefold()
    if not normalized:
        raise AccountCodeError("name must not be empty")
    return normalized


def _key(norm_name: str) -> int:
    return zlib.crc32(norm_name.encode()) & 0xFFFFFF


def _checksum(norm_name: str, bankroll: int) -> int:
    return zlib.crc32(f"{norm_name}:{bankroll}".encode()) & 0xFF


def encode_account(name: str, bankroll: int) -> str:
    """Return the 7-character account code for (name, bankroll)."""
    norm_name = _norm(name)
    if not 0 <= bankroll <= MAX_BANKROLL:
        raise AccountCodeError(f"bankroll out of range: {bankroll}")
    mixed = bankroll ^ _key(norm_name)
    raw = (mixed << 8) | _checksum(norm_name, bankroll)
    digits: list[str] = []
    for _ in range(_CODE_LENGTH):
        digits.append(ALPHABET[raw % _BASE])
        raw //= _BASE
    return "".join(reversed(digits))


def decode_account(name: str, code: str) -> int:
    """Return the bankroll stored in ``code`` for ``name``.

    The code is normalized with .strip().upper() first, so pasted codes with
    stray whitespace or in lowercase are accepted. Raises AccountCodeError on
    any mismatch: wrong length, characters outside ALPHABET, a bankroll out of
    range for this name's key, or a checksum failure.
    """
    norm_name = _norm(name)
    normalized_code = code.strip().upper()
    if len(normalized_code) != _CODE_LENGTH:
        raise AccountCodeError("account code must be exactly 7 characters")
    raw = 0
    for ch in normalized_code:
        value = _CHAR_VALUES.get(ch)
        if value is None:
            raise AccountCodeError(f"invalid character in account code: {ch!r}")
        raw = raw * _BASE + value
    mixed = raw >> 8
    check = raw & 0xFF
    bankroll = mixed ^ _key(norm_name)
    if not 0 <= bankroll <= MAX_BANKROLL:
        raise AccountCodeError("account code does not match this name")
    if check != _checksum(norm_name, bankroll):
        raise AccountCodeError("account code failed its checksum")
    return bankroll

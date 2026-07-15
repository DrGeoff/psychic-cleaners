"""TITLE-scene account handling in Game.tick."""

from psychic_cleaners.core.codec import encode_account
from psychic_cleaners.core.constants import STARTING_BANKROLL
from psychic_cleaners.core.events import (
    AccountAccepted,
    AccountRejected,
    EnterAccount,
    NewGame,
    SceneChanged,
    SceneId,
)
from psychic_cleaners.core.game import new_game


def test_valid_account_restores_exact_bankroll() -> None:
    game = new_game(1234)
    code = encode_account("Pat", 123_456)
    assert code == "F6AYADD"  # pinned so a codec regression is loud here too
    events = game.tick([EnterAccount("Pat", code)], 0.0)
    assert AccountAccepted("Pat", 123_456) in events
    assert SceneChanged(SceneId.SHOP) in events
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Pat"
    assert game.wallet.balance == 123_456
    assert game.starting_bankroll == 123_456


def test_invalid_code_rejected_and_stays_on_title() -> None:
    game = new_game(1234)
    # "AAAAAAA" decodes to raw 0 and fails the checksum for the name "Pat".
    events = game.tick([EnterAccount("Pat", "AAAAAAA")], 0.0)
    assert AccountRejected("invalid account code") in events
    assert game.scene is SceneId.TITLE
    assert game.player_name == ""
    assert game.wallet.balance == STARTING_BANKROLL
    assert game.starting_bankroll == STARTING_BANKROLL


def test_notice_set_on_rejection_and_cleared_on_success() -> None:
    game = new_game(1234)
    game.tick([EnterAccount("Pat", "AAAAAAA")], 0.0)
    assert game.notice == "invalid account code"  # TitleScene draws this verbatim
    events = game.tick([EnterAccount("Pat", encode_account("Pat", 123_456))], 0.0)
    assert AccountAccepted("Pat", 123_456) in events
    assert game.notice is None


def test_forged_low_bankroll_code_rejected_as_too_depleted() -> None:
    # A legitimate win code is always > $10,000; a code decoding under the
    # cheapest vehicle price ($2,000) can only be forged, and would otherwise
    # strand the player in SHOP unable to afford any vehicle.
    game = new_game(1234)
    code = encode_account("Pat", 1_500)
    events = game.tick([EnterAccount("Pat", code)], 0.0)
    assert AccountRejected("account too depleted") in events
    assert game.scene is SceneId.TITLE
    assert game.notice == "account too depleted"
    assert game.player_name == ""
    assert game.wallet.balance == STARTING_BANKROLL
    assert game.starting_bankroll == STARTING_BANKROLL


def test_new_game_resets_starting_bankroll() -> None:
    game = new_game(1234)
    game.starting_bankroll = 42  # simulate leftover state from a previous restore
    game.notice = "stale notice"
    events = game.tick([NewGame("Pat")], 0.0)
    assert SceneChanged(SceneId.SHOP) in events
    assert game.scene is SceneId.SHOP
    assert game.player_name == "Pat"
    assert game.wallet.balance == STARTING_BANKROLL
    assert game.starting_bankroll == STARTING_BANKROLL
    assert game.notice is None  # _reset() reinitializes every field

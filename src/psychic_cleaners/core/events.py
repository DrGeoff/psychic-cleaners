"""Typed vocabulary crossing the core boundary.

Commands flow shell -> core (player intent); Events flow core -> shell
(things that happened). Both are immutable value objects. SceneId lives
here (not in game.py) to avoid import cycles.
"""

from dataclasses import dataclass
from enum import Enum, auto

type GridPos = tuple[int, int]


class SceneId(Enum):
    TITLE = auto()
    SHOP = auto()
    MAP = auto()
    DRIVE = auto()
    BUST = auto()
    FINALE = auto()
    GAME_OVER = auto()


@dataclass(frozen=True)
class Command:
    """Base for all player-intent messages (shell -> core)."""


@dataclass(frozen=True)
class Event:
    """Base for all things-that-happened messages (core -> shell)."""


# --- commands ---------------------------------------------------------------


@dataclass(frozen=True)
class NewGame(Command):
    name: str


@dataclass(frozen=True)
class EnterAccount(Command):
    name: str
    code: str


@dataclass(frozen=True)
class SelectVehicle(Command):
    vehicle_id: str


@dataclass(frozen=True)
class BuyItem(Command):
    item_id: str


@dataclass(frozen=True)
class FinishShopping(Command):
    pass


@dataclass(frozen=True)
class SetDestination(Command):
    pos: GridPos


@dataclass(frozen=True)
class TakeLoan(Command):
    pass


@dataclass(frozen=True)
class RepayLoan(Command):
    pass


@dataclass(frozen=True)
class Steer(Command):
    delta: int  # -1 = lane up, +1 = lane down


@dataclass(frozen=True)
class MoveCleaner(Command):
    dx: float  # signed px this frame


@dataclass(frozen=True)
class PlaceCleaner(Command):
    pass


@dataclass(frozen=True)
class LaySnare(Command):
    pass


@dataclass(frozen=True)
class SpringSnare(Command):
    pass


@dataclass(frozen=True)
class DeployBait(Command):
    pass


@dataclass(frozen=True)
class StartRun(Command):
    pass


@dataclass(frozen=True)
class Continue(Command):
    """Advance past overlays / gameover -> title."""


# --- events -----------------------------------------------------------------


@dataclass(frozen=True)
class SceneChanged(Event):
    scene: SceneId


@dataclass(frozen=True)
class AccountAccepted(Event):
    name: str
    bankroll: int


@dataclass(frozen=True)
class AccountRejected(Event):
    reason: str


@dataclass(frozen=True)
class VehicleSelected(Event):
    vehicle_id: str


@dataclass(frozen=True)
class ItemBought(Event):
    item_id: str


@dataclass(frozen=True)
class PurchaseRejected(Event):
    reason: str


@dataclass(frozen=True)
class CommandRejected(Event):
    reason: str  # invalid non-purchase command, e.g. "no snare laid"


@dataclass(frozen=True)
class TravelStarted(Event):
    dest: GridPos
    distance: float


@dataclass(frozen=True)
class RentCharged(Event):
    amount: int
    day: int


@dataclass(frozen=True)
class LoanTaken(Event):
    amount: int


@dataclass(frozen=True)
class LoanRepaid(Event):
    amount: int


@dataclass(frozen=True)
class Arrived(Event):
    pos: GridPos


@dataclass(frozen=True)
class WispCaptured(Event):
    bounty: int


@dataclass(frozen=True)
class HauntStarted(Event):
    pos: GridPos


@dataclass(frozen=True)
class HauntCleared(Event):
    pos: GridPos


@dataclass(frozen=True)
class WispReachedTower(Event):
    pass


@dataclass(frozen=True)
class GhostTrapped(Event):
    fee: int


@dataclass(frozen=True)
class BustMissed(Event):
    pass


@dataclass(frozen=True)
class BeamsCrossed(Event):
    pass


@dataclass(frozen=True)
class CleanerSlimed(Event):
    cleaner: int  # 0..2 game-level index


@dataclass(frozen=True)
class SnaresEmptied(Event):
    pass


@dataclass(frozen=True)
class CleanersRestored(Event):
    pass


@dataclass(frozen=True)
class MascotAlert(Event):
    window_seconds: float


@dataclass(frozen=True)
class BaitDeployed(Event):
    pass


@dataclass(frozen=True)
class StompTriggered(Event):
    """Internal: emitted by MascotModel; Game turns it into BuildingStomped."""


@dataclass(frozen=True)
class BuildingStomped(Event):
    pos: GridPos
    fine: int


@dataclass(frozen=True)
class ConvergenceStarted(Event):
    """The Warden and the Locksmith have appeared and walk toward the Tower."""


@dataclass(frozen=True)
class FinaleUnlocked(Event):
    pass


@dataclass(frozen=True)
class RunnerEntered(Event):
    total_inside: int


@dataclass(frozen=True)
class RunnerSquashed(Event):
    pass


@dataclass(frozen=True)
class GameWon(Event):
    account_code: str


@dataclass(frozen=True)
class GameLost(Event):
    reason: str

# Day Cycle, Rent, and Bank Loan — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add back the original Ghostbusters' economic risk/reward loop — a day cycle with recurring rent and an optional bank loan — while keeping a competent playthrough able to win.

**Architecture:** A day counter derived from the existing `GameClock.minutes` (no new clock), rent charged and loan interest compounded on each day-boundary crossing inside `Game._world_tick`, missed rent resolved as a new bankruptcy path alongside the existing snare-fold check, and the finale win check switched from a raw balance comparison to a balance-minus-debt net worth comparison. Borrow/repay are two new Depot-only commands, mirroring the existing `BuyItem`/Depot-restock pattern.

**Tech Stack:** Python, dataclasses, pytest, hypothesis (existing project conventions — no new dependencies).

## Global Constraints

- `Wallet.balance` never goes negative (existing invariant in `core/economy.py` — must not be broken; rent bankruptcy is a scene transition, not a negative balance).
- Every field added to `Game` must be reinitialized in `Game._reset()` in the same change (existing documented convention at `core/game.py:588-591`).
- No free-text numeric entry anywhere in the shell — borrow/repay use fixed increments, matching the existing fixed-price command pattern.
- Rent is never auto-borrowed against the loan — missing it is a hard loss.
- Full existing test suite (445+ tests) must stay green; `ruff`/`mypy` clean after every task.
- Spec: `docs/superpowers/specs/2026-07-16-day-rent-loan-design.md` — consult it for the "why" behind any decision below.

---

### Task 1: Tuning constants

**Files:**
- Modify: `src/psychic_cleaners/core/constants.py`
- Test: `tests/core/test_constants.py`

**Interfaces:**
- Produces: `DAY_LENGTH_GAME_MINUTES: float`, `RENT_PER_DAY: int`, `LOAN_MAX: int`, `LOAN_BORROW_INCREMENT: int`, `LOAN_INTEREST_RATE_PER_DAY: float` — consumed by Tasks 2, 3, 4.

- [ ] **Step 1: Add the new constants**

In `src/psychic_cleaners/core/constants.py`, in the `# economy` section (after `MAX_BANKROLL`), add:

```python
RENT_PER_DAY: Final[int] = 250
LOAN_MAX: Final[int] = 5_000
LOAN_BORROW_INCREMENT: Final[int] = 1_000
LOAN_INTEREST_RATE_PER_DAY: Final[float] = 0.05
```

In the `# time` section (after `GAME_MINUTES_PER_REAL_SECOND`), add:

```python
DAY_LENGTH_GAME_MINUTES: Final[float] = 90.0
```

- [ ] **Step 2: Pin the new values in the constants regression test**

In `tests/core/test_constants.py`, extend `test_documented_values`:

```python
def test_documented_values() -> None:
    assert constants.STARTING_BANKROLL == 10_000
    assert constants.PSI_MAX == 9_999
    assert constants.STOMP_FINE == 4_000
    assert constants.RENT_PER_DAY == 250
    assert constants.LOAN_MAX == 5_000
    assert constants.LOAN_BORROW_INCREMENT == 1_000
    assert constants.LOAN_INTEREST_RATE_PER_DAY == 0.05
    assert constants.DAY_LENGTH_GAME_MINUTES == 90.0
```

- [ ] **Step 3: Run the test**

Run: `uv run pytest tests/core/test_constants.py -v`
Expected: PASS (2 tests, or however many exist plus this one).

- [ ] **Step 4: Commit**

```bash
git add src/psychic_cleaners/core/constants.py tests/core/test_constants.py
git commit -m "feat: add day/rent/loan tuning constants"
```

---

### Task 2: Economy — net-worth win check

**Files:**
- Modify: `src/psychic_cleaners/core/economy.py`
- Test: `tests/core/test_economy.py`

**Interfaces:**
- Consumes: `MAX_BANKROLL` (from `core/constants.py`, already imported in `economy.py`).
- Produces: `net_worth_profited_over(balance: int, debt: int, starting_balance: int) -> bool` — consumed by Task 4 (`Game._tick_finale`).
- Removes: `Wallet.profited_over` (its only caller is replaced in Task 4; no other production or test code references it — confirmed via repo-wide grep).

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/test_economy.py`:

```python
from psychic_cleaners.core.economy import Wallet, bust_fee, net_worth_profited_over


def test_net_worth_profited_over_no_debt_matches_plain_profit() -> None:
    assert net_worth_profited_over(balance=10_001, debt=0, starting_balance=10_000) is True
    assert net_worth_profited_over(balance=10_000, debt=0, starting_balance=10_000) is False


def test_net_worth_profited_over_subtracts_debt() -> None:
    # 12,000 balance with 3,000 debt nets to 9,000: not ahead of a 10,000 start.
    assert net_worth_profited_over(balance=12_000, debt=3_000, starting_balance=10_000) is False
    # 12,000 balance with 1,000 debt nets to 11,000: ahead.
    assert net_worth_profited_over(balance=12_000, debt=1_000, starting_balance=10_000) is True


def test_net_worth_profited_over_at_bankroll_cap_counts_as_profit() -> None:
    # Mirrors Wallet.profited_over's documented cap edge case: a wallet
    # pinned at MAX_BANKROLL counts as profitable even with debt outstanding,
    # since balance itself can never be pushed higher to satisfy a strict ">".
    assert (
        net_worth_profited_over(balance=MAX_BANKROLL, debt=5_000, starting_balance=MAX_BANKROLL)
        is True
    )
```

Remove the old `test_default_balance_is_starting_bankroll`'s neighbor concerns are unaffected — no existing test in this file references `profited_over`, so no test deletion is needed there (confirmed via grep in design work).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_economy.py -v`
Expected: FAIL with `ImportError: cannot import name 'net_worth_profited_over'`.

- [ ] **Step 3: Implement `net_worth_profited_over`, remove `Wallet.profited_over`**

In `src/psychic_cleaners/core/economy.py`, delete the `profited_over` method from `Wallet` (lines 37-44) and add a free function after the class:

```python
def net_worth_profited_over(balance: int, debt: int, starting_balance: int) -> bool:
    """True if balance-minus-debt strictly exceeds starting_balance, or the
    balance itself is pinned at MAX_BANKROLL.

    A wallet clamped at MAX_BANKROLL can never satisfy a strict ">" against a
    starting balance that was itself at the cap, so sitting at the cap counts
    as profitable regardless of debt (mirrors the pre-existing
    Wallet.profited_over cap edge case).
    """
    return balance - debt > starting_balance or balance >= MAX_BANKROLL
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_economy.py -v`
Expected: PASS (all tests, including the 3 new ones).

- [ ] **Step 5: Commit**

```bash
git add src/psychic_cleaners/core/economy.py tests/core/test_economy.py
git commit -m "feat: add net-worth-based profit check to economy"
```

---

### Task 3: Events — loan commands and day/rent/loan events

**Files:**
- Modify: `src/psychic_cleaners/core/events.py`
- Test: none directly (dataclasses are exercised by Task 4/5's tests; this task is a pure vocabulary addition, consistent with how existing event/command additions in this file have no dedicated test file).

**Interfaces:**
- Produces: `TakeLoan` (Command), `RepayLoan` (Command), `RentCharged(amount: int, day: int)` (Event), `LoanTaken(amount: int)` (Event), `LoanRepaid(amount: int)` (Event) — consumed by Task 4 (`Game`) and Task 5 (shell).

- [ ] **Step 1: Add the two new commands**

In `src/psychic_cleaners/core/events.py`, after the `SetDestination` command:

```python
@dataclass(frozen=True)
class TakeLoan(Command):
    pass


@dataclass(frozen=True)
class RepayLoan(Command):
    pass
```

- [ ] **Step 2: Add the three new events**

After the `TravelStarted` event:

```python
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
```

- [ ] **Step 3: Run the full suite to confirm nothing broke**

Run: `uv run pytest -q`
Expected: PASS, same count as before this task (pure additions, nothing wired up yet).

- [ ] **Step 4: Commit**

```bash
git add src/psychic_cleaners/core/events.py
git commit -m "feat: add loan commands and day/rent/loan events"
```

---

### Task 4: Game — day rollover, rent bankruptcy, loan dispatch, net-worth win check

**Files:**
- Modify: `src/psychic_cleaners/core/game.py`
- Test: `tests/integration/test_map_flow.py`, `tests/core/test_game_finale.py`, new `tests/integration/test_loan.py`

**Interfaces:**
- Consumes: `DAY_LENGTH_GAME_MINUTES`, `RENT_PER_DAY`, `LOAN_MAX`, `LOAN_BORROW_INCREMENT`, `LOAN_INTEREST_RATE_PER_DAY` (Task 1); `net_worth_profited_over` (Task 2); `TakeLoan`, `RepayLoan`, `RentCharged`, `LoanTaken`, `LoanRepaid` (Task 3).
- Produces: `Game.day: int`, `Game.debt: int` — consumed by Task 5 (HUD).

- [ ] **Step 1: Add the new imports**

In `src/psychic_cleaners/core/game.py`, extend the `from psychic_cleaners.core.constants import (...)` block with:

```python
    DAY_LENGTH_GAME_MINUTES,
    LOAN_BORROW_INCREMENT,
    LOAN_INTEREST_RATE_PER_DAY,
    LOAN_MAX,
    RENT_PER_DAY,
```

(keep the existing block alphabetized as it already is). Extend the `from psychic_cleaners.core.economy import Wallet, bust_fee` line to:

```python
from psychic_cleaners.core.economy import Wallet, bust_fee, net_worth_profited_over
```

Extend the `from psychic_cleaners.core.events import (...)` block with:

```python
    LoanRepaid,
    LoanTaken,
    RentCharged,
    RepayLoan,
    TakeLoan,
```

(alphabetized into the existing block).

- [ ] **Step 2: Write the failing tests for day rollover and rent bankruptcy**

Create `tests/integration/test_loan.py`:

```python
"""Integration tests for the day cycle, rent, and bank loan mechanics."""

from psychic_cleaners.core.catalog import VEHICLES
from psychic_cleaners.core.constants import (
    DAY_LENGTH_GAME_MINUTES,
    LOAN_BORROW_INCREMENT,
    LOAN_INTEREST_RATE_PER_DAY,
    LOAN_MAX,
    RENT_PER_DAY,
)
from psychic_cleaners.core.events import (
    CommandRejected,
    GameLost,
    LoanRepaid,
    LoanTaken,
    RentCharged,
    RepayLoan,
    SceneId,
    TakeLoan,
)
from psychic_cleaners.core.game import new_game
from psychic_cleaners.core.loadout import Loadout


def _map_game(seed: int):
    game = new_game(seed)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.loadout.add("snare")  # keeps the snare-fold rule out of play
    game.scene = SceneId.MAP
    return game


def test_day_advances_and_charges_rent_on_boundary() -> None:
    game = _map_game(1)
    balance_before = game.wallet.balance
    assert game.day == 1
    events = game.tick([], DAY_LENGTH_GAME_MINUTES)  # one game-minute-per-real-second clock
    assert game.day == 2
    assert game.wallet.balance == balance_before - RENT_PER_DAY
    assert RentCharged(RENT_PER_DAY, 1) in events


def test_no_rent_charged_before_day_boundary() -> None:
    game = _map_game(2)
    balance_before = game.wallet.balance
    game.tick([], DAY_LENGTH_GAME_MINUTES - 1.0)
    assert game.day == 1
    assert game.wallet.balance == balance_before


def test_multiple_day_boundaries_in_one_tick_charge_rent_once_per_day() -> None:
    game = _map_game(3)
    balance_before = game.wallet.balance
    game.tick([], DAY_LENGTH_GAME_MINUTES * 3)
    assert game.day == 4
    assert game.wallet.balance == balance_before - RENT_PER_DAY * 3


def test_unpayable_rent_folds_the_franchise() -> None:
    game = _map_game(4)
    game.wallet.balance = RENT_PER_DAY - 1  # one dollar short
    events = game.tick([], DAY_LENGTH_GAME_MINUTES)
    assert GameLost("rent due, can't pay — the franchise folds") in events
    assert game.scene is SceneId.GAME_OVER
    assert game.lose_reason == "rent due, can't pay — the franchise folds"


def test_take_loan_at_depot_adds_cash_and_debt() -> None:
    game = _map_game(5)  # starts at the Depot
    balance_before = game.wallet.balance
    events = game.tick([TakeLoan()], 0.0)
    assert game.debt == LOAN_BORROW_INCREMENT
    assert game.wallet.balance == balance_before + LOAN_BORROW_INCREMENT
    assert LoanTaken(LOAN_BORROW_INCREMENT) in events


def test_take_loan_rejected_away_from_depot() -> None:
    game = _map_game(6)
    game.position = (3, 3)
    events = game.tick([TakeLoan()], 0.0)
    assert game.debt == 0
    assert CommandRejected("loans only at the Depot") in events


def test_take_loan_rejected_past_the_cap() -> None:
    game = _map_game(7)
    game.debt = LOAN_MAX
    events = game.tick([TakeLoan()], 0.0)
    assert game.debt == LOAN_MAX
    assert CommandRejected("loan limit reached") in events


def test_repay_loan_reduces_debt_and_spends_cash() -> None:
    game = _map_game(8)
    game.debt = LOAN_BORROW_INCREMENT
    balance_before = game.wallet.balance
    events = game.tick([RepayLoan()], 0.0)
    assert game.debt == 0
    assert game.wallet.balance == balance_before - LOAN_BORROW_INCREMENT
    assert LoanRepaid(LOAN_BORROW_INCREMENT) in events


def test_repay_loan_clamps_to_outstanding_debt() -> None:
    game = _map_game(9)
    game.debt = 400  # less than a full LOAN_BORROW_INCREMENT
    balance_before = game.wallet.balance
    events = game.tick([RepayLoan()], 0.0)
    assert game.debt == 0
    assert game.wallet.balance == balance_before - 400
    assert LoanRepaid(400) in events


def test_repay_loan_rejected_with_no_debt() -> None:
    game = _map_game(10)
    events = game.tick([RepayLoan()], 0.0)
    assert CommandRejected("no debt to repay") in events


def test_debt_accrues_interest_on_day_rollover() -> None:
    game = _map_game(11)
    game.debt = 1_000
    game.tick([], DAY_LENGTH_GAME_MINUTES)
    assert game.debt == round(1_000 * (1 + LOAN_INTEREST_RATE_PER_DAY)) - 0  # rent doesn't touch debt


def test_reset_clears_day_and_debt() -> None:
    from psychic_cleaners.core.events import NewGame

    game = _map_game(12)
    game.day = 5
    game.debt = 2_000
    game.tick([NewGame("Alex")], 0.0)
    assert game.day == 1
    assert game.debt == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_loan.py -v`
Expected: FAIL — `Game` has no `day`/`debt` attributes yet, `TakeLoan`/`RepayLoan` are unhandled.

- [ ] **Step 4: Add `day` and `debt` fields, reset them**

In the `Game` dataclass field list (`core/game.py`, after `shop_fold_warned: bool = False`), add:

```python
    day: int = 1
    debt: int = 0
    rent_bankrupt: bool = False  # set by _tick_day_rollover, consumed and cleared in tick()
```

In `Game._reset` (after `self.shop_fold_warned = False`), add:

```python
        self.day = 1
        self.debt = 0
        self.rent_bankrupt = False
```

- [ ] **Step 5: Implement day rollover in `_world_tick`**

Replace `_world_tick` in `core/game.py`:

```python
    def _world_tick(self, dt_seconds: float) -> list[Event]:
        self.clock.advance(dt_seconds)
        if self.notice is not None:
            # Notices set on TITLE/SHOP don't reach here (those scenes don't
            # world-tick); only MAP/DRIVE/BUST notices decay and expire.
            # Accepted quirk: a notice armed mid-tick is also decremented by
            # that same tick's dt (~16ms of a 6s lifetime) — intentional,
            # not worth tracking the arming tick separately.
            self.notice_remaining -= dt_seconds
            if self.notice_remaining <= 0:
                self._clear_notice()
        events: list[Event] = []
        self._tick_day_rollover(events)
        self.psi.advance(dt_seconds, self.city.active_haunts())
        events.extend(self.city.tick(dt_seconds, self.psi.value, self.rng))
        has_sensor = self.loadout.has("sensor") if self.loadout is not None else False
        events.extend(self.mascot.tick(dt_seconds, self.psi.value, has_sensor, self.rng))
        return events

    def _tick_day_rollover(self, events: list[Event]) -> None:
        """Charge rent and compound loan interest on each day-boundary crossing.

        A `while`, not an `if`: a single long dt_seconds (e.g. a big scripted
        skip) can cross more than one day boundary, and each one must charge
        its own rent/interest rather than being merged or skipped.
        """
        while self.clock.minutes >= self.day * DAY_LENGTH_GAME_MINUTES:
            if self.debt > 0:
                self.debt = round(self.debt * (1 + LOAN_INTEREST_RATE_PER_DAY))
            if self.wallet.can_afford(RENT_PER_DAY):
                self.wallet.spend(RENT_PER_DAY)
                events.append(RentCharged(RENT_PER_DAY, self.day))
                self._set_notice(f"rent due: -${RENT_PER_DAY}")
                self.day += 1
            else:
                self.rent_bankrupt = True
                self.day += 1
                break
```

- [ ] **Step 6: Resolve rent bankruptcy alongside the existing snare-fold check**

In `Game.tick`, find:

```python
            # Bankruptcy: the franchise folds only when it cannot field a snare
            # by any means (see _cannot_field_snare).
            if (
                self.scene in _WORLD_SCENES
                and self.loadout is not None
                and self._cannot_field_snare()
            ):
                self._lose("no snares left — the franchise folds", events)
                self._change_scene(SceneId.GAME_OVER, events)
```

Replace it with:

```python
            # Bankruptcy: the franchise folds only when it cannot field a snare
            # by any means (see _cannot_field_snare), or when a day's rent
            # could not be paid (see _tick_day_rollover).
            if (
                self.scene in _WORLD_SCENES
                and self.loadout is not None
                and self._cannot_field_snare()
            ):
                self._lose("no snares left — the franchise folds", events)
                self._change_scene(SceneId.GAME_OVER, events)
            elif self.rent_bankrupt:
                self.rent_bankrupt = False
                self._lose("rent due, can't pay — the franchise folds", events)
                self._change_scene(SceneId.GAME_OVER, events)
```

- [ ] **Step 7: Wire `TakeLoan`/`RepayLoan` dispatch**

In `Game._handle_map`, replace:

```python
    def _handle_map(self, command: Command) -> list[Event]:
        if isinstance(command, SetDestination):
            return self._set_destination(command.pos)
        if isinstance(command, BuyItem):
            return self._depot_restock(command.item_id)
        return []
```

with:

```python
    def _handle_map(self, command: Command) -> list[Event]:
        if isinstance(command, SetDestination):
            return self._set_destination(command.pos)
        if isinstance(command, BuyItem):
            return self._depot_restock(command.item_id)
        if isinstance(command, TakeLoan):
            return self._take_loan()
        if isinstance(command, RepayLoan):
            return self._repay_loan()
        return []
```

Add two new methods after `_depot_restock`:

```python
    def _take_loan(self) -> list[Event]:
        if self.position != DEPOT_POS:
            return [self._reject("loans only at the Depot", CommandRejected)]
        if self.debt + LOAN_BORROW_INCREMENT > LOAN_MAX:
            return [self._reject("loan limit reached", CommandRejected)]
        self.wallet.earn(LOAN_BORROW_INCREMENT)
        self.debt += LOAN_BORROW_INCREMENT
        self._clear_notice()
        return [LoanTaken(LOAN_BORROW_INCREMENT)]

    def _repay_loan(self) -> list[Event]:
        if self.position != DEPOT_POS:
            return [self._reject("loans only at the Depot", CommandRejected)]
        if self.debt == 0:
            return [self._reject("no debt to repay", CommandRejected)]
        amount = min(LOAN_BORROW_INCREMENT, self.debt)
        if not self.wallet.spend(amount):
            return [self._reject("cannot afford repayment", CommandRejected)]
        self.debt -= amount
        self._clear_notice()
        return [LoanRepaid(amount)]
```

- [ ] **Step 8: Run the new tests to verify they pass**

Run: `uv run pytest tests/integration/test_loan.py -v`
Expected: PASS (12 tests).

- [ ] **Step 9: Write the failing test for the net-worth win check**

Add to `tests/core/test_game_finale.py`:

```python
def test_finale_win_with_profit_but_debt_that_erases_it_still_loses() -> None:
    game = _game_in_finale()
    game.wallet.earn(5_000)  # balance 12_400 > starting 10_000 on cash alone
    game.debt = 3_000  # but net worth 9_400 <= starting 10_000
    assert game.finale is not None
    game.finale.inside = 1
    game.tick([StartRun()], 0.0)
    events = game.tick([], 3.25)
    assert GameLost("the franchise never turned a profit") in events
    assert game.result == "lost"


def test_finale_win_with_debt_but_enough_net_worth_still_wins() -> None:
    game = _game_in_finale()
    game.wallet.earn(5_000)  # balance 12_400
    game.debt = 1_000  # net worth 11_400 > starting 10_000
    assert game.finale is not None
    game.finale.inside = 1
    game.tick([StartRun()], 0.0)
    events = game.tick([], 3.25)
    won = [e for e in events if isinstance(e, GameWon)]
    assert len(won) == 1
    assert game.result == "won"
```

- [ ] **Step 10: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: FAIL on the 2 new tests (win check still ignores debt).

- [ ] **Step 11: Switch the win check to net worth**

In `Game._tick_finale`, find:

```python
        if outcome is FinaleOutcome.WON:
            if self.wallet.profited_over(self.starting_bankroll):
```

Replace with:

```python
        if outcome is FinaleOutcome.WON:
            if net_worth_profited_over(self.wallet.balance, self.debt, self.starting_bankroll):
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_game_finale.py -v`
Expected: PASS (all tests, including the 2 new ones — the pre-existing finale tests are unaffected since they never set `game.debt`, which defaults to 0).

- [ ] **Step 13: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, no regressions. If any pre-existing test fails because a long-duration `tick()` call now crosses a rent day-boundary and changes an asserted exact wallet balance, fix that test by giving it enough `wallet.earn()` headroom to stay unaffected (do not weaken the rent mechanic to accommodate a test) — check `tests/integration/test_full_game.py` and `tests/integration/test_bust_flow.py` first, since they run the longest simulated durations.

- [ ] **Step 14: Typecheck and lint**

Run: `uv run mypy src/ && uv run ruff check src/ tests/`
Expected: clean.

- [ ] **Step 15: Commit**

```bash
git add src/psychic_cleaners/core/game.py tests/integration/test_loan.py tests/core/test_game_finale.py
git commit -m "feat: wire up day rollover, rent bankruptcy, loans, and net-worth win check"
```

---

### Task 5: Shell — Depot loan keys and HUD debt readout

**Files:**
- Modify: `src/psychic_cleaners/shell/scenes/city_map.py`
- Test: `tests/shell/test_city_map_scene.py`

**Interfaces:**
- Consumes: `game.debt` (Task 4), `TakeLoan`, `RepayLoan` (Task 3), `LOAN_BORROW_INCREMENT`, `LOAN_MAX` (Task 1).

- [ ] **Step 1: Write the failing tests**

Add to `tests/shell/test_city_map_scene.py`:

```python
from psychic_cleaners.core.constants import LOAN_BORROW_INCREMENT
from psychic_cleaners.core.events import RepayLoan, TakeLoan


def test_l_emits_take_loan() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(11)
    commands = scene.commands([_key(pygame.K_l)], game, 1 / 60)
    assert commands == [TakeLoan()]


def test_p_emits_repay_loan() -> None:
    pygame.init()
    scene = CityMapScene()
    game = new_game(12)
    commands = scene.commands([_key(pygame.K_p)], game, 1 / 60)
    assert commands == [RepayLoan()]


def test_hud_shows_debt_when_outstanding() -> None:
    pygame.init()
    pygame.display.set_mode((640, 400))
    scene = CityMapScene()
    game = new_game(13)
    game.loadout = Loadout(vehicle=VEHICLES["hearse"])
    game.scene = SceneId.MAP
    game.debt = LOAN_BORROW_INCREMENT
    surface = pygame.Surface((640, 400))
    scene.draw(surface, game, SpriteFactory(), TextRenderer())  # smoke: must not raise
    row = pygame.Rect(10, _HUD_Y + 4, 220, 14)
    assert _row_has_content(surface, row)  # balance + debt text occupies the row
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/shell/test_city_map_scene.py -v`
Expected: FAIL — `K_l`/`K_p` produce no commands yet; `test_hud_shows_debt_when_outstanding` passes trivially today (balance text alone already fills that row), so this one is a smoke test, not a strict regression guard — note it may pass before the change too; the two key-binding tests are the real failing ones.

- [ ] **Step 3: Add the key bindings**

In `CityMapScene.commands`, in `src/psychic_cleaners/shell/scenes/city_map.py`, extend the `elif` chain (after the `K_s` branch):

```python
            elif event.key == pygame.K_l:
                commands.append(TakeLoan())
            elif event.key == pygame.K_p:
                commands.append(RepayLoan())
```

Add `TakeLoan, RepayLoan` to the existing `from psychic_cleaners.core.events import (...)` import.

- [ ] **Step 4: Add the debt HUD readout and update the depot hint**

In `CityMapScene._draw_hud`, replace:

```python
        text.draw(surface, f"${game.wallet.balance}", (10, _HUD_Y + 4), size=16)
```

with:

```python
        balance_text = f"${game.wallet.balance}"
        if game.debt > 0:
            balance_text += f"  debt ${game.debt}"
        text.draw(surface, balance_text, (10, _HUD_Y + 4), size=16)
```

Replace:

```python
        if game.position == DEPOT_POS:
            hint = f"S: buy snare (${ITEMS['snare'].price})"
            text.draw(surface, hint, (430, _HUD_Y + 18), size=16)
```

with:

```python
        if game.position == DEPOT_POS:
            hint = f"S: snare (${ITEMS['snare'].price}) L: loan P: repay"
            text.draw(surface, hint, (300, _HUD_Y + 18), size=14)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/shell/test_city_map_scene.py -v`
Expected: PASS (all tests, including the 3 new ones).

- [ ] **Step 6: Run the full suite, typecheck, lint**

Run: `uv run pytest -q && uv run mypy src/ && uv run ruff check src/ tests/`
Expected: all clean.

- [ ] **Step 7: Commit**

```bash
git add src/psychic_cleaners/shell/scenes/city_map.py tests/shell/test_city_map_scene.py
git commit -m "feat: add Depot loan keys and HUD debt readout"
```

---

### Task 6: Balance validation via the scripted playtest harness

**Files:**
- None modified unless constants need tuning (in which case: `src/psychic_cleaners/core/constants.py`, `tests/core/test_constants.py`).

**Interfaces:**
- Consumes: everything from Tasks 1-5.

- [ ] **Step 1: Run the checked-in economy-ledger playtest harness**

Run: `uv run python tests/playtests/playtest.py 12345 --inject-profit`
Expected: all PASS/FAIL checks reported PASS, including the ones covering shop, drive, and finale flow. Read the ledger output for the final wallet balance and note whether any rent/loan lines appear (the harness does not know about rent/loan yet — a discrepancy between its ledger and `game.wallet.balance` at day-boundary crossings is expected and fine, since the ledger predates this feature; what matters is that the harness's PASS/FAIL checks — including the win/finale ones — still pass).

- [ ] **Step 2: Run a second, longer seed to sample a slower playthrough**

Run: `uv run python tests/playtests/playtest.py 99 --inject-profit`
Expected: PASS. This exercises a different RNG stream (different bust/travel pacing), giving a second, independent read on whether `RENT_PER_DAY` starves a slower-paced but still-competent playthrough.

- [ ] **Step 3: If either run shows the franchise going bankrupt on rent during otherwise-competent play**

This means `RENT_PER_DAY` (or `LOAN_INTEREST_RATE_PER_DAY`) is tuned too aggressively. Reduce `RENT_PER_DAY` in `src/psychic_cleaners/core/constants.py` in $50 steps (next candidate: `200`, then `150`) and re-run Steps 1-2 until both pass. Update the pinned value in `tests/core/test_constants.py::test_documented_values` to match. Re-run `uv run pytest tests/core/test_constants.py -v` after any change.

- [ ] **Step 4: Record the final tuning decision in the spec**

If `RENT_PER_DAY` (or any other constant) was changed from its Task 1 starting value, add a short note to
`docs/superpowers/specs/2026-07-16-day-rent-loan-design.md` §8 ("Open questions / tuning notes") recording the old value, the new value, and which playtest run motivated the change. If no change was needed, add a one-line note confirming both seeds passed at the original values.

- [ ] **Step 5: Commit**

```bash
git add src/psychic_cleaners/core/constants.py tests/core/test_constants.py docs/superpowers/specs/2026-07-16-day-rent-loan-design.md
git commit -m "test: validate day/rent/loan balance against the scripted playtest harness"
```

(If nothing changed in Steps 3-4 beyond the spec note, `git add` will still pick up the spec file; the commit is still meaningful as a record that validation ran and passed.)

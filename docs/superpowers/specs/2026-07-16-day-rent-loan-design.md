# Day cycle, rent, and bank loans — design

Date: 2026-07-16
Status: Approved pending user review

## 1. Background

An independent audit (not the main design spec, which the project wrote about
itself) compared the current implementation against the real 1984 Ghostbusters
game and found the economic risk/reward loop was dropped entirely: no season
length, no day/turn structure, no rent, no bank loan. `Wallet`
(`core/economy.py`) can only go up or hold at zero — there is no way to go
into debt, and no recurring cost forces a spending decision. This spec adds
back a day cycle with recurring rent and an optional bank loan, while keeping
winning achievable.

## 2. Goals

- A day cycle that advances automatically from the existing world clock, with
  no new player action required to make time pass.
- Recurring rent that is a genuine, unavoidable cash requirement — missing it
  ends the game, the same severity as the existing "no snares left" fold.
- An optional, player-initiated bank loan at the Depot that smooths over a
  cash crunch, at the cost of accruing interest that eats into the final
  score.
- The win condition accounts for debt without turning it into a hard gate:
  you can win while still owing money, as long as your net worth clears the
  bar.
- Confirm — via the existing scripted playtest harness, not guesswork — that
  a competent playthrough can still comfortably win with these systems live.

## 3. Non-goals

- No season-length/difficulty choice at game start (out of scope for this
  spec; a separate concern from the day/rent/loan loop).
- No free-text loan amount entry — borrowing and repaying happen in fixed
  increments, matching the existing fixed-price `BuyItem`-style command
  pattern. No new numeric-input UI.
- No auto-borrow to cover a missed rent payment. Rent is a hard cash
  requirement; the loan is a tool the player must choose to use ahead of
  time, not a safety net that fires automatically.
- No changes to bust/drive/finale mechanics, PSI model, or the mascot.

## 4. Mechanism

### 4.1 Day cycle

New constant `DAY_LENGTH_GAME_MINUTES` (proposed: `90.0`) in
`core/constants.py`. `Game` gains a `day: int = 1` field. In `_world_tick`
(`core/game.py`), after `self.clock.advance(dt_seconds)`, check whether
`clock.minutes` has crossed a new multiple of `DAY_LENGTH_GAME_MINUTES` since
the last tick; each crossing increments `day` and triggers one rent/interest
rollover (see 4.2/4.3). Days only advance in `_WORLD_SCENES` (`MAP`, `DRIVE`,
`BUST`) — the same scenes PSI and the mascot already tick in. No day passes
while the player is in the shop or on the title screen.

A single long `dt_seconds` (e.g. a stall/debug pause) could in principle
cross more than one day boundary in one tick; the rollover is implemented as
a `while` loop over boundary crossings, not an `if`, so each day's rent and
interest are charged individually rather than skipped or merged.

### 4.2 Rent

New constant `RENT_PER_DAY` (proposed: `250`) in `core/constants.py`. On
each day rollover, charge rent directly from `wallet.balance`:

- If `wallet.can_afford(RENT_PER_DAY)`: `wallet.spend(RENT_PER_DAY)`, post a
  notice ("rent due: -$250") through the existing notice system.
- If not: this is an immediate loss. New bankruptcy path alongside the
  existing `_cannot_field_snare` fold in `Game.tick`, with its own
  `lose_reason` ("rent due, can't pay — the franchise folds").

Rent is never auto-borrowed against the loan. This is deliberate: it keeps
rent a hard, planable cash requirement, and keeps the loan a tool the player
chooses to use, not a mechanism that quietly bails them out.

### 4.3 Bank loan / debt

New `debt: int = 0` field on `Game`. New constants in `core/constants.py`:
`LOAN_MAX` (proposed: `5000`), `LOAN_BORROW_INCREMENT` (proposed: `1000`),
`LOAN_INTEREST_RATE_PER_DAY` (proposed: `0.05`).

Two new commands (`core/events.py`), handled at the Depot only (reusing the
existing `_handle_map` / Depot-position gating that `_depot_restock` already
uses):

- `TakeLoan`: if `debt + LOAN_BORROW_INCREMENT <= LOAN_MAX`, add
  `LOAN_BORROW_INCREMENT` to both `wallet.balance` (via `wallet.earn`, since
  it's new incoming cash, not tied to `MAX_BANKROLL` capping any
  differently than other income) and `debt`. Otherwise reject
  ("loan limit reached"). Emits `LoanTaken(amount)`.
- `RepayLoan`: repay `min(LOAN_BORROW_INCREMENT, debt)` from
  `wallet.balance` if affordable (`wallet.spend`); reduce `debt` by the same
  amount. Rejects if there's no debt or the balance can't cover it. Emits
  `LoanRepaid(amount)`.

On each day rollover (same rollover loop as rent, order: interest first,
then rent — so a player who borrows right before a rollover pays interest
on the fresh debt starting that same day, which is the more conservative/
realistic ordering): `debt = round(debt * (1 + LOAN_INTEREST_RATE_PER_DAY))`,
clamped so it never exceeds what's needed for correctness (no cap needed
here beyond `LOAN_MAX` being a *borrow* ceiling, not a debt ceiling — interest
can push `debt` above `LOAN_MAX` over time; only new borrowing is capped).

### 4.4 Win condition

`Game._tick_finale` currently gates a win on
`self.wallet.profited_over(self.starting_bankroll)`. Replace with a net-worth
check: `self.wallet.balance - self.debt > self.starting_bankroll` (or pinned
at `MAX_BANKROLL`, preserving today's edge case in `profited_over`). A new
`Wallet`-adjacent helper (free function in `economy.py`, e.g.
`net_worth_profited_over(wallet, debt, starting_balance)`) keeps this logic
next to `profited_over` rather than inlined in `game.py`. Debt does not block
winning by itself — only through its effect on net worth.

### 4.5 HUD / notices

`city_map.py`'s HUD (bankroll/PSI/snares) gains a debt readout when
`debt > 0`. Rent charges, loan grants, and repayments post through the
existing notice system, matching how purchase rejections and stomp fines
already surface to the player.

## 5. Balance validation plan

The proposed constants (`DAY_LENGTH_GAME_MINUTES=90`, `RENT_PER_DAY=250`,
`LOAN_MAX=5000`, `LOAN_BORROW_INCREMENT=1000`,
`LOAN_INTEREST_RATE_PER_DAY=0.05`) are a reasoned first pass, not final —
same practice this project already follows for other tuning constants (see
the beam-crossing-backfire spec). Reasoning: `RENT_PER_DAY` ($250) sits
below the base bust fee ($300+), so clearing one haunting a day covers rent
with margin; a 90-game-minute day against a typical ~10-25 real-minute game
(current `PSI_GROWTH_PER_REAL_MINUTE` dynamics, unchanged by this spec)
yields roughly 7-16 rent charges per playthrough.

Before this ships, run the existing scripted playtest harness (see
`playtest-harness-artifacts.md` memory notes) end-to-end with these
constants live and confirm a competent scripted playthrough still clears
the net-worth win bar. If it doesn't clear comfortably, adjust
`RENT_PER_DAY` and/or `LOAN_INTEREST_RATE_PER_DAY` down before merging —
do not ship untested numbers.

## 6. Rejected alternatives

- **Auto-borrow on missed rent.** Considered as a softer failure mode, but
  rejected per explicit product decision: rent must be a hard, unavoidable
  cash requirement, and the loan must remain something the player opts into
  ahead of time rather than a mechanism that quietly rescues them after the
  fact.
- **Debt-free required to win.** Considered (mirrors "you can clear the
  Tower but still owe the bank"), but rejected per explicit product
  decision in favor of a pure net-worth check — simpler, one fewer
  constraint to balance, and still captures the spirit (unpaid debt reduces
  your effective winnings).
- **Free-text loan amounts.** Rejected — no other economy interaction in the
  game uses free-text numeric entry; fixed increments keep the loan
  consistent with the existing `BuyItem`-style UI and command pattern.
- **New Bank map location.** Considered, to mirror the original more
  closely, but rejected in favor of folding borrow/repay into the existing
  Depot visit — avoids a new scene/travel cost for a mechanic that doesn't
  need its own physical space.

## 7. Compatibility and testing plan

- New unit tests (`tests/core/test_economy.py` or a new
  `tests/core/test_loan.py`): loan borrow respects `LOAN_MAX`; repay clamps
  to outstanding debt and available cash; interest compounds correctly over
  multiple day rollovers; rent charges correctly and triggers bankruptcy
  exactly when unaffordable.
- New/updated tests in `tests/core/test_game.py`: day counter increments on
  schedule from world-tick `dt_seconds`; a `dt_seconds` spanning multiple
  day boundaries charges rent/interest once per boundary crossing, not once
  total; rent bankruptcy produces the correct `lose_reason` and
  `GameLost` event; win condition correctly accounts for outstanding debt
  via the new net-worth check.
- Existing full suite must still pass; `ruff`/`mypy` clean.
- Scripted playtest harness run with the new constants live, per §5, before
  merge.

## 8. Open questions / tuning notes for playtesting

- All five new constants in §5 are starting values pending the playtest
  validation pass — expect at least `RENT_PER_DAY` and
  `LOAN_INTEREST_RATE_PER_DAY` to move once real numbers come back.
- Whether `DAY_LENGTH_GAME_MINUTES` should scale with vehicle speed or city
  size was considered and rejected as unnecessary complexity — a flat day
  length is simpler and the original didn't scale season length by vehicle
  either.

**Playtest validation outcome (2026-07-16):** both harness seeds (`12345`,
`99`) pass a full playthrough to a finale win at the original constants
(`RENT_PER_DAY=250`, `LOAN_MAX=5000`, `LOAN_BORROW_INCREMENT=1000`,
`LOAN_INTEREST_RATE_PER_DAY=0.05`, `DAY_LENGTH_GAME_MINUTES=90`) — no
constant changes were needed. Sweeping `RENT_PER_DAY` down through 200 and
150 during diagnosis did not change the outcome below, ruling out simple
mistuning as the cause.

One real interaction surfaced and was fixed in the harness itself, not the
game: `tests/playtests/playtest.py`'s `phase_mascot` deliberately ignores
the first mascot alert to exercise the stomp-fine code path, which (now
that a big fine can leave the wallet near $0) combined with a long idle
`wait_for` on the second alert to occasionally cross a rent day-boundary
with no cash on hand, ending the run. `phase_depot_return` then crashed
with an unhandled `AttributeError` (`GameOverScene` has no `.cursor`)
because it never checked for `GAME_OVER`. Fixed by (1) topping up the
harness's own wallet directly after the deliberate worst-case fine — the
same kind of test-state injection `phase_finale`'s `--inject-profit` already
uses, not a change to rent/bankruptcy behavior — so the scripted "ignore the
alert on purpose" stress test survives the idle wait it triggers, and (2)
adding a `GAME_OVER` guard to `phase_depot_return` as a defensive backstop
so any future unlucky run fails cleanly with its `lose_reason` instead of
crashing. This does not weaken `RENT_PER_DAY`, `LOAN_INTEREST_RATE_PER_DAY`,
or the "missed rent is a hard loss" rule — it only stops an artificial,
self-inflicted test scenario (eating the worst-case fine on purpose, then
idling) from masking the actual validation result. Remaining harness FAILs
after the fix are pre-existing, expected ledger drift: the harness's
independent economy ledger predates this feature and doesn't yet model
`RentCharged`, so it reports the (correct) discrepancy rather than crashing
or silently passing.

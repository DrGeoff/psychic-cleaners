# Psychic Cleaners — Design Spec

Date: 2026-07-13
Status: Approved pending user review

## 1. Overview

Psychic Cleaners is a clean-room Python remake of the 1984 Activision C64 classic
*Ghostbusters* (designed by David Crane), built with pygame-ce. The game mechanics,
scene structure, pacing, and economy are cloned as faithfully as the historical
record allows; every protected creative element — names, characters, art, melodies,
lyrics — is replaced with original, legally distinct equivalents.

Presentation is retro-inspired: the scene layouts and feel evoke the original, but
the art is original modern pixel art at a higher resolution, with no C64 palette
constraint.

### Goals

- Full game loop of the original: franchise setup → shop → city map → drive →
  bust → mascot events → finale → win/lose with account carry-over.
- Small, independently testable components. Testing is a first-class requirement.
- Industry-standard tooling: uv, ruff, mypy --strict, pytest, pre-commit, CI.

### Non-goals

- No copied code, art, audio, or text from the original or its documentation.
- No use of protected names, character likenesses, melodies, or lyrics.
- No multiplayer, no online features, no save files beyond the account-code system.
- No joystick support in v1 (keyboard only; the input layer keeps this swappable).

## 2. Clean-room ground rules

- Mechanics, rules, numeric balance, and screen *structure* are recreated from
  observed gameplay behaviour and public descriptions. Game rules are not
  copyrightable.
- All source code is original. No disassembly, no reference to original code.
- All sprites, sounds, and music are original works (code-generated in v1).
- All names come from the Psychic Cleaners universe (mapping below).
- Where the original's exact numbers are documented (prices, starting money,
  fines, PSI cap) we use them; where they are not, we choose sensible defaults
  and keep every gameplay number in one `constants.py` module so later
  calibration against reference footage of the original touches exactly one file.
- This is engineering practice, not legal advice.

## 3. Theme mapping

| Original concept | Psychic Cleaners equivalent |
|---|---|
| Ghostbusters franchise | Psychic Cleaners — paranormal sanitation franchise |
| PK energy (units) | Psychic residue, PSI units |
| Roamers | Wisps |
| Slimer-type building ghost | Smudge — a greasy stain-ghost |
| Stay-Puft Marshmallow Man | Sir Squish — a giant gummy mascot |
| Gatekeeper / Keymaster | The Warden / The Locksmith |
| Temple of Zuul | Threshold Tower |
| GBHQ | The Depot |
| Ecto-1 (1963 hearse) | The Van (a 1960s hearse — generic vehicle type) |
| PK energy detector | Residue detector |
| Image intensifier | Spectral lens |
| Marshmallow sensor | Mascot sensor |
| Ghost bait | Gummy bait |
| Ghost trap | Spirit snare |
| Portable laser confinement system | Portable containment rig |
| Ghost vacuum | Roof vacuum |
| Theme song + bouncing-ball lyrics | Original chiptune, own hook and lyrics |

## 4. Game specification

All numbers below live in `core/constants.py` and are the single tuning point.
Values marked (documented) match the historical record of the original; the rest
are our defaults, subject to calibration.

### 4.1 Title & franchise setup

- Title screen plays the theme chiptune with bouncing-ball karaoke lyrics.
- Prompt: "Do you have an account?" — Yes: enter name + account code; a valid
  code restores that bankroll. No / invalid code: start with $10,000 (documented).
- Account codes encode (name, bankroll) with a checksum, like the original's
  password-save system. Corrupt or mismatched codes are rejected with a visible
  error and fall back to $10,000.

### 4.2 Shop: vehicle and equipment

One vehicle must be bought; equipment is optional but the loadout must fit the
vehicle's capacity. Money never goes negative; unaffordable or oversize
purchases are rejected with a reason.

Vehicles (price documented; speed/capacity our defaults):

| Vehicle | Price | Speed | Capacity (slots) |
|---|---|---|---|
| Compact | $2,000 | slow | 7 |
| Hearse | $4,800 | medium | 9 |
| Wagon | $6,000 | medium | 11 |
| Performance | $15,000 | fast | 14 |

Equipment (prices documented; slot sizes our defaults):

| Item | Price | Slots | Effect |
|---|---|---|---|
| Residue detector | $400 | 1 | Flashes on the map near high-PSI blocks |
| Spectral lens | $800 | 1 | Makes faint wisps visible while driving |
| Mascot sensor | $800 | 1 | Advance warning of a Sir Squish rampage |
| Gummy bait (pack of 5) | $400 | 1 | Diverts Sir Squish when deployed |
| Spirit snare | $600 each | 1 each | Required to trap a Smudge; single-use until emptied |
| Portable containment rig | $8,000 | 3 | Holds 10 caught ghosts; avoids Depot round-trips |
| Roof vacuum | $500 | 1 | Catches wisps during the drive scene |

Without the containment rig, full snares must be emptied at the Depot before
they can be reused; the trip costs game time (and therefore rising PSI).

### 4.3 City map

- Grid of city blocks with streets; the Depot on the edge, Threshold Tower at
  the centre. Buildings flash when haunted.
- The player moves a car cursor along streets to choose a destination; travel
  takes game time proportional to distance and inversely to vehicle speed.
- City PSI rises steadily with game time, spikes when a haunting goes
  un-busted, and jumps by 100 PSI each time a wisp reaches the Tower.
- Wisps spawn at random buildings and drift toward the Tower.
- At 9999 PSI (documented cap), the Warden and the Locksmith converge on the
  Tower and the finale unlocks (section 4.7).
- HUD: bankroll, city PSI meter, snares free/full, ghost count in containment.

### 4.4 Drive scene

- Entered whenever travelling to a destination. Top-down road, three lanes;
  the car moves forward automatically at vehicle speed; the player steers
  between lanes.
- Wisps drift across the road; with the roof vacuum fitted, driving close
  captures them ($100 bounty each, removes them from the city); without it
  they pass through harmlessly. Faint wisps are visible only with the
  spectral lens.
- Scene ends when the travelled distance reaches the destination distance.

### 4.5 Bust scene

- At a haunted building: a Smudge floats in front of the facade.
- The player positions two cleaners one at a time, then lays a spirit snare
  between them (requires ≥1 free snare; with none, the bust cannot start and
  the haunting continues to raise PSI).
- Both cleaners project beams that repel/steer the Smudge. When the Smudge is
  above the snare, the player springs it.
- Success: ghost caught (into snare, or containment rig if fitted), city pays
  a fee: base $300 + $100 per 1000 city PSI at the time of capture.
- Miss: the snare is spent, the Smudge escapes and eventually re-haunts.
- A cleaner touched by the Smudge is slimed: out of action until the next
  visit to the Depot (a slimed cleaner cannot be fielded in busts or the finale).
- Crossing the two beams backfires: both cleaners slimed, snare spent,
  Smudge escapes.

### 4.6 Sir Squish events

- Triggered by PSI spikes at random intervals; frequency rises with city PSI.
- With the mascot sensor: an alert gives the player a short window to deploy
  gummy bait (if carried), which diverts him — no damage.
- Without sensor or bait: Sir Squish stomps a random building; the franchise
  is fined $4,000 (documented).

### 4.7 Finale and game end

- When PSI hits 9999 and the Warden and Locksmith reach the Tower, the player
  must drive there. In front of the Tower door, Sir Squish bounces side to
  side in a readable pattern.
- The player sends cleaners one at a time, timing each run past him. A
  cleaner caught by Sir Squish is squashed out of the attempt. Getting 2 of 3
  able cleaners through the door wins the run; once fewer than 2 able
  cleaners remain outside with fewer than 2 inside, the run is lost. Slimed
  cleaners (section 4.5) cannot take part, so entering the finale with
  fewer than 2 able cleaners loses immediately.
- Win condition (documented): final bankroll strictly greater than starting
  bankroll → franchise approved; a new account code is issued for the next
  game. Otherwise: game over.
- Ordinary game over (bankruptcy: no free snare, no snare capacity to empty,
  and insufficient funds to buy one — the franchise can no longer operate)
  shows the loss screen.

## 5. Architecture

Two layers with a hard boundary:

```
src/psychic_cleaners/
  core/            # PURE Python — zero pygame imports, deterministic
    constants.py   # every gameplay number (single tuning point)
    events.py      # typed Commands (in) and Events (out) — dataclasses
    rng.py         # seedable RNG protocol
    clock.py       # game-time model (ticks → hours; drives PSI growth)
    economy.py     # wallet: purchases, fees, fines; never negative
    codec.py       # account-code encode/decode with checksum
    catalog.py     # vehicle & equipment definitions
    loadout.py     # capacity rules, purchase validation
    pk.py          # city PSI model: growth, spikes, thresholds
    city.py        # map grid, haunt spawner, wisp drift, travel
    drive.py       # lane sim, vacuum catch geometry
    bust.py        # beam geometry, Smudge steering, snare window, backfire
    giant.py       # Sir Squish event model: sensor, bait, stomp
    finale.py      # bounce pattern, run timing, 2-of-3 rule
    game.py        # GameState + top-level scene FSM, win/lose
  shell/           # ALL pygame-ce code lives here
    app.py         # main loop, fixed timestep, logical surface + scaling
    gfx.py         # code-generated sprite factory (asset loader interface)
    audio.py       # synthesized SFX + chiptune sequencer
    text.py        # font/text rendering helpers
    scenes/        # one thin module per core mechanic:
      title.py shop.py city_map.py driving.py busting.py finale.py gameover.py
  __main__.py      # entry point (uv run psychic-cleaners)
tests/
  core/            # fast pure-python unit + property tests
  integration/     # scripted full-playthrough FSM tests (headless, no pygame)
  shell/           # SDL dummy-driver smoke tests
```

### Data flow and determinism

One-directional per frame: shell maps input → `Command` objects →
`core.game.tick(commands, dt)` → updated immutable-ish state + list of `Event`
objects → shell draws the state and plays sounds for events. The core never
imports pygame; the shell never mutates core state directly.

All randomness goes through the injected RNG; all time through the injected
clock. Any recorded command sequence + seed replays identically — this is what
makes full-playthrough tests deterministic.

### Error handling

- Invalid commands (overspending, oversize loadout, springing a snare with
  none laid) produce rejection `Event`s with reasons — not exceptions. The
  shell renders them as in-game feedback.
- Corrupt account codes → typed decode error → title-screen message, fall
  back to a fresh $10,000 game.
- Core invariants (money ≥ 0, PSI in [0, 9999], slots ≤ capacity) are
  enforced in the models and covered by property tests.
- The shell's `main()` wraps the loop; on unexpected exceptions it quits
  pygame cleanly and re-raises.

### Assets

`gfx.py` and `audio.py` generate all sprites and sounds in code at startup
(drawn Surfaces, synthesized waveforms, sequenced chiptune) behind a loader
interface keyed by asset name. Hand-made PNG/OGG files can later replace any
generated asset without touching game code.

## 6. Testing strategy

- **Core unit tests** (pytest): per-module, seeded RNG, fake clock. Fast — no
  display, no SDL.
- **Property tests** (Hypothesis): codec round-trip (any name/bankroll encodes
  → decodes identically; corrupted codes always rejected), economy invariants,
  PSI monotone under no-action, beam-crossing detection geometry.
- **Integration tests**: scripted command sequences driving `core.game`
  through a complete win and a complete loss, asserting on emitted events.
- **Shell smoke tests**: `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy` —
  app constructs, each scene renders one frame without error, sprite factory
  returns surfaces of expected sizes.
- **Coverage gate**: ≥90% on `core/`, enforced in CI.

## 7. Tooling

- **pygame-ce** (the Community Edition fork, already in pyproject; imported
  as `pygame`) is the only game/media dependency, and only `shell/` may
  import it. Plain upstream pygame must never be installed alongside it.
- **uv** for env and locking; dev dependency group: pytest, pytest-cov,
  hypothesis, ruff, mypy, pre-commit.
- **ruff**: lint + format (replaces black/isort/flake8).
- **mypy --strict** across src and tests.
- **pre-commit**: ruff check/format, mypy.
- **GitHub Actions**: on push/PR — uv sync, ruff check, ruff format --check,
  mypy, pytest with SDL dummy drivers and the coverage gate.
- Project stays `requires-python >= 3.14`, src layout, console entry point
  `psychic-cleaners`.

## 8. Milestones

Each milestone ends with CI green and the game runnable:

1. **Skeleton** — src layout, tooling, pre-commit, CI; window opens with
   fixed-timestep loop and FPS counter.
2. **Core spine** — clock, rng, events, constants; `game.py` FSM with stub
   scenes; integration test walks the FSM title→…→gameover.
3. **Shop** — economy, catalog, loadout + shop scene; buy a car and gear.
4. **Accounts** — codec + title screen with account entry and theme stub.
5. **City** — PSI model + city map scene: hauntings, wisps, travel, HUD.
6. **Drive** — lane sim + driving scene with vacuum catches.
7. **Bust** — beam/snare sim + bust scene, backfire rule, fees.
8. **Mascot** — Sir Squish events, sensor/bait flow, stomp fines.
9. **Finale** — Tower run, win/lose, account carry-over issuance.
10. **Polish** — chiptune theme with karaoke ball, SFX pass, balance
    calibration against reference footage, packaging.

Detailed per-milestone tasks belong to the implementation plan (next document).

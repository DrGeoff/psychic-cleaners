"""Every gameplay number in the game. The single tuning point."""

from typing import Final

# economy (documented values from the original)
STARTING_BANKROLL: Final[int] = 10_000
STOMP_FINE: Final[int] = 4_000
VACUUM_BOUNTY: Final[int] = 100
BUST_BASE_FEE: Final[int] = 300
BUST_FEE_PER_1000_PSI: Final[int] = 100
MAX_BANKROLL: Final[int] = 9_999_999
RENT_PER_DAY: Final[int] = 250
LOAN_MAX: Final[int] = 5_000
LOAN_BORROW_INCREMENT: Final[int] = 1_000
LOAN_INTEREST_RATE_PER_DAY: Final[float] = 0.05

# psi
# PER_REAL_MINUTE rates accrue per real-world minute, regardless of
# GAME_MINUTES_PER_REAL_SECOND (the models divide dt_seconds by 60).
PSI_MAX: Final[int] = 9_999
PSI_GROWTH_PER_REAL_MINUTE: Final[float] = 250.0
PSI_HAUNT_GROWTH_PER_REAL_MINUTE: Final[float] = 100.0  # per active haunting
WISP_TOWER_PSI_JUMP: Final[int] = 100
STOMP_PSI_SPIKE: Final[int] = 500

# time
GAME_MINUTES_PER_REAL_SECOND: Final[float] = 1.0
DAY_LENGTH_GAME_MINUTES: Final[float] = 90.0

# cleaners
CLEANER_COUNT: Final[int] = 3
FINALE_NEEDED_INSIDE: Final[int] = 2

# items
BAIT_PACK_SIZE: Final[int] = 5
CONTAINMENT_RIG_CAPACITY: Final[int] = 10

# city grid
GRID_WIDTH: Final[int] = 10
GRID_HEIGHT: Final[int] = 6
TOWER_POS: Final[tuple[int, int]] = (5, 3)
DEPOT_POS: Final[tuple[int, int]] = (0, 5)
BLOCK_LENGTH: Final[float] = 400.0  # travel units per manhattan step
HAUNT_CHANCE_PER_REAL_MINUTE: Final[float] = 0.8  # scaled by (1 + psi/PSI_MAX)
MAX_ACTIVE_HAUNTS: Final[int] = 4
WISP_SPAWN_PER_REAL_MINUTE: Final[float] = 0.6
WISP_MAP_SPEED: Final[float] = 0.05  # grid cells per real second
# Shared by wisps (city.py) and the convergence walkers (convergence.py):
# how close (in grid cells) counts as "reached the Tower".
TOWER_ARRIVE_RADIUS: Final[float] = 0.5

# the Warden and the Locksmith (spec 4.3/4.7)
# ~21 real seconds from the far corner to the tower: a readable endgame beat.
CONVERGENCE_WALK_SPEED: Final[float] = 0.25  # grid cells per real second

# drive scene
DRIVE_LANES: Final[int] = 3
CAR_X: Final[float] = 80.0
# ~3-4 catches per long drive: keeps road grinding below a single bust fee
ROAD_WISP_SPAWN_PER_SECOND: Final[float] = 0.1
ROAD_WISP_SPEED: Final[float] = 120.0  # toward the car, units/sec
CATCH_RANGE: Final[float] = 24.0
FAINT_WISP_CHANCE: Final[float] = 0.3
ROAD_LENGTH_VISIBLE: Final[float] = 640.0
# Wisps spawn WISP_SPAWN_MARGIN past the visible edge so the 24px sprite
# (12px half-width) is fully off-screen at spawn and slides into view,
# instead of being drawn half-clipped at ROAD_LENGTH_VISIBLE itself.
WISP_SPAWN_MARGIN: Final[float] = 16.0

# bust scene (logical coordinates, 640x400 space)
BEAM_CROSS_GHOST_Y: Final[float] = 320.0
BUST_GROUND_Y: Final[float] = 360.0
BEAM_TOP_Y: Final[float] = 120.0
BEAM_MAX_TILT: Final[float] = 140.0
GHOST_DRIFT_SPEED: Final[float] = 140.0  # must exceed GHOST_REPEL_SPEED or SLIMED is unreachable
GHOST_SINK_SPEED: Final[float] = 8.0
GHOST_REPEL_SPEED: Final[float] = 90.0
SLIME_RANGE: Final[float] = 28.0
SNARE_WIDTH: Final[float] = 48.0
SNARE_TRIGGER_Y: Final[float] = 280.0
CLEANER_SPEED: Final[float] = 180.0  # px/sec while positioning
BUST_MIN_X: Final[float] = 40.0
BUST_MAX_X: Final[float] = 600.0
BEAM_AIM_SPREAD: Final[float] = 8.0  # keeps the two beam tips from meeting at one point
# Beam-crossing backfire: BEAM_AIM_SPREAD alone can never let the beams
# cross (proven — see docs/superpowers/specs/2026-07-16-beam-crossing-backfire-design.md).
# Past BEAM_NARROW_START_Y the tilt gain ramps toward BEAM_MAX_GAIN, which
# CAN produce a genuine cross for an off-center ghost at a narrow-enough gap;
# gap >= ~300px is immune regardless of gain.
BEAM_NARROW_START_Y: Final[float] = SNARE_TRIGGER_Y
BEAM_MAX_GAIN: Final[float] = 2.0
# Failsafe: must exceed the slowest natural backfire — sinking from BEAM_TOP_Y
# to BEAM_CROSS_GHOST_Y takes (320 - 120) / 8 = 25 s — so it never preempts it.
BUST_TIMEOUT_SECONDS: Final[float] = 45.0

# mascot (Sir Squish)
MASCOT_CHANCE_PER_REAL_MINUTE_PER_1000_PSI: Final[float] = 0.10
MASCOT_ALERT_WINDOW: Final[float] = 10.0  # real seconds to deploy bait

# finale
DOOR_X: Final[float] = 560.0
GIANT_MIN_X: Final[float] = 180.0
GIANT_MAX_X: Final[float] = 460.0
GIANT_SPEED: Final[float] = 220.0  # triangle-wave bounce, px/sec
GIANT_HOP_PERIOD: Final[float] = 1.2
GIANT_AIR_FRACTION: Final[float] = 0.6
RUNNER_START_X: Final[float] = 40.0
RUNNER_SPEED: Final[float] = 260.0
SQUASH_RANGE: Final[float] = 36.0

# ui
NOTICE_LIFETIME_SECONDS: Final[float] = 6.0

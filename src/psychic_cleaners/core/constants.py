"""Every gameplay number in the game. The single tuning point."""

from typing import Final

# economy (documented values from the original)
STARTING_BANKROLL: Final[int] = 10_000
STOMP_FINE: Final[int] = 4_000
VACUUM_BOUNTY: Final[int] = 100
BUST_BASE_FEE: Final[int] = 300
BUST_FEE_PER_1000_PSI: Final[int] = 100
MAX_BANKROLL: Final[int] = 9_999_999

# psi
PSI_MAX: Final[int] = 9_999
PSI_GROWTH_PER_MINUTE: Final[float] = 250.0
PSI_HAUNT_GROWTH_PER_MINUTE: Final[float] = 100.0  # per active haunting
WISP_TOWER_PSI_JUMP: Final[int] = 100
STOMP_PSI_SPIKE: Final[int] = 500

# time
GAME_MINUTES_PER_REAL_SECOND: Final[float] = 1.0

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
HAUNT_CHANCE_PER_MINUTE: Final[float] = 0.8  # scaled by (1 + psi/PSI_MAX)
MAX_ACTIVE_HAUNTS: Final[int] = 4
WISP_SPAWN_PER_MINUTE: Final[float] = 0.6
WISP_MAP_SPEED: Final[float] = 0.05  # grid cells per real second

# drive scene
DRIVE_LANES: Final[int] = 3
CAR_X: Final[float] = 80.0
ROAD_WISP_SPAWN_PER_SECOND: Final[float] = 0.5
ROAD_WISP_SPEED: Final[float] = 120.0  # toward the car, units/sec
CATCH_RANGE: Final[float] = 24.0
FAINT_WISP_CHANCE: Final[float] = 0.3
ROAD_LENGTH_VISIBLE: Final[float] = 640.0

# bust scene (logical coordinates, 640x400 space)
BUST_GROUND_Y: Final[float] = 360.0
BEAM_TOP_Y: Final[float] = 120.0
BEAM_MAX_TILT: Final[float] = 140.0
GHOST_DRIFT_SPEED: Final[float] = 60.0
GHOST_SINK_SPEED: Final[float] = 8.0
GHOST_REPEL_SPEED: Final[float] = 90.0
SLIME_RANGE: Final[float] = 28.0
SNARE_WIDTH: Final[float] = 48.0
SNARE_TRIGGER_Y: Final[float] = 280.0
CLEANER_SPEED: Final[float] = 180.0  # px/sec while positioning
BUST_MIN_X: Final[float] = 40.0
BUST_MAX_X: Final[float] = 600.0

# mascot (Sir Squish)
MASCOT_CHANCE_PER_MINUTE_PER_1000_PSI: Final[float] = 0.15
MASCOT_ALERT_WINDOW: Final[float] = 10.0  # real seconds to deploy bait

# finale
DOOR_X: Final[float] = 560.0
GIANT_MIN_X: Final[float] = 180.0
GIANT_MAX_X: Final[float] = 460.0
GIANT_SPEED: Final[float] = 220.0  # triangle-wave bounce, px/sec
RUNNER_START_X: Final[float] = 40.0
RUNNER_SPEED: Final[float] = 160.0
SQUASH_RANGE: Final[float] = 36.0

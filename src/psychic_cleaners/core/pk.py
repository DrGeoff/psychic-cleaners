"""City-wide psychic residue (PSI) model: growth, spikes, thresholds."""

from dataclasses import dataclass

from psychic_cleaners.core.constants import (
    PSI_GROWTH_PER_REAL_MINUTE,
    PSI_HAUNT_GROWTH_PER_REAL_MINUTE,
    PSI_MAX,
)


@dataclass
class PsiModel:
    """Raw PSI is a float that only `spike` clamps; `value` caps the public int."""

    psi: float = 0.0

    def advance(self, dt_seconds: float, active_haunts: int) -> None:
        rate = PSI_GROWTH_PER_REAL_MINUTE + PSI_HAUNT_GROWTH_PER_REAL_MINUTE * active_haunts
        self.psi += rate * dt_seconds / 60.0

    def spike(self, amount: float) -> None:
        self.psi = min(max(self.psi + amount, 0.0), float(PSI_MAX))

    @property
    def value(self) -> int:
        return min(max(int(self.psi), 0), PSI_MAX)

    @property
    def at_max(self) -> bool:
        return self.value >= PSI_MAX

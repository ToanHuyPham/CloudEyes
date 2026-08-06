"""Assessment confidence model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConfidenceLevel(StrEnum):
    """Human-readable confidence level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Confidence:
    """Independent confidence dimensions for one cohort assessment."""

    measurement: ConfidenceLevel
    statistical: ConfidenceLevel
    coverage: ConfidenceLevel

    def __post_init__(self) -> None:
        for field_name in ("measurement", "statistical", "coverage"):
            value = getattr(self, field_name)
            if not isinstance(value, ConfidenceLevel):
                object.__setattr__(self, field_name, ConfidenceLevel(value))

    @property
    def overall(self) -> ConfidenceLevel:
        """Return the lowest confidence dimension."""

        order = {
            ConfidenceLevel.LOW: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.HIGH: 2,
        }
        return min(
            (self.measurement, self.statistical, self.coverage),
            key=order.__getitem__,
        )

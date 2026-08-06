"""Confidence models for CloudEyes assessments."""

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
    """Confidence dimensions for one assessment."""

    measurement: ConfidenceLevel
    statistical: ConfidenceLevel
    coverage: ConfidenceLevel

    @property
    def overall(self) -> ConfidenceLevel:
        """Return the lowest confidence dimension."""

        order = {
            ConfidenceLevel.LOW: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.HIGH: 2,
        }

        return min(
            (
                self.measurement,
                self.statistical,
                self.coverage,
            ),
            key=order.__getitem__,
        )

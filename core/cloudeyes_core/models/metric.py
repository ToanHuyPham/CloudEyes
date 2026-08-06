"""Normalized metric model."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class MetricDirection(StrEnum):
    """How a metric should be interpreted."""

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class Metric:
    """One normalized numeric observation."""

    name: str
    value: float
    unit: str
    direction: MetricDirection = MetricDirection.NEUTRAL

    def __post_init__(self) -> None:
        name = self.name.strip()
        unit = self.unit.strip()

        if not name:
            raise ValueError("metric name must not be empty")
        if not unit:
            raise ValueError("metric unit must not be empty")
        if isinstance(self.value, bool) or not isinstance(self.value, int | float):
            raise TypeError("metric value must be numeric")

        value = float(self.value)
        if not math.isfinite(value):
            raise ValueError("metric value must be finite")

        direction = (
            self.direction
            if isinstance(self.direction, MetricDirection)
            else MetricDirection(self.direction)
        )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "direction", direction)

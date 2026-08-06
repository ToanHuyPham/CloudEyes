"""Descriptive statistics used by CloudEyes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean, median, stdev


@dataclass(frozen=True, slots=True)
class SummaryStatistics:
    """Summary of a numeric data series."""

    count: int
    minimum: float
    maximum: float
    mean: float
    median: float
    standard_deviation: float
    coefficient_of_variation: float | None
    p10: float
    p90: float


def percentile(values: tuple[float, ...], probability: float) -> float:
    """Calculate a percentile using linear interpolation."""

    if not values:
        raise ValueError("values must not be empty")

    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")

    ordered = sorted(float(value) for value in values)

    if len(ordered) == 1:
        return ordered[0]

    position = probability * (len(ordered) - 1)
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered[lower_index]

    weight = position - lower_index

    return (
        ordered[lower_index] * (1 - weight)
        + ordered[upper_index] * weight
    )


def summarize(values: tuple[float, ...]) -> SummaryStatistics:
    """Calculate descriptive statistics for numeric values."""

    if not values:
        raise ValueError("values must not be empty")

    normalized = tuple(float(value) for value in values)

    if not all(math.isfinite(value) for value in normalized):
        raise ValueError("values must contain only finite numbers")

    average = fmean(normalized)

    deviation = stdev(normalized) if len(normalized) > 1 else 0.0

    coefficient = (
        deviation / abs(average)
        if average != 0
        else None
    )

    return SummaryStatistics(
        count=len(normalized),
        minimum=min(normalized),
        maximum=max(normalized),
        mean=average,
        median=float(median(normalized)),
        standard_deviation=deviation,
        coefficient_of_variation=coefficient,
        p10=percentile(normalized, 0.10),
        p90=percentile(normalized, 0.90),
    )

"""Effective-cost helpers for normalized pricing."""

from __future__ import annotations

import math

from ..models import MetricDirection, ValueIndexDefinition


def value_index(
    metric_value: float,
    hourly_usd: float,
    direction: MetricDirection,
) -> tuple[float, ValueIndexDefinition] | None:
    """Return a direction-adjusted performance-per-price index.

    Higher-is-better metrics use ``metric / USD-per-hour``. Lower-is-better metrics
    use ``1 / (metric * USD-per-hour)`` so a larger index remains better.
    """

    metric_value = float(metric_value)
    hourly_usd = float(hourly_usd)
    direction = direction if isinstance(direction, MetricDirection) else MetricDirection(direction)
    if (
        not math.isfinite(metric_value)
        or not math.isfinite(hourly_usd)
        or hourly_usd <= 0
        or direction is MetricDirection.NEUTRAL
    ):
        return None
    if direction is MetricDirection.HIGHER_IS_BETTER:
        if metric_value <= 0:
            return None
        return metric_value / hourly_usd, ValueIndexDefinition.METRIC_PER_USD_HOUR
    if metric_value <= 0:
        return None
    return 1.0 / (metric_value * hourly_usd), ValueIndexDefinition.INVERSE_METRIC_USD_HOUR

"""Models for compatible peer performance comparison."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .confidence import ConfidenceLevel
from .metric import MetricDirection


class PeerComparisonOutcome(StrEnum):
    """Direction-adjusted result against compatible peer providers."""

    AHEAD = "ahead"
    SIMILAR = "similar"
    BEHIND = "behind"


@dataclass(frozen=True, slots=True)
class PeerMetricComparison:
    """One provider metric compared with an equal-weight peer baseline."""

    comparison_id: str
    peer_group_id: str
    peer_key: str
    profile: str
    metric_name: str
    unit: str
    direction: MetricDirection
    provider_value: float
    peer_median: float
    relative_difference_percent: float
    outcome: PeerComparisonOutcome
    confidence: ConfidenceLevel
    peer_provider_count: int
    peer_provider_ids: tuple[str, ...]
    provider_cohort_ids: tuple[str, ...]
    peer_cohort_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "comparison_id",
            "peer_group_id",
            "peer_key",
            "profile",
            "metric_name",
            "unit",
        ):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)

        direction = (
            self.direction
            if isinstance(self.direction, MetricDirection)
            else MetricDirection(self.direction)
        )
        outcome = (
            self.outcome
            if isinstance(self.outcome, PeerComparisonOutcome)
            else PeerComparisonOutcome(self.outcome)
        )
        confidence = (
            self.confidence
            if isinstance(self.confidence, ConfidenceLevel)
            else ConfidenceLevel(self.confidence)
        )
        if direction is MetricDirection.NEUTRAL:
            raise ValueError("neutral metrics cannot produce peer comparisons")

        for field_name in (
            "provider_value",
            "peer_median",
            "relative_difference_percent",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
            object.__setattr__(self, field_name, value)

        peer_ids = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.peer_provider_ids if item.strip()))
        )
        provider_cohort_ids = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.provider_cohort_ids if item.strip()))
        )
        peer_cohort_ids = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.peer_cohort_ids if item.strip()))
        )
        if self.peer_provider_count != len(peer_ids) or self.peer_provider_count < 1:
            raise ValueError("peer_provider_count must match peer_provider_ids")
        if not provider_cohort_ids or not peer_cohort_ids:
            raise ValueError("peer comparisons require provider and peer cohort evidence")

        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "peer_provider_ids", peer_ids)
        object.__setattr__(self, "provider_cohort_ids", provider_cohort_ids)
        object.__setattr__(self, "peer_cohort_ids", peer_cohort_ids)

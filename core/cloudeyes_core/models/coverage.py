"""Coverage models for CloudEyes provider assessments."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Coverage:
    """Describes how much of the target scope has been observed."""

    sample_count: int
    observation_days: int
    regions: tuple[str, ...] = field(default_factory=tuple)
    zones: tuple[str, ...] = field(default_factory=tuple)
    products: tuple[str, ...] = field(default_factory=tuple)
    plans: tuple[str, ...] = field(default_factory=tuple)
    available_metrics: tuple[str, ...] = field(default_factory=tuple)
    expected_metrics: tuple[str, ...] = field(default_factory=tuple)
    gaps: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.sample_count < 0:
            raise ValueError("sample_count must not be negative")

        if self.observation_days < 0:
            raise ValueError("observation_days must not be negative")

    @property
    def metric_ratio(self) -> float:
        """Return the ratio of expected metrics that are available."""

        if not self.expected_metrics:
            return 1.0

        expected = set(self.expected_metrics)
        available = set(self.available_metrics)

        return len(expected & available) / len(expected)

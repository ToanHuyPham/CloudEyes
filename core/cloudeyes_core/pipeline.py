"""End-to-end Core Foundation analysis pipeline."""

from __future__ import annotations

from datetime import datetime

from .cohorts import build_cohorts
from .models import ProviderReport, Sample
from .provider import build_provider_reports
from .repository import JsonSampleRepository
from .validation import ensure_valid_sample


def analyze_samples(
    samples: tuple[Sample, ...],
    *,
    expected_metrics: tuple[str, ...] = (),
    generated_at: datetime | None = None,
) -> tuple[ProviderReport, ...]:
    """Validate samples and build deterministic provider reports."""

    for sample in samples:
        ensure_valid_sample(sample)
    cohorts = build_cohorts(samples)
    return build_provider_reports(
        cohorts,
        expected_metrics=expected_metrics,
        generated_at=generated_at,
    )


def analyze_repository(
    repository: JsonSampleRepository,
    *,
    expected_metrics: tuple[str, ...] = (),
    generated_at: datetime | None = None,
) -> tuple[ProviderReport, ...]:
    """Load every repository sample and build provider reports."""

    return analyze_samples(
        tuple(repository.iter_samples()),
        expected_metrics=expected_metrics,
        generated_at=generated_at,
    )

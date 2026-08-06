"""Tests for cohort compatibility and grouping."""

from datetime import UTC, datetime, timedelta

import pytest

from cloudeyes_core.cohorts import build_cohorts, compare_samples
from tests.core_factory import make_sample


def test_compatible_samples_are_grouped_and_sorted() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    cohorts = build_cohorts(
        (
            make_sample("sample-002", created_at=start + timedelta(days=1)),
            make_sample("sample-001", created_at=start),
        )
    )
    assert len(cohorts) == 1
    assert tuple(item.sample_id for item in cohorts[0].samples) == ("sample-001", "sample-002")


def test_different_regions_create_different_cohorts() -> None:
    cohorts = build_cohorts((make_sample("a", region="hanoi"), make_sample("b", region="danang")))
    assert len(cohorts) == 2


def test_different_machine_sizes_are_incompatible() -> None:
    result = compare_samples(make_sample("a", cpu_count=2), make_sample("b", cpu_count=4))
    assert result.compatible is False
    assert "cpu_count" in result.differences


def test_different_fingerprints_are_incompatible() -> None:
    result = compare_samples(make_sample("a"), make_sample("b", fingerprint="different"))
    assert "protocol_fingerprint" in result.differences


def test_duplicate_sample_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate sample ID"):
        build_cohorts((make_sample("same"), make_sample("same")))

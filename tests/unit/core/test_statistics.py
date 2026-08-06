"""Tests for descriptive statistics and cohort aggregation."""

import pytest

from cloudeyes_core.cohorts import build_cohorts, summarize_cohort
from cloudeyes_core.statistics import percentile, summarize
from tests.core_factory import make_sample


def test_summary_values() -> None:
    result = summarize((100.0, 110.0, 120.0))
    assert result.mean == 110.0
    assert result.median == 110.0
    assert result.standard_deviation == 10.0


def test_percentile_interpolates() -> None:
    assert percentile((0.0, 10.0, 20.0), 0.25) == 5.0


def test_zero_mean_has_no_coefficient() -> None:
    assert summarize((-1.0, 0.0, 1.0)).coefficient_of_variation is None


def test_each_sample_has_equal_weight() -> None:
    cohort = build_cohorts((make_sample("a", values=(100.0, 110.0, 120.0)), make_sample("b", values=(200.0,))))[0]
    metric = summarize_cohort(cohort).metrics[0]
    assert metric.raw_observations == 4
    assert metric.contributing_samples == 2
    assert metric.statistics.mean == 155.0


def test_incompatible_units_are_rejected() -> None:
    cohort = build_cohorts((make_sample("a", unit="ops"), make_sample("b", unit="events")))[0]
    with pytest.raises(ValueError, match="incompatible units"):
        summarize_cohort(cohort)

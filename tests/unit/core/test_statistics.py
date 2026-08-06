"""Tests for CloudEyes descriptive statistics."""

from __future__ import annotations

import pytest

from core.cloudeyes_core.statistics import percentile, summarize


def test_summarize_single_value() -> None:
    result = summarize((100.0,))

    assert result.count == 1
    assert result.minimum == 100.0
    assert result.maximum == 100.0
    assert result.mean == 100.0
    assert result.median == 100.0
    assert result.standard_deviation == 0.0
    assert result.coefficient_of_variation == 0.0


def test_summarize_multiple_values() -> None:
    result = summarize((100.0, 110.0, 120.0))

    assert result.count == 3
    assert result.minimum == 100.0
    assert result.maximum == 120.0
    assert result.mean == 110.0
    assert result.median == 110.0
    assert result.standard_deviation == 10.0


def test_zero_mean_has_no_coefficient_of_variation() -> None:
    result = summarize((-1.0, 0.0, 1.0))

    assert result.mean == 0.0
    assert result.coefficient_of_variation is None


def test_percentile_uses_interpolation() -> None:
    values = (0.0, 10.0, 20.0)

    assert percentile(values, 0.25) == 5.0
    assert percentile(values, 0.50) == 10.0
    assert percentile(values, 0.75) == 15.0


def test_empty_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        summarize(())


def test_non_finite_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        summarize((1.0, float("inf")))

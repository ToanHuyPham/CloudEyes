"""Tests for cross-field sample validation."""

from dataclasses import replace

import pytest
from cloudeyes_core.models import SampleQualityStatus
from cloudeyes_core.validation import SampleValidationError, ensure_valid_sample, validate_sample

from tests.core_factory import make_sample


def test_valid_sample_passes() -> None:
    assert validate_sample(make_sample()).valid is True


def test_duplicate_measurement_ids_fail() -> None:
    sample = make_sample(values=(100.0, 101.0))
    duplicate = replace(
        sample.measurements[1], measurement_id=sample.measurements[0].measurement_id
    )
    result = validate_sample(replace(sample, measurements=(sample.measurements[0], duplicate)))
    assert result.valid is False
    assert "measurement IDs must be unique inside a sample" in result.errors


def test_protocol_mismatch_fails() -> None:
    sample = make_sample()
    measurement = replace(sample.measurements[0], protocol_version="2.0.0")
    result = validate_sample(replace(sample, measurements=(measurement,)))
    assert any("protocol version" in error for error in result.errors)


def test_invalid_quality_is_rejected() -> None:
    sample = make_sample(
        quality_status=SampleQualityStatus.INVALID,
        quality_errors=("clock_unstable",),
    )
    with pytest.raises(SampleValidationError, match="clock_unstable"):
        ensure_valid_sample(sample)

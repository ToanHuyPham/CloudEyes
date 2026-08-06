"""Tests for the validated JSON sample repository."""

import pytest
from cloudeyes_core.models import SampleQualityStatus
from cloudeyes_core.repository import JsonSampleRepository
from cloudeyes_core.validation import SampleValidationError

from tests.core_factory import make_sample


def test_repository_save_load_and_list(tmp_path) -> None:
    repository = JsonSampleRepository(tmp_path)
    original = make_sample()
    repository.save(original)
    assert repository.list_ids() == ("sample-001",)
    assert repository.load("sample-001") == original


def test_duplicate_save_requires_overwrite(tmp_path) -> None:
    repository = JsonSampleRepository(tmp_path)
    repository.save(make_sample())
    with pytest.raises(FileExistsError):
        repository.save(make_sample())


def test_overwrite_replaces_existing_sample(tmp_path) -> None:
    repository = JsonSampleRepository(tmp_path)
    repository.save(make_sample(values=(100.0,)))
    repository.save(make_sample(values=(200.0,)), overwrite=True)
    assert repository.load("sample-001").measurements[0].metrics[0].value == 200.0


def test_unsafe_sample_id_is_rejected(tmp_path) -> None:
    repository = JsonSampleRepository(tmp_path)
    with pytest.raises(ValueError, match="letters"):
        repository.save(make_sample("../escape"))


def test_invalid_sample_is_not_saved(tmp_path) -> None:
    repository = JsonSampleRepository(tmp_path)
    sample = make_sample(
        quality_status=SampleQualityStatus.INVALID,
        quality_errors=("bad_clock",),
    )
    with pytest.raises(SampleValidationError):
        repository.save(sample)
    assert repository.list_ids() == ()

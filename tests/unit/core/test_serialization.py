"""Tests for JSON serialization and deserialization."""

import json

from cloudeyes_core.serialization import dump, dumps, load_sample, loads_sample

from tests.core_factory import make_sample


def test_sample_round_trip() -> None:
    original = make_sample()
    restored = loads_sample(dumps(original))
    assert restored == original


def test_enum_and_datetime_are_serialized() -> None:
    data = json.loads(dumps(make_sample()))
    assert data["quality"]["status"] == "valid"
    assert data["measurements"][0]["status"] == "success"
    assert data["created_at"].endswith("+00:00")


def test_dump_creates_parent_directory(tmp_path) -> None:
    path = dump(make_sample(), tmp_path / "nested" / "sample.json")
    assert path.exists()


def test_load_sample_reads_file(tmp_path) -> None:
    original = make_sample()
    path = dump(original, tmp_path / "sample.json")
    assert load_sample(path) == original

"""Tests for atomic raw benchmark evidence persistence."""

from __future__ import annotations

import json

import pytest
from cloudeyes_agent.storage import load_raw_output, write_raw_output


def test_raw_output_round_trip(tmp_path) -> None:
    path = write_raw_output(
        {"profile": "storage", "value": 1},
        directory=tmp_path,
        stem="sample-1-storage",
    )

    assert path.name == "sample-1-storage.json"
    assert load_raw_output(path) == {"profile": "storage", "value": 1}
    assert json.loads(path.read_text(encoding="utf-8"))["profile"] == "storage"


def test_raw_output_stem_is_sanitized(tmp_path) -> None:
    path = write_raw_output({}, directory=tmp_path, stem="sample / unsafe")

    assert path.parent == tmp_path
    assert "/" not in path.name


def test_raw_output_rejects_empty_safe_stem(tmp_path) -> None:
    with pytest.raises(ValueError, match="safe character"):
        write_raw_output({}, directory=tmp_path, stem="///")

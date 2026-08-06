"""End-to-end smoke test for Database Profile v1."""

from __future__ import annotations

from cloudeyes_agent.discovery import discover_all
from cloudeyes_agent.profiles.database import DatabaseProfileConfig, run_database_profile
from cloudeyes_agent.storage import load_raw_output
from cloudeyes_core.serialization import dump, load_sample
from cloudeyes_core.validation import validate_sample


def test_quick_database_profile_runs_end_to_end(tmp_path) -> None:
    sample = run_database_profile(
        config=DatabaseProfileConfig.quick(),
        discovery=discover_all(env={}),
        sample_id="database-integration",
        work_dir=tmp_path / "work",
        raw_output_dir=tmp_path / "raw",
    )

    output = dump(sample, tmp_path / "sample.json")
    restored = load_sample(output)

    assert restored.protocol.profile == "database"
    assert len(restored.measurements[0].metrics) == 9
    assert validate_sample(restored).valid is True
    raw_path = restored.measurements[0].raw_output_path
    assert raw_path is not None
    evidence = load_raw_output(raw_path)
    assert evidence["profile"] == "database"
    assert evidence["safety"]["temporary_database"] is True

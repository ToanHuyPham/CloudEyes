"""End-to-end smoke test for General Profile v1."""

from __future__ import annotations

from cloudeyes_agent.discovery import discover_all
from cloudeyes_agent.profiles.general import GeneralProfileConfig, run_general_profile
from cloudeyes_core.models import MeasurementStatus
from cloudeyes_core.serialization import dump, load_sample
from cloudeyes_core.validation import validate_sample


def test_quick_general_profile_runs_end_to_end(tmp_path) -> None:
    sample = run_general_profile(
        config=GeneralProfileConfig.quick(),
        discovery=discover_all(env={}),
        sample_id="general-integration",
        work_dir=tmp_path,
    )
    output = dump(sample, tmp_path / "sample.json")
    restored = load_sample(output)

    successful = [
        measurement
        for measurement in restored.measurements
        if measurement.status is MeasurementStatus.SUCCESS
    ]

    assert len(successful) == 3
    assert validate_sample(restored).valid is True
    assert output.exists()

"""End-to-end smoke test for Compute Profile v1."""

from __future__ import annotations

from cloudeyes_agent.discovery import discover_all
from cloudeyes_agent.profiles.compute import ComputeProfileConfig, run_compute_profile
from cloudeyes_agent.storage import load_raw_output
from cloudeyes_core.serialization import dump, load_sample
from cloudeyes_core.validation import validate_sample


def test_quick_compute_profile_runs_end_to_end(tmp_path) -> None:
    sample = run_compute_profile(
        config=ComputeProfileConfig.quick(workers=1),
        discovery=discover_all(env={}),
        sample_id="compute-integration",
        raw_output_dir=tmp_path / "raw",
    )

    output = dump(sample, tmp_path / "sample.json")
    restored = load_sample(output)

    assert restored.protocol.profile == "compute"
    assert len(restored.measurements[0].metrics) == 7
    assert validate_sample(restored).valid is True
    raw_path = restored.measurements[0].raw_output_path
    assert raw_path is not None
    assert load_raw_output(raw_path)["profile"] == "compute"

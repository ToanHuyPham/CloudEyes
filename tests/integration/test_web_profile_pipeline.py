"""End-to-end smoke test for Web Profile v1."""

from __future__ import annotations

from cloudeyes_agent.discovery import discover_all
from cloudeyes_agent.profiles.web import (
    NetworkScope,
    WebProfileConfig,
    run_web_profile,
)
from cloudeyes_agent.storage import load_raw_output
from cloudeyes_core.serialization import dump, load_sample
from cloudeyes_core.validation import validate_sample

from tests.web_test_server import local_web_endpoint


def test_quick_web_profile_runs_end_to_end(tmp_path) -> None:
    with local_web_endpoint() as base_url:
        sample = run_web_profile(
            config=WebProfileConfig.quick(
                target_url=f"{base_url}/slow",
                scope=NetworkScope.PRIVATE,
            ),
            discovery=discover_all(env={}),
            sample_id="web-integration",
            raw_output_dir=tmp_path / "raw",
        )

    output = dump(sample, tmp_path / "sample.json")
    restored = load_sample(output)

    assert restored.protocol.profile == "web"
    assert len(restored.measurements[0].metrics) == 8
    assert validate_sample(restored).valid is True
    raw_path = restored.measurements[0].raw_output_path
    assert raw_path is not None
    assert load_raw_output(raw_path)["profile"] == "web"

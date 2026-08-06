"""End-to-end smoke test for Networking Profile v1."""

from __future__ import annotations

from cloudeyes_agent.discovery import discover_all
from cloudeyes_agent.profiles.networking import (
    NetworkingProfileConfig,
    NetworkScope,
    run_networking_profile,
)
from cloudeyes_agent.storage import load_raw_output
from cloudeyes_core.serialization import dump, load_sample
from cloudeyes_core.validation import validate_sample

from tests.network_test_server import local_network_endpoint


def test_quick_networking_profile_runs_end_to_end(tmp_path) -> None:
    with local_network_endpoint() as (download_url, upload_url):
        sample = run_networking_profile(
            config=NetworkingProfileConfig.quick(
                target_url=download_url,
                upload_url=upload_url,
                scope=NetworkScope.PRIVATE,
            ),
            discovery=discover_all(env={}),
            sample_id="networking-integration",
            raw_output_dir=tmp_path / "raw",
        )

    output = dump(sample, tmp_path / "sample.json")
    restored = load_sample(output)

    assert restored.protocol.profile == "networking"
    assert len(restored.measurements[0].metrics) >= 7
    assert validate_sample(restored).valid is True
    raw_path = restored.measurements[0].raw_output_path
    assert raw_path is not None
    assert load_raw_output(raw_path)["profile"] == "networking"

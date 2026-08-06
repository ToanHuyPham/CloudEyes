"""Integration test for offline provider analytics CLI output."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from cloudeyes_agent import cli
from cloudeyes_core.serialization import dump

from tests.core_factory import make_sample


def test_analyze_directory_writes_json_and_markdown(tmp_path, capsys) -> None:
    sample_dir = tmp_path / "samples"
    start = datetime(2026, 8, 1, tzinfo=UTC)
    for index, value in enumerate((99.0, 100.0, 101.0)):
        dump(
            make_sample(
                f"sample-{index + 1}",
                created_at=start + timedelta(days=index),
                values=(value,),
            ),
            sample_dir / f"sample-{index + 1}.json",
        )

    output = tmp_path / "analytics.json"
    markdown = tmp_path / "analytics.md"
    exit_code = cli.main(
        (
            "analyze",
            str(sample_dir),
            "--expected-metric",
            "compute.cpu.events_per_second",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--compact",
        )
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))
    assert printed == written
    assert written["provider_count"] == 1
    assert written["providers"][0]["scorecard"]["coverage_ratio"] == 1.0
    rendered = markdown.read_text(encoding="utf-8")
    assert "CloudEyes Provider Analytics v1" in rendered
    assert "universal_score_not_calculated" in rendered

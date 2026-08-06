"""End-to-end CLI tests for result bundle creation, verification, and dry-run submission."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_agent import cli
from cloudeyes_core.serialization import dump

from tests.core_factory import make_sample


def test_bundle_verify_and_submit_dry_run_cli(tmp_path: Path, capsys) -> None:
    sample = tmp_path / "sample.json"
    bundle = tmp_path / "result.zip"
    dump(make_sample(), sample)

    assert cli.main(("bundle", str(sample), "--output", str(bundle), "--compact")) == 0
    build_output = json.loads(capsys.readouterr().out)
    assert build_output["sample_count"] == 1
    assert bundle.is_file()

    assert cli.main(("verify-bundle", str(bundle), "--compact")) == 0
    verification = json.loads(capsys.readouterr().out)
    assert verification["sample_count"] == 1
    assert len(verification["bundle_sha256"]) == 64

    assert (
        cli.main(
            (
                "submit",
                str(bundle),
                "--endpoint",
                "https://collector.example.test/v1/submissions",
                "--dry-run",
                "--compact",
            )
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "dry_run"
    assert plan["bundle_id"] == verification["bundle_id"]


def test_submit_requires_token_without_anonymous_flag(tmp_path: Path, capsys) -> None:
    sample = tmp_path / "sample.json"
    bundle = tmp_path / "result.zip"
    dump(make_sample(), sample)
    assert cli.main(("bundle", str(sample), "--output", str(bundle))) == 0
    capsys.readouterr()

    exit_code = cli.main(
        (
            "submit",
            str(bundle),
            "--endpoint",
            "https://collector.example.test/v1/submissions",
        )
    )

    assert exit_code == 8
    assert "submission token is missing" in capsys.readouterr().out

"""Tests for the Agent inspect command."""

from __future__ import annotations

import json

from cloudeyes_agent import cli
from cloudeyes_agent.commands import inspect as inspect_command

from tests.unit.agent.test_discovery_models import make_result


def test_inspect_prints_and_writes_json(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(inspect_command, "discover_all", make_result)
    output = tmp_path / "discovery.json"

    exit_code = cli.main(("inspect", "--output", str(output)))

    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed == written
    assert written["provider"]["provider_id"] == "azure"


def test_compact_output_has_no_indentation(monkeypatch, capsys) -> None:
    monkeypatch.setattr(inspect_command, "discover_all", make_result)

    exit_code = cli.main(("inspect", "--compact"))
    output = capsys.readouterr().out.strip()

    assert exit_code == 0
    assert "\n" not in output


def test_run_general_writes_core_sample(tmp_path, monkeypatch, capsys) -> None:
    from cloudeyes_agent.commands import run as run_command

    from tests.core_factory import make_sample

    monkeypatch.setattr(run_command, "run_general_profile", lambda **_: make_sample())
    output = tmp_path / "sample.json"

    exit_code = cli.main(
        (
            "run",
            "general",
            "--quick",
            "--no-storage",
            "--output",
            str(output),
            "--compact",
        )
    )

    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed == written
    assert written["protocol"]["profile"] == "general"

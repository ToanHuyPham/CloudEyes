"""Tests for the CloudEyes Agent command-line interface."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from cloudeyes_agent import cli
from cloudeyes_agent.commands import inspect as inspect_command
from cloudeyes_agent.commands import run as run_command
from cloudeyes_agent.execution import IsolatedExecutionCancelled

from tests.core_factory import make_sample
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
    monkeypatch.setattr(run_command, "run_general_profile", lambda **_: make_sample())
    output = tmp_path / "sample.json"

    exit_code = cli.main(
        (
            "run",
            "general",
            "--quick",
            "--no-isolation",
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


def test_run_storage_writes_sample_and_selects_work_dir(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    sample = make_sample()
    captured: dict[str, object] = {}

    def fake_storage_profile(**kwargs):
        captured.update(kwargs)
        return sample

    monkeypatch.setattr(run_command, "run_storage_profile", fake_storage_profile)
    output = tmp_path / "storage-sample.json"
    work_dir = tmp_path / "benchmark-target"

    exit_code = cli.main(
        (
            "run",
            "storage",
            "--quick",
            "--no-isolation",
            "--work-dir",
            str(work_dir),
            "--output",
            str(output),
            "--compact",
        )
    )

    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed == written
    assert output.exists()
    assert captured["work_dir"] == work_dir
    assert captured["raw_output_dir"] == output.parent / "raw"


def test_run_networking_passes_endpoint_options(tmp_path, monkeypatch, capsys) -> None:
    sample = make_sample()
    captured: dict[str, object] = {}

    def fake_networking_profile(**kwargs):
        captured.update(kwargs)
        return sample

    monkeypatch.setattr(run_command, "run_networking_profile", fake_networking_profile)
    output = tmp_path / "networking-sample.json"

    exit_code = cli.main(
        (
            "run",
            "networking",
            "--quick",
            "--no-isolation",
            "--target",
            "http://10.0.0.10:8080/download",
            "--upload-target",
            "http://10.0.0.10:8080/upload",
            "--scope",
            "private",
            "--no-ping",
            "--output",
            str(output),
            "--compact",
        )
    )

    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed == written
    config = captured["config"]
    assert config.target_url == "http://10.0.0.10:8080/download"
    assert config.upload_url == "http://10.0.0.10:8080/upload"
    assert config.scope.value == "private"
    assert config.ping_count == 0
    assert captured["raw_output_dir"] == output.parent / "raw"


def test_run_compute_passes_worker_count(tmp_path, monkeypatch, capsys) -> None:
    sample = make_sample(profile="compute")
    captured: dict[str, object] = {}

    def fake_compute_profile(**kwargs):
        captured.update(kwargs)
        return sample

    monkeypatch.setattr(run_command, "run_compute_profile", fake_compute_profile)
    output = tmp_path / "compute-sample.json"

    exit_code = cli.main(
        (
            "run",
            "compute",
            "--quick",
            "--no-isolation",
            "--workers",
            "3",
            "--output",
            str(output),
            "--compact",
        )
    )

    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed == written
    assert captured["config"].workers == 3
    assert captured["raw_output_dir"] == output.parent / "raw"


def test_workers_option_is_rejected_for_non_compute_profile(capsys) -> None:
    exit_code = cli.main(("run", "general", "--quick", "--no-isolation", "--workers", "2"))

    assert exit_code == 4
    assert "only valid for the compute profile" in capsys.readouterr().out


def test_workers_option_rejects_out_of_range_value() -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(("run", "compute", "--workers", "65"))

    assert error.value.code == 2


def test_isolated_run_injects_cancellation_token(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_isolated(target, **kwargs):
        captured["target"] = target
        captured.update(kwargs)
        return SimpleNamespace(value=make_sample())

    monkeypatch.setattr(run_command, "run_isolated", fake_run_isolated)

    exit_code = cli.main(("run", "general", "--quick", "--compact"))

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["protocol"]["profile"] == "general"
    assert captured["cancellation_kwarg"] == "cancellation_token"


def test_interrupted_isolated_run_returns_130(monkeypatch, capsys) -> None:
    def cancel(*_, **__):
        raise IsolatedExecutionCancelled("cooperative cleanup completed")

    monkeypatch.setattr(run_command, "run_isolated", cancel)

    exit_code = cli.main(("run", "general", "--quick"))

    assert exit_code == 130
    assert "profile cancelled" in capsys.readouterr().out

"""End-to-end test for the installed Agent Discovery command."""

from __future__ import annotations

import json
import os
import subprocess
import sys


def test_module_cli_generates_valid_json(tmp_path) -> None:
    output = tmp_path / "discovery.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(("agent", "core"))

    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "cloudeyes_agent",
            "inspect",
            "--compact",
            "--output",
            str(output),
        ),
        capture_output=True,
        check=False,
        cwd=os.getcwd(),
        env=environment,
        text=True,
        timeout=15,
    )

    assert completed.returncode == 0, completed.stderr
    printed = json.loads(completed.stdout)
    written = json.loads(output.read_text(encoding="utf-8"))
    assert printed == written
    assert printed["schema_version"] == "1.0.0"

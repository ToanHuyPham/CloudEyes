"""Tests for runtime dependency bootstrap behavior."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from cloudeyes_agent.bootstrap import (
    RuntimeDependencyError,
    RuntimeDependencyReport,
    ensure_runtime_dependencies,
    render_install_command,
)


def test_ready_report_never_installs() -> None:
    report = RuntimeDependencyReport(platform="ubuntu", package_manager="apt-get")
    runner = Mock()
    with patch("cloudeyes_agent.bootstrap.runner.detect_runtime_dependencies", return_value=report):
        assert ensure_runtime_dependencies(run=runner) == report
    runner.assert_not_called()


def test_missing_dependencies_require_explicit_opt_in() -> None:
    report = RuntimeDependencyReport(
        platform="ubuntu",
        package_manager="apt-get",
        missing_commands=("ip",),
        packages=("iproute2",),
    )
    with (
        patch("cloudeyes_agent.bootstrap.runner.detect_runtime_dependencies", return_value=report),
        pytest.raises(RuntimeDependencyError, match="--install-deps"),
    ):
        ensure_runtime_dependencies()


def test_assume_yes_runs_native_install_command() -> None:
    missing = RuntimeDependencyReport(
        platform="sles",
        package_manager="zypper",
        missing_commands=("lspci",),
        packages=("pciutils",),
    )
    ready = RuntimeDependencyReport(platform="sles", package_manager="zypper")
    runner = Mock()
    with patch(
        "cloudeyes_agent.bootstrap.runner.detect_runtime_dependencies",
        side_effect=(missing, ready),
    ):
        result = ensure_runtime_dependencies(auto_install=True, assume_yes=True, run=runner)
    assert result.ready
    command = runner.call_args.args[0]
    assert "zypper" in command
    assert "pciutils" in command


def test_package_commands_cover_supported_linux_families() -> None:
    expected = {
        "apt-get": "iproute2",
        "dnf": "iproute",
        "yum": "iproute",
        "zypper": "iproute2",
        "apk": "iproute2",
        "pacman": "iproute2",
    }
    for manager, package in expected.items():
        report = RuntimeDependencyReport(
            platform="linux",
            package_manager=manager,
            missing_commands=("ip",),
            packages=(package,),
        )
        command = render_install_command(report)
        assert manager in command
        assert package in command

"""Tests for runtime dependency bootstrap behavior."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from cloudeyes_agent.bootstrap import (
    RuntimeDependencyError,
    RuntimeDependencyReport,
    detect_runtime_dependencies,
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


def test_networking_ping_dependency_maps_to_native_package() -> None:
    report = RuntimeDependencyReport(
        platform="ubuntu",
        package_manager="apt-get",
        missing_commands=("ping",),
        packages=("iputils-ping",),
    )

    command = render_install_command(report)

    assert "apt-get" in command
    assert "iputils-ping" in command


def test_detector_includes_profile_specific_ping_command() -> None:
    def fake_which(command: str) -> str | None:
        if command == "apt-get":
            return "/usr/bin/apt-get"
        if command in {"lscpu", "free", "ip", "lspci"}:
            return f"/usr/bin/{command}"
        return None

    with (
        patch("cloudeyes_agent.bootstrap.detector.platform.system", return_value="Linux"),
        patch("cloudeyes_agent.bootstrap.detector.shutil.which", side_effect=fake_which),
        patch(
            "cloudeyes_agent.bootstrap.detector._read_os_id",
            return_value='ID="ubuntu"',
        ),
    ):
        report = detect_runtime_dependencies(extra_commands=("ping",))

    assert report.missing_commands == ("ping",)
    assert report.packages == ("iputils-ping",)

"""Contract tests for operating-system bootstrap scripts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LINUX_INSTALLER = ROOT / "scripts" / "install.sh"
WINDOWS_INSTALLER = ROOT / "scripts" / "install.ps1"
HAS_BASH = shutil.which("bash") is not None


@pytest.mark.skipif(not HAS_BASH, reason="bash is not installed on this host")
def test_linux_installer_has_valid_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(LINUX_INSTALLER)], check=True)


def test_linux_installer_supports_required_package_managers() -> None:
    content = LINUX_INSTALLER.read_text(encoding="utf-8")
    for command in ("apt-get", "dnf", "yum", "zypper", "apk", "pacman"):
        assert f"command -v {command}" in content


def test_installers_require_python_311_or_newer() -> None:
    linux = LINUX_INSTALLER.read_text(encoding="utf-8")
    windows = WINDOWS_INSTALLER.read_text(encoding="utf-8")
    assert "sys.version_info >= (3, 11)" in linux
    assert "sys.version_info >= (3,11)" in windows


def test_installers_create_isolated_virtual_environment() -> None:
    linux = LINUX_INSTALLER.read_text(encoding="utf-8")
    windows = WINDOWS_INSTALLER.read_text(encoding="utf-8")
    assert '-m venv "$VENV_DIR"' in linux
    assert "-m venv $VenvPath" in windows


@pytest.mark.skipif(not HAS_BASH, reason="bash is not installed on this host")
def test_linux_dry_run_does_not_require_root() -> None:
    result = subprocess.run(
        ["bash", str(LINUX_INSTALLER), "--dry-run"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Unsupported package manager" not in result.stdout

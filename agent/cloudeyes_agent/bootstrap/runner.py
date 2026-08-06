"""Install runtime dependencies through the host package manager."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence

from .detector import detect_runtime_dependencies
from .model import RuntimeDependencyReport


class RuntimeDependencyError(RuntimeError):
    """Raised when runtime dependencies cannot be prepared safely."""


def _command_for(report: RuntimeDependencyReport, *, assume_yes: bool) -> list[str]:
    manager = report.package_manager
    packages = list(report.packages)
    if not manager or not packages:
        return []

    prefix: list[str] = []
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0:
        prefix = ["sudo"]

    if manager == "apt-get":
        return [*prefix, manager, "install", "-y", *packages]
    if manager in {"dnf", "yum"}:
        return [*prefix, manager, "install", "-y", *packages]
    if manager == "zypper":
        return [*prefix, manager, "--non-interactive", "install", *packages]
    if manager == "apk":
        return [*prefix, manager, "add", "--no-cache", *packages]
    if manager == "pacman":
        yes_args = ["--noconfirm"] if assume_yes else []
        return [*prefix, manager, "-S", "--needed", *yes_args, *packages]
    return []


def ensure_runtime_dependencies(
    *,
    auto_install: bool = False,
    assume_yes: bool = False,
    input_fn: Callable[[str], str] = input,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    extra_commands: tuple[str, ...] = (),
) -> RuntimeDependencyReport:
    """Check dependencies and optionally install missing native packages.

    The default mode never modifies the operating system. Installation only
    occurs when ``auto_install`` is true and, unless ``assume_yes`` is true,
    the user confirms the exact package command.
    """

    report = detect_runtime_dependencies(extra_commands=extra_commands)
    if report.ready:
        return report

    missing = ", ".join(report.missing_commands)
    if not auto_install:
        raise RuntimeDependencyError(
            "Missing recommended runtime commands: "
            f"{missing}. Re-run with --install-deps to install them automatically."
        )

    command = _command_for(report, assume_yes=assume_yes)
    if not command:
        raise RuntimeDependencyError(
            f"Cannot install missing commands automatically on {report.platform}: {missing}"
        )

    if not assume_yes:
        answer = input_fn(f"Run {' '.join(command)}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            raise RuntimeDependencyError("Runtime dependency installation was cancelled.")

    run(command, check=True, text=True)
    refreshed = detect_runtime_dependencies(extra_commands=extra_commands)
    if not refreshed.ready:
        remaining = ", ".join(refreshed.missing_commands)
        raise RuntimeDependencyError(
            f"Dependencies are still missing after installation: {remaining}"
        )
    return refreshed


def render_install_command(
    report: RuntimeDependencyReport,
    *,
    assume_yes: bool = True,
) -> Sequence[str]:
    """Expose the deterministic native command for diagnostics and tests."""

    return tuple(_command_for(report, assume_yes=assume_yes))

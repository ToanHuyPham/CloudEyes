"""Small, bounded helpers shared by discovery modules."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Safe command execution result."""

    returncode: int
    stdout: str
    stderr: str


def read_text(path: str | Path) -> str | None:
    """Read a small UTF-8 system text file, returning None on failure."""

    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, ValueError):
        return None


def run_command(args: Iterable[str], *, timeout: float = 2.0) -> CommandResult | None:
    """Run a fixed argument list without a shell and with a short timeout."""

    try:
        completed = subprocess.run(
            tuple(args),
            capture_output=True,
            check=False,
            shell=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def clean_optional(value: str | None) -> str | None:
    """Normalize an optional string."""

    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def lower_signals(values: Iterable[str | None]) -> tuple[str, ...]:
    """Normalize discovery signals for deterministic matching."""

    return tuple(
        sorted(
            {cleaned.lower() for value in values if (cleaned := clean_optional(value)) is not None}
        )
    )

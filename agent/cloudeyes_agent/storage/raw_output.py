"""Atomic persistence for privacy-safe raw benchmark evidence."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _safe_stem(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() or character in "-_" else "-" for character in value
    )
    cleaned = cleaned.strip("-")
    if not cleaned:
        raise ValueError("raw output stem must contain a safe character")
    return cleaned


def write_raw_output(
    payload: Mapping[str, Any],
    *,
    directory: str | Path,
    stem: str,
) -> Path:
    """Write one JSON evidence document atomically and return its path."""

    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / f"{_safe_stem(stem)}.json"

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-",
        suffix=".tmp",
        dir=target_directory,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target


def load_raw_output(path: str | Path) -> dict[str, Any]:
    """Load one raw benchmark evidence document."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("raw output must contain a JSON object")
    return data

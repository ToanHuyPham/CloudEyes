"""Canonical JSON and atomic file helpers used by result bundles."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON suitable for checksumming."""

    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def pretty_json_text(value: Any, *, pretty: bool = True) -> str:
    """Return stable JSON text for CLI output and receipts."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        allow_nan=False,
    )


def atomic_write_bytes(path: Path, content: bytes) -> Path:
    """Atomically replace ``path`` with ``content`` in the same filesystem."""

    output = path.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return output


def atomic_write_json(path: Path, value: Any, *, pretty: bool = True) -> Path:
    """Atomically write deterministic JSON text."""

    return atomic_write_bytes(path, (pretty_json_text(value, pretty=pretty) + "\n").encode())


__all__ = [
    "atomic_write_bytes",
    "atomic_write_json",
    "canonical_json_bytes",
    "pretty_json_text",
]

"""JSON serialization for discovery results."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def to_primitive(value: Any) -> Any:
    """Convert nested discovery values into JSON-compatible primitives."""

    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple | list):
        return [to_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_primitive(item) for key, item in value.items()}
    return value


def dumps(value: Any, *, pretty: bool = True) -> str:
    """Serialize a discovery value into deterministic JSON."""

    return json.dumps(
        to_primitive(value),
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=True,
    )


def dump(value: Any, path: str | Path, *, pretty: bool = True) -> Path:
    """Write discovery JSON atomically enough for local CLI usage."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dumps(value, pretty=pretty) + "\n", encoding="utf-8")
    return output_path

"""JSON serialization for CloudEyes data models."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def to_primitive(value: Any) -> Any:
    """Convert CloudEyes objects into JSON-compatible values."""

    if is_dataclass(value) and not isinstance(value, type):
        return {
            key: to_primitive(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, tuple | list):
        return [to_primitive(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): to_primitive(item)
            for key, item in value.items()
        }

    return value


def dumps(value: Any, *, indent: int = 2) -> str:
    """Serialize a CloudEyes object to JSON text."""

    return json.dumps(
        to_primitive(value),
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
    )


def dump(value: Any, path: str | Path, *, indent: int = 2) -> Path:
    """Serialize a CloudEyes object into a JSON file."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        dumps(value, indent=indent) + "\n",
        encoding="utf-8",
    )

    return output_path

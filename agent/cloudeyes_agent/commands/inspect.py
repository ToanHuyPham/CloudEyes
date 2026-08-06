"""Implementation of the local environment inspection command."""

from __future__ import annotations

from pathlib import Path

from ..discovery import discover_all, dump, dumps


def run_inspect(*, output: Path | None = None, pretty: bool = True) -> int:
    """Run discovery, print JSON, and optionally write the same result to disk."""

    result = discover_all()
    rendered = dumps(result, pretty=pretty)

    if output is not None:
        dump(result, output, pretty=pretty)

    print(rendered)
    return 0

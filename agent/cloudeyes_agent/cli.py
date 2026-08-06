"""Command-line interface for the CloudEyes Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .commands import run_inspect


def build_parser() -> argparse.ArgumentParser:
    """Build the public command-line parser."""

    parser = argparse.ArgumentParser(
        prog="cloudeyes",
        description="Evidence-based cloud environment inspection",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0.dev0")

    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser(
        "inspect",
        help="collect privacy-safe local system discovery data",
    )
    inspect_parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON output path",
    )
    inspect_parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CloudEyes Agent CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return run_inspect(output=args.output, pretty=not args.compact)
    raise AssertionError(f"unsupported command: {args.command}")

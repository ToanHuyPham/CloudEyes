"""Command-line interface for the CloudEyes Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .commands import run_inspect, run_profile


def build_parser() -> argparse.ArgumentParser:
    """Build the public command-line parser."""

    parser = argparse.ArgumentParser(
        prog="cloudeyes",
        description="Evidence-based cloud environment inspection and measurement",
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

    run_parser = commands.add_parser(
        "run",
        help="run a bounded measurement profile",
    )
    run_parser.add_argument("profile", choices=("general",))
    run_parser.add_argument("--output", type=Path, help="optional sample JSON output path")
    run_parser.add_argument("--quick", action="store_true", help="use the CI-sized workload")
    run_parser.add_argument(
        "--no-storage",
        action="store_true",
        help="skip the temporary-file storage benchmark",
    )
    run_parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    run_parser.add_argument("--provider-id")
    run_parser.add_argument("--provider-name")
    run_parser.add_argument("--country-code")
    run_parser.add_argument("--product")
    run_parser.add_argument("--plan")
    run_parser.add_argument("--region")
    run_parser.add_argument("--zone")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CloudEyes Agent CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return run_inspect(output=args.output, pretty=not args.compact)
    if args.command == "run":
        return run_profile(
            profile=args.profile,
            output=args.output,
            quick=args.quick,
            include_storage=not args.no_storage,
            pretty=not args.compact,
            provider_id=args.provider_id,
            provider_name=args.provider_name,
            country_code=args.country_code,
            product=args.product,
            plan=args.plan,
            region=args.region,
            zone=args.zone,
        )
    raise AssertionError(f"unsupported command: {args.command}")

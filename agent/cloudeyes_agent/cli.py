"""Command-line interface for the CloudEyes Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .commands import run_inspect, run_profile


def _worker_count(value: str) -> int:
    try:
        workers = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("workers must be an integer") from exc
    if not 0 <= workers <= 64:
        raise argparse.ArgumentTypeError("workers must be between 0 and 64")
    return workers


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
    run_parser.add_argument("profile", choices=("general", "storage", "networking", "compute"))
    run_parser.add_argument("--output", type=Path, help="optional sample JSON output path")
    run_parser.add_argument("--quick", action="store_true", help="use the CI-sized workload")
    run_parser.add_argument(
        "--no-storage",
        action="store_true",
        help="skip the temporary-file storage benchmark",
    )
    run_parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    run_parser.add_argument(
        "--work-dir",
        type=Path,
        help="filesystem path used for temporary benchmark data",
    )
    run_parser.add_argument(
        "--install-deps",
        action="store_true",
        help="install missing OS packages before the benchmark",
    )
    run_parser.add_argument(
        "--yes",
        action="store_true",
        help="approve dependency installation without prompting",
    )
    run_parser.add_argument("--provider-id")
    run_parser.add_argument("--provider-name")
    run_parser.add_argument("--country-code")
    run_parser.add_argument("--product")
    run_parser.add_argument("--plan")
    run_parser.add_argument("--region")
    run_parser.add_argument("--zone")
    run_parser.add_argument(
        "--target",
        help="HTTP(S) endpoint for the networking profile",
    )
    run_parser.add_argument(
        "--upload-target",
        help="optional HTTP(S) POST endpoint for upload throughput",
    )
    run_parser.add_argument(
        "--scope",
        choices=("public", "private"),
        default="public",
        help="network address scope allowed for the target",
    )
    run_parser.add_argument(
        "--insecure",
        action="store_true",
        help="disable TLS certificate verification for an explicitly trusted endpoint",
    )
    run_parser.add_argument(
        "--no-ping",
        action="store_true",
        help="skip optional ICMP packet-loss sampling",
    )
    run_parser.add_argument(
        "--workers",
        type=_worker_count,
        help="compute worker processes; 0 selects the bounded automatic count",
    )
    run_parser.add_argument(
        "--timeout-seconds",
        type=float,
        help="hard wall-clock deadline for the isolated profile process",
    )
    run_parser.add_argument(
        "--no-isolation",
        action="store_true",
        help="run in the CLI process for debugging; disables hard timeout enforcement",
    )
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
            install_deps=args.install_deps,
            assume_yes=args.yes,
            work_dir=args.work_dir,
            target_url=args.target,
            upload_url=args.upload_target,
            network_scope=args.scope,
            verify_tls=not args.insecure,
            enable_ping=not args.no_ping,
            workers=args.workers,
            isolated=not args.no_isolation,
            timeout_seconds=args.timeout_seconds,
        )
    raise AssertionError(f"unsupported command: {args.command}")

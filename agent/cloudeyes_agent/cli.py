"""Command-line interface for the CloudEyes Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from cloudeyes_core.models import PricingCommitment, PricingOperatingSystem

from .commands import run_analyze, run_inspect, run_profile


def _bounded_integer(name: str, value: str, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be an integer") from exc
    if not minimum <= parsed <= maximum:
        raise argparse.ArgumentTypeError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _worker_count(value: str) -> int:
    return _bounded_integer("workers", value, minimum=0, maximum=64)


def _web_request_count(value: str) -> int:
    return _bounded_integer("requests", value, minimum=1, maximum=1_000)


def _web_concurrency(value: str) -> int:
    return _bounded_integer("concurrency", value, minimum=1, maximum=64)


def _web_response_bytes(value: str) -> int:
    return _bounded_integer(
        "max-response-bytes",
        value,
        minimum=1_024,
        maximum=16 * 1024 * 1024,
    )


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
    run_parser.add_argument(
        "profile", choices=("general", "storage", "networking", "compute", "web")
    )
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
        help="HTTP(S) endpoint; required for the web profile",
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
        "--requests",
        dest="request_count",
        type=_web_request_count,
        help="bounded GET request count for the web profile",
    )
    run_parser.add_argument(
        "--concurrency",
        type=_web_concurrency,
        help="maximum concurrent GET requests for the web profile",
    )
    run_parser.add_argument(
        "--max-response-bytes",
        type=_web_response_bytes,
        help="maximum response bytes read per web request",
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

    analyze_parser = commands.add_parser(
        "analyze",
        help="build offline provider analytics from local sample JSON files",
    )
    analyze_parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="sample JSON file or directory containing sample JSON files",
    )
    analyze_parser.add_argument("--output", type=Path, help="optional analytics JSON output path")
    analyze_parser.add_argument(
        "--markdown", type=Path, help="optional human-readable Markdown output path"
    )
    analyze_parser.add_argument(
        "--expected-metric",
        action="append",
        default=[],
        help="expected metric name; repeat to declare multiple metrics",
    )
    analyze_parser.add_argument(
        "--pricing",
        action="append",
        type=Path,
        default=[],
        help="pricing catalog JSON path; repeat to load multiple catalogs",
    )
    analyze_parser.add_argument(
        "--pricing-commitment",
        choices=tuple(item.value for item in PricingCommitment),
        default=PricingCommitment.ON_DEMAND.value,
        help="commercial commitment used for normalized value comparison",
    )
    analyze_parser.add_argument(
        "--pricing-os",
        choices=tuple(item.value for item in PricingOperatingSystem),
        default=PricingOperatingSystem.LINUX.value,
        help="operating-system price family used for normalized value comparison",
    )
    analyze_parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CloudEyes Agent CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return run_inspect(output=args.output, pretty=not args.compact)
    if args.command == "analyze":
        return run_analyze(
            inputs=tuple(args.inputs),
            output=args.output,
            markdown=args.markdown,
            expected_metrics=tuple(args.expected_metric),
            pretty=not args.compact,
            pricing=tuple(args.pricing),
            pricing_commitment=PricingCommitment(args.pricing_commitment),
            pricing_operating_system=PricingOperatingSystem(args.pricing_os),
        )
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
            request_count=args.request_count,
            concurrency=args.concurrency,
            max_response_bytes=args.max_response_bytes,
            isolated=not args.no_isolation,
            timeout_seconds=args.timeout_seconds,
        )
    raise AssertionError(f"unsupported command: {args.command}")

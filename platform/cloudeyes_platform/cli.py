"""Command-line entry point for Backend Ingestion v1."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .config import DEFAULT_DATA_DIR, IngestionConfig, validate_bind_policy
from .errors import ConfigurationError
from .server import IngestionApplication, create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloudeyes-ingestion")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="run the local ingestion HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    serve.add_argument("--token-env", default="CLOUDEYES_INGEST_TOKEN")
    serve.add_argument("--allow-anonymous", action="store_true")
    serve.add_argument("--allow-insecure-network", action="store_true")
    serve.add_argument("--quarantine-payloads", action="store_true")
    return parser


def _serve(args: argparse.Namespace) -> int:
    if args.port < 0 or args.port > 65535:
        raise ConfigurationError("port must be between 0 and 65535")
    validate_bind_policy(
        args.host,
        allow_anonymous=args.allow_anonymous,
        allow_insecure_network=args.allow_insecure_network,
    )
    token = os.environ.get(args.token_env)
    if not args.allow_anonymous and not (token and token.strip()):
        raise ConfigurationError(
            f"bearer token environment variable is missing or empty: {args.token_env}"
        )
    config = IngestionConfig(
        data_dir=args.data_dir,
        quarantine_payloads=args.quarantine_payloads,
    )
    application = IngestionApplication(
        config,
        token=token,
        allow_anonymous=args.allow_anonymous,
    )
    server = create_server(application, host=args.host, port=args.port)
    address, port = server.server_address[:2]
    print(
        json.dumps(
            {
                "anonymous": args.allow_anonymous,
                "data_dir": str(config.data_dir),
                "host": address,
                "port": port,
                "status": "ready",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            return _serve(args)
    except (ConfigurationError, ValueError) as error:
        print(f"cloudeyes-ingestion: error: {error}", file=sys.stderr)
        return 2
    parser.error("unsupported command")
    return 2


__all__ = ["build_parser", "main"]

"""Explicit submission command for verified CloudEyes result bundles."""

from __future__ import annotations

from pathlib import Path

from cloudeyes_core.serialization import to_primitive

from ..bundle import (
    BundleVerificationError,
    SubmissionError,
    submission_plan,
    submit_bundle,
    token_from_environment,
)
from ..bundle.jsonutil import atomic_write_json, pretty_json_text


def run_submit(
    *,
    bundle: Path,
    endpoint: str,
    receipt: Path | None,
    token_environment: str,
    anonymous: bool,
    allow_http: bool,
    dry_run: bool,
    timeout_seconds: float,
    pretty: bool,
) -> int:
    """Verify and submit one result bundle, or print a network-free dry run."""

    try:
        token = None if anonymous else token_from_environment(token_environment)
        if not anonymous and token is None and not dry_run:
            raise SubmissionError(
                f"submission token is missing from environment variable {token_environment}; "
                "use --anonymous only when the endpoint explicitly accepts anonymous bundles"
            )
        if dry_run:
            plan = submission_plan(
                bundle,
                endpoint=endpoint,
                allow_http=allow_http,
                authenticated=token is not None,
            )
            print(pretty_json_text(plan, pretty=pretty))
            return 0

        result = submit_bundle(
            bundle,
            endpoint=endpoint,
            token=token,
            allow_http=allow_http,
            timeout_seconds=timeout_seconds,
        )
        primitive = to_primitive(result)
        if receipt is not None:
            atomic_write_json(receipt, primitive, pretty=True)
        print(pretty_json_text(primitive, pretty=pretty))
        return 0 if result.accepted else 8
    except (
        BundleVerificationError,
        FileNotFoundError,
        OSError,
        SubmissionError,
        TypeError,
        ValueError,
    ) as error:
        print(f"CloudEyes submission failed: {error}")
        return 8


__all__ = ["run_submit"]

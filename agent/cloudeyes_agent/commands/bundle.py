"""CLI commands for building and verifying CloudEyes result bundles."""

from __future__ import annotations

from pathlib import Path

from cloudeyes_core.serialization import to_primitive

from ..bundle import (
    BundleBuildError,
    BundleVerificationError,
    build_bundle,
    verify_bundle,
)
from ..bundle.jsonutil import pretty_json_text


def run_bundle(
    *,
    inputs: tuple[Path, ...],
    output: Path,
    raw_root: Path | None,
    allow_invalid_samples: bool,
    allow_missing_raw: bool,
    pretty: bool,
) -> int:
    """Build one integrity-protected result bundle from local sample JSON files."""

    try:
        manifest = build_bundle(
            inputs,
            output=output,
            raw_root=raw_root,
            allow_invalid_samples=allow_invalid_samples,
            allow_missing_raw=allow_missing_raw,
        )
        summary = {
            "bundle_id": manifest["bundle_id"],
            "file_count": len(manifest["files"]),
            "output": str(output),
            "sample_count": manifest["sample_count"],
            "warnings": manifest["warnings"],
        }
        print(pretty_json_text(summary, pretty=pretty))
        return 0
    except (BundleBuildError, FileNotFoundError, OSError, TypeError, ValueError) as error:
        print(f"CloudEyes bundle creation failed: {error}")
        return 6


def run_verify_bundle(*, bundle: Path, pretty: bool) -> int:
    """Verify bundle structure, checksums, and sample semantics."""

    try:
        verification = verify_bundle(bundle)
        print(pretty_json_text(to_primitive(verification), pretty=pretty))
        return 0
    except (BundleVerificationError, FileNotFoundError, OSError) as error:
        print(f"CloudEyes bundle verification failed: {error}")
        return 7


__all__ = ["run_bundle", "run_verify_bundle"]

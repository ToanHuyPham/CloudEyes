"""Test helpers for creating deterministic CloudEyes result bundles."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from cloudeyes_agent.bundle.builder import build_bundle
from cloudeyes_platform.ingestion import MEDIA_TYPE

ROOT = Path(__file__).resolve().parents[1]


def build_test_bundle(
    tmp_path: Path,
    *,
    name: str = "bundle.zip",
    sample_name: str = "general-profile-sample.json",
    created_at: datetime | None = None,
) -> tuple[Path, dict[str, str]]:
    output = tmp_path / name
    manifest = build_bundle(
        (ROOT / "examples" / sample_name,),
        output=output,
        created_at=created_at or datetime(2026, 8, 6, 12, 0, tzinfo=UTC),
    )
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return output, {
        "Content-Type": MEDIA_TYPE,
        "Idempotency-Key": digest,
        "User-Agent": "CloudEyes-Test/1",
        "X-CloudEyes-Bundle-Id": str(manifest["bundle_id"]),
        "X-CloudEyes-Bundle-SHA256": digest,
    }

"""Privacy-conscious quarantine metadata for rejected bundles."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

_SAFE_HEADERS = {
    "content-type",
    "idempotency-key",
    "x-cloudeyes-bundle-id",
    "x-cloudeyes-bundle-sha256",
    "user-agent",
}


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class QuarantineStore:
    """Store rejection metadata and optionally retain the rejected payload."""

    def __init__(self, root: Path, *, retain_payloads: bool) -> None:
        self.root = root
        self.retain_payloads = retain_payloads
        self.root.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        payload: Path,
        *,
        reason_code: str,
        message: str,
        headers: Mapping[str, str],
        received_at: datetime,
    ) -> str:
        digest = _sha256_path(payload)
        timestamp = received_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        quarantine_id = f"quarantine-{timestamp}-{digest[:16]}"
        safe_headers = {
            key.casefold(): value[:512]
            for key, value in headers.items()
            if key.casefold() in _SAFE_HEADERS
        }
        metadata: dict[str, object] = {
            "bundle_sha256": digest,
            "headers": dict(sorted(safe_headers.items())),
            "message": message[:512],
            "payload_retained": self.retain_payloads,
            "reason_code": reason_code,
            "received_at": received_at.isoformat(),
            "request_size_bytes": payload.stat().st_size,
            "schema_version": "1.0.0",
        }
        if self.retain_payloads:
            payload_dir = self.root / "payloads"
            payload_dir.mkdir(parents=True, exist_ok=True)
            destination = payload_dir / f"{digest}.zip"
            if not destination.exists():
                shutil.copyfile(payload, destination)
                try:
                    destination.chmod(0o600)
                except OSError:
                    pass
            metadata["payload_path"] = f"payloads/{destination.name}"
        _atomic_json(self.root / f"{quarantine_id}.json", metadata)
        return quarantine_id


__all__ = ["QuarantineStore"]

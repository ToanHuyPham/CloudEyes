"""Build integrity-protected CloudEyes result bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cloudeyes_core.serialization import sample_from_dict, to_primitive
from cloudeyes_core.validation import validate_sample

from .. import __version__
from ..sample.redaction import redact_json
from .jsonutil import canonical_json_bytes

BUNDLE_SCHEMA_VERSION = "1.0.0"
MAX_SAMPLE_BYTES = 4 * 1024 * 1024
MAX_RAW_EVIDENCE_BYTES = 16 * 1024 * 1024
MAX_BUNDLE_PAYLOAD_BYTES = 128 * 1024 * 1024
MAX_SAMPLE_COUNT = 1_000
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class BundleBuildError(ValueError):
    """Raised when local samples cannot form a safe result bundle."""


def sha256_bytes(content: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(content).hexdigest()


def _safe_basename(value: str, *, fallback: str) -> str:
    cleaned = _SAFE_NAME.sub("-", Path(value).name).strip("-.")
    return (cleaned or fallback)[:96]


def _sample_inputs(inputs: Iterable[Path]) -> tuple[Path, ...]:
    paths: dict[Path, None] = {}
    for raw_path in inputs:
        path = raw_path.expanduser()
        if not path.exists():
            raise FileNotFoundError(f"bundle input does not exist: {path}")
        candidates = (path,) if path.is_file() else tuple(sorted(path.glob("*.json")))
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.casefold() == ".json":
                paths[candidate.resolve()] = None
    if not paths:
        raise BundleBuildError("no JSON sample files were found")
    if len(paths) > MAX_SAMPLE_COUNT:
        raise BundleBuildError(f"bundle sample count exceeds {MAX_SAMPLE_COUNT}")
    return tuple(paths)


def _load_json_object(path: Path, *, maximum_bytes: int, label: str) -> dict[str, Any]:
    size = path.stat().st_size
    if size > maximum_bytes:
        raise BundleBuildError(f"{label} exceeds {maximum_bytes} bytes: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleBuildError(f"cannot read {label} as UTF-8 JSON: {path}: {error}") from error
    if not isinstance(value, dict):
        raise BundleBuildError(f"{label} must contain a JSON object: {path}")
    return value


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_raw_path(
    raw_path: str,
    *,
    sample_path: Path,
    raw_root: Path | None,
) -> Path | None:
    requested = Path(raw_path).expanduser()
    allowed_roots = {Path.cwd().resolve(), sample_path.parent.resolve()}
    candidates: list[Path] = []
    if raw_root is not None:
        resolved_root = raw_root.expanduser().resolve()
        allowed_roots.add(resolved_root)
        candidates.extend((resolved_root / requested, resolved_root / requested.name))
    if requested.is_absolute():
        candidates.append(requested)
    else:
        candidates.extend(
            (
                Path.cwd() / requested,
                sample_path.parent / requested,
                sample_path.parent / "raw" / requested.name,
            )
        )

    for candidate in candidates:
        resolved = candidate.resolve()
        if not any(_is_within(resolved, root) for root in allowed_roots):
            continue
        if resolved.is_file():
            return resolved
    return None


def _file_entry(
    *,
    path: str,
    content: bytes,
    media_type: str,
    redaction_count: int = 0,
) -> dict[str, Any]:
    return {
        "media_type": media_type,
        "path": path,
        "redaction_count": redaction_count,
        "sha256": sha256_bytes(content),
        "size_bytes": len(content),
    }


def _bundle_id(files: list[dict[str, Any]]) -> str:
    identity = [
        {"path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]}
        for item in sorted(files, key=lambda item: item["path"])
    ]
    return f"bundle-{sha256_bytes(canonical_json_bytes(identity))[:24]}"


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _write_bundle(path: Path, payloads: dict[str, bytes], manifest: bytes) -> None:
    output = path.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            archive.writestr(_zip_info("manifest.json"), manifest)
            for name in sorted(payloads):
                archive.writestr(_zip_info(name), payloads[name])
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def build_bundle(
    inputs: tuple[Path, ...],
    *,
    output: Path,
    raw_root: Path | None = None,
    allow_invalid_samples: bool = False,
    allow_missing_raw: bool = False,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Validate samples, include referenced evidence, and write one ZIP bundle."""

    input_paths = _sample_inputs(inputs)
    payloads: dict[str, bytes] = {}
    file_entries: list[dict[str, Any]] = []
    sample_entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_sample_ids: set[str] = set()
    total_bytes = 0

    loaded: list[tuple[str, Path, Any, dict[str, Any], tuple[str, ...]]] = []
    for sample_path in input_paths:
        data = _load_json_object(sample_path, maximum_bytes=MAX_SAMPLE_BYTES, label="sample")
        try:
            sample = sample_from_dict(data)
        except (KeyError, TypeError, ValueError) as error:
            raise BundleBuildError(f"invalid sample structure: {sample_path}: {error}") from error
        canonical_value = to_primitive(sample)
        if data != canonical_value:
            raise BundleBuildError(f"sample contains missing or unsupported fields: {sample_path}")
        validation = validate_sample(sample)
        if not validation.valid and not allow_invalid_samples:
            raise BundleBuildError(
                f"sample {sample.sample_id} is invalid: {'; '.join(validation.errors)}"
            )
        if sample.sample_id in seen_sample_ids:
            raise BundleBuildError(f"duplicate sample ID: {sample.sample_id}")
        seen_sample_ids.add(sample.sample_id)
        if not validation.valid:
            warnings.append(f"invalid_sample_included:{sample.sample_id}")
        loaded.append(
            (
                sample.sample_id,
                sample_path,
                sample,
                canonical_value,
                tuple(validation.warnings),
            )
        )

    for index, (sample_id, sample_path, sample, canonical_value, validation_warnings) in enumerate(
        sorted(loaded, key=lambda item: item[0]),
        start=1,
    ):
        sample_name = f"samples/{index:04d}.json"
        sample_content = canonical_json_bytes(canonical_value)
        payloads[sample_name] = sample_content
        sample_file_entry = _file_entry(
            path=sample_name,
            content=sample_content,
            media_type="application/vnd.cloudeyes.sample+json",
        )
        file_entries.append(sample_file_entry)
        total_bytes += len(sample_content)

        raw_bundle_paths: list[str] = []
        raw_references = tuple(
            dict.fromkeys(
                measurement.raw_output_path
                for measurement in sample.measurements
                if measurement.raw_output_path is not None
            )
        )
        for raw_index, raw_reference in enumerate(raw_references, start=1):
            resolved = _resolve_raw_path(
                raw_reference,
                sample_path=sample_path,
                raw_root=raw_root,
            )
            if resolved is None:
                message = f"missing_raw_evidence:{sample_id}:{Path(raw_reference).name}"
                if allow_missing_raw:
                    warnings.append(message)
                    continue
                raise BundleBuildError(
                    f"referenced raw evidence was not found for {sample_id}: {raw_reference}"
                )
            raw_value = _load_json_object(
                resolved,
                maximum_bytes=MAX_RAW_EVIDENCE_BYTES,
                label="raw evidence",
            )
            redacted = redact_json(raw_value)
            raw_content = canonical_json_bytes(redacted.value)
            raw_name = _safe_basename(
                resolved.name,
                fallback=f"evidence-{raw_index:02d}.json",
            )
            bundle_path = f"raw/{index:04d}/{raw_index:02d}-{raw_name}"
            payloads[bundle_path] = raw_content
            file_entries.append(
                _file_entry(
                    path=bundle_path,
                    content=raw_content,
                    media_type="application/vnd.cloudeyes.raw-evidence+json",
                    redaction_count=redacted.redaction_count,
                )
            )
            raw_bundle_paths.append(bundle_path)
            total_bytes += len(raw_content)
            if redacted.redaction_count:
                warnings.append(
                    f"raw_evidence_redacted:{sample_id}:{raw_index}:{redacted.redaction_count}"
                )

        sample_entries.append(
            {
                "profile": sample.protocol.profile,
                "raw_evidence_paths": raw_bundle_paths,
                "sample_id": sample_id,
                "sample_path": sample_name,
                "validation_warnings": list(validation_warnings),
            }
        )

    if total_bytes > MAX_BUNDLE_PAYLOAD_BYTES:
        raise BundleBuildError(f"bundle payload exceeds {MAX_BUNDLE_PAYLOAD_BYTES} bytes")

    generated_at = created_at or datetime.now(UTC)
    if generated_at.tzinfo is None:
        raise BundleBuildError("created_at must contain timezone information")
    manifest = {
        "agent_version": __version__,
        "bundle_id": _bundle_id(file_entries),
        "created_at": generated_at.isoformat(),
        "files": sorted(file_entries, key=lambda item: item["path"]),
        "policy": {
            "allow_invalid_samples": allow_invalid_samples,
            "allow_missing_raw": allow_missing_raw,
            "raw_evidence_redaction": "credential-keys-and-url-secrets-v1",
        },
        "sample_count": len(sample_entries),
        "samples": sample_entries,
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "warnings": list(dict.fromkeys(warnings)),
    }
    manifest_bytes = canonical_json_bytes(manifest)
    _write_bundle(output, payloads, manifest_bytes)
    return manifest


__all__ = [
    "BUNDLE_SCHEMA_VERSION",
    "BundleBuildError",
    "build_bundle",
    "sha256_bytes",
]

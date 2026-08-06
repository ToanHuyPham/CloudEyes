"""Verify result-bundle ZIP structure, checksums, and sample semantics."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from cloudeyes_core.serialization import loads_sample
from cloudeyes_core.validation import validate_sample

from .builder import (
    BUNDLE_SCHEMA_VERSION,
    MAX_BUNDLE_PAYLOAD_BYTES,
    _bundle_id,
    sha256_bytes,
)
from .model import BundleVerification

MAX_ARCHIVE_FILES = 2_100
MAX_MANIFEST_BYTES = 1024 * 1024


class BundleVerificationError(ValueError):
    """Raised when a bundle is malformed, tampered with, or semantically invalid."""


def _safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and "\\" not in name
        and not path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() == name
    )


def _required_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BundleVerificationError(f"manifest field {field} must be an object")
    return value


def _required_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise BundleVerificationError(f"manifest field {field} must be an array")
    return value


def _validate_manifest_shape(manifest: dict[str, Any]) -> None:
    required = {
        "agent_version",
        "bundle_id",
        "created_at",
        "files",
        "policy",
        "sample_count",
        "samples",
        "schema_version",
        "warnings",
    }
    if set(manifest) != required:
        raise BundleVerificationError("manifest contains missing or unsupported fields")
    if manifest["schema_version"] != BUNDLE_SCHEMA_VERSION:
        raise BundleVerificationError(
            f"unsupported bundle schema version: {manifest['schema_version']}"
        )
    if not isinstance(manifest["bundle_id"], str) or not manifest["bundle_id"]:
        raise BundleVerificationError("manifest bundle_id must be a non-empty string")
    if not isinstance(manifest["sample_count"], int) or manifest["sample_count"] < 1:
        raise BundleVerificationError("manifest sample_count must be a positive integer")
    _required_mapping(manifest["policy"], "policy")
    samples = _required_list(manifest["samples"], "samples")
    files = _required_list(manifest["files"], "files")
    warnings = _required_list(manifest["warnings"], "warnings")
    if manifest["sample_count"] != len(samples):
        raise BundleVerificationError("manifest sample_count does not match samples")
    if not all(isinstance(item, str) for item in warnings):
        raise BundleVerificationError("manifest warnings must contain strings")
    if not files:
        raise BundleVerificationError("manifest must list at least one payload file")


def _archive_entries(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_FILES:
        raise BundleVerificationError("bundle contains too many archive entries")
    entries: dict[str, zipfile.ZipInfo] = {}
    total_size = 0
    for info in infos:
        if not _safe_archive_name(info.filename):
            raise BundleVerificationError(f"unsafe archive path: {info.filename}")
        if info.filename in entries:
            raise BundleVerificationError(f"duplicate archive path: {info.filename}")
        if info.flag_bits & 0x1:
            raise BundleVerificationError("encrypted bundle entries are not supported")
        file_type = (info.external_attr >> 16) & 0o170000
        if file_type == 0o120000:
            raise BundleVerificationError("symbolic links are not allowed in bundles")
        if info.is_dir():
            raise BundleVerificationError("directory entries are not allowed in bundles")
        total_size += info.file_size
        if total_size > MAX_BUNDLE_PAYLOAD_BYTES + MAX_MANIFEST_BYTES:
            raise BundleVerificationError("bundle uncompressed size exceeds the safety limit")
        entries[info.filename] = info
    return entries


def verify_bundle(path: Path) -> BundleVerification:
    """Verify one result bundle and return a privacy-safe summary."""

    bundle_path = path.expanduser()
    if not bundle_path.is_file():
        raise FileNotFoundError(f"bundle does not exist: {bundle_path}")
    bundle_bytes = bundle_path.read_bytes()
    bundle_sha256 = sha256_bytes(bundle_bytes)

    try:
        with zipfile.ZipFile(bundle_path, mode="r") as archive:
            entries = _archive_entries(archive)
            manifest_info = entries.get("manifest.json")
            if manifest_info is None:
                raise BundleVerificationError("bundle does not contain manifest.json")
            if manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise BundleVerificationError("bundle manifest exceeds the safety limit")
            try:
                manifest_value = json.loads(archive.read(manifest_info).decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise BundleVerificationError("bundle manifest is not valid UTF-8 JSON") from error
            manifest = _required_mapping(manifest_value, "root")
            _validate_manifest_shape(manifest)

            file_entries = _required_list(manifest["files"], "files")
            listed_paths: set[str] = set()
            normalized_file_entries: list[dict[str, Any]] = []
            for raw_entry in file_entries:
                entry = _required_mapping(raw_entry, "files[]")
                required_file_fields = {
                    "media_type",
                    "path",
                    "redaction_count",
                    "sha256",
                    "size_bytes",
                }
                if set(entry) != required_file_fields:
                    raise BundleVerificationError("manifest file entry has unsupported fields")
                archive_path = entry.get("path")
                if not isinstance(archive_path, str) or not _safe_archive_name(archive_path):
                    raise BundleVerificationError("manifest contains an unsafe file path")
                if archive_path == "manifest.json" or archive_path in listed_paths:
                    raise BundleVerificationError(f"duplicate manifest file path: {archive_path}")
                listed_paths.add(archive_path)
                info = entries.get(archive_path)
                if info is None:
                    raise BundleVerificationError(f"listed bundle file is missing: {archive_path}")
                content = archive.read(info)
                if entry.get("size_bytes") != len(content):
                    raise BundleVerificationError(f"size mismatch for {archive_path}")
                if entry.get("sha256") != sha256_bytes(content):
                    raise BundleVerificationError(f"checksum mismatch for {archive_path}")
                redaction_count = entry.get("redaction_count")
                if not isinstance(redaction_count, int) or redaction_count < 0:
                    raise BundleVerificationError(f"invalid redaction_count for {archive_path}")
                normalized_file_entries.append(entry)

            archive_payloads = set(entries) - {"manifest.json"}
            if archive_payloads != listed_paths:
                raise BundleVerificationError("bundle contains unlisted payload files")
            if manifest["bundle_id"] != _bundle_id(normalized_file_entries):
                raise BundleVerificationError("bundle_id does not match payload checksums")

            policy = _required_mapping(manifest["policy"], "policy")
            allow_invalid = policy.get("allow_invalid_samples") is True
            warnings = [str(item) for item in manifest["warnings"]]
            seen_sample_ids: set[str] = set()
            referenced_sample_paths: set[str] = set()
            referenced_raw_paths: set[str] = set()
            for raw_sample_entry in _required_list(manifest["samples"], "samples"):
                sample_entry = _required_mapping(raw_sample_entry, "samples[]")
                required_sample_fields = {
                    "profile",
                    "raw_evidence_paths",
                    "sample_id",
                    "sample_path",
                    "validation_warnings",
                }
                if set(sample_entry) != required_sample_fields:
                    raise BundleVerificationError("manifest sample entry has unsupported fields")
                sample_id = sample_entry.get("sample_id")
                sample_path = sample_entry.get("sample_path")
                if not isinstance(sample_id, str) or not sample_id:
                    raise BundleVerificationError("manifest sample_id must be non-empty")
                if sample_id in seen_sample_ids:
                    raise BundleVerificationError(f"duplicate sample ID in manifest: {sample_id}")
                seen_sample_ids.add(sample_id)
                if not isinstance(sample_path, str) or sample_path not in listed_paths:
                    raise BundleVerificationError(f"sample payload is missing for {sample_id}")
                referenced_sample_paths.add(sample_path)
                try:
                    sample = loads_sample(archive.read(sample_path).decode("utf-8"))
                except (KeyError, TypeError, UnicodeError, ValueError) as error:
                    raise BundleVerificationError(
                        f"sample payload is invalid for {sample_id}: {error}"
                    ) from error
                if sample.sample_id != sample_id:
                    raise BundleVerificationError(f"sample ID mismatch for {sample_path}")
                if sample.protocol.profile != sample_entry.get("profile"):
                    raise BundleVerificationError(f"sample profile mismatch for {sample_id}")
                validation = validate_sample(sample)
                if not validation.valid and not allow_invalid:
                    raise BundleVerificationError(
                        f"sample {sample_id} failed semantic validation: "
                        f"{'; '.join(validation.errors)}"
                    )
                warnings.extend(validation.warnings)

                raw_paths = _required_list(
                    sample_entry.get("raw_evidence_paths"),
                    "raw_evidence_paths",
                )
                for raw_path in raw_paths:
                    if not isinstance(raw_path, str) or raw_path not in listed_paths:
                        raise BundleVerificationError(
                            f"raw evidence payload is missing for {sample_id}"
                        )
                    if not raw_path.startswith("raw/"):
                        raise BundleVerificationError(
                            f"raw evidence path is outside raw/ for {sample_id}"
                        )
                    referenced_raw_paths.add(raw_path)
                    try:
                        raw_value = json.loads(archive.read(raw_path).decode("utf-8"))
                    except (UnicodeError, json.JSONDecodeError) as error:
                        raise BundleVerificationError(
                            f"raw evidence is not valid UTF-8 JSON: {raw_path}"
                        ) from error
                    if not isinstance(raw_value, dict):
                        raise BundleVerificationError(
                            f"raw evidence must contain a JSON object: {raw_path}"
                        )

            sample_payloads = {path for path in listed_paths if path.startswith("samples/")}
            raw_payloads = {path for path in listed_paths if path.startswith("raw/")}
            if sample_payloads != referenced_sample_paths:
                raise BundleVerificationError("bundle contains unreferenced sample payloads")
            if raw_payloads != referenced_raw_paths:
                raise BundleVerificationError("bundle contains unreferenced raw evidence")
    except zipfile.BadZipFile as error:
        raise BundleVerificationError("bundle is not a valid ZIP archive") from error

    return BundleVerification(
        bundle_id=manifest["bundle_id"],
        bundle_sha256=bundle_sha256,
        sample_count=manifest["sample_count"],
        file_count=len(manifest["files"]),
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = ["BundleVerificationError", "verify_bundle"]

"""Fail-closed bundle validation, deduplication, quarantine, and persistence."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cloudeyes_agent.bundle.jsonutil import canonical_json_bytes
from cloudeyes_agent.bundle.verification import BundleVerificationError, verify_bundle
from cloudeyes_core.serialization import loads_sample, to_primitive

from .config import IngestionConfig
from .errors import IngestionError
from .models import IngestionReceipt, SampleRecord
from .quarantine import QuarantineStore
from .repository import IngestionRepository
from .storage import BundleStore

MEDIA_TYPE = "application/vnd.cloudeyes.bundle+zip; version=1"
_HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.casefold()
    for key, value in headers.items():
        if key.casefold() == wanted:
            return value.strip()
    return None


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _required_digest(value: str | None, field: str) -> str:
    if value is None or not _HEX_SHA256.fullmatch(value):
        raise IngestionError(
            status_code=400,
            code="invalid_request_digest",
            message=f"{field} must be a 64-character SHA-256 digest",
        )
    return value.casefold()


def _required_bundle_id(value: str | None) -> str:
    if value is None or not value or len(value) > 256:
        raise IngestionError(
            status_code=400,
            code="invalid_bundle_id",
            message="X-CloudEyes-Bundle-Id must be a non-empty value of at most 256 characters",
        )
    return value


def _manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    value = json.loads(archive.read("manifest.json").decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest must be an object")
    return value


class IngestionPipeline:
    """Ingest one already-bounded request body into local durable storage."""

    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.config.prepare()
        self.repository = IngestionRepository(config.database_path)
        self.bundle_store = BundleStore(config.bundle_dir)
        self.quarantine = QuarantineStore(
            config.quarantine_dir,
            retain_payloads=config.quarantine_payloads,
        )

    def _reject_and_quarantine(
        self,
        payload: Path,
        *,
        headers: Mapping[str, str],
        received_at: datetime,
        code: str,
        message: str,
    ) -> IngestionError:
        error = IngestionError(
            status_code=400,
            code=code,
            message=message,
            quarantine=True,
        )
        try:
            error.quarantine_id = self.quarantine.record(
                payload,
                reason_code=code,
                message=message,
                headers=headers,
                received_at=received_at,
            )
        except OSError:
            error.quarantine_id = None
        return error

    def ingest(
        self,
        payload: Path,
        *,
        headers: Mapping[str, str],
        received_at: datetime | None = None,
    ) -> IngestionReceipt:
        """Validate and persist one result bundle."""

        timestamp = received_at or datetime.now(UTC)
        if timestamp.tzinfo is None:
            raise ValueError("received_at must contain timezone information")
        size = payload.stat().st_size
        if size <= 0:
            raise IngestionError(
                status_code=400,
                code="empty_request_body",
                message="submission body must not be empty",
            )
        if size > self.config.max_request_bytes:
            raise IngestionError(
                status_code=413,
                code="request_too_large",
                message=f"submission exceeds {self.config.max_request_bytes} bytes",
            )

        content_type = _header(headers, "Content-Type")
        if content_type != MEDIA_TYPE:
            raise IngestionError(
                status_code=415,
                code="unsupported_media_type",
                message=f"Content-Type must be {MEDIA_TYPE}",
            )
        idempotency_key = _required_digest(_header(headers, "Idempotency-Key"), "Idempotency-Key")
        claimed_sha256 = _required_digest(
            _header(headers, "X-CloudEyes-Bundle-SHA256"),
            "X-CloudEyes-Bundle-SHA256",
        )
        claimed_bundle_id = _required_bundle_id(_header(headers, "X-CloudEyes-Bundle-Id"))
        if idempotency_key != claimed_sha256:
            raise IngestionError(
                status_code=409,
                code="idempotency_digest_conflict",
                message="Idempotency-Key must equal X-CloudEyes-Bundle-SHA256",
            )

        actual_sha256 = _sha256_path(payload)
        if actual_sha256 != claimed_sha256:
            raise self._reject_and_quarantine(
                payload,
                headers=headers,
                received_at=timestamp,
                code="bundle_digest_mismatch",
                message="request body SHA-256 does not match the declared digest",
            )

        existing_key = self.repository.by_idempotency_key(idempotency_key)
        if existing_key is not None:
            if existing_key.bundle_sha256 != actual_sha256:
                raise IngestionError(
                    status_code=409,
                    code="idempotency_key_reused",
                    message="Idempotency-Key was already used for different content",
                )
            return existing_key
        existing_bundle = self.repository.by_bundle_sha256(actual_sha256)
        if existing_bundle is not None:
            return existing_bundle

        try:
            verification = verify_bundle(payload)
            with zipfile.ZipFile(payload) as archive:
                manifest = _manifest(archive)
                if verification.bundle_id != claimed_bundle_id:
                    raise ValueError("declared bundle ID does not match the verified manifest")
                submission_id = f"submission-{actual_sha256[:24]}"
                file_entries = {str(item["path"]): item for item in manifest["files"]}
                sample_records: list[SampleRecord] = []
                evidence_records: list[tuple[str, str, str, int, str]] = []
                for entry in manifest["samples"]:
                    sample_path = str(entry["sample_path"])
                    sample_bytes = archive.read(sample_path)
                    sample = loads_sample(sample_bytes.decode("utf-8"))
                    canonical = canonical_json_bytes(to_primitive(sample))
                    if canonical != sample_bytes:
                        raise ValueError(f"sample payload is not canonical: {sample_path}")
                    file_entry = file_entries[sample_path]
                    raw_paths = tuple(str(item) for item in entry["raw_evidence_paths"])
                    sample_records.append(
                        SampleRecord(
                            sample_id=sample.sample_id,
                            submission_id=submission_id,
                            sample_path=sample_path,
                            sample_sha256=str(file_entry["sha256"]),
                            sample_json=sample_bytes.decode("utf-8"),
                            profile=sample.protocol.profile,
                            provider_id=sample.provider.provider_id,
                            provider_name=sample.provider.name,
                            country_code=sample.provider.country_code,
                            product=sample.product.product,
                            plan=sample.product.plan,
                            region=sample.product.region,
                            zone=sample.product.zone,
                            machine_type=sample.machine.machine_type,
                            cpu_count=sample.machine.cpu_count,
                            memory_bytes=sample.machine.memory_bytes,
                            architecture=sample.machine.architecture,
                            protocol_version=sample.protocol.version,
                            protocol_fingerprint=sample.protocol.fingerprint,
                            quality_status=sample.quality.status.value,
                            created_at=sample.created_at.isoformat(),
                            raw_evidence_count=len(raw_paths),
                        )
                    )
                    for raw_path in raw_paths:
                        raw_file = file_entries[raw_path]
                        evidence_records.append(
                            (
                                sample.sample_id,
                                raw_path,
                                str(raw_file["sha256"]),
                                int(raw_file["size_bytes"]),
                                str(raw_file["media_type"]),
                            )
                        )
        except (
            BundleVerificationError,
            KeyError,
            OSError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
            zipfile.BadZipFile,
        ) as error:
            raise self._reject_and_quarantine(
                payload,
                headers=headers,
                received_at=timestamp,
                code="invalid_bundle",
                message=f"bundle verification failed: {error}",
            ) from error

        conflicts = self.repository.existing_sample_ids(
            [sample.sample_id for sample in sample_records]
        )
        if conflicts:
            raise IngestionError(
                status_code=409,
                code="sample_already_ingested",
                message=f"sample IDs already exist: {', '.join(conflicts[:10])}",
            )

        receipt = IngestionReceipt(
            schema_version="1.0.0",
            submission_id=submission_id,
            status="accepted",
            received_at=timestamp,
            bundle_id=verification.bundle_id,
            bundle_sha256=verification.bundle_sha256,
            sample_count=verification.sample_count,
            file_count=verification.file_count,
            warnings=verification.warnings,
        )
        stored_path: Path | None = None
        created = False
        try:
            stored_path, created = self.bundle_store.put(payload, actual_sha256)
            self.repository.persist(
                receipt=receipt,
                idempotency_key=idempotency_key,
                bundle_path=str(stored_path.relative_to(self.config.data_dir)),
                agent_version=str(manifest["agent_version"]),
                bundle_created_at=str(manifest["created_at"]),
                samples=sample_records,
                evidence=evidence_records,
            )
        except sqlite3.IntegrityError as error:
            duplicate = self.repository.by_bundle_sha256(actual_sha256)
            if duplicate is not None:
                return duplicate
            if created and stored_path is not None:
                stored_path.unlink(missing_ok=True)
            raise IngestionError(
                status_code=409,
                code="ingestion_conflict",
                message="bundle conflicts with existing persisted data",
            ) from error
        except BaseException:
            if created and stored_path is not None:
                stored_path.unlink(missing_ok=True)
            raise
        return receipt


__all__ = ["MEDIA_TYPE", "IngestionPipeline"]

"""SQLite persistence for accepted bundles and canonical samples."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from .models import IngestionReceipt, SampleRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    submission_id TEXT PRIMARY KEY,
    bundle_id TEXT NOT NULL,
    bundle_sha256 TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    received_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'accepted'),
    sample_count INTEGER NOT NULL CHECK (sample_count > 0),
    file_count INTEGER NOT NULL CHECK (file_count > 0),
    warnings_json TEXT NOT NULL,
    bundle_path TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    bundle_created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    sample_path TEXT NOT NULL,
    sample_sha256 TEXT NOT NULL,
    sample_json TEXT NOT NULL,
    profile TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    country_code TEXT,
    product TEXT,
    plan TEXT,
    region TEXT,
    zone TEXT,
    machine_type TEXT NOT NULL,
    cpu_count INTEGER NOT NULL CHECK (cpu_count > 0),
    memory_bytes INTEGER NOT NULL CHECK (memory_bytes > 0),
    architecture TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    protocol_fingerprint TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_evidence_count INTEGER NOT NULL CHECK (raw_evidence_count >= 0)
);

CREATE TABLE IF NOT EXISTS evidence (
    submission_id TEXT NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    sample_id TEXT NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE,
    archive_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    media_type TEXT NOT NULL,
    PRIMARY KEY (submission_id, archive_path)
);

CREATE INDEX IF NOT EXISTS idx_samples_provider_profile
ON samples(provider_id, profile, protocol_version, protocol_fingerprint);
"""


class IngestionRepository:
    """Small transactional repository with one SQLite connection per operation."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.executescript(_SCHEMA)
        try:
            self.database_path.chmod(0o600)
        except OSError:
            pass

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _receipt_from_row(row: sqlite3.Row, *, duplicate: bool) -> IngestionReceipt:
        from datetime import datetime

        submission_id = str(row["submission_id"])
        return IngestionReceipt(
            schema_version="1.0.0",
            submission_id=submission_id,
            status="duplicate" if duplicate else str(row["status"]),
            received_at=datetime.fromisoformat(str(row["received_at"])),
            bundle_id=str(row["bundle_id"]),
            bundle_sha256=str(row["bundle_sha256"]),
            sample_count=int(row["sample_count"]),
            file_count=int(row["file_count"]),
            warnings=tuple(json.loads(str(row["warnings_json"]))),
            duplicate_of=submission_id if duplicate else None,
        )

    def by_idempotency_key(self, key: str) -> IngestionReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM submissions WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
        return None if row is None else self._receipt_from_row(row, duplicate=True)

    def by_bundle_sha256(self, digest: str) -> IngestionReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM submissions WHERE bundle_sha256 = ?",
                (digest,),
            ).fetchone()
        return None if row is None else self._receipt_from_row(row, duplicate=True)

    def existing_sample_ids(self, sample_ids: Sequence[str]) -> tuple[str, ...]:
        if not sample_ids:
            return ()
        placeholders = ",".join("?" for _ in sample_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT sample_id FROM samples WHERE sample_id IN ({placeholders})",  # noqa: S608
                tuple(sample_ids),
            ).fetchall()
        return tuple(sorted(str(row["sample_id"]) for row in rows))

    def persist(
        self,
        *,
        receipt: IngestionReceipt,
        idempotency_key: str,
        bundle_path: str,
        agent_version: str,
        bundle_created_at: str,
        samples: Sequence[SampleRecord],
        evidence: Sequence[tuple[str, str, str, int, str]],
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO submissions (
                    submission_id, bundle_id, bundle_sha256, idempotency_key,
                    received_at, status, sample_count, file_count, warnings_json,
                    bundle_path, agent_version, bundle_created_at
                ) VALUES (?, ?, ?, ?, ?, 'accepted', ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.submission_id,
                    receipt.bundle_id,
                    receipt.bundle_sha256,
                    idempotency_key,
                    receipt.received_at.isoformat(),
                    receipt.sample_count,
                    receipt.file_count,
                    json.dumps(list(receipt.warnings), separators=(",", ":")),
                    bundle_path,
                    agent_version,
                    bundle_created_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO samples (
                    sample_id, submission_id, sample_path, sample_sha256, sample_json,
                    profile, provider_id, provider_name, country_code, product, plan,
                    region, zone, machine_type, cpu_count, memory_bytes, architecture,
                    protocol_version, protocol_fingerprint, quality_status, created_at,
                    raw_evidence_count
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [
                    (
                        sample.sample_id,
                        sample.submission_id,
                        sample.sample_path,
                        sample.sample_sha256,
                        sample.sample_json,
                        sample.profile,
                        sample.provider_id,
                        sample.provider_name,
                        sample.country_code,
                        sample.product,
                        sample.plan,
                        sample.region,
                        sample.zone,
                        sample.machine_type,
                        sample.cpu_count,
                        sample.memory_bytes,
                        sample.architecture,
                        sample.protocol_version,
                        sample.protocol_fingerprint,
                        sample.quality_status,
                        sample.created_at,
                        sample.raw_evidence_count,
                    )
                    for sample in samples
                ],
            )
            connection.executemany(
                """
                INSERT INTO evidence (
                    submission_id, sample_id, archive_path, sha256, size_bytes, media_type
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (receipt.submission_id, sample_id, path, digest, size_bytes, media_type)
                    for sample_id, path, digest, size_bytes, media_type in evidence
                ],
            )

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            submissions = int(connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0])
            samples = int(connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0])
            evidence = int(connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0])
        return {"evidence": evidence, "samples": samples, "submissions": submissions}


__all__ = ["IngestionRepository"]

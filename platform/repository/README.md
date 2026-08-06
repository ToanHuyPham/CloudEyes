# Repository

Backend Ingestion v1 uses SQLite for submission, sample, and evidence indexes, plus immutable content-addressed ZIP storage for verified bundles.

The v1 schema enforces unique bundle digests, idempotency keys, and sample IDs. Distributed databases and object-storage adapters remain future work.

# Ingestion

Backend Ingestion v1 is implemented by `cloudeyes_platform.ingestion` and exposed through `cloudeyes-ingestion serve`.

The pipeline verifies request metadata, validates bundle integrity and sample semantics, rejects duplicate sample identities, stores verified bundles by SHA-256, and commits submission/sample/evidence metadata in one SQLite transaction.

# Changelog

## Unreleased

- Added Backend Ingestion and Validation v1 with bounded HTTP uploads, repeated bundle verification, SHA-256 idempotency, duplicate-sample rejection, and privacy-conscious quarantine metadata.
- Added SQLite submission/sample/evidence persistence, immutable content-addressed bundle storage, bearer-token authentication, health reporting, receipt schema, CLI service entry point, documentation, and tests.
- Added Result Bundle and Submission v1 with canonical sample packaging, raw-evidence redaction, per-file SHA-256 manifests, atomic ZIP creation, and offline verification.
- Added explicit authenticated or anonymous submission, HTTPS-by-default endpoint policy, private-only HTTP testing, redirect refusal, response limits, idempotency headers, receipts, CLI commands, schemas, documentation, and tests.
- Added Database Profile v1 with bounded temporary SQLite connection, point-read, durable insert/update, and concurrent mixed workloads.
- Added WAL plus synchronous FULL compatibility rules, privacy-safe raw evidence, deterministic cleanup, CLI controls, catalog entries, examples, and tests.
- Added Web Profile v1 with bounded concurrent HTTP GET workloads, request-rate, error-rate, TTFB, total-latency, and response-throughput metrics.
- Added explicit public/private target scope enforcement, privacy-safe per-request raw evidence, CLI workload controls, protocol catalog entries, examples, and cross-platform tests.
- Added Normalized Pricing v1 with versioned offline price catalogs, explicit billing-period hours, source tiers, FX-to-USD normalization, and time-bounded cohort matching.
- Added equal-provider-weight price-performance indexes, compatible value peer comparisons, value scorecard assessment, analytics schema 1.2, CLI pricing options, and Markdown pricing sections.
- Added Compatible Peer Comparison v1 with strict cross-provider hardware, geography, profile, and protocol matching.
- Added equal provider weighting, subject-excluded peer medians, direction-aware relative differences, five-percent similarity outcomes, and auditable cohort references.
- Provider Analytics schema 1.1 now includes peer-group counts and per-provider metric comparisons; performance remains unassessed when no defensible baseline exists.
- Added offline Provider Analytics v1 with deterministic provider aggregation, multidimensional scorecards, traceable explanations, and JSON/Markdown output.
- Added `cloudeyes analyze` for local sample files and directories.
- Added strict Provider Analytics v1 schema and explicit guards against universal scores, peer-free performance grading, and price-free value grading.
- Added Compute Profile v1 with bounded integer, floating-point, SHA-256, compression, and multi-process scaling measurements.
- Added configurable worker limits, raw compute evidence, `cloudeyes run compute`, metric catalog entries, and protocol documentation.
- Added Networking Profile v1 with DNS, TCP, TLS, HTTP latency, bounded throughput, request-loss, and optional ICMP measurements.
- Added public/private target safety policies and privacy-safe raw network evidence.
- Added `cloudeyes run networking` CLI support and profile-aware ping dependency installation.
- Added Storage Profile v1 with bounded sequential, random, and fsync measurements.
- Added atomic raw storage evidence JSON and `cloudeyes run storage`.
- Created CloudEyes v1.1 Foundation.

- Added shared deterministic sample-quality and elapsed-time reliability policies.

- Add cross-platform spawned-process isolation and hard profile deadlines.
- Added process-safe cooperative cancellation, cleanup checkpoints, graceful timeout shutdown, and exit code 130 for interrupted runs.

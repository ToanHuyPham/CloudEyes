# Development Log

## 2026-08-06 — Core Foundation v1 completed

### Completed

- Immutable provider, product, machine, metric, measurement, protocol, sample, cohort, coverage, confidence, and report models.
- Deterministic JSON serialization and sample deserialization.
- Cross-field sample validation.
- Atomic local JSON sample repository.
- Strict cohort compatibility and grouping.
- Equal-weight cohort metric aggregation.
- Descriptive statistics with percentiles and coefficient of variation.
- Coverage and evidence-gap calculation.
- Independent measurement, statistical, and coverage confidence.
- Provider-level report aggregation across multiple cohorts.
- Sample and provider-report JSON schemas.
- End-to-end repository-to-report pipeline.
- Unit, schema-contract, and integration tests.

### Current state

- Phase: Foundation
- Component: Core Foundation
- Status: Complete
- Next component: Agent system discovery

### Deferred by design

- Hardware and operating-system discovery.
- Benchmark tool execution.
- Pricing collection.
- Use-case verdicts.
- Central platform persistence and API.

## 2026-08-06 — Storage Profile v1 completed

### Completed

- Bounded cross-platform temporary-file storage benchmark.
- Sequential write and cached sequential read throughput.
- Queue-depth-one cached random read and batched-fsync random write IOPS.
- Fsync p50 and p95 latency.
- Warm-up, deterministic random offsets, repetitions, and median aggregation.
- Free-space checks, 1 GiB file limit, 8 GiB estimated-I/O limit, and cleanup.
- Atomic raw evidence JSON persistence.
- `cloudeyes run storage` CLI support with selectable work directory.
- Metric catalog and storage protocol version updates.
- Unit, schema-contract, CLI, and end-to-end integration tests.

### Current state

- Phase: Reliable measurements
- Component: Storage Profile v1
- Status: Complete
- Next component: Networking Profile v1

### Explicit limitations

- Portable read measurements may use the operating-system page cache.
- Random I/O is single-process and queue-depth one.
- A result represents only the tested filesystem path and protocol fingerprint.

## 2026-08-06 — Networking Profile v1 completed

### Completed

- Explicit HTTP(S) endpoint measurement with public and private scope policies.
- DNS, TCP, TLS, HTTP TTFB, bounded download, and optional bounded upload metrics.
- HTTP request-loss and optional ICMP packet-loss measurement.
- Link-local, multicast, unspecified, reserved, and unsafe public targets blocked.
- Privacy-safe raw evidence without full URLs, queries, credentials, payloads, or IP values.
- Profile-aware runtime installation for the optional `ping` command.
- `cloudeyes run networking` CLI options for endpoint, upload endpoint, scope, TLS, and ICMP.
- Unit, schema-contract, CLI, local-server, and end-to-end integration tests.

### Current state

- Phase: Reliable measurements
- Component: Networking Profile v1
- Status: Complete
- Next component: Shared timeout and sample-quality policies

### Explicit limitations

- Results describe one endpoint and route at one point in time.
- HTTP throughput includes application, TCP, and optional TLS overhead.
- ICMP loss may not match TCP or HTTP behavior when networks filter ping.



## 2026-08-06 — Compute Profile v1 completed

### Completed

- Bounded deterministic integer and floating-point CPU workloads.
- Single-process SHA-256 and zlib compression throughput.
- Multi-process integer throughput, scaling ratio, and worker efficiency.
- Warm-up, repetitions, median aggregation, and verification checksums.
- Default automatic worker cap of four with explicit `--workers` override.
- Privacy-safe atomic raw evidence JSON.
- `cloudeyes run compute` CLI support.
- Metric catalog, protocol version, examples, documentation, and tests.

### Current state

- Phase: Reliable measurements
- Component: Compute Profile v1
- Status: Complete
- Next component: Shared timeout and sample-quality policies

### Explicit limitations

- Results include Python interpreter and standard-library implementation effects.
- Multi-core throughput includes worker-process coordination overhead.
- CPU frequency, host contention, and thermal state can change results.

## 2026-08-06 — Shared Measurement Reliability v1

- Centralized sample-quality classification for General, Storage, Networking, and Compute.
- Added profile-specific soft elapsed-time budgets.
- Preserved partial-result warnings and profile-specific invalid error codes.
- Added unit coverage and reliability policy documentation.

## Process-isolated execution v1

- Added a spawned child-process boundary for complete profile runs.
- Added hard wall-clock timeout enforcement with terminate/kill fallback.
- Added `--timeout-seconds` and debugging-only `--no-isolation` CLI options.
- Kept dependency installation in the parent process so elevation and prompts are explicit.

## 2026-08-06 — Cooperative Cancellation and Cleanup v1

### Completed

- Added a process-safe cancellation token shared by the parent profile worker and compute subprocesses.
- Added safe cancellation checkpoints to General, Storage, Networking, and Compute workloads.
- Changed timeout shutdown order to cancellation request, grace period, terminate, then kill.
- Preserved atomic raw evidence and parent-only final sample writes.
- Added deterministic storage temporary-file cleanup tests.
- Added CLI exit code `130` for interrupted isolated runs while retaining `124` for deadlines.
- Added cross-platform spawn tests for cooperative cleanup and hard fallback behavior.

### Current state

- Phase: Reliable measurements
- Component: Cooperative Cancellation and Cleanup v1
- Status: Complete
- Next component: Provider Analytics v1

### Explicit limitations

- A blocking operating-system call observes cancellation only after it returns or reaches its own timeout.
- Hard termination remains necessary when third-party or operating-system code ignores the cooperative contract.

## 2026-08-06 — Provider Analytics v1

### Completed

- Added offline analytics bundles with one report per provider.
- Reused strict cohorts, equal-weight summaries, coverage, and confidence from Core Foundation.
- Added independent evidence, consistency, reliability, performance, and value dimensions.
- Added explicit `not_assessed` results when compatible peers or normalized pricing are absent.
- Added traceable strengths, limitations, observations, rule IDs, and evidence references.
- Added `cloudeyes analyze` with JSON and optional Markdown output.
- Added a strict Provider Analytics v1 JSON Schema and unit, integration, and schema tests.

### Current state

- Phase: Provider analytics
- Component: Provider Analytics v1
- Status: Complete
- Next component: Compatible Peer Comparison v1

### Explicit limitations

- Consistency describes only observed cohort variation.
- Reliability describes benchmark completion and sample quality, not provider uptime.
- Performance and value remain unassessed without compatible peer and pricing evidence.



## 2026-08-06 — Compatible Peer Comparison v1

### Completed

- Added strict cross-provider peer keys using country, exact machine identity, profile, protocol version, and protocol fingerprint.
- Added provider-equal aggregation so sample-rich providers do not dominate the baseline.
- Added subject-excluded peer medians and direction-adjusted relative performance.
- Added ahead, similar, and behind outcomes using a fixed five-percent band.
- Added per-comparison confidence, provider/cohort evidence references, JSON schema 1.1, and Markdown rendering.
- Connected compatible comparisons to the performance scorecard while retaining `not_assessed` when no baseline exists.

### Current state

- Phase: Provider analytics
- Component: Compatible Peer Comparison v1
- Status: Complete
- Next component: Normalized Pricing v1

### Explicit limitations

- Hardware values are exact; approximate memory-size bucketing is intentionally not performed.
- Product, plan, region, and zone labels are provider-specific and are not assumed equivalent.
- A one-peer baseline is allowed but cannot receive high comparison confidence.
- Relative performance is not a universal provider score and does not include price.

## 2026-08-06 — Normalized Pricing v1

### Completed

- Added versioned offline pricing catalogs with explicit validity, billing-period hours, FX conversion, tax state, source tier, and source reference.
- Added deterministic quote matching by exact provider/product/plan, optional location scope, full cohort validity, source strength, and observation time.
- Added USD-per-hour normalization and conservative pricing confidence.
- Added direction-aware price-performance indexes for higher-is-better and lower-is-better metrics.
- Added provider-equal compatible value baselines, subject-excluded peer medians, five-percent outcomes, and traceable price/cohort references.
- Added `--pricing`, `--pricing-commitment`, and `--pricing-os` analytics options.
- Added analytics schema 1.2, pricing catalog schema 1.0, JSON/Markdown output, examples, and tests.

### Current state

- Phase: Provider analytics
- Component: Normalized Pricing v1
- Status: Complete
- Next component: Web Profile v1

### Explicit limitations

- CloudEyes does not fetch live prices, taxes, discounts, or exchange rates.
- Catalog authors must provide an explicit billing-period duration and FX multiplier.
- Value is relative to compatible priced peers and is not an absolute or universal provider score.
- Reserved and spot quotes are analyzed only when explicitly selected and are never mixed with on-demand quotes.

## 2026-08-06 — Web Profile v1

### Completed

- Added a bounded concurrent HTTP GET workload for one explicit endpoint.
- Added successful request rate, HTTP error rate, TTFB p50/p95, total latency p50/p95/p99, and bounded response throughput.
- Reused explicit public/private address-scope policy and TLS verification controls.
- Added per-request privacy-safe raw evidence without query strings, response bodies, credentials, or resolved addresses.
- Added `cloudeyes run web`, request/concurrency/response limits, process isolation, cancellation, examples, catalog entries, and tests.

### Current state

- Phase: Specialized profiles
- Component: Web Profile v1
- Status: Complete
- Next component: Database Profile v1

### Explicit limitations

- Protocol 1.0.0 uses a fresh connection for each request, so timing includes transport setup.
- Results describe the selected endpoint and workload only, not an entire provider or application.
- Application state, route conditions, caching, and rate limits can change independently of the tested VM.
- CloudEyes does not follow redirects or send authentication material in Web Profile v1.

## 2026-08-06 — Database Profile v1

### Completed

- Added a bounded temporary SQLite workload with verified connection setup, indexed point reads, durable single-row insert/update transactions, and concurrent mixed reads/writes.
- Fixed WAL journal mode and synchronous FULL as protocol compatibility requirements.
- Added seed-size, operation-count, concurrency, busy-timeout, and free-space safety limits.
- Added cooperative cancellation checkpoints, process-isolated hard timeout support, deterministic temporary database cleanup, and atomic raw evidence.
- Added `cloudeyes run database`, workload controls, metrics/protocol catalogs, documentation, examples, schema tests, and integration tests.

### Current state

- Phase: Specialized profiles
- Component: Database Profile v1
- Status: Complete
- Next component: Result Bundle and Submission v1

### Explicit limitations

- Protocol 1.0.0 measures a local temporary SQLite database, not a managed database service.
- Results combine Python, SQLite, CPU, memory, filesystem, and operating-system behavior.
- Point reads may use page caches, and SQLite serializes write transactions.
- PostgreSQL, MySQL, remote database authentication, and network latency are outside Database Profile v1.

## 2026-08-06 — Result Bundle and Submission v1

### Completed

- Added canonical multi-sample ZIP bundles with safe internal names and atomic output replacement.
- Added semantic sample validation, duplicate-ID rejection, explicit invalid/missing-evidence policy,
  trusted-root raw evidence resolution, credential-key and URL-secret redaction, and SHA-256/size
  manifest entries.
- Added offline verification for archive traversal, duplicate entries, symlinks, encryption,
  archive limits, unlisted files, checksum mismatches, sample identity, and raw JSON structure.
- Added explicit `cloudeyes bundle`, `cloudeyes verify-bundle`, and `cloudeyes submit` commands.
- Added HTTPS-by-default submission, environment-only bearer tokens, private/loopback HTTP test
  policy, redirect refusal, bounded responses, idempotency keys, privacy-safe receipts, schemas,
  documentation, integration tests, and local HTTP transport tests.

### Current state

- Phase: Platform entry
- Component: Result Bundle and Submission v1
- Status: Complete
- Next component: Backend Ingestion and Validation v1

### Explicit limitations

- The agent does not discover an ingestion endpoint and never submits automatically.
- Bundle v1 supports JSON samples and JSON raw evidence only.
- Bearer-token acquisition, server-side signature verification, moderation, and durable ingestion
  are platform responsibilities outside this module.
- Anonymous mode must be explicitly selected and accepted by the configured collector.

## 2026-08-06 — Backend Ingestion and Validation v1 completed

### Completed

- Added `cloudeyes-ingestion serve` with a loopback-safe default bind and bearer-token authentication.
- Added bounded request streaming with a 128 MiB limit and exact CloudEyes bundle media type.
- Re-verified bundle structure, checksums, manifest identity, and canonical sample semantics at the server boundary.
- Added SHA-256 idempotency, deterministic submission identities, whole-bundle deduplication, and duplicate-sample rejection.
- Added SQLite persistence for submissions, canonical samples, and evidence indexes.
- Added immutable content-addressed bundle storage and metadata-only quarantine by default.
- Added accepted/duplicate receipt schema, health reporting, documentation, unit tests, schema tests, and loopback HTTP integration tests.

### Current state

- Phase: Platform
- Component: Backend Ingestion and Validation v1
- Status: Complete
- Next component: Reporting and Dashboard v1

### Explicit limitations

- The v1 service is single-node and uses local SQLite plus filesystem storage.
- The built-in server does not terminate TLS and should remain on loopback or behind a TLS reverse proxy.
- Background aggregation workers, moderation, public read APIs, and dashboards are not part of this module.


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

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

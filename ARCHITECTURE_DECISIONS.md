# Architecture Decisions

## ADR-001 — Provider assessment is based on cohorts

A single benchmark run represents one sample only. Compatible samples must be grouped before provider-level conclusions are made.

## ADR-002 — Measurements and assessments are separate

Raw tool output and normalized metrics do not contain provider verdicts.

## ADR-003 — Explanations must be traceable

Every verdict, strength, limitation, and recommendation must reference evidence and assessment rules.

## ADR-004 — No primary universal provider score

CloudEyes uses multidimensional scorecards and workload-specific verdicts.

## ADR-005 — Protocols are versioned

Results from incompatible protocol versions must not be silently combined.

## ADR-006 — The agent remains usable offline

Users can inspect, run, validate, and export samples without a central platform.

## ADR-007 — Storage v1 uses bounded temporary files

The portable Storage Profile uses only new files inside a temporary directory,
checks free space, enforces hard workload limits, and removes workload files after
each run. It never targets an existing path as a file.

## ADR-008 — Cached storage metrics are named explicitly

Portable Python reads cannot guarantee cache bypass across every supported
operating system. Storage v1 therefore labels affected read metrics as `cached`
and records this limitation in raw evidence instead of claiming raw-device speed.

## ADR-009 — Networking v1 measures only explicit endpoints

Networking Profile v1 never scans address ranges or ports. Every remote request
is directed to a user-selected HTTP or HTTPS endpoint, uses bounded payloads and
timeouts, and records endpoint identity without retaining queries or payloads.

## ADR-010 — Network scope is enforced before application probes

Public scope rejects private, loopback, link-local, multicast, unspecified, and
reserved addresses. Private scope permits controlled private and loopback tests
but still blocks link-local metadata addresses and unsafe address classes.



## ADR-011 — Compute v1 is bounded and runtime-aware

Compute Profile v1 uses deterministic Python standard-library workloads so it remains
portable and offline. The default automatic worker count is capped at four processes;
users must explicitly request a larger count. Raw evidence records the Python implementation,
version, resolved worker count, repetitions, and verification checksums. Results are not
presented as native instruction throughput or FLOPS.

## ADR — Soft elapsed-time budgets before hard cancellation

CloudEyes records elapsed-time budget overruns as deterministic quality warnings. It does
not kill in-process benchmark work in v1 because forced thread cancellation cannot guarantee
cleanup of temporary files, sockets, or evidence. Hard timeouts require process isolation
and an explicit cleanup contract.

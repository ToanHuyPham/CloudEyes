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

## ADR-013 — Cooperative cancellation precedes forced termination

When an isolated profile exceeds its deadline or the parent is interrupted, CloudEyes first
sets a process-safe cancellation event and waits for a bounded grace period. Implemented
profiles check that event only at safe cleanup boundaries and propagate cancellation instead
of converting it into a failed measurement. Terminate and kill remain final fallbacks for
blocking system calls or non-cooperative code. A deadline still returns exit code 124 even
when cooperative cleanup succeeds; an interactive interruption returns 130.

## ADR-014 — Provider Analytics v1 is multidimensional and evidence-bounded

Provider Analytics v1 evaluates evidence confidence, observed consistency, and benchmark
completion reliability as independent dimensions. It does not calculate a universal provider
score. Performance is not graded without a compatible peer baseline, value is not graded without
normalized pricing evidence, and benchmark completion must not be presented as provider uptime.
Every explanation carries a versioned rule ID and evidence references.


## ADR-015 — Peer comparison is strict and provider-equal

Compatible Peer Comparison v1 matches country, exact machine identity, profile, protocol version,
and protocol fingerprint. Provider-specific product, plan, region, and zone labels are retained as
cohort evidence but are not treated as cross-provider identifiers. Each provider contributes one
median value to a peer group regardless of sample or cohort count, and the subject provider is
excluded from its own peer baseline. Unknown provider or country identity is not compared. Relative
performance remains a separate dimension and is not combined into a universal provider score.

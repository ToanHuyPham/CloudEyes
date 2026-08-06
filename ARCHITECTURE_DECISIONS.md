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

## ADR-016 — Pricing is offline, explicit, time-bounded, and peer-relative

Normalized Pricing v1 does not fetch or infer commercial data during analysis. Operators supply
versioned catalogs containing source amount, currency, explicit billing-period hours, FX-to-USD
multiplier, validity interval, commitment, operating-system family, tax state, source tier, and
source reference. Quotes match exact provider, product, and plan identity; optional region and zone
fields are explicit wildcards when absent. A quote must cover the complete cohort interval. Equal
ranked conflicting quotes stop analysis. Price-performance indexes preserve a larger-is-better
direction and are compared only inside strict compatible peer groups with equal provider weighting.
Commitment and operating-system families are selected explicitly and never mixed. Value remains an
independent dimension and is not combined into a universal provider score.

## ADR-017 — Web v1 is bounded, unauthenticated, and endpoint-specific

Web Profile v1 sends GET requests only to an explicitly selected HTTP or HTTPS endpoint. URLs with
embedded credentials are rejected, and the agent does not send cookies, authorization headers, or
request bodies. Public scope rejects non-public address classes; private targets require explicit
operator selection. Requests connect directly to an address that passed scope validation, avoiding
a second DNS resolution between validation and connection. Request count, concurrency, response bytes, socket timeout, aggregate bounded
traffic, and process duration are limited. Raw evidence stores the target origin and a path digest,
but never the query string, response body, credentials, or resolved addresses. Protocol 1.0.0 uses
a fresh connection per request and therefore treats connection setup as part of observed web-service
latency. Results are comparable only when endpoint identity and all workload bounds match.

## ADR-018 — Database v1 uses a disposable local SQLite protocol

Database Profile v1 creates a new temporary SQLite database for every sample and never accepts an
existing database path. WAL journal mode and `synchronous=FULL` are fixed compatibility requirements.
Seed payload, operation counts, concurrency, busy timeout, free space, and process duration are
bounded. Each concurrent worker owns one connection, cancellation is checked only at safe transaction
boundaries, and every connection is closed before the temporary directory is removed. Raw evidence
records SQLite version, sanitized error classes, workload configuration, latencies, rates, and file
sizes, but not record payloads or the temporary path. Results describe the local VM stack and must not
be labeled as PostgreSQL, MySQL, networked database, or managed database service performance.

## ADR-019 — Collection and transport are separate, integrity-checked operations

Profile execution never performs network submission. Operators first create a local bundle from
validated Core samples and referenced JSON evidence. Bundle payloads use canonical JSON and safe
archive names; every payload receives a SHA-256 digest and exact byte size in a versioned manifest.
Credential-like fields and URL user/query/fragment components are redacted in the bundled copy,
while original local evidence remains unchanged. Missing evidence and invalid samples fail closed
unless an explicit policy exception is recorded in the manifest.

Verification occurs before every submission and rejects traversal paths, duplicate entries,
symlinks, encrypted entries, unlisted payloads, unsafe archive size, checksum mismatch, unsupported
manifest shape, and semantically invalid samples. Transport is HTTPS by default, does not follow
redirects, bounds timeout and response size, reads bearer tokens only from an environment variable,
and sends the bundle digest as an idempotency key. Plain HTTP is restricted to explicitly allowed
private or loopback test endpoints. Receipts contain endpoint, status, bundle identity, and response
digest, but never credentials or response bodies.

## ADR-020 — Ingestion repeats verification and persists immutable bundle evidence

The central platform never trusts client-side verification. Every request must declare the exact
CloudEyes bundle media type, bundle ID, SHA-256 digest, and an idempotency key equal to that digest.
The server bounds the request body before reading it, streams it to private temporary storage, and
runs the complete bundle verifier again before persistence. Whole-bundle replays return the original
submission identity; a different bundle that reuses an existing sample ID is rejected rather than
replacing or silently merging evidence.

Accepted ZIP bytes are stored immutably under their content digest. SQLite records submission,
canonical sample, and evidence indexes in a single transaction with unique constraints on bundle
digests, idempotency keys, and sample IDs. Invalid bundle metadata is quarantined without retaining
authorization headers. Rejected payload bytes are not retained by default because unverified archives
may contain sensitive material. Backend Ingestion v1 remains single-node; distributed queues, object
storage, moderation, aggregation workers, and public APIs are separate platform stages.


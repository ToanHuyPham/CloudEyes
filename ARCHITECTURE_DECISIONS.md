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

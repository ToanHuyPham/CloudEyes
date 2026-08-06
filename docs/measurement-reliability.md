# Shared Measurement Reliability v1

CloudEyes classifies benchmark samples through one deterministic policy shared by the
General, Storage, Networking, and Compute profiles.

## Quality rules

- At least one successful measurement is required for a valid sample.
- Failed and skipped measurements remain visible as warnings when partial results exist.
- Profile and discovery warnings are deduplicated without changing their order.
- A profile-specific elapsed-time budget adds
  `measurement_duration_exceeded:<tool>` when a completed measurement exceeds its
  expected duration.
- A failed single-measurement profile remains invalid and keeps its profile-specific
  error code.

## Timeout scope

The v1 timeout rule is a soft elapsed-time budget. It does not terminate a running
thread or process because forced cancellation can leave temporary files, sockets, or
raw evidence in an unknown state. Benchmark workloads remain bounded by their profile
configuration. Hard process isolation and cancellation are deferred until execution
workers have a cleanup contract.

Current default elapsed-time budgets:

| Profile | Budget |
| --- | ---: |
| General | 120 seconds |
| Networking | 180 seconds |
| Compute | 600 seconds |
| Storage | 900 seconds |

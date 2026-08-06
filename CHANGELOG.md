# Changelog

## Unreleased

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

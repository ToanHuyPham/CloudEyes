# Compute Profile v1

Portable, bounded CPU measurements implemented with Python 3.11+ and the standard library.

The profile measures deterministic integer and floating-point loops, SHA-256 throughput,
zlib compression throughput, multi-process scaling, and per-worker efficiency. It records
individual repetitions and verification checksums in privacy-safe raw evidence.

`workers: 0` selects an automatic worker count capped at four by default. Use the CLI
`--workers` option to request a specific process count. Requests above the detected logical
CPU count are capped and reported as a quality warning.

The profile does not claim instruction-level FLOPS or native compiler performance. Results
include Python runtime, standard-library, process-start, and scheduling effects, so compare
only compatible protocol fingerprints and similar Python implementations.

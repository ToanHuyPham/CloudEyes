# Compute Profile v1

Compute Profile v1 is a bounded, offline CPU benchmark that uses only Python 3.11+
standard-library components. It creates a Core Sample and privacy-safe raw evidence.

## Metrics

- deterministic integer throughput on one process;
- aggregate deterministic integer throughput across worker processes;
- deterministic scalar floating-point throughput;
- SHA-256 throughput;
- zlib compression throughput;
- concurrency scaling ratio;
- per-worker efficiency percentage.

The integer and floating-point units are protocol-defined iterations per second. They are
not CPU instructions, FLOPS, or a replacement for a native compiler benchmark.

## Safe worker policy

The default configuration uses automatic worker selection capped at four processes. This
prevents an unattended run from saturating a large host. `--workers N` requests an explicit
count between 1 and 64. A request above the detected logical CPU count is capped and emitted
as a sample-quality warning. `--workers 0` returns to bounded automatic selection.

## Commands

Quick smoke test:

```bash
python -m cloudeyes_agent run compute \
  --quick \
  --output data/compute-smoke-sample.json
```

Explicit worker count:

```bash
python -m cloudeyes_agent run compute \
  --workers 4 \
  --output data/compute-sample.json
```

The raw evidence file is written to `data/raw/<sample-id>-compute.json` when an output
path is supplied.

## Evidence and comparison

Raw evidence records all repetitions, resolved worker count, workload configuration,
verification checksums, Python implementation, and Python version. It does not record
hostnames, process lists, environment variables, or user data.

Compare only matching protocol fingerprints. For multi-core and worker-efficiency metrics,
also require the same resolved worker count. Results can change because of host contention,
CPU frequency policy, virtualization, thermal state, Python implementation, and Python
version.

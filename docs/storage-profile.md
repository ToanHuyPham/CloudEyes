# Storage Profile v1

## Purpose

The Storage Profile measures one filesystem path with a bounded, temporary-file
workload. It produces a normal CloudEyes Core sample and preserves the raw values
from every repetition in a separate JSON evidence file.

The result describes only the tested machine, path, protocol fingerprint, and
collection time. It must not be treated as a universal score for every storage
product from the provider.

## Workload

The default protocol creates a 64 MiB temporary file and runs three repetitions.
The quick protocol creates an 8 MiB file and runs one repetition.

Each repetition measures:

- sequential write throughput with a final flush and `fsync`;
- sequential read throughput;
- deterministic 4 KiB random reads at queue depth one;
- deterministic 4 KiB random writes with one final batch `fsync`;
- individual `fsync` latency samples.

Throughput and IOPS are reported as the median across repetitions. Fsync latency
is reported as p50 and p95 across all latency samples.

## Safety

The implementation:

- writes only inside a newly-created temporary directory;
- removes every workload file after the run;
- refuses files larger than 1 GiB;
- refuses estimated total I/O above 8 GiB;
- checks free space before creating the workload;
- never opens or overwrites an existing user file.

## Raw evidence

The CLI stores raw evidence beside the sample:

```text
sample output: data/storage-sample.json
raw evidence:  data/raw/<sample-id>-storage.json
```

The evidence contains configuration, free space, per-repetition observations,
aggregates, and explicit limitations. It does not contain file contents,
hostnames, usernames, IP addresses, or credentials.

## Commands

Quick smoke test:

```bash
python -m cloudeyes_agent run storage \
  --quick \
  --output data/storage-sample.json
```

Select the filesystem path to test:

```bash
python -m cloudeyes_agent run storage \
  --work-dir /mnt/benchmark-target \
  --output data/storage-sample.json
```

Install missing discovery packages before the benchmark:

```bash
python -m cloudeyes_agent run storage \
  --quick \
  --install-deps \
  --yes \
  --output data/storage-sample.json
```

## Interpretation limits

Read metrics may benefit from the operating-system page cache. The random test is
single-process and queue-depth one. Storage arrays, network volumes, local disks,
filesystems, mount options, encryption, noisy neighbours, and provider throttling
can all affect results. Compatible samples must still be grouped into cohorts
before provider-level conclusions are made.

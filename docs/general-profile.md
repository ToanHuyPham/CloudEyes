# General Profile v1

## Purpose

General Profile v1 is the first executable CloudEyes measurement profile. It connects
Agent Discovery to the immutable Core Sample model and provides a safe baseline for
comparing compute, memory, and local storage behavior.

## Complete flow

```text
Agent Discovery
→ bounded built-in benchmarks
→ normalized Core metrics
→ protocol fingerprint
→ sample quality
→ Core Sample JSON
→ JSON Schema validation
```

## Protocol identity

- Profile: `general`
- Version: `1.0.0`
- Fingerprint: SHA-256 of the complete validated profile configuration

Changing any workload size, storage setting, or protocol version changes the fingerprint.
Samples with different fingerprints must not be placed in the same cohort.

## Metrics

| Metric | Unit | Direction |
|---|---|---|
| `compute.cpu.sha256_mib_per_second` | `mib_per_second` | higher is better |
| `memory.copy.mib_per_second` | `mib_per_second` | higher is better |
| `storage.sequential_write.mib_per_second` | `mib_per_second` | higher is better |
| `storage.sequential_read.mib_per_second` | `mib_per_second` | higher is better |

These are portable Agent baseline metrics. They are not substitutes for workload-specific
profiles such as database, networking, AI, or recovery.

## Quality behavior

A benchmark exception becomes a failed `Measurement`. Successful measurements remain
available, while sample quality becomes `valid_with_warnings`. A sample with no successful
measurements becomes `invalid`.

Skipping storage with `--no-storage` is explicit and also produces
`valid_with_warnings`; it is never silently treated as complete coverage.

## CLI

Quick validation run:

```powershell
py -m cloudeyes_agent run general --quick --output data\general-sample.json
```

Default bounded run:

```powershell
py -m cloudeyes_agent run general --output data\general-sample.json
```

Optional identity metadata:

```powershell
py -m cloudeyes_agent run general `
  --provider-id viettel-cloud `
  --provider-name "Viettel Cloud" `
  --country-code VN `
  --product "Cloud Server" `
  --plan "2-vCPU-4GB" `
  --region hanoi `
  --zone zone-1 `
  --output data\general-sample.json
```

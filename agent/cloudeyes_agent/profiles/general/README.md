# General Profile v1

The General Profile produces one privacy-safe CloudEyes Core sample using only Python's
standard library. It runs bounded CPU, memory, and temporary-file storage workloads.

## Metrics

- `compute.cpu.sha256_mib_per_second`
- `memory.copy.mib_per_second`
- `storage.sequential_write.mib_per_second`
- `storage.sequential_read.mib_per_second`

## Safety

- No external network requests.
- No hostname, username, local address, or file content is reported.
- Storage data is created in a temporary directory and removed after the run.
- Configuration validation limits the storage workload to 512 MiB.
- A failed benchmark is preserved as a failed measurement instead of being hidden.

## Run

```powershell
py -m cloudeyes_agent run general --quick --output data\general-sample.json
```

Use the default workload after the quick run succeeds:

```powershell
py -m cloudeyes_agent run general --output data\general-sample.json
```

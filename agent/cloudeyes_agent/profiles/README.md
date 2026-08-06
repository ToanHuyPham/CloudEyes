# Storage Profile v1

The Storage Profile runs a bounded temporary-file workload against one selected
filesystem path. It records sequential throughput, queue-depth-one random IOPS,
and fsync latency while preserving raw per-repetition evidence.

The profile never writes to an existing user file. All workload files are created
inside a temporary directory and removed after the run.

# Database Profile v1

Database Profile v1 provides a portable, offline database workload using Python's SQLite module.
It is designed to compare compatible VM environments without requiring credentials, a remote
service, or a pre-existing database.

## Workload

Each run creates a new temporary SQLite database, enables WAL journal mode and
`synchronous=FULL`, seeds deterministic records, performs a bounded warm-up, and measures:

- connection-open latency including protocol session setup and a verified `SELECT 1`;
- indexed point-read latency;
- durable single-row insert transactions;
- durable single-row update transactions;
- concurrent mixed point reads and durable updates;
- mixed-operation error rate.

The standard workload uses three repetitions and four workers. `--quick` uses one repetition and
two workers for CI and smoke testing.

## Safety and cleanup

CloudEyes never accepts an existing database path in protocol version 1.0.0. The profile creates a
private temporary directory inside `--work-dir`, verifies free space, limits seeded payload and
operation counts, checks cooperative cancellation between safe operations, closes all connections,
and removes database, WAL, and shared-memory files before returning.

Raw evidence records configuration, SQLite version, aggregate statistics, per-repetition latency
samples, file sizes before cleanup, and sanitized SQLite error classes. It does not retain record
payloads or the temporary database path.

## Interpretation

This is a local SQLite benchmark. It reflects the combined behavior of Python, SQLite, the VM CPU,
memory, filesystem, and operating system. It must not be presented as PostgreSQL, MySQL, networked
database, or managed database service performance. Comparisons require an identical protocol
fingerprint.

## CLI

```bash
python -m cloudeyes_agent run database \
  --work-dir /tmp/cloudeyes-database \
  --database-records 2000 \
  --database-payload-bytes 256 \
  --concurrency 4 \
  --output data/database-sample.json
```

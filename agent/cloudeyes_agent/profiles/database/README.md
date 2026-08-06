# Database Profile v1

Database Profile v1 runs a bounded, temporary SQLite workload. It measures connection setup,
point reads, durable single-row insert/update transactions, and a concurrent mixed read/write
workload.

The profile never opens an existing database. It creates a private temporary directory inside the
selected `--work-dir`, enables WAL mode with `synchronous=FULL`, closes every connection, and removes
the database and WAL files after the run.

This profile measures the local VM stack. It is not a benchmark of a managed PostgreSQL, MySQL, or
other remote database service.

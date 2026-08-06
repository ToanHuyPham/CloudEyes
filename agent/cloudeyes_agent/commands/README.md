# Agent commands

- `inspect`: collect privacy-safe local discovery data.
- `run`: execute a bounded measurement profile.
- `analyze`: build offline Provider Analytics v1 from local sample JSON files.
- `bundle`: validate samples and package canonical sample/raw-evidence payloads with SHA-256.
- `verify-bundle`: verify ZIP safety, manifest integrity, checksums, and sample semantics.
- `submit`: explicitly send one verified bundle to a configured ingestion endpoint.

Analytics and bundle creation are offline. Submission occurs only after the operator invokes the
`submit` command.

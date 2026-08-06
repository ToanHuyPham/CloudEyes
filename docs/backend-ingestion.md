# Backend Ingestion and Validation v1

Backend Ingestion v1 accepts CloudEyes result bundles created by `cloudeyes bundle`, verifies every bundle again at the server boundary, deduplicates submissions, and persists canonical sample metadata in SQLite.

## Safety model

The service fails closed. It requires the exact CloudEyes bundle media type, a 64-character SHA-256 idempotency key, matching digest headers, and a verified bundle ID. Bundle verification rejects unsafe ZIP paths, unsupported manifest fields, unlisted files, checksum mismatches, oversized payloads, and semantically invalid samples.

The request body limit is 128 MiB. The server streams request bodies to a temporary file instead of keeping the complete bundle in memory. Invalid bundle metadata is quarantined without storing authorization headers. Rejected payload bytes are not retained unless `--quarantine-payloads` is explicitly enabled.

The built-in HTTP server binds to `127.0.0.1` by default. Production deployments should place it behind a TLS reverse proxy. Anonymous mode is restricted to loopback. Non-loopback binding requires the explicit `--allow-insecure-network` acknowledgement and a bearer token.

## Local startup

Set a token in an environment variable:

```bash
export CLOUDEYES_INGEST_TOKEN='replace-with-a-long-random-token'
```

Start the service:

```bash
cloudeyes-ingestion serve \
  --host 127.0.0.1 \
  --port 8080 \
  --data-dir data/platform
```

For local-only smoke tests, authentication may be disabled explicitly:

```bash
cloudeyes-ingestion serve \
  --host 127.0.0.1 \
  --port 8080 \
  --data-dir data/platform-smoke \
  --allow-anonymous
```

## Submission endpoint

```text
POST /v1/submissions
Content-Type: application/vnd.cloudeyes.bundle+zip; version=1
Authorization: Bearer <token>
Idempotency-Key: <bundle SHA-256>
X-CloudEyes-Bundle-Id: <manifest bundle ID>
X-CloudEyes-Bundle-SHA256: <bundle SHA-256>
```

A new bundle returns HTTP `201` with `status: accepted`. Replaying the same verified bundle returns HTTP `200` with `status: duplicate` and the original submission ID. Reusing a sample ID in a different bundle returns HTTP `409` rather than silently replacing evidence.

The agent can submit to a local service with:

```bash
export CLOUDEYES_API_TOKEN="$CLOUDEYES_INGEST_TOKEN"
cloudeyes submit data/results.zip \
  --endpoint http://127.0.0.1:8080/v1/submissions \
  --allow-http
```

## Persistence layout

```text
data/platform/
├── ingestion.sqlite3
├── bundles/<sha-prefix>/<bundle-sha256>.zip
├── quarantine/*.json
└── tmp/
```

SQLite uses foreign keys, WAL journaling, synchronous FULL, a unique bundle digest, a unique idempotency key, and unique sample IDs. Stored sample rows contain only canonical CloudEyes fields required by later cohort and assessment workers. Original verified bundles remain content-addressed and immutable.

## Health endpoint

```text
GET /healthz
```

The response reports service status and local submission, sample, and evidence counts. It does not expose tokens, bundle content, filesystem paths, or sample payloads.

## Explicit limitations

Backend Ingestion v1 is a single-node service using local SQLite and content-addressed filesystem storage. It does not provide distributed locking, object storage, background workers, moderation, public APIs, or dashboard functionality. Those remain separate platform stages.

# Networking Profile v1

## Purpose

Networking Profile v1 measures the path from the current CloudEyes Agent host to
one explicitly configured HTTP or HTTPS endpoint. It is intended for controlled,
repeatable tests such as a server in the same region, a private VPC endpoint, or a
public benchmark endpoint operated by the user.

It does not discover remote hosts, scan ports, upload local files, or store
request and response payloads.

## Measurements

The profile can produce:

- DNS lookup latency p50 and p95.
- TCP connect latency p50 and p95.
- TLS handshake latency p50 and p95 for HTTPS.
- HTTP TTFB p50 and p95.
- Bounded download throughput.
- Optional bounded upload throughput.
- HTTP request-loss percentage.
- Optional ICMP packet-loss percentage.

Upload throughput requires `--upload-target`. The endpoint must accept a POST
request containing deterministic synthetic bytes. No local file is uploaded.

## Scope policy

`--scope public` is the default. It rejects targets resolving to private,
loopback, link-local, multicast, unspecified, or reserved addresses.

`--scope private` permits private and loopback targets for controlled VPC and
local tests. Link-local targets remain blocked to prevent accidental access to
cloud metadata services.

## Quick public smoke test

The default endpoint is `https://example.com/`. It is suitable only for checking
that DNS, TCP, TLS, and HTTP execution work. Its response is too small for a
meaningful throughput comparison, so the sample contains a quality warning.

```bash
python -m cloudeyes_agent run networking \
  --quick \
  --output data/networking-smoke-sample.json
```

## Controlled public endpoint

```bash
python -m cloudeyes_agent run networking \
  --target https://benchmark.example.net/download \
  --upload-target https://benchmark.example.net/upload \
  --scope public \
  --install-deps \
  --yes \
  --output data/networking-public-sample.json
```

## Private endpoint

```bash
python -m cloudeyes_agent run networking \
  --target http://10.10.0.20:8080/download \
  --upload-target http://10.10.0.20:8080/upload \
  --scope private \
  --output data/networking-private-sample.json
```

Use `--no-ping` when ICMP is intentionally blocked. Use `--insecure` only for a
trusted HTTPS test endpoint with a self-signed certificate. Disabling TLS
verification is recorded as a sample warning.

## Raw evidence

When `--output data/networking-sample.json` is used, raw evidence is written to:

```text
data/raw/<sample-id>-networking.json
```

Raw evidence stores timing arrays, byte counts, HTTP status codes, endpoint
origin, and a SHA-256 hash of the URL path. It deliberately omits the full URL,
query string, credentials, request body, response body, and resolved IP values.

## Comparability

Samples should be grouped only when all of these match:

- Networking protocol fingerprint.
- Target origin and path identity.
- Public or private scope.
- Download and upload sizes.
- Repetition and timeout settings.
- TLS verification behavior.

A result measures the route and endpoint available at that time. It is not a
universal measure of every network path offered by a provider.

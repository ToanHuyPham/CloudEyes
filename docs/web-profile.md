# Web Profile v1

Web Profile v1 measures the end-to-end behavior of one explicitly selected HTTP or HTTPS endpoint
under a bounded concurrent GET workload. It complements Networking Profile v1: Networking isolates
DNS, TCP, TLS, upload, and ICMP behavior, while Web Profile measures the service response seen by a
client when several requests are active.

## Metrics

- Successful requests per second.
- HTTP error rate.
- TTFB p50 and p95.
- Total request latency p50, p95, and p99.
- Aggregate bounded response throughput.

A request succeeds only when it receives a `2xx` status. Redirects, client errors, server errors,
timeouts, TLS failures, and connection failures contribute to the error rate. CloudEyes still emits
metrics when at least one request succeeds; partial failures are preserved as warnings and raw
evidence. When every measured request fails, the measurement is invalid.

## Safety and privacy

The profile sends only GET requests. It does not send credentials, cookies, authorization headers,
or request bodies. URLs containing username or password fields are rejected. Public scope rejects
private, loopback, link-local, multicast, reserved, and unspecified addresses; private targets must
be selected explicitly with `--scope private`.

The workload is bounded by request count, concurrency, per-request timeout, per-response byte limit,
a 512 MiB aggregate response ceiling, process isolation, cooperative cancellation, and a default
180-second hard deadline.

Raw evidence contains:

- target origin;
- SHA-256 digest of the path;
- whether a query string was present;
- IPv4/IPv6 family availability, without resolved addresses;
- workload bounds;
- status and error-type counts;
- per-request timing, status, and bounded byte counts.

Raw evidence never contains the query string, credentials, response body, or resolved IP address.

## CLI

Quick public smoke test:

```bash
python -m cloudeyes_agent run web \
  --quick \
  --target https://example.com/ \
  --output data/web-smoke-sample.json
```

Controlled private endpoint:

```bash
python -m cloudeyes_agent run web \
  --target http://10.10.0.20:8080/health \
  --scope private \
  --requests 100 \
  --concurrency 10 \
  --max-response-bytes 1048576 \
  --output data/web-private-sample.json
```

Do not benchmark third-party services without authorization. The profile is intentionally bounded,
but it still creates traffic and should target an endpoint owned or explicitly approved by the
operator.

## Comparability

Compatible comparisons require the same endpoint identity, scope, request count, concurrency,
warm-up count, timeout, response limit, TLS policy, and protocol fingerprint. Quick and full runs
are therefore separate cohorts.

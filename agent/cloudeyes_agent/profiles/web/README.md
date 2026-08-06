# Web Profile v1

Web Profile v1 measures one explicitly selected HTTP or HTTPS endpoint with a bounded concurrent
GET workload. It reports successful request rate, error rate, TTFB percentiles, total latency
percentiles, and bounded response throughput.

Safety properties:

- GET only; no request body, cookies, credentials, or custom authorization headers.
- Public targets may not resolve to private, loopback, link-local, multicast, or reserved addresses.
- Private targets require `--scope private`. Requests are pinned to an address that passed scope validation.
- Request count, concurrency, response bytes, socket timeout, and total process time are bounded.
- Raw evidence stores the origin and a SHA-256 path digest, never the query string or response body.
- TLS verification is enabled unless the operator explicitly selects `--insecure`.

This profile measures end-to-end web-service behavior under bounded concurrency. Networking Profile
v1 remains the source for isolated DNS, TCP, TLS, upload, and ICMP measurements.

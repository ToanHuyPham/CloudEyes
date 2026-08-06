# Networking Profile v1

The Networking Profile measures one explicit HTTP or HTTPS endpoint. It does not
scan ports, enumerate hosts, or transmit local files.

Implemented measurements:

- DNS lookup latency p50 and p95.
- TCP connection latency p50 and p95.
- TLS handshake latency p50 and p95 for HTTPS targets.
- HTTP time-to-first-byte p50 and p95.
- Bounded download throughput.
- Optional bounded upload throughput to a separate POST endpoint.
- HTTP request-loss percentage.
- Optional ICMP packet-loss sampling when `ping` is available.

The endpoint URL, upload URL, query string, request body, response body, and
resolved IP addresses are not persisted in raw evidence. Only the origin, a hash
of the path, counts, timings, status codes, and bounded byte totals are retained.

Public scope rejects private, loopback, link-local, multicast, unspecified, and
reserved target addresses. Private scope permits private and loopback addresses,
but still rejects link-local metadata addresses and unsafe address classes.

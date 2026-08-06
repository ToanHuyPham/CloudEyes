"""Bounded concurrent HTTP benchmarks using only the Python standard library."""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import socket
import ssl
import statistics
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import SplitResult, urlsplit

from cloudeyes_core.models import Metric, MetricDirection

from ...execution import CancellationRequested, CancellationToken
from .config import NetworkScope, WebProfileConfig

_MIB = 1024 * 1024
_Timer = Callable[[], float]
_Resolver = Callable[..., list[tuple[Any, ...]]]


class WebSafetyError(RuntimeError):
    """Raised when a target violates the configured address-scope policy."""


@dataclass(frozen=True, slots=True)
class WebRequestObservation:
    """Privacy-safe evidence for one bounded GET request."""

    request_index: int
    status_code: int | None
    success: bool
    ttfb_milliseconds: float | None
    total_milliseconds: float
    response_bytes: int
    response_truncated: bool
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class WebBenchmarkResult:
    """Normalized metrics, warnings, and raw evidence from one web run."""

    metrics: tuple[Metric, ...]
    evidence: dict[str, Any]
    warnings: tuple[str, ...] = ()


_Requester = Callable[
    [
        SplitResult,
        WebProfileConfig,
        Sequence[tuple[int, str]],
        int,
        _Timer,
        CancellationToken | None,
    ],
    WebRequestObservation,
]


def _checkpoint(token: CancellationToken | None) -> None:
    if token is not None:
        token.checkpoint()


def _elapsed(started_at: float, timer: _Timer) -> float:
    return max(timer() - started_at, 1e-9)


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _endpoint(parsed: SplitResult) -> tuple[str, int]:
    host = parsed.hostname
    if host is None:
        raise ValueError("target URL does not include a hostname")
    return host, parsed.port or (443 if parsed.scheme == "https" else 80)


def _request_path(parsed: SplitResult) -> str:
    path = parsed.path or "/"
    return f"{path}?{parsed.query}" if parsed.query else path


def _origin(parsed: SplitResult) -> str:
    host = parsed.hostname or "unknown"
    default_port = 443 if parsed.scheme == "https" else 80
    port = parsed.port or default_port
    rendered_host = f"[{host}]" if ":" in host else host
    suffix = "" if port == default_port else f":{port}"
    return f"{parsed.scheme}://{rendered_host}{suffix}"


def _path_hash(parsed: SplitResult) -> str:
    path = parsed.path or "/"
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def _address_allowed(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    scope: NetworkScope,
) -> bool:
    if address.is_unspecified or address.is_multicast or address.is_link_local:
        return False
    if address.is_reserved:
        return False
    if scope is NetworkScope.PUBLIC:
        return not address.is_private and not address.is_loopback
    return True


def _resolve_addresses(
    host: str,
    port: int,
    *,
    resolver: _Resolver,
) -> tuple[tuple[int, str], ...]:
    records = resolver(host, port, type=socket.SOCK_STREAM)
    addresses: list[tuple[int, str]] = []
    for family, _, _, _, sockaddr in records:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        item = (family, str(sockaddr[0]))
        if item not in addresses:
            addresses.append(item)
    if not addresses:
        raise OSError(f"no TCP addresses resolved for {host}")
    return tuple(addresses)


def _validate_addresses(
    addresses: Sequence[tuple[int, str]],
    *,
    scope: NetworkScope,
) -> None:
    rejected: list[str] = []
    for _, raw_address in addresses:
        address = ipaddress.ip_address(raw_address)
        if not _address_allowed(address, scope):
            rejected.append(raw_address)
    if rejected:
        raise WebSafetyError(f"target resolves to addresses disallowed for {scope.value} scope")


class _ResolvedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection pinned to one previously validated address."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        family: int,
        address: str,
        timeout: float,
        tls_context: ssl.SSLContext | None = None,
    ) -> None:
        super().__init__(host, port, timeout=timeout)
        self._family = family
        self._address = address
        self._tls_context = tls_context

    def connect(self) -> None:
        sock = socket.socket(self._family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        target: tuple[Any, ...]
        if self._family == socket.AF_INET6:
            target = (self._address, self.port, 0, 0)
        else:
            target = (self._address, self.port)
        try:
            sock.connect(target)
            if self._tls_context is not None:
                sock = self._tls_context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise
        self.sock = sock


def _connection(
    parsed: SplitResult,
    config: WebProfileConfig,
    addresses: Sequence[tuple[int, str]],
    request_index: int,
) -> http.client.HTTPConnection:
    host, port = _endpoint(parsed)
    family, address = addresses[request_index % len(addresses)]
    context: ssl.SSLContext | None = None
    if parsed.scheme == "https":
        context = ssl.create_default_context()
        if not config.verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
    return _ResolvedHTTPConnection(
        host,
        port,
        family=family,
        address=address,
        timeout=config.timeout_seconds,
        tls_context=context,
    )


def _request_once(
    parsed: SplitResult,
    config: WebProfileConfig,
    addresses: Sequence[tuple[int, str]],
    request_index: int,
    timer: _Timer,
    cancellation_token: CancellationToken | None,
) -> WebRequestObservation:
    _checkpoint(cancellation_token)
    started_at = timer()
    connection = _connection(parsed, config, addresses, request_index)
    try:
        connection.request(
            "GET",
            _request_path(parsed),
            headers={
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "identity",
                "Connection": "close",
                "User-Agent": config.user_agent,
            },
        )
        response = connection.getresponse()
        ttfb_ms = _elapsed(started_at, timer) * 1000.0

        read_limit = config.max_response_bytes + 1
        payload_bytes = 0
        while payload_bytes < read_limit:
            _checkpoint(cancellation_token)
            chunk = response.read(min(64 * 1024, read_limit - payload_bytes))
            if not chunk:
                break
            payload_bytes += len(chunk)

        truncated = payload_bytes > config.max_response_bytes
        bounded_bytes = min(payload_bytes, config.max_response_bytes)
        return WebRequestObservation(
            request_index=request_index,
            status_code=int(response.status),
            success=200 <= response.status < 300,
            ttfb_milliseconds=ttfb_ms,
            total_milliseconds=_elapsed(started_at, timer) * 1000.0,
            response_bytes=bounded_bytes,
            response_truncated=truncated,
        )
    except CancellationRequested:
        raise
    except Exception as error:
        return WebRequestObservation(
            request_index=request_index,
            status_code=None,
            success=False,
            ttfb_milliseconds=None,
            total_milliseconds=_elapsed(started_at, timer) * 1000.0,
            response_bytes=0,
            response_truncated=False,
            error_type=type(error).__name__,
        )
    finally:
        connection.close()


def _metric(name: str, value: float, unit: str, direction: MetricDirection) -> Metric:
    return Metric(name=name, value=value, unit=unit, direction=direction)


def benchmark_web_profile(
    *,
    config: WebProfileConfig,
    timer: _Timer = time.perf_counter,
    resolver: _Resolver = socket.getaddrinfo,
    requester: _Requester = _request_once,
    cancellation_token: CancellationToken | None = None,
) -> WebBenchmarkResult:
    """Run one bounded concurrent HTTP GET workload against an explicit target."""

    _checkpoint(cancellation_token)
    target = urlsplit(config.target_url)
    host, port = _endpoint(target)
    addresses = _resolve_addresses(host, port, resolver=resolver)
    _validate_addresses(addresses, scope=config.scope)

    warmup_failures = 0
    for index in range(config.warmup_requests):
        _checkpoint(cancellation_token)
        observation = requester(
            target,
            config,
            addresses,
            -(index + 1),
            timer,
            cancellation_token,
        )
        if not observation.success:
            warmup_failures += 1

    _checkpoint(cancellation_token)
    benchmark_started = timer()
    observations: list[WebRequestObservation] = []
    with ThreadPoolExecutor(
        max_workers=config.concurrency,
        thread_name_prefix="cloudeyes-web",
    ) as executor:
        futures = [
            executor.submit(
                requester,
                target,
                config,
                addresses,
                index,
                timer,
                cancellation_token,
            )
            for index in range(config.request_count)
        ]
        for future in as_completed(futures):
            _checkpoint(cancellation_token)
            observations.append(future.result())
    elapsed_seconds = _elapsed(benchmark_started, timer)
    observations.sort(key=lambda item: item.request_index)

    successful = [item for item in observations if item.success]
    if not successful:
        raise OSError("all bounded web requests failed")

    ttfb_values = [
        item.ttfb_milliseconds for item in successful if item.ttfb_milliseconds is not None
    ]
    total_values = [item.total_milliseconds for item in successful]
    success_count = len(successful)
    failure_count = len(observations) - success_count
    total_bytes = sum(item.response_bytes for item in successful)

    metrics = (
        _metric(
            "web.http.successful_requests_per_second",
            success_count / elapsed_seconds,
            "requests_per_second",
            MetricDirection.HIGHER_IS_BETTER,
        ),
        _metric(
            "web.http.error_rate.percent",
            failure_count / len(observations) * 100.0,
            "percent",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "web.http.ttfb.p50_milliseconds",
            statistics.median(ttfb_values),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "web.http.ttfb.p95_milliseconds",
            _percentile(ttfb_values, 0.95),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "web.http.total_latency.p50_milliseconds",
            statistics.median(total_values),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "web.http.total_latency.p95_milliseconds",
            _percentile(total_values, 0.95),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "web.http.total_latency.p99_milliseconds",
            _percentile(total_values, 0.99),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "web.http.response_throughput.mib_per_second",
            total_bytes / _MIB / elapsed_seconds,
            "mib_per_second",
            MetricDirection.HIGHER_IS_BETTER,
        ),
    )

    warnings: list[str] = []
    if warmup_failures:
        warnings.append("web_warmup_failures")
    if failure_count:
        warnings.append("web_partial_request_failures")
    if any(item.response_truncated for item in observations):
        warnings.append("web_response_body_truncated")
    if any(item.status_code is not None and 300 <= item.status_code < 400 for item in observations):
        warnings.append("web_redirect_responses_observed")
    if any(item.status_code is not None and item.status_code >= 500 for item in observations):
        warnings.append("web_server_error_responses_observed")
    if total_bytes == 0:
        warnings.append("web_empty_response_bodies")
    if not config.verify_tls and target.scheme == "https":
        warnings.append("tls_verification_disabled")

    status_counts = Counter(
        str(item.status_code) for item in observations if item.status_code is not None
    )
    error_counts = Counter(item.error_type for item in observations if item.error_type is not None)
    family_names = tuple(
        dict.fromkeys("ipv6" if family == socket.AF_INET6 else "ipv4" for family, _ in addresses)
    )

    evidence = {
        "profile": "web",
        "protocol_version": config.version,
        "target": {
            "origin": _origin(target),
            "path_sha256": _path_hash(target),
            "query_present": bool(target.query),
            "scope": config.scope.value,
            "resolved_address_families": family_names,
        },
        "workload": {
            "method": "GET",
            "request_count": config.request_count,
            "concurrency": config.concurrency,
            "warmup_requests": config.warmup_requests,
            "timeout_seconds": config.timeout_seconds,
            "max_response_bytes": config.max_response_bytes,
            "verify_tls": config.verify_tls,
            "connection_reuse": False,
        },
        "summary": {
            "elapsed_seconds": elapsed_seconds,
            "successful_requests": success_count,
            "failed_requests": failure_count,
            "response_bytes": total_bytes,
            "status_counts": dict(sorted(status_counts.items())),
            "error_type_counts": dict(sorted(error_counts.items())),
        },
        "requests": [asdict(item) for item in observations],
        "warnings": tuple(dict.fromkeys(warnings)),
    }
    return WebBenchmarkResult(
        metrics=metrics,
        evidence=evidence,
        warnings=tuple(dict.fromkeys(warnings)),
    )

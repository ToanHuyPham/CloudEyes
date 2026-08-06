"""Bounded networking benchmarks using only the Python standard library."""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import math
import platform
import re
import shutil
import socket
import ssl
import statistics
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import SplitResult, urlsplit

from cloudeyes_core.models import Metric, MetricDirection

from ...execution import CancellationRequested, CancellationToken
from .config import NetworkingProfileConfig, NetworkScope

_MIB = 1024 * 1024
_Timer = Callable[[], float]
_Resolver = Callable[..., list[tuple[Any, ...]]]


class NetworkingSafetyError(RuntimeError):
    """Raised when a target violates the configured network-scope policy."""


@dataclass(frozen=True, slots=True)
class NetworkingBenchmarkResult:
    """Normalized metrics, warnings, and raw evidence from one network run."""

    metrics: tuple[Metric, ...]
    evidence: dict[str, Any]
    warnings: tuple[str, ...] = ()


def _elapsed(started_at: float, timer: _Timer) -> float:
    return max(timer() - started_at, 1e-9)


def _checkpoint(token: CancellationToken | None) -> None:
    if token is not None:
        token.checkpoint()


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


def _resolve_once(
    host: str,
    port: int,
    *,
    resolver: _Resolver,
    timer: _Timer,
) -> tuple[float, tuple[tuple[int, str], ...]]:
    started = timer()
    records = resolver(host, port, type=socket.SOCK_STREAM)
    elapsed_ms = _elapsed(started, timer) * 1000.0

    addresses: list[tuple[int, str]] = []
    for family, _, _, _, sockaddr in records:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        address = str(sockaddr[0])
        item = (family, address)
        if item not in addresses:
            addresses.append(item)
    if not addresses:
        raise OSError(f"no TCP addresses resolved for {host}")
    return elapsed_ms, tuple(addresses)


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
        rendered = ", ".join(rejected)
        raise NetworkingSafetyError(
            f"target resolves to addresses disallowed for {scope.value} scope: {rendered}"
        )


def _connect_address(
    family: int,
    address: str,
    port: int,
    *,
    timeout: float,
    timer: _Timer,
) -> tuple[socket.socket, float]:
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    target: tuple[Any, ...]
    if family == socket.AF_INET6:
        target = (address, port, 0, 0)
    else:
        target = (address, port)
    started = timer()
    try:
        sock.connect(target)
    except Exception:
        sock.close()
        raise
    return sock, _elapsed(started, timer) * 1000.0


def _connect_resolved(
    addresses: Sequence[tuple[int, str]],
    port: int,
    *,
    timeout: float,
    timer: _Timer,
) -> tuple[socket.socket, float, int]:
    started = timer()
    last_error: OSError | None = None
    for family, address in addresses:
        try:
            sock, _ = _connect_address(
                family,
                address,
                port,
                timeout=timeout,
                timer=timer,
            )
            return sock, _elapsed(started, timer) * 1000.0, family
        except OSError as error:
            last_error = error
    raise OSError("none of the resolved target addresses accepted a TCP connection") from last_error


def _tls_handshake(
    sock: socket.socket,
    *,
    host: str,
    verify_tls: bool,
    timer: _Timer,
) -> tuple[ssl.SSLSocket, float, str | None]:
    context = ssl.create_default_context()
    if not verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    started = timer()
    wrapped = context.wrap_socket(sock, server_hostname=host)
    elapsed_ms = _elapsed(started, timer) * 1000.0
    return wrapped, elapsed_ms, wrapped.version()


def _connection(parsed: SplitResult, config: NetworkingProfileConfig) -> http.client.HTTPConnection:
    host, port = _endpoint(parsed)
    if parsed.scheme == "https":
        context = ssl.create_default_context()
        if not config.verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return http.client.HTTPSConnection(
            host,
            port,
            timeout=config.timeout_seconds,
            context=context,
        )
    return http.client.HTTPConnection(host, port, timeout=config.timeout_seconds)


def _http_download_probe(
    parsed: SplitResult,
    config: NetworkingProfileConfig,
    *,
    timer: _Timer,
    cancellation_token: CancellationToken | None = None,
) -> dict[str, Any]:
    _checkpoint(cancellation_token)
    connection = _connection(parsed, config)
    request_started = timer()
    try:
        connection.request(
            "GET",
            _request_path(parsed),
            headers={
                "Accept": "application/octet-stream,*/*;q=0.8",
                "Connection": "close",
                "User-Agent": config.user_agent,
            },
        )
        response = connection.getresponse()
        ttfb_ms = _elapsed(request_started, timer) * 1000.0
        if not 200 <= response.status < 400:
            response.read()
            raise OSError(f"HTTP download returned status {response.status}")

        downloaded = 0
        download_started = timer()
        while downloaded < config.download_limit_bytes:
            _checkpoint(cancellation_token)
            chunk = response.read(min(64 * 1024, config.download_limit_bytes - downloaded))
            if not chunk:
                break
            downloaded += len(chunk)
        download_seconds = _elapsed(download_started, timer)
        return {
            "status": response.status,
            "ttfb_milliseconds": ttfb_ms,
            "downloaded_bytes": downloaded,
            "download_seconds": download_seconds,
            "download_mib_per_second": downloaded / _MIB / download_seconds,
        }
    finally:
        connection.close()


def _http_upload_probe(
    parsed: SplitResult,
    config: NetworkingProfileConfig,
    *,
    timer: _Timer,
    cancellation_token: CancellationToken | None = None,
) -> dict[str, Any]:
    _checkpoint(cancellation_token)
    payload = b"\xa5" * config.upload_bytes
    connection = _connection(parsed, config)
    started = timer()
    try:
        connection.request(
            "POST",
            _request_path(parsed),
            body=payload,
            headers={
                "Connection": "close",
                "Content-Type": "application/octet-stream",
                "User-Agent": config.user_agent,
            },
        )
        response = connection.getresponse()
        response.read()
        _checkpoint(cancellation_token)
        elapsed_seconds = _elapsed(started, timer)
        if not 200 <= response.status < 400:
            raise OSError(f"HTTP upload returned status {response.status}")
        return {
            "status": response.status,
            "uploaded_bytes": len(payload),
            "upload_seconds": elapsed_seconds,
            "upload_mib_per_second": len(payload) / _MIB / elapsed_seconds,
        }
    finally:
        connection.close()


def parse_packet_loss(output: str) -> float | None:
    """Parse packet-loss percentage from common Unix and Windows ping output."""

    patterns = (
        r"(?P<loss>\d+(?:\.\d+)?)%\s*packet loss",
        r"\((?P<loss>\d+(?:\.\d+)?)%\s*loss\)",
    )
    for pattern in patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE)
        if match:
            return float(match.group("loss"))
    return None


def _ping_command(host: str, *, count: int, timeout: float) -> list[str]:
    if platform.system().lower() == "windows":
        return ["ping", "-n", str(count), "-w", str(math.ceil(timeout * 1000)), host]
    return ["ping", "-c", str(count), "-W", str(max(1, math.ceil(timeout))), host]


def _ping_probe(
    host: str,
    config: NetworkingProfileConfig,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
    cancellation_token: CancellationToken | None = None,
) -> tuple[float | None, str | None]:
    _checkpoint(cancellation_token)
    if config.ping_count == 0:
        return None, "icmp_sampling_disabled"
    if shutil.which("ping") is None:
        return None, "ping_command_unavailable"

    command = _ping_command(
        host,
        count=config.ping_count,
        timeout=config.timeout_seconds,
    )
    try:
        result = run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds * config.ping_count + 5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None, "icmp_sampling_failed"

    output = f"{result.stdout}\n{result.stderr}"
    loss = parse_packet_loss(output)
    if loss is None:
        return None, "icmp_output_unrecognized"
    return loss, None


def _metric(name: str, value: float, unit: str, direction: MetricDirection) -> Metric:
    return Metric(name=name, value=value, unit=unit, direction=direction)


def benchmark_networking_profile(
    *,
    config: NetworkingProfileConfig,
    timer: _Timer = time.perf_counter,
    resolver: _Resolver = socket.getaddrinfo,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    cancellation_token: CancellationToken | None = None,
) -> NetworkingBenchmarkResult:
    """Measure one explicit HTTP(S) endpoint with bounded traffic and timeouts."""

    _checkpoint(cancellation_token)
    target = urlsplit(config.target_url)
    target_host, target_port = _endpoint(target)

    dns_latencies: list[float] = []
    resolved: tuple[tuple[int, str], ...] = ()
    for _ in range(config.repetitions):
        _checkpoint(cancellation_token)
        latency, addresses = _resolve_once(
            target_host,
            target_port,
            resolver=resolver,
            timer=timer,
        )
        dns_latencies.append(latency)
        resolved = addresses
    _validate_addresses(resolved, scope=config.scope)

    tcp_latencies: list[float] = []
    tls_latencies: list[float] = []
    tls_versions: list[str] = []
    selected_families: list[int] = []
    for _ in range(config.repetitions):
        _checkpoint(cancellation_token)
        sock, tcp_latency, selected_family = _connect_resolved(
            resolved,
            target_port,
            timeout=config.timeout_seconds,
            timer=timer,
        )
        selected_families.append(selected_family)
        tcp_latencies.append(tcp_latency)
        if target.scheme == "https":
            wrapped: ssl.SSLSocket | None = None
            try:
                wrapped, tls_latency, tls_version = _tls_handshake(
                    sock,
                    host=target_host,
                    verify_tls=config.verify_tls,
                    timer=timer,
                )
                tls_latencies.append(tls_latency)
                if tls_version:
                    tls_versions.append(tls_version)
            finally:
                (wrapped or sock).close()
        else:
            sock.close()

    download_runs: list[dict[str, Any]] = []
    download_errors: list[str] = []
    for _ in range(config.repetitions):
        _checkpoint(cancellation_token)
        try:
            download_runs.append(
                _http_download_probe(
                    target,
                    config,
                    timer=timer,
                    cancellation_token=cancellation_token,
                )
            )
        except CancellationRequested:
            raise
        except Exception as error:
            download_errors.append(type(error).__name__)

    upload_runs: list[dict[str, Any]] = []
    upload_errors: list[str] = []
    upload_target = urlsplit(config.upload_url) if config.upload_url is not None else None
    if upload_target is not None:
        upload_host, upload_port = _endpoint(upload_target)
        _, upload_addresses = _resolve_once(
            upload_host,
            upload_port,
            resolver=resolver,
            timer=timer,
        )
        _validate_addresses(upload_addresses, scope=config.scope)
        for _ in range(config.repetitions):
            _checkpoint(cancellation_token)
            try:
                upload_runs.append(
                    _http_upload_probe(
                        upload_target,
                        config,
                        timer=timer,
                        cancellation_token=cancellation_token,
                    )
                )
            except CancellationRequested:
                raise
            except Exception as error:
                upload_errors.append(type(error).__name__)

    warnings: list[str] = []
    if not download_runs:
        warnings.append("http_download_failed")
    elif statistics.median(run_data["downloaded_bytes"] for run_data in download_runs) < 64 * 1024:
        warnings.append("download_payload_too_small")
    if upload_target is None:
        warnings.append("upload_target_not_configured")
    elif not upload_runs:
        warnings.append("http_upload_failed")
    if not config.verify_tls and target.scheme == "https":
        warnings.append("tls_verification_disabled")

    packet_loss, ping_warning = _ping_probe(
        target_host,
        config,
        run=run,
        cancellation_token=cancellation_token,
    )
    if ping_warning is not None:
        warnings.append(ping_warning)

    _checkpoint(cancellation_token)
    metrics: list[Metric] = [
        _metric(
            "network.dns.lookup.p50_milliseconds",
            _percentile(dns_latencies, 0.50),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "network.dns.lookup.p95_milliseconds",
            _percentile(dns_latencies, 0.95),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "network.tcp.connect.p50_milliseconds",
            _percentile(tcp_latencies, 0.50),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
        _metric(
            "network.tcp.connect.p95_milliseconds",
            _percentile(tcp_latencies, 0.95),
            "milliseconds",
            MetricDirection.LOWER_IS_BETTER,
        ),
    ]
    if tls_latencies:
        metrics.extend(
            (
                _metric(
                    "network.tls.handshake.p50_milliseconds",
                    _percentile(tls_latencies, 0.50),
                    "milliseconds",
                    MetricDirection.LOWER_IS_BETTER,
                ),
                _metric(
                    "network.tls.handshake.p95_milliseconds",
                    _percentile(tls_latencies, 0.95),
                    "milliseconds",
                    MetricDirection.LOWER_IS_BETTER,
                ),
            )
        )

    request_attempts = config.repetitions
    request_failures = len(download_errors)
    metrics.append(
        _metric(
            "network.http.request_loss_percent",
            request_failures / request_attempts * 100.0,
            "percent",
            MetricDirection.LOWER_IS_BETTER,
        )
    )
    if download_runs:
        metrics.extend(
            (
                _metric(
                    "network.http.ttfb.p50_milliseconds",
                    _percentile(
                        [run_data["ttfb_milliseconds"] for run_data in download_runs],
                        0.50,
                    ),
                    "milliseconds",
                    MetricDirection.LOWER_IS_BETTER,
                ),
                _metric(
                    "network.http.ttfb.p95_milliseconds",
                    _percentile(
                        [run_data["ttfb_milliseconds"] for run_data in download_runs],
                        0.95,
                    ),
                    "milliseconds",
                    MetricDirection.LOWER_IS_BETTER,
                ),
                _metric(
                    "network.download.mib_per_second",
                    statistics.median(
                        run_data["download_mib_per_second"] for run_data in download_runs
                    ),
                    "mib_per_second",
                    MetricDirection.HIGHER_IS_BETTER,
                ),
            )
        )
    if upload_runs:
        metrics.append(
            _metric(
                "network.upload.mib_per_second",
                statistics.median(run_data["upload_mib_per_second"] for run_data in upload_runs),
                "mib_per_second",
                MetricDirection.HIGHER_IS_BETTER,
            )
        )
    if packet_loss is not None:
        metrics.append(
            _metric(
                "network.icmp.packet_loss_percent",
                packet_loss,
                "percent",
                MetricDirection.LOWER_IS_BETTER,
            )
        )

    address_families = sorted(
        {"ipv4" if family_value == socket.AF_INET else "ipv6" for family_value, _ in resolved}
    )
    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile": "networking",
        "protocol_version": config.version,
        "configuration": {
            **asdict(config),
            "scope": config.scope.value,
            "target_url": None,
            "upload_url": None,
        },
        "target": {
            "origin": _origin(target),
            "path_sha256": _path_hash(target),
            "scope": config.scope.value,
            "resolved_address_count": len(resolved),
            "address_families": address_families,
            "selected_address_families": sorted(
                {
                    "ipv4" if family_value == socket.AF_INET else "ipv6"
                    for family_value in selected_families
                }
            ),
        },
        "dns_latencies_milliseconds": dns_latencies,
        "tcp_connect_latencies_milliseconds": tcp_latencies,
        "tls_handshake_latencies_milliseconds": tls_latencies,
        "tls_versions": sorted(set(tls_versions)),
        "download_runs": download_runs,
        "download_error_types": download_errors,
        "upload": {
            "configured": upload_target is not None,
            "origin": _origin(upload_target) if upload_target is not None else None,
            "path_sha256": _path_hash(upload_target) if upload_target is not None else None,
            "runs": upload_runs,
            "error_types": upload_errors,
        },
        "icmp_packet_loss_percent": packet_loss,
        "warnings": list(dict.fromkeys(warnings)),
        "limitations": [
            "results describe the configured endpoint path and route at measurement time",
            "HTTP throughput includes application, TCP, and optional TLS overhead",
            "ICMP loss may differ from TCP or HTTP behavior because networks can filter ping",
            "no response body, request body, query string, credential, or resolved IP is persisted",
        ],
    }
    return NetworkingBenchmarkResult(
        metrics=tuple(metrics),
        evidence=evidence,
        warnings=tuple(dict.fromkeys(warnings)),
    )

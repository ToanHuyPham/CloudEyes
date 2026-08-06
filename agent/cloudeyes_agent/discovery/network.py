"""Privacy-safe local network capability discovery."""

from __future__ import annotations

import socket

from .model import NetworkInfo


def _interface_count() -> int:
    try:
        return len(socket.if_nameindex())
    except (AttributeError, OSError):
        return 0


def _hostname_resolves() -> bool:
    try:
        socket.getaddrinfo(socket.gethostname(), None)
    except OSError:
        return False
    return True


def discover_network() -> NetworkInfo:
    """Collect capability flags without storing addresses or interface names."""

    return NetworkInfo(
        interface_count=_interface_count(),
        supports_ipv4=hasattr(socket, "AF_INET"),
        supports_ipv6=bool(getattr(socket, "has_ipv6", False)),
        hostname_resolves=_hostname_resolves(),
    )

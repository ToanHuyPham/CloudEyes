"""Operating system discovery."""

from __future__ import annotations

import platform
from datetime import datetime

from .model import SystemInfo


def discover_system() -> SystemInfo:
    """Collect portable operating system and Python runtime details."""

    now = datetime.now().astimezone()
    timezone_name = now.tzname() or str(now.utcoffset() or "UTC")

    return SystemInfo(
        os_name=platform.system() or "unknown",
        os_version=platform.version() or "unknown",
        kernel_version=platform.release() or "unknown",
        architecture=platform.machine() or "unknown",
        python_version=platform.python_version(),
        timezone=timezone_name,
    )

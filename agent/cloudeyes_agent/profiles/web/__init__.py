"""CloudEyes Web Profile v1 public API."""

from .benchmarks import (
    WebBenchmarkResult,
    WebRequestObservation,
    WebSafetyError,
    benchmark_web_profile,
)
from .config import NetworkScope, WebProfileConfig
from .profile import run_web_profile

__all__ = [
    "NetworkScope",
    "WebBenchmarkResult",
    "WebProfileConfig",
    "WebRequestObservation",
    "WebSafetyError",
    "benchmark_web_profile",
    "run_web_profile",
]

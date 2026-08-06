"""Public API for the CloudEyes General Profile."""

from .benchmarks import benchmark_cpu, benchmark_memory, benchmark_storage
from .config import GeneralProfileConfig
from .profile import run_general_profile

__all__ = [
    "GeneralProfileConfig",
    "benchmark_cpu",
    "benchmark_memory",
    "benchmark_storage",
    "run_general_profile",
]

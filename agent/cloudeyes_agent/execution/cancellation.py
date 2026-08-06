"""Cooperative cancellation primitives shared by profile workloads."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


class CancellationRequested(RuntimeError):
    """Raised at a safe checkpoint after cancellation has been requested."""


@dataclass(slots=True)
class CancellationToken:
    """Small wrapper around a thread-safe or process-safe event.

    The token is intentionally poll-based. Benchmarks call ``checkpoint`` only at
    safe boundaries so open files, sockets, and temporary directories are closed by
    their normal context managers before control leaves the worker process.
    """

    _event: Any

    @classmethod
    def local(cls) -> CancellationToken:
        """Return a token suitable for in-process execution and unit tests."""

        return cls(threading.Event())

    @property
    def is_cancellation_requested(self) -> bool:
        """Return whether cancellation has been requested."""

        return bool(self._event.is_set())

    def request_cancellation(self) -> None:
        """Request cancellation without blocking the caller."""

        self._event.set()

    def checkpoint(self) -> None:
        """Raise ``CancellationRequested`` when cancellation is pending."""

        if self.is_cancellation_requested:
            raise CancellationRequested("CloudEyes execution cancellation requested")

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for cancellation and return ``True`` when it was requested."""

        return bool(self._event.wait(timeout))

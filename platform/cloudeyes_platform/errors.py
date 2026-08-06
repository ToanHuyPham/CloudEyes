"""Typed errors exposed by the ingestion boundary."""

from __future__ import annotations


class IngestionError(RuntimeError):
    """A safe client-facing ingestion failure."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        quarantine: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.quarantine = quarantine
        self.quarantine_id: str | None = None


class ConfigurationError(ValueError):
    """Raised when the ingestion service configuration is unsafe."""


__all__ = ["ConfigurationError", "IngestionError"]

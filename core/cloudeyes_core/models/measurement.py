"""Measurement model produced by one benchmark tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .metric import Metric


class MeasurementStatus(StrEnum):
    """Execution status of a measurement."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class Measurement:
    """One tool execution containing zero or more normalized metrics."""

    measurement_id: str
    tool: str
    tool_version: str | None
    profile: str
    protocol_version: str
    started_at: datetime
    finished_at: datetime
    status: MeasurementStatus
    metrics: tuple[Metric, ...] = field(default_factory=tuple)
    raw_output_path: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("measurement_id", "tool", "profile", "protocol_version"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)

        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("measurement timestamps must contain timezone information")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not be earlier than started_at")

        status = (
            self.status
            if isinstance(self.status, MeasurementStatus)
            else MeasurementStatus(self.status)
        )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "metrics", tuple(self.metrics))

        if status is MeasurementStatus.SUCCESS and not self.metrics:
            raise ValueError("successful measurements must contain at least one metric")
        if status is MeasurementStatus.FAILED and not (self.error and self.error.strip()):
            raise ValueError("failed measurements must contain an error message")

        for field_name in ("tool_version", "raw_output_path", "error"):
            value = getattr(self, field_name)
            if value is not None:
                cleaned = value.strip()
                object.__setattr__(self, field_name, cleaned or None)

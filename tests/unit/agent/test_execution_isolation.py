"""Tests for process-isolated execution and hard deadlines."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from cloudeyes_agent.execution import (
    CancellationToken,
    IsolatedExecutionError,
    IsolatedExecutionTimeout,
    run_isolated,
)


def _return_sum(*, left: int, right: int) -> int:
    return left + right


def _raise_error() -> None:
    raise RuntimeError("worker exploded")


def _sleep_forever() -> None:
    time.sleep(30)


def _wait_for_cancellation(
    *,
    marker_path: str,
    cancellation_token: CancellationToken,
) -> None:
    try:
        while True:
            cancellation_token.checkpoint()
            time.sleep(0.01)
    finally:
        Path(marker_path).write_text("cleanup-complete", encoding="utf-8")


def test_run_isolated_returns_picklable_value() -> None:
    result = run_isolated(
        _return_sum,
        kwargs={"left": 2, "right": 5},
        timeout_seconds=5,
    )

    assert result.value == 7
    assert result.exit_code == 0


def test_run_isolated_propagates_child_error() -> None:
    with pytest.raises(IsolatedExecutionError, match="worker exploded"):
        run_isolated(_raise_error, timeout_seconds=5)


def test_run_isolated_enforces_hard_timeout() -> None:
    started = time.monotonic()

    with pytest.raises(IsolatedExecutionTimeout, match="exceeded"):
        run_isolated(
            _sleep_forever,
            timeout_seconds=0.2,
            grace_seconds=0.1,
        )

    assert time.monotonic() - started < 5


def test_run_isolated_rejects_invalid_deadline() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        run_isolated(_return_sum, timeout_seconds=0)


def test_run_isolated_requests_cooperative_cleanup_before_termination(tmp_path) -> None:
    marker = tmp_path / "cleanup.txt"

    with pytest.raises(IsolatedExecutionTimeout, match="cooperative cleanup completed"):
        run_isolated(
            _wait_for_cancellation,
            kwargs={"marker_path": str(marker)},
            timeout_seconds=0.2,
            grace_seconds=2.0,
            cancellation_kwarg="cancellation_token",
        )

    assert marker.read_text(encoding="utf-8") == "cleanup-complete"


def test_run_isolated_rejects_empty_cancellation_keyword() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        run_isolated(
            _return_sum,
            timeout_seconds=1,
            cancellation_kwarg="",
        )

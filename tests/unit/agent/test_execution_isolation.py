"""Tests for process-isolated execution and hard deadlines."""

from __future__ import annotations

import time

import pytest
from cloudeyes_agent.execution import (
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

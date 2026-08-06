"""Cross-platform process isolation with bounded shutdown semantics."""

from __future__ import annotations

import multiprocessing as mp
import queue
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class IsolatedExecutionError(RuntimeError):
    """Raised when an isolated child fails without returning a value."""


class IsolatedExecutionTimeout(TimeoutError):
    """Raised when an isolated child exceeds its wall-clock deadline."""


@dataclass(frozen=True, slots=True)
class IsolatedExecutionResult(Generic[T]):
    """Value and process metadata returned by an isolated execution."""

    value: T
    exit_code: int


def _child_entry(
    result_queue: Any,
    target: Callable[..., T],
    kwargs: Mapping[str, Any],
) -> None:
    try:
        value = target(**dict(kwargs))
    except BaseException as exc:  # pragma: no cover - exercised through parent API
        result_queue.put(
            (
                "error",
                type(exc).__name__,
                str(exc),
                traceback.format_exc(),
            )
        )
        return
    result_queue.put(("ok", value))


def _stop_process(process: mp.Process, *, grace_seconds: float) -> None:
    if not process.is_alive():
        process.join()
        return
    process.terminate()
    process.join(grace_seconds)
    if process.is_alive():
        kill = getattr(process, "kill", None)
        if kill is not None:
            kill()
        else:  # pragma: no cover - supported Python versions expose kill
            process.terminate()
        process.join()


def run_isolated(
    target: Callable[..., T],
    *,
    kwargs: Mapping[str, Any] | None = None,
    timeout_seconds: float,
    grace_seconds: float = 2.0,
    start_method: str = "spawn",
) -> IsolatedExecutionResult[T]:
    """Run a top-level callable in a child process and enforce a hard timeout.

    ``spawn`` is deliberately used on every platform so Windows and Linux follow
    the same import and serialization path. The target and its arguments must be
    picklable.
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if grace_seconds < 0:
        raise ValueError("grace_seconds must not be negative")

    context = mp.get_context(start_method)
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_child_entry,
        args=(result_queue, target, dict(kwargs or {})),
        name="cloudeyes-profile-worker",
    )
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        _stop_process(process, grace_seconds=grace_seconds)
        result_queue.close()
        result_queue.join_thread()
        raise IsolatedExecutionTimeout(f"isolated execution exceeded {timeout_seconds:g} seconds")

    exit_code = process.exitcode if process.exitcode is not None else 1
    try:
        payload = result_queue.get(timeout=1.0)
    except queue.Empty as exc:
        result_queue.close()
        result_queue.join_thread()
        raise IsolatedExecutionError(
            f"isolated child exited with code {exit_code} without returning a result"
        ) from exc
    finally:
        process.join()

    result_queue.close()
    result_queue.join_thread()
    if payload[0] == "ok":
        return IsolatedExecutionResult(value=payload[1], exit_code=exit_code)

    _, error_type, message, child_traceback = payload
    detail = f"{error_type}: {message}" if message else str(error_type)
    raise IsolatedExecutionError(f"{detail}\n{child_traceback}")

"""Cross-platform process isolation with cooperative and hard shutdown semantics."""

from __future__ import annotations

import multiprocessing as mp
import queue
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from .cancellation import CancellationToken

T = TypeVar("T")


class IsolatedExecutionError(RuntimeError):
    """Raised when an isolated child fails without returning a value."""


class IsolatedExecutionTimeout(TimeoutError):
    """Raised when an isolated child exceeds its wall-clock deadline."""


class IsolatedExecutionCancelled(InterruptedError):
    """Raised when the parent is interrupted while an isolated child is running."""


@dataclass(frozen=True, slots=True)
class IsolatedExecutionResult(Generic[T]):
    """Value and process metadata returned by an isolated execution."""

    value: T
    exit_code: int


def _child_entry(
    result_queue: Any,
    target: Callable[..., T],
    kwargs: Mapping[str, Any],
    cancellation_event: Any,
    cancellation_kwarg: str | None,
) -> None:
    child_kwargs = dict(kwargs)
    if cancellation_kwarg is not None:
        child_kwargs[cancellation_kwarg] = CancellationToken(cancellation_event)

    try:
        value = target(**child_kwargs)
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


def _hard_stop_process(process: mp.Process, *, terminate_grace_seconds: float) -> None:
    if not process.is_alive():
        process.join()
        return

    process.terminate()
    process.join(terminate_grace_seconds)
    if process.is_alive():
        kill = getattr(process, "kill", None)
        if kill is not None:
            kill()
        else:  # pragma: no cover - supported Python versions expose kill
            process.terminate()
        process.join()


def _request_cooperative_stop(
    process: mp.Process,
    token: CancellationToken,
    *,
    grace_seconds: float,
    terminate_grace_seconds: float,
) -> bool:
    """Request cancellation, then hard-stop only when cleanup does not finish."""

    token.request_cancellation()
    process.join(grace_seconds)
    if not process.is_alive():
        return True

    _hard_stop_process(process, terminate_grace_seconds=terminate_grace_seconds)
    return False


def _close_queue(result_queue: Any) -> None:
    result_queue.close()
    result_queue.join_thread()


def run_isolated(
    target: Callable[..., T],
    *,
    kwargs: Mapping[str, Any] | None = None,
    timeout_seconds: float,
    grace_seconds: float = 2.0,
    terminate_grace_seconds: float = 1.0,
    start_method: str = "spawn",
    cancellation_kwarg: str | None = None,
) -> IsolatedExecutionResult[T]:
    """Run a top-level callable in a child process and enforce a hard timeout.

    ``spawn`` is deliberately used on every platform so Windows and Linux follow
    the same import and serialization path. When ``cancellation_kwarg`` is set, a
    process-safe :class:`CancellationToken` is injected into the child callable.
    The parent requests cooperative cancellation before using terminate/kill.
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if grace_seconds < 0:
        raise ValueError("grace_seconds must not be negative")
    if terminate_grace_seconds < 0:
        raise ValueError("terminate_grace_seconds must not be negative")
    if cancellation_kwarg == "":
        raise ValueError("cancellation_kwarg must not be empty")

    context = mp.get_context(start_method)
    cancellation_token = CancellationToken(context.Event())
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_child_entry,
        args=(
            result_queue,
            target,
            dict(kwargs or {}),
            cancellation_token._event,
            cancellation_kwarg,
        ),
        name="cloudeyes-profile-worker",
    )
    process.start()

    try:
        process.join(timeout_seconds)
    except KeyboardInterrupt as exc:
        cooperative = _request_cooperative_stop(
            process,
            cancellation_token,
            grace_seconds=grace_seconds,
            terminate_grace_seconds=terminate_grace_seconds,
        )
        _close_queue(result_queue)
        detail = "cooperative cleanup completed" if cooperative else "hard termination required"
        raise IsolatedExecutionCancelled(f"isolated execution interrupted; {detail}") from exc

    if process.is_alive():
        cooperative = _request_cooperative_stop(
            process,
            cancellation_token,
            grace_seconds=grace_seconds,
            terminate_grace_seconds=terminate_grace_seconds,
        )
        _close_queue(result_queue)
        detail = "cooperative cleanup completed" if cooperative else "hard termination required"
        raise IsolatedExecutionTimeout(
            f"isolated execution exceeded {timeout_seconds:g} seconds; {detail}"
        )

    exit_code = process.exitcode if process.exitcode is not None else 1
    try:
        payload = result_queue.get(timeout=1.0)
    except queue.Empty as exc:
        _close_queue(result_queue)
        raise IsolatedExecutionError(
            f"isolated child exited with code {exit_code} without returning a result"
        ) from exc
    finally:
        process.join()

    _close_queue(result_queue)
    if payload[0] == "ok":
        return IsolatedExecutionResult(value=payload[1], exit_code=exit_code)

    _, error_type, message, child_traceback = payload
    detail = f"{error_type}: {message}" if message else str(error_type)
    raise IsolatedExecutionError(f"{detail}\n{child_traceback}")

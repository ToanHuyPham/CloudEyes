"""Tests for cooperative cancellation tokens."""

from __future__ import annotations

import pytest
from cloudeyes_agent.execution import CancellationRequested, CancellationToken


def test_local_token_is_idle_until_requested() -> None:
    token = CancellationToken.local()

    assert token.is_cancellation_requested is False
    assert token.wait(0) is False
    token.checkpoint()

    token.request_cancellation()

    assert token.is_cancellation_requested is True
    assert token.wait(0) is True
    with pytest.raises(CancellationRequested, match="cancellation requested"):
        token.checkpoint()

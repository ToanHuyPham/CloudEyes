"""Tests for authentication and server application state."""

from __future__ import annotations

import pytest
from cloudeyes_platform.config import IngestionConfig
from cloudeyes_platform.server import IngestionApplication, TokenAuthenticator


def test_token_authenticator_uses_bearer_scheme() -> None:
    authenticator = TokenAuthenticator("secret-token", allow_anonymous=False)

    assert authenticator.authorized("Bearer secret-token")
    assert not authenticator.authorized("secret-token")
    assert not authenticator.authorized("Bearer wrong")
    assert not authenticator.authorized(None)


def test_missing_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="bearer token"):
        TokenAuthenticator(None, allow_anonymous=False)


def test_health_reports_repository_counts(tmp_path) -> None:
    app = IngestionApplication(
        IngestionConfig(tmp_path / "service"),
        token=None,
        allow_anonymous=True,
    )

    assert app.health() == {
        "counts": {"evidence": 0, "samples": 0, "submissions": 0},
        "schema_version": "1.0.0",
        "status": "ok",
    }

"""Tests for safe ingestion configuration."""

from __future__ import annotations

import pytest
from cloudeyes_platform.config import IngestionConfig, validate_bind_policy
from cloudeyes_platform.errors import ConfigurationError


def test_config_prepares_private_layout(tmp_path) -> None:
    config = IngestionConfig(tmp_path / "platform")
    config.prepare()

    assert config.database_path.parent == config.data_dir
    assert config.bundle_dir.is_dir()
    assert config.quarantine_dir.is_dir()
    assert config.temporary_dir.is_dir()


def test_anonymous_non_loopback_bind_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="anonymous"):
        validate_bind_policy(
            "0.0.0.0",
            allow_anonymous=True,
            allow_insecure_network=True,
        )


def test_non_loopback_bind_requires_explicit_override() -> None:
    with pytest.raises(ConfigurationError, match="allow-insecure-network"):
        validate_bind_policy(
            "0.0.0.0",
            allow_anonymous=False,
            allow_insecure_network=False,
        )

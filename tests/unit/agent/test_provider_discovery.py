"""Tests for offline cloud provider inference."""

from __future__ import annotations

from cloudeyes_agent.discovery import DiscoveryConfidence, discover_provider


def test_environment_signal_has_high_confidence() -> None:
    result = discover_provider(
        env={"AWS_REGION": "ap-southeast-1"},
        signals=(),
    )

    assert result.provider_id == "aws"
    assert result.confidence is DiscoveryConfidence.HIGH
    assert result.source == "environment"
    assert result.evidence == ("environment:AWS_REGION",)


def test_system_signal_has_medium_confidence() -> None:
    result = discover_provider(
        env={},
        signals=("Google Compute Engine",),
    )

    assert result.provider_id == "gcp"
    assert result.confidence is DiscoveryConfidence.MEDIUM
    assert result.source == "system"


def test_unknown_provider_is_not_guessed() -> None:
    result = discover_provider(env={}, signals=("Custom Workstation",))

    assert result.provider_id is None
    assert result.provider_name is None
    assert result.source == "unknown"

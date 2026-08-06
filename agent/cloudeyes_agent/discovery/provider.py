"""Offline cloud provider inference."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .model import DiscoveryConfidence, ProviderInfo
from .utils import lower_signals
from .virtualization import collect_system_signals


@dataclass(frozen=True, slots=True)
class _ProviderRule:
    provider_id: str
    provider_name: str
    environment_keys: tuple[str, ...]
    system_markers: tuple[str, ...]


_RULES = (
    _ProviderRule(
        "aws",
        "Amazon Web Services",
        ("AWS_EXECUTION_ENV", "AWS_REGION", "ECS_CONTAINER_METADATA_URI_V4"),
        ("amazon ec2", "amazon-nitro"),
    ),
    _ProviderRule(
        "azure",
        "Microsoft Azure",
        ("WEBSITE_INSTANCE_ID", "AZURE_HTTP_USER_AGENT", "IDENTITY_ENDPOINT"),
        ("microsoft corporation virtual machine", "azure"),
    ),
    _ProviderRule(
        "gcp",
        "Google Cloud",
        ("GOOGLE_CLOUD_PROJECT", "GCE_METADATA_HOST", "K_SERVICE"),
        ("google compute engine", "google"),
    ),
    _ProviderRule(
        "oracle-cloud",
        "Oracle Cloud Infrastructure",
        ("OCI_RESOURCE_PRINCIPAL_VERSION",),
        ("oraclecloud", "oracle cloud"),
    ),
    _ProviderRule(
        "digitalocean",
        "DigitalOcean",
        (),
        ("digitalocean",),
    ),
    _ProviderRule(
        "hetzner-cloud",
        "Hetzner Cloud",
        (),
        ("hetzner",),
    ),
    _ProviderRule(
        "alibaba-cloud",
        "Alibaba Cloud",
        ("ALIBABA_CLOUD_ACCESS_KEY_ID",),
        ("alibaba cloud", "alicloud"),
    ),
    _ProviderRule(
        "tencent-cloud",
        "Tencent Cloud",
        ("TENCENTCLOUD_SECRET_ID",),
        ("tencent cloud",),
    ),
    _ProviderRule(
        "openstack",
        "OpenStack",
        ("OS_AUTH_URL", "OS_CLOUD"),
        ("openstack",),
    ),
)


def discover_provider(
    *,
    env: Mapping[str, str] | None = None,
    signals: tuple[str, ...] | None = None,
) -> ProviderInfo:
    """Infer a provider from environment names and system manufacturer strings."""

    environment = os.environ if env is None else env
    system_signals = collect_system_signals() if signals is None else lower_signals(signals)
    combined = " | ".join(system_signals)

    for rule in _RULES:
        matched_keys = tuple(key for key in rule.environment_keys if key in environment)
        if matched_keys:
            return ProviderInfo(
                provider_id=rule.provider_id,
                provider_name=rule.provider_name,
                confidence=DiscoveryConfidence.HIGH,
                source="environment",
                evidence=tuple(f"environment:{key}" for key in matched_keys),
            )

    for rule in _RULES:
        marker = next((item for item in rule.system_markers if item in combined), None)
        if marker is not None:
            return ProviderInfo(
                provider_id=rule.provider_id,
                provider_name=rule.provider_name,
                confidence=DiscoveryConfidence.MEDIUM,
                source="system",
                evidence=(f"system:{marker}",),
            )

    return ProviderInfo(
        provider_id=None,
        provider_name=None,
        confidence=DiscoveryConfidence.LOW,
        source="unknown",
    )

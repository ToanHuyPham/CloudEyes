"""Run an Agent measurement profile."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cloudeyes_core.models import Sample, SampleQualityStatus
from cloudeyes_core.serialization import dump, dumps

from ..bootstrap import RuntimeDependencyError, ensure_runtime_dependencies
from ..profiles.general import GeneralProfileConfig, run_general_profile
from ..profiles.networking import (
    NetworkingProfileConfig,
    NetworkScope,
    run_networking_profile,
)
from ..profiles.storage import StorageProfileConfig, run_storage_profile


def _general_sample(
    *,
    quick: bool,
    include_storage: bool,
    work_dir: Path | None,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
    product: str | None,
    plan: str | None,
    region: str | None,
    zone: str | None,
) -> Sample:
    config = (
        GeneralProfileConfig.quick(include_storage=include_storage)
        if quick
        else replace(GeneralProfileConfig(), include_storage=include_storage)
    )
    return run_general_profile(
        config=config,
        work_dir=work_dir,
        provider_id=provider_id,
        provider_name=provider_name,
        country_code=country_code,
        product=product,
        plan=plan,
        region=region,
        zone=zone,
    )


def _storage_sample(
    *,
    quick: bool,
    work_dir: Path | None,
    raw_output_dir: Path,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
    product: str | None,
    plan: str | None,
    region: str | None,
    zone: str | None,
) -> Sample:
    config = StorageProfileConfig.quick() if quick else StorageProfileConfig()
    return run_storage_profile(
        config=config,
        work_dir=work_dir,
        raw_output_dir=raw_output_dir,
        provider_id=provider_id,
        provider_name=provider_name,
        country_code=country_code,
        product=product,
        plan=plan,
        region=region,
        zone=zone,
    )


def _networking_sample(
    *,
    quick: bool,
    raw_output_dir: Path,
    target_url: str | None,
    upload_url: str | None,
    network_scope: str,
    verify_tls: bool,
    enable_ping: bool,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
    product: str | None,
    plan: str | None,
    region: str | None,
    zone: str | None,
) -> Sample:
    resolved_target = target_url or "https://example.com/"
    scope = NetworkScope(network_scope)
    config = (
        NetworkingProfileConfig.quick(
            target_url=resolved_target,
            upload_url=upload_url,
            scope=scope,
            verify_tls=verify_tls,
        )
        if quick
        else NetworkingProfileConfig(
            target_url=resolved_target,
            upload_url=upload_url,
            scope=scope,
            verify_tls=verify_tls,
        )
    )
    if not enable_ping:
        config = replace(config, ping_count=0)
    return run_networking_profile(
        config=config,
        raw_output_dir=raw_output_dir,
        provider_id=provider_id,
        provider_name=provider_name,
        country_code=country_code,
        product=product,
        plan=plan,
        region=region,
        zone=zone,
    )


def run_profile(
    *,
    profile: str,
    output: Path | None,
    quick: bool,
    include_storage: bool,
    pretty: bool,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
    product: str | None,
    plan: str | None,
    region: str | None,
    zone: str | None,
    install_deps: bool = False,
    assume_yes: bool = False,
    work_dir: Path | None = None,
    target_url: str | None = None,
    upload_url: str | None = None,
    network_scope: str = "public",
    verify_tls: bool = True,
    enable_ping: bool = True,
) -> int:
    """Execute one supported profile and emit a Core sample as JSON."""

    if profile != "general" and not include_storage:
        print("--no-storage is only valid for the general profile")
        return 4

    if install_deps:
        try:
            ensure_runtime_dependencies(
                auto_install=True,
                assume_yes=assume_yes,
                extra_commands=("ping",) if profile == "networking" and enable_ping else (),
            )
        except RuntimeDependencyError as exc:
            print(f"CloudEyes dependency installation failed: {exc}")
            return 3

    selected_work_dir = work_dir or (output.parent if output is not None else None)
    if profile == "general":
        sample = _general_sample(
            quick=quick,
            include_storage=include_storage,
            work_dir=selected_work_dir,
            provider_id=provider_id,
            provider_name=provider_name,
            country_code=country_code,
            product=product,
            plan=plan,
            region=region,
            zone=zone,
        )
    elif profile == "storage":
        raw_output_dir = output.parent / "raw" if output is not None else Path("data/raw")
        sample = _storage_sample(
            quick=quick,
            work_dir=selected_work_dir,
            raw_output_dir=raw_output_dir,
            provider_id=provider_id,
            provider_name=provider_name,
            country_code=country_code,
            product=product,
            plan=plan,
            region=region,
            zone=zone,
        )
    elif profile == "networking":
        raw_output_dir = output.parent / "raw" if output is not None else Path("data/raw")
        sample = _networking_sample(
            quick=quick,
            raw_output_dir=raw_output_dir,
            target_url=target_url,
            upload_url=upload_url,
            network_scope=network_scope,
            verify_tls=verify_tls,
            enable_ping=enable_ping,
            provider_id=provider_id,
            provider_name=provider_name,
            country_code=country_code,
            product=product,
            plan=plan,
            region=region,
            zone=zone,
        )
    else:
        raise ValueError(f"unsupported profile: {profile}")

    indent = 2 if pretty else None
    text = dumps(sample, indent=indent)
    print(text)
    if output is not None:
        dump(sample, output, indent=indent)

    return 2 if sample.quality.status is SampleQualityStatus.INVALID else 0

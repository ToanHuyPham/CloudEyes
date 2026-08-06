"""Run an Agent measurement profile."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cloudeyes_core.models import Sample, SampleQualityStatus
from cloudeyes_core.serialization import dump, dumps

from ..bootstrap import RuntimeDependencyError, ensure_runtime_dependencies
from ..execution import IsolatedExecutionError, IsolatedExecutionTimeout, run_isolated
from ..profiles.compute import ComputeProfileConfig, run_compute_profile
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


def _compute_sample(
    *,
    quick: bool,
    workers: int | None,
    raw_output_dir: Path,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
    product: str | None,
    plan: str | None,
    region: str | None,
    zone: str | None,
) -> Sample:
    selected_workers = 0 if workers is None else workers
    config = (
        ComputeProfileConfig.quick(workers=selected_workers)
        if quick
        else replace(ComputeProfileConfig(), workers=selected_workers)
    )
    return run_compute_profile(
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


PROFILE_TIMEOUT_SECONDS = {
    "general": 120.0,
    "networking": 180.0,
    "compute": 600.0,
    "storage": 900.0,
}


def _execute_profile(
    *,
    profile: str,
    quick: bool,
    include_storage: bool,
    output: Path | None,
    work_dir: Path | None,
    target_url: str | None,
    upload_url: str | None,
    network_scope: str,
    verify_tls: bool,
    enable_ping: bool,
    workers: int | None,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
    product: str | None,
    plan: str | None,
    region: str | None,
    zone: str | None,
) -> Sample:
    selected_work_dir = work_dir or (output.parent if output is not None else None)
    if profile == "general":
        return _general_sample(
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
    if profile == "storage":
        raw_output_dir = output.parent / "raw" if output is not None else Path("data/raw")
        return _storage_sample(
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
    if profile == "networking":
        raw_output_dir = output.parent / "raw" if output is not None else Path("data/raw")
        return _networking_sample(
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
    if profile == "compute":
        raw_output_dir = output.parent / "raw" if output is not None else Path("data/raw")
        return _compute_sample(
            quick=quick,
            workers=workers,
            raw_output_dir=raw_output_dir,
            provider_id=provider_id,
            provider_name=provider_name,
            country_code=country_code,
            product=product,
            plan=plan,
            region=region,
            zone=zone,
        )
    raise ValueError(f"unsupported profile: {profile}")


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
    workers: int | None = None,
    isolated: bool = True,
    timeout_seconds: float | None = None,
) -> int:
    """Execute one supported profile and emit a Core sample as JSON."""

    if profile != "general" and not include_storage:
        print("--no-storage is only valid for the general profile")
        return 4
    if profile != "compute" and workers is not None:
        print("--workers is only valid for the compute profile")
        return 4
    if timeout_seconds is not None and timeout_seconds <= 0:
        print("--timeout-seconds must be greater than zero")
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

    execution_kwargs = {
        "profile": profile,
        "quick": quick,
        "include_storage": include_storage,
        "output": output,
        "work_dir": work_dir,
        "target_url": target_url,
        "upload_url": upload_url,
        "network_scope": network_scope,
        "verify_tls": verify_tls,
        "enable_ping": enable_ping,
        "workers": workers,
        "provider_id": provider_id,
        "provider_name": provider_name,
        "country_code": country_code,
        "product": product,
        "plan": plan,
        "region": region,
        "zone": zone,
    }
    if isolated:
        deadline = timeout_seconds or PROFILE_TIMEOUT_SECONDS[profile]
        try:
            sample = run_isolated(
                _execute_profile,
                kwargs=execution_kwargs,
                timeout_seconds=deadline,
            ).value
        except IsolatedExecutionTimeout as exc:
            print(f"CloudEyes profile timed out: {exc}")
            return 124
        except IsolatedExecutionError as exc:
            print(f"CloudEyes isolated profile failed: {exc}")
            return 2
    else:
        sample = _execute_profile(**execution_kwargs)

    indent = 2 if pretty else None
    text = dumps(sample, indent=indent)
    print(text)
    if output is not None:
        dump(sample, output, indent=indent)

    return 2 if sample.quality.status is SampleQualityStatus.INVALID else 0

"""Run an Agent measurement profile."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cloudeyes_core.models import SampleQualityStatus
from cloudeyes_core.serialization import dump, dumps

from ..bootstrap import RuntimeDependencyError, ensure_runtime_dependencies
from ..profiles.general import GeneralProfileConfig, run_general_profile


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
) -> int:
    """Execute one supported profile and emit a Core sample as JSON."""

    if profile != "general":
        raise ValueError(f"unsupported profile: {profile}")

    if install_deps:
        try:
            ensure_runtime_dependencies(
                auto_install=True,
                assume_yes=assume_yes,
            )
        except RuntimeDependencyError as exc:
            print(f"CloudEyes dependency installation failed: {exc}")
            return 3

    config = (
        GeneralProfileConfig.quick(include_storage=include_storage)
        if quick
        else replace(GeneralProfileConfig(), include_storage=include_storage)
    )
    sample = run_general_profile(
        config=config,
        work_dir=output.parent if output is not None else None,
        provider_id=provider_id,
        provider_name=provider_name,
        country_code=country_code,
        product=product,
        plan=plan,
        region=region,
        zone=zone,
    )

    indent = 2 if pretty else None
    text = dumps(sample, indent=indent)
    print(text)
    if output is not None:
        dump(sample, output, indent=indent)

    return 2 if sample.quality.status is SampleQualityStatus.INVALID else 0

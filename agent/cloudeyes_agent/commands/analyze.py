"""Offline provider analytics command."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from cloudeyes_core.models import PricingCommitment, PricingOperatingSystem
from cloudeyes_core.pipeline import analyze_provider_analytics
from cloudeyes_core.serialization import (
    dump,
    dumps,
    load_pricing_catalog,
    load_sample,
)

from ..reporting import render_analytics_markdown


def _sample_paths(inputs: Iterable[Path]) -> tuple[Path, ...]:
    paths: dict[Path, None] = {}
    for raw_path in inputs:
        path = raw_path.expanduser()
        if not path.exists():
            raise FileNotFoundError(f"analytics input does not exist: {path}")
        candidates = (path,) if path.is_file() else tuple(sorted(path.glob("*.json")))
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.casefold() == ".json":
                paths[candidate.resolve()] = None
    if not paths:
        raise ValueError("no JSON sample files were found")
    return tuple(paths)


def _pricing_quotes(inputs: Iterable[Path]):
    quotes = []
    seen_ids: set[str] = set()
    for raw_path in inputs:
        path = raw_path.expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"pricing catalog does not exist: {path}")
        catalog = load_pricing_catalog(path)
        for quote in catalog.quotes:
            if quote.quote_id in seen_ids:
                raise ValueError(f"duplicate pricing quote ID: {quote.quote_id}")
            seen_ids.add(quote.quote_id)
            quotes.append(quote)
    return tuple(quotes)


def run_analyze(
    *,
    inputs: tuple[Path, ...],
    output: Path | None,
    markdown: Path | None,
    expected_metrics: tuple[str, ...],
    pretty: bool,
    pricing: tuple[Path, ...] = (),
    pricing_commitment: PricingCommitment = PricingCommitment.ON_DEMAND,
    pricing_operating_system: PricingOperatingSystem = PricingOperatingSystem.LINUX,
) -> int:
    """Load local sample and pricing JSON files and emit deterministic analytics."""

    try:
        paths = _sample_paths(inputs)
        samples = tuple(load_sample(path) for path in paths)
        pricing_quotes = _pricing_quotes(pricing)
        bundle = analyze_provider_analytics(
            samples,
            expected_metrics=expected_metrics,
            pricing_quotes=pricing_quotes,
            pricing_commitment=pricing_commitment,
            pricing_operating_system=pricing_operating_system,
        )
        text = dumps(bundle, indent=2 if pretty else None)
        if output is not None:
            dump(bundle, output, indent=2 if pretty else None)
        if markdown is not None:
            markdown.parent.mkdir(parents=True, exist_ok=True)
            markdown.write_text(render_analytics_markdown(bundle), encoding="utf-8")
        print(text)
        return 0
    except (FileNotFoundError, OSError, TypeError, ValueError) as error:
        print(f"CloudEyes analytics failed: {error}")
        return 5

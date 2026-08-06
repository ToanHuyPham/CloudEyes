"""Deterministic normalization and matching of offline pricing quotes."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from ..models import (
    Cohort,
    CohortReport,
    ConfidenceLevel,
    NormalizedPriceEvidence,
    PriceQuote,
    PricingCommitment,
    PricingOperatingSystem,
    PricingSourceTier,
    ProviderReport,
)


@dataclass(frozen=True, slots=True)
class PricingMatchResult:
    """Normalized evidence plus cohort lookup and unmatched quote IDs."""

    evidence: tuple[NormalizedPriceEvidence, ...]
    cohort_evidence: dict[str, NormalizedPriceEvidence]
    selected_quote_ids: tuple[str, ...]
    unmatched_quote_ids: tuple[str, ...]


def _identifier(prefix: str, parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalized(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().casefold()
    return cleaned or None


def _source_rank(tier: PricingSourceTier) -> int:
    return {
        PricingSourceTier.MANUAL: 1,
        PricingSourceTier.RESELLER: 2,
        PricingSourceTier.OFFICIAL_DOCUMENT: 3,
        PricingSourceTier.OFFICIAL_API: 4,
    }[tier]


def source_confidence(tier: PricingSourceTier) -> ConfidenceLevel:
    """Map pricing source traceability to a conservative confidence level."""

    if tier in (PricingSourceTier.OFFICIAL_API, PricingSourceTier.OFFICIAL_DOCUMENT):
        return ConfidenceLevel.HIGH
    if tier is PricingSourceTier.RESELLER:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def normalize_hourly_usd(quote: PriceQuote) -> float:
    """Normalize one quote to USD per hour."""

    result = quote.hourly_usd
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"quote {quote.quote_id} produced an invalid hourly USD value")
    return result


def _covers_cohort(quote: PriceQuote, cohort: Cohort) -> bool:
    if quote.valid_from > cohort.started_at:
        return False
    return quote.valid_until is None or quote.valid_until >= cohort.ended_at


def _matches_identity(quote: PriceQuote, cohort: Cohort) -> bool:
    key = cohort.key
    if _normalized(quote.provider_id) != key.provider_id:
        return False
    if _normalized(quote.product) != key.product or _normalized(quote.plan) != key.plan:
        return False
    region = _normalized(quote.region)
    zone = _normalized(quote.zone)
    if region is not None and region != key.region:
        return False
    return zone is None or zone == key.zone


def _rank(quote: PriceQuote) -> tuple[int, int, int, float]:
    return (
        int(quote.region is not None),
        int(quote.zone is not None),
        _source_rank(quote.source.tier),
        quote.observed_at.timestamp(),
    )


def _select_quote(
    cohort: Cohort,
    quotes: tuple[PriceQuote, ...],
    *,
    generated_at: datetime,
) -> PriceQuote | None:
    candidates = tuple(
        quote
        for quote in quotes
        if quote.observed_at <= generated_at
        and _matches_identity(quote, cohort)
        and _covers_cohort(quote, cohort)
    )
    if not candidates:
        return None

    best_rank = max(_rank(item) for item in candidates)
    best = tuple(item for item in candidates if _rank(item) == best_rank)
    hourly_prices = {round(normalize_hourly_usd(item), 12) for item in best}
    if len(hourly_prices) > 1:
        quote_ids = ", ".join(sorted(item.quote_id for item in best))
        raise ValueError(f"ambiguous pricing quotes for cohort {cohort.key.value}: {quote_ids}")
    return min(best, key=lambda item: item.quote_id)


def _cohort_reports_by_key(
    reports: tuple[ProviderReport, ...],
) -> dict[str, CohortReport]:
    result: dict[str, CohortReport] = {}
    for report in reports:
        for cohort in report.cohorts:
            result[cohort.cohort_key] = cohort
    return result


def match_pricing_evidence(
    cohorts: tuple[Cohort, ...],
    reports: tuple[ProviderReport, ...],
    quotes: tuple[PriceQuote, ...],
    *,
    generated_at: datetime,
    commitment: PricingCommitment = PricingCommitment.ON_DEMAND,
    operating_system: PricingOperatingSystem = PricingOperatingSystem.LINUX,
) -> PricingMatchResult:
    """Match the most specific valid quote to each cohort and normalize it."""

    if generated_at.tzinfo is None:
        raise ValueError("generated_at must contain timezone information")
    commitment = (
        commitment if isinstance(commitment, PricingCommitment) else PricingCommitment(commitment)
    )
    operating_system = (
        operating_system
        if isinstance(operating_system, PricingOperatingSystem)
        else PricingOperatingSystem(operating_system)
    )

    selected = tuple(
        sorted(
            (
                quote
                for quote in quotes
                if quote.commitment is commitment and quote.operating_system is operating_system
            ),
            key=lambda item: item.quote_id,
        )
    )
    quote_ids = [item.quote_id for item in selected]
    if len(quote_ids) != len(set(quote_ids)):
        raise ValueError("pricing quote IDs must be unique across catalogs")

    cohort_reports = _cohort_reports_by_key(reports)
    assignments: dict[str, PriceQuote] = {}
    grouped: dict[str, list[Cohort]] = defaultdict(list)
    quote_by_id = {item.quote_id: item for item in selected}

    for cohort in cohorts:
        quote = _select_quote(cohort, selected, generated_at=generated_at)
        if quote is None:
            continue
        assignments[cohort.key.value] = quote
        grouped[quote.quote_id].append(cohort)

    evidence_by_quote: dict[str, NormalizedPriceEvidence] = {}
    for quote_id, matched_cohorts in sorted(grouped.items()):
        quote = quote_by_id[quote_id]
        cohort_ids = tuple(
            sorted(cohort_reports[item.key.value].cohort_id for item in matched_cohorts)
        )
        sample_ids = tuple(
            sorted({sample.sample_id for cohort in matched_cohorts for sample in cohort.samples})
        )
        evidence_id = _identifier("pricing-evidence", (quote.quote_id, *cohort_ids))
        evidence_by_quote[quote_id] = NormalizedPriceEvidence(
            pricing_evidence_id=evidence_id,
            quote_id=quote.quote_id,
            provider_id=quote.provider_id,
            product=quote.product,
            plan=quote.plan,
            region=quote.region,
            zone=quote.zone,
            commitment=quote.commitment,
            operating_system=quote.operating_system,
            observed_at=quote.observed_at,
            valid_from=quote.valid_from,
            valid_until=quote.valid_until,
            source_amount=quote.amount,
            source_currency=quote.currency,
            billing_period=quote.billing_period,
            billing_period_hours=quote.billing_period_hours,
            fx_to_usd=quote.fx_to_usd,
            hourly_usd=normalize_hourly_usd(quote),
            tax_included=quote.tax_included,
            source=quote.source,
            confidence=source_confidence(quote.source.tier),
            cohort_ids=cohort_ids,
            sample_ids=sample_ids,
        )

    cohort_evidence = {
        cohort_key: evidence_by_quote[quote.quote_id] for cohort_key, quote in assignments.items()
    }
    matched_ids = set(evidence_by_quote)
    return PricingMatchResult(
        evidence=tuple(
            sorted(evidence_by_quote.values(), key=lambda item: item.pricing_evidence_id)
        ),
        cohort_evidence=cohort_evidence,
        selected_quote_ids=tuple(quote_ids),
        unmatched_quote_ids=tuple(sorted(set(quote_ids) - matched_ids)),
    )

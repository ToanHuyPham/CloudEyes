"""Normalized pricing and price-performance comparison models."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .comparison import PeerComparisonOutcome
from .confidence import ConfidenceLevel
from .metric import MetricDirection


class PricingCommitment(StrEnum):
    """Commercial commitment represented by a price quote."""

    ON_DEMAND = "on_demand"
    RESERVED = "reserved"
    SPOT = "spot"


class PricingOperatingSystem(StrEnum):
    """Operating-system price family."""

    LINUX = "linux"
    WINDOWS = "windows"
    OTHER = "other"


class PricingSourceTier(StrEnum):
    """Traceability tier for one pricing source."""

    OFFICIAL_API = "official_api"
    OFFICIAL_DOCUMENT = "official_document"
    RESELLER = "reseller"
    MANUAL = "manual"


class ValueIndexDefinition(StrEnum):
    """Formula used to convert performance and hourly price into a value index."""

    METRIC_PER_USD_HOUR = "metric_per_usd_hour"
    INVERSE_METRIC_USD_HOUR = "inverse_metric_usd_hour"


@dataclass(frozen=True, slots=True)
class PricingSource:
    """Source metadata retained with every normalized quote."""

    tier: PricingSourceTier
    reference: str

    def __post_init__(self) -> None:
        tier = (
            self.tier if isinstance(self.tier, PricingSourceTier) else PricingSourceTier(self.tier)
        )
        reference = self.reference.strip()
        if not reference:
            raise ValueError("pricing source reference must not be empty")
        object.__setattr__(self, "tier", tier)
        object.__setattr__(self, "reference", reference)


@dataclass(frozen=True, slots=True)
class PriceQuote:
    """One time-bounded provider price quote before normalization."""

    quote_id: str
    provider_id: str
    product: str
    plan: str
    region: str | None
    zone: str | None
    observed_at: datetime
    valid_from: datetime
    valid_until: datetime | None
    commitment: PricingCommitment
    operating_system: PricingOperatingSystem
    amount: float
    currency: str
    billing_period: str
    billing_period_hours: float
    fx_to_usd: float
    tax_included: bool | None
    source: PricingSource

    def __post_init__(self) -> None:
        for field_name in ("quote_id", "provider_id", "product", "plan", "billing_period"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)

        for field_name in ("region", "zone"):
            value = getattr(self, field_name)
            object.__setattr__(self, field_name, value.strip() if value and value.strip() else None)

        for field_name in ("observed_at", "valid_from"):
            value = getattr(self, field_name)
            if value.tzinfo is None:
                raise ValueError(f"{field_name} must contain timezone information")
        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise ValueError("valid_until must contain timezone information")
            if self.valid_until <= self.valid_from:
                raise ValueError("valid_until must be later than valid_from")

        commitment = (
            self.commitment
            if isinstance(self.commitment, PricingCommitment)
            else PricingCommitment(self.commitment)
        )
        operating_system = (
            self.operating_system
            if isinstance(self.operating_system, PricingOperatingSystem)
            else PricingOperatingSystem(self.operating_system)
        )
        source = (
            self.source if isinstance(self.source, PricingSource) else PricingSource(**self.source)
        )
        object.__setattr__(self, "commitment", commitment)
        object.__setattr__(self, "operating_system", operating_system)
        object.__setattr__(self, "source", source)

        for field_name in ("amount", "billing_period_hours", "fx_to_usd"):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field_name} must be a positive finite number")
            object.__setattr__(self, field_name, value)

        currency = self.currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code")
        if currency == "USD" and not math.isclose(self.fx_to_usd, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("USD quotes must use fx_to_usd=1")
        object.__setattr__(self, "currency", currency)

    @property
    def hourly_usd(self) -> float:
        """Return the quote normalized to USD per hour."""

        return self.amount * self.fx_to_usd / self.billing_period_hours


@dataclass(frozen=True, slots=True)
class PricingCatalog:
    """Versioned collection of offline pricing quotes."""

    schema_version: str
    quotes: tuple[PriceQuote, ...]

    def __post_init__(self) -> None:
        version = self.schema_version.strip()
        if version != "1.0.0":
            raise ValueError("unsupported pricing catalog schema_version")
        quotes = tuple(self.quotes)
        quote_ids = [item.quote_id for item in quotes]
        if len(quote_ids) != len(set(quote_ids)):
            raise ValueError("pricing quote IDs must be unique")
        object.__setattr__(self, "schema_version", version)
        object.__setattr__(self, "quotes", quotes)


@dataclass(frozen=True, slots=True)
class NormalizedPriceEvidence:
    """Traceable USD-per-hour pricing evidence matched to analyzed cohorts."""

    pricing_evidence_id: str
    quote_id: str
    provider_id: str
    product: str
    plan: str
    region: str | None
    zone: str | None
    commitment: PricingCommitment
    operating_system: PricingOperatingSystem
    observed_at: datetime
    valid_from: datetime
    valid_until: datetime | None
    source_amount: float
    source_currency: str
    billing_period: str
    billing_period_hours: float
    fx_to_usd: float
    hourly_usd: float
    tax_included: bool | None
    source: PricingSource
    confidence: ConfidenceLevel
    cohort_ids: tuple[str, ...] = field(default_factory=tuple)
    sample_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for field_name in (
            "pricing_evidence_id",
            "quote_id",
            "provider_id",
            "product",
            "plan",
            "billing_period",
        ):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        for field_name in ("region", "zone"):
            value = getattr(self, field_name)
            object.__setattr__(self, field_name, value.strip() if value and value.strip() else None)
        for field_name in ("observed_at", "valid_from"):
            if getattr(self, field_name).tzinfo is None:
                raise ValueError(f"{field_name} must contain timezone information")
        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise ValueError("valid_until must contain timezone information")
            if self.valid_until <= self.valid_from:
                raise ValueError("valid_until must be later than valid_from")

        commitment = (
            self.commitment
            if isinstance(self.commitment, PricingCommitment)
            else PricingCommitment(self.commitment)
        )
        operating_system = (
            self.operating_system
            if isinstance(self.operating_system, PricingOperatingSystem)
            else PricingOperatingSystem(self.operating_system)
        )
        confidence = (
            self.confidence
            if isinstance(self.confidence, ConfidenceLevel)
            else ConfidenceLevel(self.confidence)
        )
        source = (
            self.source if isinstance(self.source, PricingSource) else PricingSource(**self.source)
        )
        object.__setattr__(self, "commitment", commitment)
        object.__setattr__(self, "operating_system", operating_system)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "source", source)

        for field_name in (
            "source_amount",
            "billing_period_hours",
            "fx_to_usd",
            "hourly_usd",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field_name} must be a positive finite number")
            object.__setattr__(self, field_name, value)

        currency = self.source_currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("source_currency must be a three-letter alphabetic code")
        object.__setattr__(self, "source_currency", currency)
        cohort_ids = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.cohort_ids if item.strip()))
        )
        sample_ids = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.sample_ids if item.strip()))
        )
        if not cohort_ids or not sample_ids:
            raise ValueError("normalized pricing evidence requires matched cohorts and samples")
        object.__setattr__(self, "cohort_ids", cohort_ids)
        object.__setattr__(self, "sample_ids", sample_ids)


@dataclass(frozen=True, slots=True)
class ValueMetricComparison:
    """One price-performance index compared with compatible peer providers."""

    comparison_id: str
    peer_group_id: str
    peer_key: str
    profile: str
    metric_name: str
    metric_unit: str
    metric_direction: MetricDirection
    index_definition: ValueIndexDefinition
    provider_hourly_usd: float
    peer_hourly_usd_median: float
    provider_value_index: float
    peer_value_index_median: float
    relative_difference_percent: float
    outcome: PeerComparisonOutcome
    confidence: ConfidenceLevel
    peer_provider_count: int
    peer_provider_ids: tuple[str, ...]
    provider_cohort_ids: tuple[str, ...]
    peer_cohort_ids: tuple[str, ...]
    provider_pricing_evidence_ids: tuple[str, ...]
    peer_pricing_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "comparison_id",
            "peer_group_id",
            "peer_key",
            "profile",
            "metric_name",
            "metric_unit",
        ):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)

        direction = (
            self.metric_direction
            if isinstance(self.metric_direction, MetricDirection)
            else MetricDirection(self.metric_direction)
        )
        if direction is MetricDirection.NEUTRAL:
            raise ValueError("neutral metrics cannot produce value comparisons")
        definition = (
            self.index_definition
            if isinstance(self.index_definition, ValueIndexDefinition)
            else ValueIndexDefinition(self.index_definition)
        )
        outcome = (
            self.outcome
            if isinstance(self.outcome, PeerComparisonOutcome)
            else PeerComparisonOutcome(self.outcome)
        )
        confidence = (
            self.confidence
            if isinstance(self.confidence, ConfidenceLevel)
            else ConfidenceLevel(self.confidence)
        )
        object.__setattr__(self, "metric_direction", direction)
        object.__setattr__(self, "index_definition", definition)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "confidence", confidence)

        for field_name in (
            "provider_hourly_usd",
            "peer_hourly_usd_median",
            "provider_value_index",
            "peer_value_index_median",
            "relative_difference_percent",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
            if field_name != "relative_difference_percent" and value <= 0:
                raise ValueError(f"{field_name} must be positive")
            object.__setattr__(self, field_name, value)

        peer_ids = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.peer_provider_ids if item.strip()))
        )
        provider_cohorts = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.provider_cohort_ids if item.strip()))
        )
        peer_cohorts = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.peer_cohort_ids if item.strip()))
        )
        provider_prices = tuple(
            sorted(
                dict.fromkeys(
                    item.strip() for item in self.provider_pricing_evidence_ids if item.strip()
                )
            )
        )
        peer_prices = tuple(
            sorted(
                dict.fromkeys(
                    item.strip() for item in self.peer_pricing_evidence_ids if item.strip()
                )
            )
        )
        if self.peer_provider_count != len(peer_ids) or self.peer_provider_count < 1:
            raise ValueError("peer_provider_count must match peer_provider_ids")
        if not provider_cohorts or not peer_cohorts or not provider_prices or not peer_prices:
            raise ValueError("value comparisons require cohort and pricing evidence")
        object.__setattr__(self, "peer_provider_ids", peer_ids)
        object.__setattr__(self, "provider_cohort_ids", provider_cohorts)
        object.__setattr__(self, "peer_cohort_ids", peer_cohorts)
        object.__setattr__(self, "provider_pricing_evidence_ids", provider_prices)
        object.__setattr__(self, "peer_pricing_evidence_ids", peer_prices)

"""Deterministic provider analytics models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .comparison import PeerMetricComparison
from .confidence import ConfidenceLevel
from .pricing import NormalizedPriceEvidence, ValueMetricComparison
from .report import ProviderReport


class AssessmentDimension(StrEnum):
    """Independent provider assessment dimensions."""

    EVIDENCE = "evidence"
    CONSISTENCY = "consistency"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    VALUE = "value"


class AssessmentStatus(StrEnum):
    """Whether a dimension could be assessed from the available evidence."""

    ASSESSED = "assessed"
    NOT_ASSESSED = "not_assessed"


class ExplanationKind(StrEnum):
    """Classification of one traceable explanation item."""

    STRENGTH = "strength"
    LIMITATION = "limitation"
    OBSERVATION = "observation"


@dataclass(frozen=True, slots=True)
class DimensionAssessment:
    """Result for one scorecard dimension without a universal aggregate score."""

    dimension: AssessmentDimension
    status: AssessmentStatus
    level: ConfidenceLevel | None
    rule_id: str
    summary: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        dimension = (
            self.dimension
            if isinstance(self.dimension, AssessmentDimension)
            else AssessmentDimension(self.dimension)
        )
        status = (
            self.status
            if isinstance(self.status, AssessmentStatus)
            else AssessmentStatus(self.status)
        )
        level = self.level
        if level is not None and not isinstance(level, ConfidenceLevel):
            level = ConfidenceLevel(level)

        rule_id = self.rule_id.strip()
        summary = self.summary.strip()
        if not rule_id or not summary:
            raise ValueError("assessment rule_id and summary must not be empty")
        if status is AssessmentStatus.ASSESSED and level is None:
            raise ValueError("assessed dimensions must contain a level")
        if status is AssessmentStatus.NOT_ASSESSED and level is not None:
            raise ValueError("not-assessed dimensions must not contain a level")

        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "level", level)
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(dict.fromkeys(item.strip() for item in self.evidence_refs if item.strip())),
        )
        object.__setattr__(
            self,
            "limitations",
            tuple(dict.fromkeys(item.strip() for item in self.limitations if item.strip())),
        )


@dataclass(frozen=True, slots=True)
class ExplanationItem:
    """Human-readable statement tied to a deterministic rule and evidence."""

    code: str
    kind: ExplanationKind
    message: str
    rule_id: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        kind = self.kind if isinstance(self.kind, ExplanationKind) else ExplanationKind(self.kind)
        code = self.code.strip()
        message = self.message.strip()
        rule_id = self.rule_id.strip()
        if not code or not message or not rule_id:
            raise ValueError("explanation code, message, and rule_id must not be empty")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(dict.fromkeys(item.strip() for item in self.evidence_refs if item.strip())),
        )


@dataclass(frozen=True, slots=True)
class ProviderScorecard:
    """Multidimensional scorecard; deliberately has no universal overall score."""

    sample_count: int
    cohort_count: int
    profile_count: int
    profiles: tuple[str, ...]
    coverage_ratio: float
    successful_measurement_ratio: float
    dimensions: tuple[DimensionAssessment, ...]

    def __post_init__(self) -> None:
        if self.sample_count < 0 or self.cohort_count < 0 or self.profile_count < 0:
            raise ValueError("scorecard counts must not be negative")
        if not 0.0 <= self.coverage_ratio <= 1.0:
            raise ValueError("coverage_ratio must be between 0 and 1")
        if not 0.0 <= self.successful_measurement_ratio <= 1.0:
            raise ValueError("successful_measurement_ratio must be between 0 and 1")

        profiles = tuple(
            sorted(dict.fromkeys(item.strip() for item in self.profiles if item.strip()))
        )
        dimensions = tuple(self.dimensions)
        if self.profile_count != len(profiles):
            raise ValueError("profile_count must match profiles")
        if self.cohort_count == 0 and self.sample_count != 0:
            raise ValueError("sample_count must be zero when cohort_count is zero")
        dimension_names = [item.dimension for item in dimensions]
        if len(dimension_names) != len(set(dimension_names)):
            raise ValueError("scorecard dimensions must be unique")

        object.__setattr__(self, "profiles", profiles)
        object.__setattr__(self, "dimensions", dimensions)

    def dimension(self, name: AssessmentDimension) -> DimensionAssessment:
        """Return one dimension by name."""

        normalized = name if isinstance(name, AssessmentDimension) else AssessmentDimension(name)
        for item in self.dimensions:
            if item.dimension is normalized:
                return item
        raise KeyError(normalized.value)


@dataclass(frozen=True, slots=True)
class ProviderAnalyticsReport:
    """Evidence report plus deterministic provider assessment and explanation."""

    schema_version: str
    analytics_id: str
    generated_at: datetime
    provider_id: str
    provider_name: str
    evidence: ProviderReport
    scorecard: ProviderScorecard
    explanations: tuple[ExplanationItem, ...]
    peer_comparisons: tuple[PeerMetricComparison, ...] = field(default_factory=tuple)
    pricing_evidence: tuple[NormalizedPriceEvidence, ...] = field(default_factory=tuple)
    value_comparisons: tuple[ValueMetricComparison, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for field_name in ("schema_version", "analytics_id", "provider_id", "provider_name"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must contain timezone information")
        if self.provider_id != self.evidence.provider_id:
            raise ValueError("provider_id must match evidence report")
        if self.provider_name != self.evidence.provider_name:
            raise ValueError("provider_name must match evidence report")
        if self.generated_at != self.evidence.generated_at:
            raise ValueError("generated_at must match evidence report")
        comparisons = tuple(self.peer_comparisons)
        pricing_evidence = tuple(self.pricing_evidence)
        value_comparisons = tuple(self.value_comparisons)
        if any(item.profile not in self.scorecard.profiles for item in comparisons):
            raise ValueError("peer comparison profile must exist in scorecard profiles")
        if any(item.profile not in self.scorecard.profiles for item in value_comparisons):
            raise ValueError("value comparison profile must exist in scorecard profiles")
        if any(
            item.provider_id.casefold() != self.provider_id.casefold() for item in pricing_evidence
        ):
            raise ValueError("pricing evidence provider must match analytics provider")
        comparison_ids = [item.comparison_id for item in comparisons]
        value_comparison_ids = [item.comparison_id for item in value_comparisons]
        pricing_ids = [item.pricing_evidence_id for item in pricing_evidence]
        if len(comparison_ids) != len(set(comparison_ids)):
            raise ValueError("peer comparison IDs must be unique per provider")
        if len(value_comparison_ids) != len(set(value_comparison_ids)):
            raise ValueError("value comparison IDs must be unique per provider")
        if len(pricing_ids) != len(set(pricing_ids)):
            raise ValueError("pricing evidence IDs must be unique per provider")
        available_pricing_ids = set(pricing_ids)
        for item in value_comparisons:
            if not set(item.provider_pricing_evidence_ids).issubset(available_pricing_ids):
                raise ValueError("value comparison must reference provider pricing evidence")
        object.__setattr__(self, "explanations", tuple(self.explanations))
        object.__setattr__(self, "peer_comparisons", comparisons)
        object.__setattr__(self, "pricing_evidence", pricing_evidence)
        object.__setattr__(self, "value_comparisons", value_comparisons)


@dataclass(frozen=True, slots=True)
class AnalyticsBundle:
    """Offline analytics result for one input sample collection."""

    schema_version: str
    generated_at: datetime
    source_sample_count: int
    analyzed_sample_count: int
    excluded_sample_ids: tuple[str, ...]
    provider_count: int
    providers: tuple[ProviderAnalyticsReport, ...]
    peer_group_count: int = 0
    pricing_quote_count: int = 0
    normalized_pricing_evidence_count: int = 0
    unmatched_pricing_quote_ids: tuple[str, ...] = field(default_factory=tuple)
    value_peer_group_count: int = 0

    def __post_init__(self) -> None:
        if not self.schema_version.strip():
            raise ValueError("schema_version must not be empty")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must contain timezone information")
        if self.source_sample_count < 0 or self.analyzed_sample_count < 0:
            raise ValueError("sample counts must not be negative")
        if self.peer_group_count < 0 or self.value_peer_group_count < 0:
            raise ValueError("peer group counts must not be negative")
        if self.pricing_quote_count < 0 or self.normalized_pricing_evidence_count < 0:
            raise ValueError("pricing counts must not be negative")
        if self.analyzed_sample_count > self.source_sample_count:
            raise ValueError("analyzed_sample_count must not exceed source_sample_count")
        providers = tuple(self.providers)
        excluded = tuple(
            dict.fromkeys(item.strip() for item in self.excluded_sample_ids if item.strip())
        )
        if self.provider_count != len(providers):
            raise ValueError("provider_count must match providers")
        if self.source_sample_count != self.analyzed_sample_count + len(excluded):
            raise ValueError("source sample count must equal analyzed plus excluded samples")
        if any(item.generated_at != self.generated_at for item in providers):
            raise ValueError("provider generated_at values must match bundle")
        peer_groups = {
            comparison.peer_group_id
            for provider in providers
            for comparison in provider.peer_comparisons
        }
        value_peer_groups = {
            comparison.peer_group_id
            for provider in providers
            for comparison in provider.value_comparisons
        }
        pricing_evidence_ids = {
            evidence.pricing_evidence_id
            for provider in providers
            for evidence in provider.pricing_evidence
        }
        unmatched_pricing = tuple(
            sorted(
                dict.fromkeys(
                    item.strip() for item in self.unmatched_pricing_quote_ids if item.strip()
                )
            )
        )
        if self.peer_group_count != len(peer_groups):
            raise ValueError("peer_group_count must match provider peer comparisons")
        if self.value_peer_group_count != len(value_peer_groups):
            raise ValueError("value_peer_group_count must match provider value comparisons")
        if self.normalized_pricing_evidence_count != len(pricing_evidence_ids):
            raise ValueError(
                "normalized_pricing_evidence_count must match provider pricing evidence"
            )
        if self.pricing_quote_count < self.normalized_pricing_evidence_count:
            raise ValueError("pricing_quote_count must cover normalized pricing evidence")
        if self.pricing_quote_count != (
            self.normalized_pricing_evidence_count + len(unmatched_pricing)
        ):
            raise ValueError("pricing quote count must equal matched plus unmatched quotes")
        object.__setattr__(self, "schema_version", self.schema_version.strip())
        object.__setattr__(self, "providers", providers)
        object.__setattr__(self, "excluded_sample_ids", excluded)
        object.__setattr__(self, "unmatched_pricing_quote_ids", unmatched_pricing)

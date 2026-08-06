"""Traceable explanation generation for provider scorecards."""

from __future__ import annotations

from ..models import (
    AssessmentStatus,
    ConfidenceLevel,
    ExplanationItem,
    ExplanationKind,
    ProviderReport,
    ProviderScorecard,
)
from .rules import DIMENSION_RULE, GAP_RULE, NO_UNIVERSAL_SCORE_RULE


def _dimension_item(item) -> ExplanationItem:
    if item.status is AssessmentStatus.NOT_ASSESSED:
        kind = ExplanationKind.LIMITATION
        code = f"{item.dimension.value}_not_assessed"
    elif item.level is ConfidenceLevel.HIGH:
        kind = ExplanationKind.STRENGTH
        code = f"{item.dimension.value}_high"
    elif item.level is ConfidenceLevel.MEDIUM:
        kind = ExplanationKind.OBSERVATION
        code = f"{item.dimension.value}_medium"
    else:
        kind = ExplanationKind.LIMITATION
        code = f"{item.dimension.value}_low"

    return ExplanationItem(
        code=code,
        kind=kind,
        message=item.summary,
        rule_id=item.rule_id or DIMENSION_RULE,
        evidence_refs=item.evidence_refs,
    )


def build_explanations(
    report: ProviderReport,
    scorecard: ProviderScorecard,
) -> tuple[ExplanationItem, ...]:
    """Build ordered, deduplicated explanations from scorecard rules and gaps."""

    items = [_dimension_item(item) for item in scorecard.dimensions]
    cohort_refs = tuple(item.cohort_id for item in report.cohorts)

    for gap in report.gaps:
        items.append(
            ExplanationItem(
                code=f"coverage_gap:{gap}",
                kind=ExplanationKind.LIMITATION,
                message=f"Evidence gap recorded: {gap}.",
                rule_id=GAP_RULE,
                evidence_refs=cohort_refs,
            )
        )

    items.append(
        ExplanationItem(
            code="universal_score_not_calculated",
            kind=ExplanationKind.OBSERVATION,
            message=(
                "CloudEyes reports independent dimensions and does not calculate a universal "
                "provider score."
            ),
            rule_id=NO_UNIVERSAL_SCORE_RULE,
            evidence_refs=(report.report_id,),
        )
    )

    deduplicated: dict[str, ExplanationItem] = {}
    for item in items:
        deduplicated.setdefault(item.code, item)
    return tuple(deduplicated.values())

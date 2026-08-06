"""Price-performance assessment guardrails."""

from __future__ import annotations

from ..models import AssessmentDimension, AssessmentStatus, DimensionAssessment


def assess_value() -> DimensionAssessment:
    """Refuse a value verdict until normalized pricing evidence is available."""

    return DimensionAssessment(
        dimension=AssessmentDimension.VALUE,
        status=AssessmentStatus.NOT_ASSESSED,
        level=None,
        rule_id="value.normalized_price_required.v1",
        summary=(
            "Value was not assessed because the samples do not contain normalized pricing evidence."
        ),
        limitations=("normalized_pricing_required",),
    )

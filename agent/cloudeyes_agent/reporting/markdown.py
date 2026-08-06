"""Markdown rendering for offline provider analytics."""

from __future__ import annotations

from cloudeyes_core.models import AnalyticsBundle, AssessmentStatus


def _level(item) -> str:
    if item.status is AssessmentStatus.NOT_ASSESSED:
        return "not assessed"
    assert item.level is not None
    return item.level.value


def render_analytics_markdown(bundle: AnalyticsBundle) -> str:
    """Render a deterministic human-readable analytics report."""

    lines = [
        "# CloudEyes Provider Analytics v1",
        "",
        f"Generated: `{bundle.generated_at.isoformat()}`",
        "",
        f"Source samples: **{bundle.source_sample_count}**  ",
        f"Analyzed samples: **{bundle.analyzed_sample_count}**  ",
        f"Providers: **{bundle.provider_count}**  ",
        f"Compatible peer groups: **{bundle.peer_group_count}**  ",
        f"Selected pricing quotes: **{bundle.pricing_quote_count}**  ",
        f"Normalized pricing evidence: **{bundle.normalized_pricing_evidence_count}**  ",
        f"Priced value peer groups: **{bundle.value_peer_group_count}**",
        "",
    ]
    if bundle.excluded_sample_ids:
        lines.extend(
            (
                "Excluded invalid samples: "
                + ", ".join(f"`{item}`" for item in bundle.excluded_sample_ids),
                "",
            )
        )

    if bundle.unmatched_pricing_quote_ids:
        lines.extend(
            (
                "Unmatched pricing quotes: "
                + ", ".join(f"`{item}`" for item in bundle.unmatched_pricing_quote_ids),
                "",
            )
        )

    for provider in bundle.providers:
        scorecard = provider.scorecard
        lines.extend(
            [
                f"## {provider.provider_name} (`{provider.provider_id}`)",
                "",
                f"Samples: **{scorecard.sample_count}**  ",
                f"Cohorts: **{scorecard.cohort_count}**  ",
                f"Profiles: {', '.join(scorecard.profiles)}  ",
                f"Expected-metric coverage: **{scorecard.coverage_ratio:.1%}**  ",
                f"Measurement success: **{scorecard.successful_measurement_ratio:.1%}**",
                "",
                "### Scorecard",
                "",
                "| Dimension | Result | Rule | Summary |",
                "|---|---|---|---|",
            ]
        )
        for item in scorecard.dimensions:
            summary = item.summary.replace("|", "\\|")
            lines.append(
                f"| {item.dimension.value} | {_level(item)} | `{item.rule_id}` | {summary} |"
            )

        if provider.peer_comparisons:
            lines.extend(
                [
                    "",
                    "### Compatible peer comparisons",
                    "",
                    (
                        "| Profile | Metric | Provider | Peer median | Difference | "
                        "Outcome | Confidence | Peers |"
                    ),
                    "|---|---|---:|---:|---:|---|---|---:|",
                ]
            )
            for comparison in provider.peer_comparisons:
                lines.append(
                    "| "
                    f"{comparison.profile} | `{comparison.metric_name}` | "
                    f"{comparison.provider_value:.6g} {comparison.unit} | "
                    f"{comparison.peer_median:.6g} {comparison.unit} | "
                    f"{comparison.relative_difference_percent:+.1f}% | "
                    f"{comparison.outcome.value} | {comparison.confidence.value} | "
                    f"{comparison.peer_provider_count} |"
                )

        if provider.pricing_evidence:
            lines.extend(
                [
                    "",
                    "### Normalized pricing evidence",
                    "",
                    (
                        "| Quote | Product / plan | Scope | Commitment / OS | "
                        "Source price | USD/hour | Confidence |"
                    ),
                    "|---|---|---|---|---:|---:|---|",
                ]
            )
            for price in provider.pricing_evidence:
                scope = "/".join(item or "*" for item in (price.region, price.zone))
                lines.append(
                    "| "
                    f"`{price.quote_id}` | {price.product} / {price.plan} | {scope} | "
                    f"{price.commitment.value} / {price.operating_system.value} | "
                    f"{price.source_amount:.6g} {price.source_currency} per "
                    f"{price.billing_period} | {price.hourly_usd:.6g} | "
                    f"{price.confidence.value} |"
                )

        if provider.value_comparisons:
            lines.extend(
                [
                    "",
                    "### Normalized value comparisons",
                    "",
                    (
                        "| Profile | Metric | Provider USD/h | Peer USD/h | "
                        "Value difference | Outcome | Confidence | Peers |"
                    ),
                    "|---|---|---:|---:|---:|---|---|---:|",
                ]
            )
            for comparison in provider.value_comparisons:
                lines.append(
                    "| "
                    f"{comparison.profile} | `{comparison.metric_name}` | "
                    f"{comparison.provider_hourly_usd:.6g} | "
                    f"{comparison.peer_hourly_usd_median:.6g} | "
                    f"{comparison.relative_difference_percent:+.1f}% | "
                    f"{comparison.outcome.value} | {comparison.confidence.value} | "
                    f"{comparison.peer_provider_count} |"
                )

        lines.extend(["", "### Cohorts", ""])
        for cohort in provider.evidence.cohorts:
            lines.extend(
                [
                    f"#### `{cohort.cohort_id}` — {cohort.protocol.profile}",
                    "",
                    (
                        f"Samples: {cohort.sample_count}; observation days: "
                        f"{cohort.coverage.observation_days}; confidence: "
                        f"{cohort.confidence.overall.value}."
                    ),
                    "",
                    "| Metric | Median | p10 | p90 | CV | Samples |",
                    "|---|---:|---:|---:|---:|---:|",
                ]
            )
            for metric in cohort.metrics:
                coefficient = metric.statistics.coefficient_of_variation
                cv = "n/a" if coefficient is None else f"{coefficient:.3f}"
                lines.append(
                    "| "
                    f"`{metric.name}` | {metric.statistics.median:.6g} {metric.unit} | "
                    f"{metric.statistics.p10:.6g} | {metric.statistics.p90:.6g} | "
                    f"{cv} | {metric.contributing_samples} |"
                )
            if cohort.coverage.gaps:
                lines.extend(
                    [
                        "",
                        "Gaps: " + ", ".join(f"`{item}`" for item in cohort.coverage.gaps),
                    ]
                )
            lines.append("")

        lines.extend(["### Explanations", ""])
        for item in provider.explanations:
            refs = ", ".join(f"`{ref}`" for ref in item.evidence_refs) or "none"
            lines.append(
                f"- **{item.kind.value} — {item.code}:** {item.message} "
                f"Rule `{item.rule_id}`; evidence {refs}."
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

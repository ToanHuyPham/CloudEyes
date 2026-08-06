"""Integration test for offline provider analytics CLI output."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from cloudeyes_agent import cli
from cloudeyes_core.serialization import dump

from tests.core_factory import make_sample


def test_analyze_directory_writes_json_and_markdown(tmp_path, capsys) -> None:
    sample_dir = tmp_path / "samples"
    start = datetime(2026, 8, 1, tzinfo=UTC)
    for index, value in enumerate((99.0, 100.0, 101.0)):
        dump(
            make_sample(
                f"sample-{index + 1}",
                created_at=start + timedelta(days=index),
                values=(value,),
            ),
            sample_dir / f"sample-{index + 1}.json",
        )

    output = tmp_path / "analytics.json"
    markdown = tmp_path / "analytics.md"
    exit_code = cli.main(
        (
            "analyze",
            str(sample_dir),
            "--expected-metric",
            "compute.cpu.events_per_second",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--compact",
        )
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))
    assert printed == written
    assert written["provider_count"] == 1
    assert written["providers"][0]["scorecard"]["coverage_ratio"] == 1.0
    rendered = markdown.read_text(encoding="utf-8")
    assert "CloudEyes Provider Analytics v1" in rendered
    assert "universal_score_not_calculated" in rendered


def test_analyze_compares_compatible_providers(tmp_path, capsys) -> None:
    first = tmp_path / "alpha.json"
    second = tmp_path / "beta.json"
    dump(
        make_sample(
            "alpha-sample",
            provider_id="alpha",
            provider_name="Alpha Cloud",
            values=(120.0,),
        ),
        first,
    )
    dump(
        make_sample(
            "beta-sample",
            provider_id="beta",
            provider_name="Beta Cloud",
            values=(100.0,),
        ),
        second,
    )

    markdown = tmp_path / "comparison.md"
    exit_code = cli.main(
        (
            "analyze",
            str(first),
            str(second),
            "--markdown",
            str(markdown),
            "--compact",
        )
    )

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["peer_group_count"] == 1
    assert all(item["peer_comparisons"] for item in result["providers"])
    rendered = markdown.read_text(encoding="utf-8")
    assert "Compatible peer comparisons" in rendered
    assert "ahead" in rendered
    assert "behind" in rendered


def test_analyze_with_pricing_builds_normalized_value_report(tmp_path, capsys) -> None:
    sample_dir = tmp_path / "samples"
    pricing_path = tmp_path / "pricing.json"
    providers = (
        ("alpha", "Alpha Cloud", 120.0, 0.12),
        ("beta", "Beta Cloud", 100.0, 0.08),
        ("gamma", "Gamma Cloud", 105.0, 0.09),
    )
    quotes = []
    for provider_id, provider_name, value, amount in providers:
        dump(
            make_sample(
                f"{provider_id}-sample",
                provider_id=provider_id,
                provider_name=provider_name,
                values=(value,),
            ),
            sample_dir / f"{provider_id}.json",
        )
        quotes.append(
            {
                "quote_id": f"{provider_id}-price",
                "provider_id": provider_id,
                "product": "Cloud Server",
                "plan": "2-vcpu-4gb",
                "region": "hanoi",
                "zone": "zone-1",
                "observed_at": "2026-08-05T00:00:00+00:00",
                "valid_from": "2026-07-01T00:00:00+00:00",
                "valid_until": None,
                "commitment": "on_demand",
                "operating_system": "linux",
                "amount": amount,
                "currency": "USD",
                "billing_period": "hour",
                "billing_period_hours": 1.0,
                "fx_to_usd": 1.0,
                "tax_included": False,
                "source": {
                    "tier": "official_api",
                    "reference": f"example://{provider_id}/price",
                },
            }
        )
    pricing_path.write_text(
        json.dumps({"schema_version": "1.0.0", "quotes": quotes}),
        encoding="utf-8",
    )

    output = tmp_path / "analytics.json"
    markdown = tmp_path / "analytics.md"
    exit_code = cli.main(
        (
            "analyze",
            str(sample_dir),
            "--pricing",
            str(pricing_path),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--compact",
        )
    )

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema_version"] == "1.2.0"
    assert result["normalized_pricing_evidence_count"] == 3
    assert result["value_peer_group_count"] == 1
    outcomes = {
        provider["provider_id"]: provider["value_comparisons"][0]["outcome"]
        for provider in result["providers"]
    }
    assert outcomes == {"alpha": "behind", "beta": "ahead", "gamma": "similar"}
    rendered = markdown.read_text(encoding="utf-8")
    assert "Normalized pricing evidence" in rendered
    assert "Normalized value comparisons" in rendered

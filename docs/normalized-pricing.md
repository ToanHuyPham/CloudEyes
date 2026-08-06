# Normalized Pricing v1

Normalized Pricing v1 adds traceable price evidence and compatible price-performance comparison to
Provider Analytics. It remains fully offline: CloudEyes reads pricing catalogs supplied by the
operator and does not scrape provider websites or call pricing APIs during analysis.

## Pricing catalog

A catalog uses schema `schemas/pricing/catalog-v1.schema.json` and contains one or more quotes.
Every quote records:

- provider, product, plan, optional region, and optional zone;
- observation and validity timestamps;
- commitment and operating-system family;
- source amount, currency, billing-period label, and explicit billing-period hours;
- an explicit FX multiplier to USD;
- tax inclusion state;
- source tier and source reference.

`billing_period_hours` is explicit so CloudEyes does not silently assume a number of hours in a
month. A USD quote must use `fx_to_usd: 1`. For a non-USD quote, the catalog author supplies the FX
multiplier and remains responsible for its provenance.

## Matching policy

A quote can match a cohort only when provider, product, and plan are exact. Region and zone values
are exact when present; `null` means the quote intentionally applies across that scope. The quote
must cover the cohort's complete start-to-end observation interval.

When more than one quote matches, CloudEyes prefers greater location specificity, stronger source
tier, and the latest observation timestamp. If equally ranked quotes disagree on normalized price,
analysis fails with an ambiguity error.

## Normalization and confidence

Hourly USD is calculated as:

```text
hourly_usd = amount × fx_to_usd ÷ billing_period_hours
```

Source confidence is conservative:

- `official_api` and `official_document`: high;
- `reseller`: medium;
- `manual`: low.

The confidence of a value comparison cannot exceed the weakest contributing measurement or pricing
evidence.

## Price-performance value index

For compatible peer metrics, CloudEyes produces a value index where larger is always better:

```text
higher-is-better: metric_value / hourly_usd
lower-is-better:  1 / (metric_value × hourly_usd)
```

Each provider contributes one median index regardless of sample or cohort count. The subject
provider is excluded from its own peer baseline. The same five-percent similarity band used by
performance comparison produces `ahead`, `similar`, or `behind` outcomes.

Pricing without a compatible priced peer remains evidence only; the value dimension stays
`not_assessed`. CloudEyes does not produce an absolute value verdict or universal provider score.

## CLI

```bash
python -m cloudeyes_agent analyze \
  examples/samples/peer-comparison-v1 \
  --pricing examples/pricing/peer-comparison-v1.json \
  --pricing-commitment on_demand \
  --pricing-os linux \
  --output reports/provider-value.json \
  --markdown reports/provider-value.md
```

Repeat `--pricing` to load multiple catalogs. Quote IDs must remain unique across all supplied
catalogs. The analytics output reports selected quote count, normalized evidence count, unmatched
quote IDs, value peer-group count, per-provider pricing evidence, and per-metric value comparisons.

# Provider Analytics v1

Provider Analytics v1 turns validated local samples into deterministic, offline provider reports.
It preserves the CloudEyes separation between measurement, evidence, assessment, and explanation.

## Input

One or more CloudEyes sample JSON files. A directory input reads only `*.json` files directly
inside that directory; it does not recurse into raw-evidence folders.

Invalid samples are excluded and listed in `excluded_sample_ids`. Duplicate sample IDs or malformed
valid samples stop analysis instead of producing a partial conclusion.

## Output

The analytics bundle contains one report per provider with:

- strict compatible cohorts;
- equal-weight metric summaries;
- expected-metric coverage and explicit evidence gaps;
- measurement, statistical, and coverage confidence;
- independent evidence, consistency, reliability, performance, and value dimensions;
- traceable explanation items with rule IDs and evidence references;
- optional Markdown rendering.

CloudEyes deliberately does not calculate a universal provider score.

## Deterministic rules

### Evidence

The evidence dimension uses the lowest cohort confidence dimension already defined by Core
Foundation v1. Expected-metric coverage is reported separately as a ratio.

### Consistency

Consistency uses the worst finite coefficient of variation among metrics with at least two
contributing samples:

- high: at most 0.10;
- medium: at most 0.25;
- low: above 0.25 or no usable variation result.

This is a statement about the observed samples, not provider-wide historical stability.

### Reliability

Reliability measures benchmark completion and sample quality only:

- high: at least 95% successful measurements with no sample warnings or errors;
- medium: at least 80% successful measurements and no sample errors;
- low: below the medium threshold.

It must not be interpreted as provider uptime or SLA compliance.

### Performance and value

Performance remains `not_assessed` until a compatible peer baseline is supplied. Value remains
`not_assessed` until normalized pricing evidence exists. Measured throughput alone is not converted
into an absolute provider verdict.

## CLI

```bash
python -m cloudeyes_agent analyze data/samples \
  --expected-metric compute.cpu.integer.single_core.million_operations_per_second \
  --output reports/provider-analytics.json \
  --markdown reports/provider-analytics.md
```

Multiple files and directories may be provided:

```bash
python -m cloudeyes_agent analyze \
  data/general-sample.json \
  data/storage-sample.json \
  data/networking-sample.json \
  data/compute-sample.json \
  --output reports/provider-analytics.json
```

Keep analytics output outside an input directory so a later run does not attempt to load the report
as a sample.

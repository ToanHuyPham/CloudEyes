# Core Foundation v1

## Status

Complete and testable.

## Input

One or more immutable `Sample` objects or JSON sample files.

## Output

One `ProviderReport` per provider. A report contains:

- strict cohort identity;
- sample and observation coverage;
- equal-weight metric summaries;
- measurement, statistical, and coverage confidence;
- explicit evidence gaps;
- deterministic report and cohort identifiers.

## Cohort compatibility

Samples are grouped only when these fields match:

- provider and country;
- product, plan, region, and zone;
- machine type, CPU count, memory size, and architecture;
- profile, protocol version, and protocol fingerprint.

## Statistical rule

Repeated values of one metric inside one sample are reduced to their median. The cohort summary then uses one value from each sample. This prevents a sample with more repetitions from receiving extra weight.

## Confidence thresholds

### Measurement

- High: worst metric coefficient of variation is at most 10%.
- Medium: worst metric coefficient of variation is at most 25%.
- Low: above 25% or no usable metric.

### Statistical

- High: at least 10 samples across at least 7 days.
- Medium: at least 3 samples across at least 3 days.
- Low: below the medium threshold.

### Coverage

- High: at least 90% of expected metrics, with known region and plan.
- Medium: at least 60% of expected metrics.
- Low: below 60%.

Overall confidence is the lowest of the three dimensions.

## Repository guarantees

`JsonSampleRepository` validates every sample, rejects unsafe IDs, prevents accidental overwrite, and performs atomic file replacement.

## Commands

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check core tests
```

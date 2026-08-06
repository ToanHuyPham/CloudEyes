# CloudEyes Provider Analytics v1

Generated: `2026-08-06T09:56:44.089922+00:00`

Source samples: **9**  
Analyzed samples: **9**  
Providers: **3**  
Compatible peer groups: **1**

## Alpha Cloud (`alpha-cloud`)

Samples: **3**  
Cohorts: **1**  
Profiles: general  
Expected-metric coverage: **100.0%**  
Measurement success: **100.0%**

### Scorecard

| Dimension | Result | Rule | Summary |
|---|---|---|---|
| evidence | medium | `evidence.minimum_confidence.v1` | Evidence confidence is medium; mean expected-metric coverage is 100.0%. |
| consistency | high | `consistency.cv.v1` | Observed metrics were stable; worst coefficient of variation was 0.017. |
| reliability | high | `reliability.measurement_completion.v1` | Measurement completion was high at 100.0%, with no sample warnings or errors. |
| performance | high | `performance.compatible_peer_relative.v1` | Across 1 compatible peer metrics at the 5% similarity threshold: 1 ahead, 0 similar, and 0 behind. |
| value | not assessed | `value.normalized_price_required.v1` | Value was not assessed because the samples do not contain normalized pricing evidence. |

### Compatible peer comparisons

| Profile | Metric | Provider | Peer median | Difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 120 events_per_second | 102.5 events_per_second | +17.1% | ahead | medium | 2 |

### Cohorts

#### `cohort-29a5b067541de1c9` — general

Samples: 3; observation days: 3; confidence: medium.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `compute.cpu.events_per_second` | 120 events_per_second | 118.4 | 121.6 | 0.017 | 3 |

### Explanations

- **observation — evidence_medium:** Evidence confidence is medium; mean expected-metric coverage is 100.0%. Rule `evidence.minimum_confidence.v1`; evidence `cohort-29a5b067541de1c9`.
- **strength — consistency_high:** Observed metrics were stable; worst coefficient of variation was 0.017. Rule `consistency.cv.v1`; evidence `cohort-29a5b067541de1c9:compute.cpu.events_per_second`.
- **strength — reliability_high:** Measurement completion was high at 100.0%, with no sample warnings or errors. Rule `reliability.measurement_completion.v1`; evidence `alpha-cloud-1`, `alpha-cloud-2`, `alpha-cloud-3`.
- **strength — performance_high:** Across 1 compatible peer metrics at the 5% similarity threshold: 1 ahead, 0 similar, and 0 behind. Rule `performance.compatible_peer_relative.v1`; evidence `peer-comparison-93548ddb5d2248ca`.
- **limitation — value_not_assessed:** Value was not assessed because the samples do not contain normalized pricing evidence. Rule `value.normalized_price_required.v1`; evidence none.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-7e13c6c59c38a744`.

## Beta Cloud (`beta-cloud`)

Samples: **3**  
Cohorts: **1**  
Profiles: general  
Expected-metric coverage: **100.0%**  
Measurement success: **100.0%**

### Scorecard

| Dimension | Result | Rule | Summary |
|---|---|---|---|
| evidence | medium | `evidence.minimum_confidence.v1` | Evidence confidence is medium; mean expected-metric coverage is 100.0%. |
| consistency | high | `consistency.cv.v1` | Observed metrics were stable; worst coefficient of variation was 0.020. |
| reliability | high | `reliability.measurement_completion.v1` | Measurement completion was high at 100.0%, with no sample warnings or errors. |
| performance | low | `performance.compatible_peer_relative.v1` | Across 1 compatible peer metrics at the 5% similarity threshold: 0 ahead, 0 similar, and 1 behind. |
| value | not assessed | `value.normalized_price_required.v1` | Value was not assessed because the samples do not contain normalized pricing evidence. |

### Compatible peer comparisons

| Profile | Metric | Provider | Peer median | Difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 100 events_per_second | 112.5 events_per_second | -11.1% | behind | medium | 2 |

### Cohorts

#### `cohort-5f79a4fdc9e76ccd` — general

Samples: 3; observation days: 3; confidence: medium.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `compute.cpu.events_per_second` | 100 events_per_second | 98.4 | 101.6 | 0.020 | 3 |

### Explanations

- **observation — evidence_medium:** Evidence confidence is medium; mean expected-metric coverage is 100.0%. Rule `evidence.minimum_confidence.v1`; evidence `cohort-5f79a4fdc9e76ccd`.
- **strength — consistency_high:** Observed metrics were stable; worst coefficient of variation was 0.020. Rule `consistency.cv.v1`; evidence `cohort-5f79a4fdc9e76ccd:compute.cpu.events_per_second`.
- **strength — reliability_high:** Measurement completion was high at 100.0%, with no sample warnings or errors. Rule `reliability.measurement_completion.v1`; evidence `beta-cloud-1`, `beta-cloud-2`, `beta-cloud-3`.
- **limitation — performance_low:** Across 1 compatible peer metrics at the 5% similarity threshold: 0 ahead, 0 similar, and 1 behind. Rule `performance.compatible_peer_relative.v1`; evidence `peer-comparison-c34e9c0506e39d40`.
- **limitation — value_not_assessed:** Value was not assessed because the samples do not contain normalized pricing evidence. Rule `value.normalized_price_required.v1`; evidence none.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-747693c2c74720da`.

## Gamma Cloud (`gamma-cloud`)

Samples: **3**  
Cohorts: **1**  
Profiles: general  
Expected-metric coverage: **100.0%**  
Measurement success: **100.0%**

### Scorecard

| Dimension | Result | Rule | Summary |
|---|---|---|---|
| evidence | medium | `evidence.minimum_confidence.v1` | Evidence confidence is medium; mean expected-metric coverage is 100.0%. |
| consistency | high | `consistency.cv.v1` | Observed metrics were stable; worst coefficient of variation was 0.010. |
| reliability | high | `reliability.measurement_completion.v1` | Measurement completion was high at 100.0%, with no sample warnings or errors. |
| performance | medium | `performance.compatible_peer_relative.v1` | Across 1 compatible peer metrics at the 5% similarity threshold: 0 ahead, 1 similar, and 0 behind. |
| value | not assessed | `value.normalized_price_required.v1` | Value was not assessed because the samples do not contain normalized pricing evidence. |

### Compatible peer comparisons

| Profile | Metric | Provider | Peer median | Difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 105 events_per_second | 110 events_per_second | -4.5% | similar | medium | 2 |

### Cohorts

#### `cohort-7d6fe530223d3340` — general

Samples: 3; observation days: 3; confidence: medium.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `compute.cpu.events_per_second` | 105 events_per_second | 104.2 | 105.8 | 0.010 | 3 |

### Explanations

- **observation — evidence_medium:** Evidence confidence is medium; mean expected-metric coverage is 100.0%. Rule `evidence.minimum_confidence.v1`; evidence `cohort-7d6fe530223d3340`.
- **strength — consistency_high:** Observed metrics were stable; worst coefficient of variation was 0.010. Rule `consistency.cv.v1`; evidence `cohort-7d6fe530223d3340:compute.cpu.events_per_second`.
- **strength — reliability_high:** Measurement completion was high at 100.0%, with no sample warnings or errors. Rule `reliability.measurement_completion.v1`; evidence `gamma-cloud-1`, `gamma-cloud-2`, `gamma-cloud-3`.
- **observation — performance_medium:** Across 1 compatible peer metrics at the 5% similarity threshold: 0 ahead, 1 similar, and 0 behind. Rule `performance.compatible_peer_relative.v1`; evidence `peer-comparison-95bb2b54a49bbddb`.
- **limitation — value_not_assessed:** Value was not assessed because the samples do not contain normalized pricing evidence. Rule `value.normalized_price_required.v1`; evidence none.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-7af761639c3f1b60`.

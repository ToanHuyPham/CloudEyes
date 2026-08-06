# CloudEyes Provider Analytics v1

Generated: `2026-08-06T12:00:00+00:00`

Source samples: **9**  
Analyzed samples: **9**  
Providers: **3**  
Compatible peer groups: **1**  
Selected pricing quotes: **3**  
Normalized pricing evidence: **3**  
Priced value peer groups: **1**

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
| value | low | `value.compatible_peer_price_performance.v1` | Across 1 normalized price-performance metrics at the 5% similarity threshold: 0 ahead, 0 similar, and 1 behind. |

### Compatible peer comparisons

| Profile | Metric | Provider | Peer median | Difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 120 events_per_second | 102.5 events_per_second | +17.1% | ahead | medium | 2 |

### Normalized pricing evidence

| Quote | Product / plan | Scope | Commitment / OS | Source price | USD/hour | Confidence |
|---|---|---|---|---:|---:|---|
| `alpha-cloud-on-demand-linux-2026-08` | Cloud Server / 2-vcpu-4gb | hanoi/zone-1 | on_demand / linux | 0.12 USD per hour | 0.12 | high |

### Normalized value comparisons

| Profile | Metric | Provider USD/h | Peer USD/h | Value difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 0.12 | 0.085 | -17.2% | behind | medium | 2 |

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
- **limitation — value_low:** Across 1 normalized price-performance metrics at the 5% similarity threshold: 0 ahead, 0 similar, and 1 behind. Rule `value.compatible_peer_price_performance.v1`; evidence `value-comparison-93548ddb5d2248ca`.
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
| value | high | `value.compatible_peer_price_performance.v1` | Across 1 normalized price-performance metrics at the 5% similarity threshold: 1 ahead, 0 similar, and 0 behind. |

### Compatible peer comparisons

| Profile | Metric | Provider | Peer median | Difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 100 events_per_second | 112.5 events_per_second | -11.1% | behind | medium | 2 |

### Normalized pricing evidence

| Quote | Product / plan | Scope | Commitment / OS | Source price | USD/hour | Confidence |
|---|---|---|---|---:|---:|---|
| `beta-cloud-on-demand-linux-2026-08` | Cloud Server / 2-vcpu-4gb | hanoi/zone-1 | on_demand / linux | 0.08 USD per hour | 0.08 | high |

### Normalized value comparisons

| Profile | Metric | Provider USD/h | Peer USD/h | Value difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 0.08 | 0.105 | +15.4% | ahead | medium | 2 |

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
- **strength — value_high:** Across 1 normalized price-performance metrics at the 5% similarity threshold: 1 ahead, 0 similar, and 0 behind. Rule `value.compatible_peer_price_performance.v1`; evidence `value-comparison-c34e9c0506e39d40`.
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
| value | medium | `value.compatible_peer_price_performance.v1` | Across 1 normalized price-performance metrics at the 5% similarity threshold: 0 ahead, 1 similar, and 0 behind. |

### Compatible peer comparisons

| Profile | Metric | Provider | Peer median | Difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 105 events_per_second | 110 events_per_second | -4.5% | similar | medium | 2 |

### Normalized pricing evidence

| Quote | Product / plan | Scope | Commitment / OS | Source price | USD/hour | Confidence |
|---|---|---|---|---:|---:|---|
| `gamma-cloud-on-demand-linux-2026-08` | Cloud Server / 2-vcpu-4gb | hanoi/zone-1 | on_demand / linux | 0.09 USD per hour | 0.09 | high |

### Normalized value comparisons

| Profile | Metric | Provider USD/h | Peer USD/h | Value difference | Outcome | Confidence | Peers |
|---|---|---:|---:|---:|---|---|---:|
| general | `compute.cpu.events_per_second` | 0.09 | 0.1 | +3.7% | similar | medium | 2 |

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
- **observation — value_medium:** Across 1 normalized price-performance metrics at the 5% similarity threshold: 0 ahead, 1 similar, and 0 behind. Rule `value.compatible_peer_price_performance.v1`; evidence `value-comparison-95bb2b54a49bbddb`.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-7af761639c3f1b60`.

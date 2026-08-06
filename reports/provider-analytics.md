# CloudEyes Provider Analytics v1

Generated: `2026-08-06T09:39:32.462937+00:00`

Source samples: **4**  
Analyzed samples: **4**  
Providers: **3**

## Microsoft Azure (`azure`)

Samples: **2**  
Cohorts: **2**  
Profiles: compute, storage  
Expected-metric coverage: **100.0%**  
Measurement success: **100.0%**

### Scorecard

| Dimension | Result | Rule | Summary |
|---|---|---|---|
| evidence | low | `evidence.minimum_confidence.v1` | Evidence confidence is low; mean expected-metric coverage is 100.0%. |
| consistency | low | `consistency.cv.v1` | No metric had enough finite variation data for a stable consistency result. |
| reliability | high | `reliability.measurement_completion.v1` | Measurement completion was high at 100.0%, with no sample warnings or errors. |
| performance | not assessed | `performance.compatible_peer_required.v1` | Performance was measured but not graded because no compatible peer baseline was supplied. |
| value | not assessed | `value.normalized_price_required.v1` | Value was not assessed because the samples do not contain normalized pricing evidence. |

### Cohorts

#### `cohort-07049731e59bf16a` — compute

Samples: 1; observation days: 1; confidence: low.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `compute.compression.single_core.mib_per_second` | 38.8257 mib_per_second | 38.8257 | 38.8257 | 0.000 | 1 |
| `compute.concurrency.scaling_ratio` | 1.16624 ratio | 1.16624 | 1.16624 | 0.000 | 1 |
| `compute.concurrency.worker_efficiency_percent` | 58.3118 percent | 58.3118 | 58.3118 | 0.000 | 1 |
| `compute.floating_point.single_core.iterations_per_second` | 1.02033e+07 iterations_per_second | 1.02033e+07 | 1.02033e+07 | 0.000 | 1 |
| `compute.integer.multi_core.iterations_per_second` | 3.81301e+06 iterations_per_second | 3.81301e+06 | 3.81301e+06 | 0.000 | 1 |
| `compute.integer.single_core.iterations_per_second` | 3.2695e+06 iterations_per_second | 3.2695e+06 | 3.2695e+06 | 0.000 | 1 |
| `compute.sha256.single_core.mib_per_second` | 1115.73 mib_per_second | 1115.73 | 1115.73 | 0.000 | 1 |

Gaps: `insufficient_samples`, `short_observation_period`

#### `cohort-871d3af8c7e9c0e8` — storage

Samples: 1; observation days: 1; confidence: low.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `storage.fsync.p50_milliseconds` | 0.291671 milliseconds | 0.291671 | 0.291671 | 0.000 | 1 |
| `storage.fsync.p95_milliseconds` | 0.67358 milliseconds | 0.67358 | 0.67358 | 0.000 | 1 |
| `storage.random_read.cached_iops` | 564446 operations_per_second | 564446 | 564446 | 0.000 | 1 |
| `storage.random_write.fsync_batch_iops` | 14027.2 operations_per_second | 14027.2 | 14027.2 | 0.000 | 1 |
| `storage.sequential_read.cached_mib_per_second` | 1148.6 mib_per_second | 1148.6 | 1148.6 | 0.000 | 1 |
| `storage.sequential_write.fsync_mib_per_second` | 453.351 mib_per_second | 453.351 | 453.351 | 0.000 | 1 |

Gaps: `insufficient_samples`, `short_observation_period`

### Explanations

- **limitation — evidence_low:** Evidence confidence is low; mean expected-metric coverage is 100.0%. Rule `evidence.minimum_confidence.v1`; evidence `cohort-07049731e59bf16a`, `cohort-871d3af8c7e9c0e8`.
- **limitation — consistency_low:** No metric had enough finite variation data for a stable consistency result. Rule `consistency.cv.v1`; evidence `cohort-07049731e59bf16a`, `cohort-871d3af8c7e9c0e8`.
- **strength — reliability_high:** Measurement completion was high at 100.0%, with no sample warnings or errors. Rule `reliability.measurement_completion.v1`; evidence `compute-example`, `storage-example`.
- **limitation — performance_not_assessed:** Performance was measured but not graded because no compatible peer baseline was supplied. Rule `performance.compatible_peer_required.v1`; evidence `cohort-07049731e59bf16a`, `cohort-871d3af8c7e9c0e8`.
- **limitation — value_not_assessed:** Value was not assessed because the samples do not contain normalized pricing evidence. Rule `value.normalized_price_required.v1`; evidence none.
- **limitation — coverage_gap:insufficient_samples:** Evidence gap recorded: insufficient_samples. Rule `explanation.coverage_gap.v1`; evidence `cohort-07049731e59bf16a`, `cohort-871d3af8c7e9c0e8`.
- **limitation — coverage_gap:short_observation_period:** Evidence gap recorded: short_observation_period. Rule `explanation.coverage_gap.v1`; evidence `cohort-07049731e59bf16a`, `cohort-871d3af8c7e9c0e8`.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-e36e750cbec92029`.

## Example Cloud (`example-cloud`)

Samples: **1**  
Cohorts: **1**  
Profiles: general  
Expected-metric coverage: **100.0%**  
Measurement success: **100.0%**

### Scorecard

| Dimension | Result | Rule | Summary |
|---|---|---|---|
| evidence | low | `evidence.minimum_confidence.v1` | Evidence confidence is low; mean expected-metric coverage is 100.0%. |
| consistency | low | `consistency.cv.v1` | No metric had enough finite variation data for a stable consistency result. |
| reliability | high | `reliability.measurement_completion.v1` | Measurement completion was high at 100.0%, with no sample warnings or errors. |
| performance | not assessed | `performance.compatible_peer_required.v1` | Performance was measured but not graded because no compatible peer baseline was supplied. |
| value | not assessed | `value.normalized_price_required.v1` | Value was not assessed because the samples do not contain normalized pricing evidence. |

### Cohorts

#### `cohort-cf93abc552c6ada5` — general

Samples: 1; observation days: 1; confidence: low.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `compute.cpu.sha256_mib_per_second` | 512.5 mib_per_second | 512.5 | 512.5 | 0.000 | 1 |
| `memory.copy.mib_per_second` | 8450.25 mib_per_second | 8450.25 | 8450.25 | 0.000 | 1 |
| `storage.sequential_read.mib_per_second` | 1250.75 mib_per_second | 1250.75 | 1250.75 | 0.000 | 1 |
| `storage.sequential_write.mib_per_second` | 420.5 mib_per_second | 420.5 | 420.5 | 0.000 | 1 |

Gaps: `insufficient_samples`, `short_observation_period`

### Explanations

- **limitation — evidence_low:** Evidence confidence is low; mean expected-metric coverage is 100.0%. Rule `evidence.minimum_confidence.v1`; evidence `cohort-cf93abc552c6ada5`.
- **limitation — consistency_low:** No metric had enough finite variation data for a stable consistency result. Rule `consistency.cv.v1`; evidence `cohort-cf93abc552c6ada5`.
- **strength — reliability_high:** Measurement completion was high at 100.0%, with no sample warnings or errors. Rule `reliability.measurement_completion.v1`; evidence `general-example`.
- **limitation — performance_not_assessed:** Performance was measured but not graded because no compatible peer baseline was supplied. Rule `performance.compatible_peer_required.v1`; evidence `cohort-cf93abc552c6ada5`.
- **limitation — value_not_assessed:** Value was not assessed because the samples do not contain normalized pricing evidence. Rule `value.normalized_price_required.v1`; evidence none.
- **limitation — coverage_gap:insufficient_samples:** Evidence gap recorded: insufficient_samples. Rule `explanation.coverage_gap.v1`; evidence `cohort-cf93abc552c6ada5`.
- **limitation — coverage_gap:short_observation_period:** Evidence gap recorded: short_observation_period. Rule `explanation.coverage_gap.v1`; evidence `cohort-cf93abc552c6ada5`.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-7ff3c6234c7e9779`.

## Google Cloud (`gcp`)

Samples: **1**  
Cohorts: **1**  
Profiles: networking  
Expected-metric coverage: **100.0%**  
Measurement success: **100.0%**

### Scorecard

| Dimension | Result | Rule | Summary |
|---|---|---|---|
| evidence | low | `evidence.minimum_confidence.v1` | Evidence confidence is low; mean expected-metric coverage is 100.0%. |
| consistency | low | `consistency.cv.v1` | No metric had enough finite variation data for a stable consistency result. |
| reliability | medium | `reliability.measurement_completion.v1` | Measurement completion was 100.0%; some samples contained quality warnings. |
| performance | not assessed | `performance.compatible_peer_required.v1` | Performance was measured but not graded because no compatible peer baseline was supplied. |
| value | not assessed | `value.normalized_price_required.v1` | Value was not assessed because the samples do not contain normalized pricing evidence. |

### Cohorts

#### `cohort-6617c3158b7a0d8d` — networking

Samples: 1; observation days: 1; confidence: low.

| Metric | Median | p10 | p90 | CV | Samples |
|---|---:|---:|---:|---:|---:|
| `network.dns.lookup.p50_milliseconds` | 0.42 milliseconds | 0.42 | 0.42 | 0.000 | 1 |
| `network.dns.lookup.p95_milliseconds` | 0.61 milliseconds | 0.61 | 0.61 | 0.000 | 1 |
| `network.download.mib_per_second` | 412.75 mib_per_second | 412.75 | 412.75 | 0.000 | 1 |
| `network.http.request_loss_percent` | 0 percent | 0 | 0 | n/a | 1 |
| `network.http.ttfb.p50_milliseconds` | 3.76 milliseconds | 3.76 | 3.76 | 0.000 | 1 |
| `network.http.ttfb.p95_milliseconds` | 4.12 milliseconds | 4.12 | 4.12 | 0.000 | 1 |
| `network.tcp.connect.p50_milliseconds` | 1.84 milliseconds | 1.84 | 1.84 | 0.000 | 1 |
| `network.tcp.connect.p95_milliseconds` | 2.11 milliseconds | 2.11 | 2.11 | 0.000 | 1 |
| `network.upload.mib_per_second` | 286.4 mib_per_second | 286.4 | 286.4 | 0.000 | 1 |

Gaps: `insufficient_samples`, `short_observation_period`

### Explanations

- **limitation — evidence_low:** Evidence confidence is low; mean expected-metric coverage is 100.0%. Rule `evidence.minimum_confidence.v1`; evidence `cohort-6617c3158b7a0d8d`.
- **limitation — consistency_low:** No metric had enough finite variation data for a stable consistency result. Rule `consistency.cv.v1`; evidence `cohort-6617c3158b7a0d8d`.
- **observation — reliability_medium:** Measurement completion was 100.0%; some samples contained quality warnings. Rule `reliability.measurement_completion.v1`; evidence `networking-example`.
- **limitation — performance_not_assessed:** Performance was measured but not graded because no compatible peer baseline was supplied. Rule `performance.compatible_peer_required.v1`; evidence `cohort-6617c3158b7a0d8d`.
- **limitation — value_not_assessed:** Value was not assessed because the samples do not contain normalized pricing evidence. Rule `value.normalized_price_required.v1`; evidence none.
- **limitation — coverage_gap:insufficient_samples:** Evidence gap recorded: insufficient_samples. Rule `explanation.coverage_gap.v1`; evidence `cohort-6617c3158b7a0d8d`.
- **limitation — coverage_gap:short_observation_period:** Evidence gap recorded: short_observation_period. Rule `explanation.coverage_gap.v1`; evidence `cohort-6617c3158b7a0d8d`.
- **observation — universal_score_not_calculated:** CloudEyes reports independent dimensions and does not calculate a universal provider score. Rule `explanation.no_universal_score.v1`; evidence `provider-report-662a30e063bfc6f0`.

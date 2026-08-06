# Compatible Peer Comparison v1

Compatible Peer Comparison v1 supplies the baseline required by the performance dimension. It is
strict by design: a result is produced only when at least two identified providers have matching
hardware, geography, profile, protocol version, and protocol fingerprint.

## Cross-provider compatibility key

The peer key contains:

- country code;
- machine type, logical CPU count, memory bytes, and architecture;
- profile name;
- protocol version and fingerprint.

Provider ID is excluded because providers are the subjects being compared. Product, plan, region,
and zone labels are also excluded because their naming is provider-specific. Those fields remain in
the underlying cohort evidence and are never discarded.

Samples with an unknown provider or unknown country are not compared. Hardware values are exact in
v1; CloudEyes does not silently bucket approximate memory sizes or assume two product labels are
equivalent.

## Equal weighting

CloudEyes first reduces repeated observations inside one sample to a sample median, as in the cohort
summary. When one provider has multiple compatible cohorts, their cohort medians are reduced to one
provider median. The peer baseline is then the median of the other providers' values. Each provider
therefore contributes one value regardless of sample count or number of matching cohorts.

The subject provider is excluded from its own baseline.

## Direction and outcome

Only metrics marked `higher_is_better` or `lower_is_better` are compared. A positive relative
difference always means the subject provider performed better after metric direction is applied.

The fixed v1 similarity band is five percent:

- `ahead`: at least +5%;
- `similar`: greater than -5% and less than +5%;
- `behind`: at most -5%.

A peer median of zero is not converted into a percentage and is skipped rather than producing an
infinite or misleading result.

## Comparison confidence

Each metric comparison records a separate confidence level:

- high: at least two peer providers and all contributing cohort confidence levels are high;
- medium: all contributing cohort confidence levels are at least medium;
- low: otherwise.

A one-peer baseline can be useful but cannot receive high comparison confidence.

## Performance dimension

The performance dimension is assessed only when compatible metric comparisons exist. It reports the
number of metrics ahead, similar, and behind. `high`, `medium`, and `low` describe the directional
balance of those compatible metrics; they are not a universal provider score and do not combine
performance with reliability, evidence quality, or price.

The JSON and Markdown reports retain every comparison ID, peer group ID, peer provider ID, and cohort
evidence reference needed to audit the conclusion.

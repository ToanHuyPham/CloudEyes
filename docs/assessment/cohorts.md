# Cohorts

A cohort contains samples that match the strict compatibility key:

- provider and country;
- product, plan, region, and zone;
- machine type, CPU count, memory size, and architecture;
- profile, protocol version, and protocol fingerprint.

Invalid samples are not added to cohorts. Samples are ordered by creation time and sample ID.
Repeated observations of one metric inside one sample are reduced to a median before the cohort is
summarized, so every sample receives equal weight.

A cohort is evidence for only its measured scope. Provider Analytics v1 does not merge different
protocol fingerprints, machine sizes, regions, plans, or profiles into one performance conclusion.

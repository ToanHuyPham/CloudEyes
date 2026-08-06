# Normalized Pricing v1

The pricing package accepts offline, versioned price catalogs and normalizes selected quotes to
USD per hour. Pricing is matched to cohorts by exact provider, product, and plan identity. Region
and zone may be exact or omitted as an explicit wildcard. A quote must cover the complete cohort
observation window.

Quote selection is deterministic:

1. selected commitment and operating-system family;
2. exact product and plan;
3. most specific region and zone;
4. strongest source tier;
5. latest observation time.

Conflicting top-ranked quotes stop analysis rather than silently choosing a price. The value index
keeps larger values better for every metric direction:

- higher-is-better: `metric / USD-per-hour`;
- lower-is-better: `1 / (metric * USD-per-hour)`.

Value is compared only inside the same strict compatible peer group used by performance analysis.
Each provider contributes one median value to the peer baseline. CloudEyes does not fetch live
prices, infer taxes, invent exchange rates, or combine value into a universal provider score.

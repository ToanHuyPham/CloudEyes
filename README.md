# CloudEyes

CloudEyes is an evidence-based cloud provider assessment framework.

It measures infrastructure, preserves raw evidence, groups compatible samples into cohorts, and explains whether a provider is suitable for a given workload.

This repository is the long-term project foundation.

Implemented Agent profiles:

- General Profile v1
- Storage Profile v1
- Networking Profile v1
- Compute Profile v1
- Web Profile v1

Example controlled networking run:

```bash
python -m cloudeyes_agent run networking \
  --target https://benchmark.example.net/download \
  --upload-target https://benchmark.example.net/upload \
  --scope public \
  --output data/networking-sample.json
```


Example bounded compute run:

```bash
python -m cloudeyes_agent run compute \
  --workers 4 \
  --output data/compute-sample.json
```

Example bounded web-service run:

```bash
python -m cloudeyes_agent run web \
  --target https://example.com/ \
  --requests 40 \
  --concurrency 4 \
  --output data/web-sample.json
```

Offline provider analytics with optional normalized pricing:

```bash
python -m cloudeyes_agent analyze data/samples \
  --pricing data/pricing/catalog.json \
  --output reports/provider-analytics.json \
  --markdown reports/provider-analytics.md
```

Provider Analytics v1 reports independent evidence, consistency, reliability, performance, and
value dimensions. Compatible Peer Comparison v1 grades performance only when country, machine,
profile, and protocol identity match exactly across providers. Normalized Pricing v1 accepts
traceable offline price catalogs, converts selected quotes to USD per hour, and grades value only
inside compatible priced peer groups. It deliberately does not calculate a universal provider score.


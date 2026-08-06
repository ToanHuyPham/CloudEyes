# CloudEyes

CloudEyes is an evidence-based cloud provider assessment framework.

It measures infrastructure, preserves raw evidence, groups compatible samples into cohorts, and explains whether a provider is suitable for a given workload.

This repository is the long-term project foundation.

Implemented Agent profiles:

- General Profile v1
- Storage Profile v1
- Networking Profile v1
- Compute Profile v1

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

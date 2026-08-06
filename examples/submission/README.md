# Result Bundle Example

From the repository root:

```bash
python -m cloudeyes_agent bundle \
  examples/compute-profile-sample.json \
  examples/database-profile-sample.json \
  examples/networking-profile-sample.json \
  examples/storage-profile-sample.json \
  examples/web-profile-sample.json \
  --output data/example-results.zip

python -m cloudeyes_agent verify-bundle data/example-results.zip

python -m cloudeyes_agent submit data/example-results.zip \
  --endpoint https://collector.example.test/v1/submissions \
  --dry-run
```

The example does not contact a real service.

# Result Bundle and Submission v1

CloudEyes does not upload benchmark results automatically. Profile execution writes local sample
JSON and optional raw evidence. A separate explicit workflow validates, packages, verifies, and
submits those files.

## Build a bundle

```bash
python -m cloudeyes_agent bundle \
  data/general-sample.json \
  data/storage-sample.json \
  data/networking-sample.json \
  --output data/submissions/cloud-run.zip
```

The builder:

- deserializes every sample into the Core model;
- runs cross-field semantic validation;
- resolves referenced `raw_output_path` JSON files only under trusted local roots;
- redacts credential-like keys and URL user/query/fragment components from raw evidence;
- writes canonical JSON payloads;
- records SHA-256 and byte size for every payload;
- writes the ZIP atomically with safe internal paths.

Missing raw evidence and invalid samples fail closed by default. `--allow-missing-raw` and
`--allow-invalid` are explicit exceptions recorded in the manifest warnings and policy.

## Verify before transport

```bash
python -m cloudeyes_agent verify-bundle data/submissions/cloud-run.zip
```

Verification rejects path traversal, duplicate ZIP entries, symbolic links, encryption, unlisted
payloads, checksum mismatches, unsupported manifest fields, invalid sample payloads, and oversized
archives.

## Dry-run a submission

```bash
python -m cloudeyes_agent submit data/submissions/cloud-run.zip \
  --endpoint https://collector.example.net/v1/submissions \
  --dry-run
```

Dry run performs all local verification and endpoint policy checks without network access.

## Authenticated submission

```bash
export CLOUDEYES_API_TOKEN='replace-with-a-secret-from-the-collector'
python -m cloudeyes_agent submit data/submissions/cloud-run.zip \
  --endpoint https://collector.example.net/v1/submissions \
  --receipt data/submissions/cloud-run.receipt.json
```

The token is read from an environment variable and is never stored in the bundle or receipt.
CloudEyes sends the bundle SHA-256 as the idempotency key, refuses redirects, limits the response
to 64 KiB, and writes a privacy-safe receipt. Plain HTTP requires `--allow-http` and is restricted
to private or loopback test endpoints.

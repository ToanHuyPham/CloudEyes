# Bundle Schemas

`manifest-v1.schema.json` defines the integrity manifest stored as `manifest.json` inside a
CloudEyes result bundle. Payload checksums cover canonical sample JSON and privacy-filtered raw
evidence. The ZIP archive itself is hashed separately at verification and submission time.

# Result Bundles

This package creates deterministic JSON payloads inside a ZIP container, verifies every SHA-256
checksum before submission, redacts credential-like raw-evidence fields, and performs explicit
bounded HTTP submission. Network submission never happens during profile execution or bundle
creation.

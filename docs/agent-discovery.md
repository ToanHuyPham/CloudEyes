# Agent Discovery v1

Agent Discovery is the first completed module of the Agent MVP. It runs locally and does not
contact cloud metadata endpoints.

## Data flow

```text
Local OS APIs and bounded commands
→ normalized discovery models
→ privacy-safe JSON
→ discovery schema validation
```

## Privacy boundary

The module deliberately excludes usernames, raw hostnames, IP addresses, MAC addresses,
serial numbers, machine IDs, environment values, and credentials. Provider inference uses only
known environment variable names and non-unique manufacturer strings.

## Commands

```powershell
py -m cloudeyes_agent inspect
py -m cloudeyes_agent inspect --compact
py -m cloudeyes_agent inspect --output data/discovery.json
```

After editable installation, the equivalent command is:

```powershell
cloudeyes inspect --output data/discovery.json
```

## Supported systems

- Windows: platform APIs, `GlobalMemoryStatusEx`, and bounded PowerShell CIM queries.
- Linux: `/proc`, DMI files, and optional `systemd-detect-virt`.
- macOS: platform APIs and bounded `sysctl` queries.

Missing optional values are represented as `null`; discovery does not invent them.

# Agent Discovery

Agent Discovery collects a privacy-safe snapshot of the local execution environment.

## Collected

- operating system, kernel, architecture, Python version, and timezone;
- logical and physical CPU capacity where available;
- total memory and CPU model where available;
- virtual machine or container evidence;
- offline provider inference from environment variable names and manufacturer strings;
- network capability flags and interface count.

## Not collected

- username or home directory;
- hostname value;
- IP or MAC addresses;
- serial numbers or machine IDs;
- cloud metadata endpoint responses;
- secrets or environment variable values.

## Run

```powershell
py -m cloudeyes_agent inspect
py -m cloudeyes_agent inspect --output data/discovery.json
```

The result follows `schemas/discovery/result.schema.json` version `1.0.0`.

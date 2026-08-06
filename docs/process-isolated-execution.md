# Process-isolated execution

CloudEyes executes measurement profiles in a fresh spawned process by default. The
same start method is used on Windows and Linux, exposing serialization and import
problems consistently.

## Deadlines

Each profile inherits its reliability budget as the default hard deadline:

| Profile | Default deadline |
| --- | ---: |
| General | 120 seconds |
| Networking | 180 seconds |
| Compute | 600 seconds |
| Storage | 900 seconds |

Override the deadline explicitly:

```console
python -m cloudeyes_agent run compute --timeout-seconds 300
```

A timeout returns exit code `124`. CloudEyes first requests cooperative cancellation
and waits for profile cleanup. It then uses terminate and hard kill only when the
process remains alive. Dependency installation is performed before isolation so
prompts and privilege changes remain visible.

An interactive interruption returns exit code `130`.

`--no-isolation` is intended only for debugging. It disables hard timeout
enforcement and runs the benchmark in the CLI process.

# Execution isolation and cancellation

CloudEyes executes each complete measurement profile in a spawned child process by
default. This provides a real wall-clock deadline and prevents a stuck benchmark
from blocking the CLI indefinitely.

When a deadline expires or the parent process is interrupted, shutdown happens in
three stages:

1. The parent sets a process-safe cancellation token.
2. Profile code observes the token at safe checkpoints, closes files and sockets,
   removes temporary directories, and exits during the grace period.
3. If the child does not exit, the parent uses terminate and then kill as a final
   fallback.

General, Storage, Networking, and Compute workloads all accept the shared token.
Compute worker processes inherit the same cancellation state, so CPU loops can stop
without waiting for the complete repetition. Raw evidence remains atomic: a final
JSON file is replaced only after a complete write.

The CLI defaults to isolation. Use `--no-isolation` only for debugging. Set a
profile-specific deadline with `--timeout-seconds`; otherwise CloudEyes uses the
shared reliability budget for that profile. Timeout returns exit code `124` and an
interactive cancellation returns `130`.

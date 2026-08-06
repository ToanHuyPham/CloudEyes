# Execution isolation

CloudEyes can execute a complete measurement profile in a spawned child process.
This provides a real wall-clock deadline and prevents a stuck benchmark from
blocking the CLI indefinitely.

The parent process first asks the child to exit by terminating it, waits for the
configured grace period, and then uses a hard kill when the platform exposes it.
Profile code remains responsible for atomic raw-evidence writes and temporary-file
cleanup during normal completion.

The CLI defaults to isolation. Use `--no-isolation` only for debugging. Set a
profile-specific deadline with `--timeout-seconds`; otherwise CloudEyes uses the
shared reliability budget for that profile.

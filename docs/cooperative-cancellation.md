# Cooperative Cancellation v1

CloudEyes combines cooperative cleanup with process-isolated hard deadlines.
Forced termination is retained as a safety net, but it is no longer the first
shutdown action.

## Contract

A profile receives a process-safe `CancellationToken`. Long-running loops call
`checkpoint()` only at boundaries where normal Python cleanup can safely run.
When cancellation is pending, the checkpoint raises `CancellationRequested`.
Profile measurement wrappers deliberately propagate that exception instead of
turning it into an invalid benchmark sample.

Safe checkpoints cover:

- General CPU, memory, and temporary-file loops.
- Storage warm-up, sequential I/O, random I/O, fsync loops, and repetitions.
- Networking DNS/TCP repetitions, HTTP transfers, upload probes, and ICMP stages.
- Compute warm-up, scalar kernels, hash/compression loops, process-pool waits, and
  worker kernels.

## Deadline behavior

For an isolated run, the parent waits until the configured deadline. On expiry it:

1. requests cancellation;
2. waits for the cooperative grace period;
3. calls `terminate()` if the worker remains alive;
4. calls `kill()` when termination still does not complete.

The CLI still returns `124` whenever the deadline was exceeded, even when cleanup
completed cooperatively. This prevents a late result from being mistaken for a
successful in-budget measurement.

## Cleanup guarantees

- Storage benchmark files live in `TemporaryDirectory` scopes and are removed when
  cancellation unwinds the workload.
- HTTP connections and sockets are closed in `finally` blocks.
- Compute process workers observe the same cancellation event.
- Raw evidence uses temporary files plus atomic replacement, so incomplete JSON is
  not published.
- The final sample output is written only by the parent after a successful child
  result.

A blocking operating-system call may not observe a checkpoint immediately. Network
socket timeouts, subprocess timeouts, and the final terminate/kill fallback bound
that case.

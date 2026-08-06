# Runtime Dependency Bootstrap v1

CloudEyes benchmarks use Python's standard library. Additional native tools are
used to improve hardware, network, and virtualization evidence when available.

By default, CloudEyes runs without changing the host:

```bash
python -m cloudeyes_agent run general --quick
```

To detect and install missing recommended operating-system packages before running
the benchmark:

```bash
python -m cloudeyes_agent run general --quick --install-deps
```

For unattended images or CI runners:

```bash
python -m cloudeyes_agent run general --quick --install-deps --yes
```

Supported package managers are `apt-get`, `dnf`, `yum`, `zypper`, `apk`, and
`pacman`. Non-root Linux users are elevated through `sudo`. CloudEyes never
changes `/usr/bin/python3` and never replaces the operating system's Python.

The automatically managed native commands are:

| Command | Purpose |
|---|---|
| `lscpu` | CPU topology evidence |
| `free` | memory evidence |
| `ip` | network interface evidence |
| `lspci` | hardware and virtualization evidence |

Windows General Profile requires no extra native package; the check therefore
continues without changing the system.

## Profile-specific tools

Networking Profile v1 requests the optional `ping` command only when ICMP
sampling is enabled. With `--install-deps`, CloudEyes maps it to the native
package for the detected Linux family (`iputils-ping` on Debian/Ubuntu and
`iputils` on RHEL, SLES, Alpine, and Arch families).

```bash
python -m cloudeyes_agent run networking \
  --quick \
  --install-deps \
  --yes
```

Use `--no-ping` when ICMP is intentionally unavailable; CloudEyes then does not
request the package and records that ICMP coverage was disabled.

# CloudEyes installation

CloudEyes requires Python 3.11 or newer. Use the repository bootstrap scripts so
system Python is not replaced.

## Linux and Unix-like systems

```bash
chmod +x scripts/install.sh
./scripts/install.sh
source .venv/bin/activate
python -m pytest
python -m cloudeyes_agent inspect
```

Supported package managers:

- APT: Ubuntu and Debian
- DNF/YUM: RHEL, CentOS Stream, Rocky Linux, AlmaLinux, Fedora
- Zypper: SUSE Linux Enterprise Server and openSUSE
- APK: Alpine Linux
- Pacman: Arch Linux and derivatives

When the installed system Python is older than 3.11, the script installs a
user-scoped managed Python through a pinned uv installer. It does not replace
`/usr/bin/python3`.

Useful options:

```bash
./scripts/install.sh --dry-run
./scripts/install.sh --runtime-only
./scripts/install.sh --python 3.12.4
./scripts/install.sh --venv /opt/cloudeyes/venv
```

SLES 12.5 may require enabled SDK/development repositories for compiler and
`*-devel` packages. The script reports the failing package command without
changing the system Python.

## Windows 10 and 11

Run PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m cloudeyes_agent inspect
```

The Windows installer uses an existing Python 3.11+ installation or installs
Python 3.11 with WinGet when available.

## Manual verification

```bash
python --version
python -m ruff check agent core tests
python -m pytest
python -m cloudeyes_agent run general --quick --output data/general-sample.json
```

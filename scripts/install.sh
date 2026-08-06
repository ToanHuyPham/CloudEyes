#!/usr/bin/env bash
set -Eeuo pipefail

PYTHON_VERSION="${CLOUDEYES_PYTHON_VERSION:-3.11.9}"
VENV_DIR="${CLOUDEYES_VENV_DIR:-.venv}"
UV_VERSION="${CLOUDEYES_UV_VERSION:-0.11.13}"
DRY_RUN=0
WITH_DEV=1

log() { printf '[CloudEyes] %s\n' "$*"; }
fail() { printf '[CloudEyes] ERROR: %s\n' "$*" >&2; exit 1; }
run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then printf '+ %q ' "$@"; printf '\n'; else "$@"; fi
}
usage() {
  cat <<USAGE
Usage: scripts/install.sh [--dry-run] [--runtime-only] [--python VERSION] [--venv PATH]

Supported package managers: apt, dnf, yum, zypper, apk, pacman.
The script installs OS build tools, a managed Python when required, creates a
virtual environment, and installs CloudEyes.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --runtime-only) WITH_DEV=0 ;;
    --python) shift; PYTHON_VERSION="${1:?missing Python version}" ;;
    --venv) shift; VENV_DIR="${1:?missing venv path}" ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
  shift
done

[[ -f pyproject.toml ]] || fail "Run this script from the CloudEyes repository root."

SUDO=()
if [[ "$(id -u)" -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || fail "sudo is required to install OS packages."
  SUDO=(sudo)
fi

install_os_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    run "${SUDO[@]}" apt-get update
    run "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y \
      ca-certificates curl git build-essential pkg-config libssl-dev zlib1g-dev \
      libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev tk-dev
  elif command -v dnf >/dev/null 2>&1; then
    run "${SUDO[@]}" dnf install -y \
      ca-certificates curl git gcc gcc-c++ make patch pkgconf-pkg-config \
      openssl-devel zlib-devel bzip2-devel readline-devel sqlite-devel \
      libffi-devel xz-devel tk-devel
  elif command -v yum >/dev/null 2>&1; then
    run "${SUDO[@]}" yum install -y \
      ca-certificates curl git gcc gcc-c++ make patch pkgconfig openssl-devel \
      zlib-devel bzip2-devel readline-devel sqlite-devel libffi-devel xz-devel
  elif command -v zypper >/dev/null 2>&1; then
    run "${SUDO[@]}" zypper --non-interactive refresh
    run "${SUDO[@]}" zypper --non-interactive install \
      ca-certificates curl git gcc gcc-c++ make patch pkg-config \
      libopenssl-devel zlib-devel libbz2-devel readline-devel sqlite3-devel \
      libffi-devel xz-devel tk-devel
  elif command -v apk >/dev/null 2>&1; then
    run "${SUDO[@]}" apk add --no-cache \
      ca-certificates curl git build-base pkgconf openssl-dev zlib-dev \
      bzip2-dev readline-dev sqlite-dev libffi-dev xz-dev tk-dev
  elif command -v pacman >/dev/null 2>&1; then
    run "${SUDO[@]}" pacman -Sy --needed --noconfirm \
      ca-certificates curl git base-devel openssl zlib bzip2 readline sqlite \
      libffi xz tk
  else
    fail "Unsupported package manager. Install Python >=3.11, git, curl, and compiler tools manually."
  fi
}

python_ok() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
    >/dev/null 2>&1
}

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && python_ok "$candidate"; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

install_uv() {
  local uv_bin="$HOME/.local/bin/uv"
  if command -v uv >/dev/null 2>&1; then command -v uv; return 0; fi
  if [[ -x "$uv_bin" ]]; then printf '%s\n' "$uv_bin"; return 0; fi

  local tmp
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' RETURN
  log "Downloading pinned uv installer ${UV_VERSION}"
  run curl --proto '=https' --tlsv1.2 -fsSL \
    "https://releases.astral.sh/github/uv/releases/download/${UV_VERSION}/uv-installer.sh" \
    -o "$tmp"
  run env UV_NO_MODIFY_PATH=1 sh "$tmp"
  [[ -x "$uv_bin" ]] || fail "uv installation failed."
  printf '%s\n' "$uv_bin"
}

install_os_packages

PYTHON_BIN="$(find_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  UV_BIN="$(install_uv)"
  log "Installing managed Python ${PYTHON_VERSION}"
  run "$UV_BIN" python install "$PYTHON_VERSION"
  PYTHON_BIN="$($UV_BIN python find "$PYTHON_VERSION")"
fi

log "Using Python: $PYTHON_BIN"
run "$PYTHON_BIN" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python"
run "$VENV_PYTHON" -m pip install --upgrade pip
if [[ "$WITH_DEV" -eq 1 ]]; then
  run "$VENV_PYTHON" -m pip install -e '.[dev]'
else
  run "$VENV_PYTHON" -m pip install -e .
fi

log "Installation complete."
log "Activate with: source $VENV_DIR/bin/activate"
log "Verify with: $VENV_PYTHON -m pytest"

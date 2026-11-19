#!/bin/sh
set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this host-check script as a normal user; the build helper invokes sudo."
fi

if [ ! -r /etc/os-release ]; then
    echo "Cannot identify build host."
    exit 1
fi

. /etc/os-release
printf 'Build host: %s %s\n' "${PRETTY_NAME:-unknown}" "${VERSION_CODENAME:-}"

if [ "${ID:-}" != "debian" ] || [ "${VERSION_CODENAME:-}" != "trixie" ]; then
    echo "WARNING: The recommended build host is Debian 13 Trixie amd64."
fi

ARCH="$(dpkg --print-architecture)"
if [ "$ARCH" != "amd64" ]; then
    echo "ERROR: This initial configuration targets amd64; detected $ARCH."
    exit 1
fi

FREE_KB="$(df -Pk . | awk 'NR==2 {print $4}')"
if [ "${FREE_KB:-0}" -lt 30000000 ]; then
    echo "WARNING: Less than approximately 30 GB free in the build directory filesystem."
fi

echo "Host check complete."

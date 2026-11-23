#!/usr/bin/env bash
set -euo pipefail

echo "== ORVANTA WSL2 build environment =="
if ! grep -qi microsoft /proc/version; then
  echo "This helper is intended for Debian running under WSL2."
  echo "It may still work on native Debian, but review the environment first."
fi

sudo apt-get update
sudo apt-get install -y \
  live-build debootstrap xorriso squashfs-tools \
  grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
  git ca-certificates curl

echo
echo "Checking project architecture..."
dpkg --print-architecture
sed -n '1,8p' /etc/os-release

echo
echo "Starting ORVANTA ISO build..."
chmod +x auto/* scripts/*
./scripts/build.sh

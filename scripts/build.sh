#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

./scripts/check-host.sh

if ! command -v lb >/dev/null 2>&1; then
    echo "live-build is missing. Install it with:"
    echo "sudo apt install live-build debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin mtools dosfstools"
    exit 1
fi

chmod +x auto/config auto/build auto/clean
sudo lb config
sudo lb build
echo
echo "Build finished. Inspect the generated ISO and build.log."

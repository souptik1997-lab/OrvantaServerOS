#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
sudo lb clean --purge
rm -rf config/packages.chroot
rm -f orvanta-control-center_*.deb orvanta-control-center_*.buildinfo orvanta-control-center_*.changes

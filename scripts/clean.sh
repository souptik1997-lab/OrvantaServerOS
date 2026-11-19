#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
sudo lb clean --purge

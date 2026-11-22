#!/bin/sh
# Boot smoke test of an ORVANTA ISO in QEMU, in UEFI and BIOS mode.
# Presses Enter at the boot menu and saves screenshots (PNG) at ~12 s, ~60 s
# and ~3 min. This shows whether the image reaches the desktop; it is not a
# hardware, Secure Boot or performance test.
#
# Usage (root, on Debian 13 with qemu-system-x86, ovmf, python3-pyside6.qtgui):
#   ./scripts/qemu-smoke-test.sh orvanta-0.1-amd64.hybrid.iso [output-dir]
set -eu
ISO="$(realpath "$1")"
OUT="$(realpath -m "${2:-qemu-smoke}")"
mkdir -p "$OUT"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

ACCEL="-accel tcg"
[ -w /dev/kvm ] && ACCEL="-accel kvm -cpu host"
echo "ISO: $ISO"; echo "acceleration: $ACCEL"

to_png() {
    QT_QPA_PLATFORM=offscreen python3 -c 'import sys
from PySide6.QtGui import QImage
im = QImage(sys.argv[1]); im.save(sys.argv[2]); print(sys.argv[2], im.width(), "x", im.height())' "$1" "$2"
}

run() { # $1 = name, remaining args = firmware options
    name=$1; shift
    # shellcheck disable=SC2086 # $ACCEL holds several options
    ( sleep 12; echo "screendump $work/$name-1.ppm"; echo "sendkey ret"
      sleep 45; echo "screendump $work/$name-2.ppm"
      sleep 135; echo "screendump $work/$name-3.ppm"; sleep 2; echo quit ) | \
    timeout 300 qemu-system-x86_64 $ACCEL -m 4096 -smp 4 -machine q35 "$@" \
        -cdrom "$ISO" -boot d -vga virtio -display none -monitor stdio \
        -nic user,model=virtio-net-pci > "$work/$name-qemu.log" 2>&1
    echo "$name: qemu exit $?"
    for i in 1 2 3; do to_png "$work/$name-$i.ppm" "$OUT/$name-$i.png"; done
}

cp /usr/share/OVMF/OVMF_VARS_4M.fd "$work/vars.fd"
run uefi -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
         -drive if=pflash,format=raw,file="$work/vars.fd"
run bios
echo "Screenshots in $OUT"

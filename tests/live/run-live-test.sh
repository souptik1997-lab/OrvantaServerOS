#!/bin/bash
# ORVANTA in-session robustness test (network, storage and access controls,
# plus control-panel screenshots). Run as root on Debian 13 with
# qemu-system-x86 ovmf socat curl dosfstools parted xorriso squashfs-tools
# python3-pyside6.qtgui (and debhelper when OVERLAY_TREE=1).
#
#   sudo tests/live/run-live-test.sh orvanta-0.1-amd64.hybrid.iso [output-dir]
#
# The ISO is not modified: a copy gets one extra live layer
# (/live/zzz-orvanta-selftest.squashfs, test-only) with an autostart script
# that runs tests/live/guest/orvanta-selftest as the live user, writes
# results to a scratch disk and powers off. The host probes forwarded ports
# during the guest's firewall phases, pulls the virtual network cable when
# asked and takes the screenshots (QEMU screendump). No key is pressed.
#
# OVERLAY_TREE=1 additionally layers this checkout's config/includes.chroot,
# hook output and a freshly built Control Center onto an older ISO, to test
# changes before a full 'lb build'.
set -u
ISO_IN="$(realpath "$1")"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$REPO/tests/live"
OUT="$(realpath -m "${2:-live-test-results}")"
W="$(mktemp -d)"
ISO=$W/test.iso
# shellcheck disable=SC2317 # called through the EXIT trap
cleanup() {
    for m in "$W/hookchroot" "$W/sq" "$W/iso" "$W/res" "$W/hd"; do
        mountpoint -q "$m" && umount "$m"
    done
    [ -n "${LO:-}" ] && losetup -d "$LO" 2>/dev/null
    rm -rf "$W"
}
trap cleanup EXIT
rm -rf "$OUT"; mkdir -p "$W"/{layer,testlayer,hookroot,hookwk,hookchroot,sq,iso,res,hd} "$OUT/screenshots"

echo "== test ISO"
maps=()
if [ "${OVERLAY_TREE:-0}" = 1 ]; then
    sed 's|@VERSION@|0.1|g' "$REPO/config/bootloaders/grub-pc/splash.svg" > "$W/splash.svg"
    rsvg-convert --format png --height 600 --width 800 "$W/splash.svg" -o "$W/splash.png"
    cp -a "$REPO/config/includes.chroot/." "$W/hookroot/"
    (cd "$W" && cp -a "$REPO/orvanta-control-center" cc && cd cc && dpkg-buildpackage --no-sign -b >/dev/null 2>&1) \
        || { echo "Control Center build failed"; exit 1; }
    cp "$W"/orvanta-control-center_*_all.deb "$W/hookroot/cc.deb"
    cp "$REPO/config/hooks/normal/0100-orvanta-live-hardening.hook.chroot" "$W/hookroot/hook1.sh"
    cp "$REPO/config/hooks/normal/0200-orvanta-branding.hook.chroot" "$W/hookroot/hook2.sh"
    mount -o loop,ro "$ISO_IN" "$W/iso"
    mount -o loop,ro "$W/iso/live/filesystem.squashfs" "$W/sq"
    mount -t overlay overlay -o "lowerdir=$W/sq,upperdir=$W/hookroot,workdir=$W/hookwk" "$W/hookchroot"
    chroot "$W/hookchroot" dpkg -i /cc.deb >/dev/null
    cp "$REPO/config/includes.chroot/usr/share/icons/hicolor/scalable/apps/orvanta.svg" \
       "$W/hookchroot/usr/share/icons/hicolor/scalable/apps/orvanta.svg"
    if ! chroot "$W/hookchroot" sh -e /hook1.sh || ! chroot "$W/hookchroot" sh -e /hook2.sh; then
        echo "hook failed"; exit 1
    fi
    rm -f "$W/hookchroot/cc.deb" "$W/hookchroot/hook1.sh" "$W/hookchroot/hook2.sh"
    umount "$W/hookchroot" "$W/sq" "$W/iso"
    find "$W/hookroot" -type c -delete
    mksquashfs "$W/hookroot" "$W/zz-orvanta-tree.squashfs" -noappend -quiet -all-root
    maps+=(-map "$W/splash.png" /boot/grub/splash.png -map "$W/zz-orvanta-tree.squashfs" /live/zz-orvanta-tree.squashfs)
fi
mkdir -p "$W/testlayer/usr/local/bin" "$W/testlayer/etc/xdg/autostart"
install -m 0755 "$HERE/guest/orvanta-selftest" "$W/testlayer/usr/local/bin/"
install -m 0644 "$HERE/guest/zz-orvanta-selftest.desktop" "$W/testlayer/etc/xdg/autostart/"
install -m 0644 "$HERE/guest/kscreenlockerrc" "$HERE/guest/powerdevilrc" "$W/testlayer/etc/xdg/"
mksquashfs "$W/testlayer" "$W/zzz-orvanta-selftest.squashfs" -noappend -quiet -all-root
xorriso -indev "$ISO_IN" -outdev "$ISO" -boot_image any replay "${maps[@]}" \
    -map "$W/zzz-orvanta-selftest.squashfs" /live/zzz-orvanta-selftest.squashfs >/dev/null 2>&1

echo "== disks"
truncate -s 1G "$W/results.img"; mkfs.vfat -n ORVRESULT "$W/results.img" >/dev/null
truncate -s 2G "$W/scratch.img"
truncate -s 1G "$W/hostdata.img"
parted -s "$W/hostdata.img" mklabel gpt mkpart data ext4 1MiB 80% mkpart swap linux-swap 80% 100%
LO=$(losetup -fP --show "$W/hostdata.img")
mkfs.ext4 -q -L HOSTDATA "${LO}p1"; mkswap -L HOSTSWAP "${LO}p2" >/dev/null
mount "${LO}p1" "$W/hd"; echo "user data on an internal disk" > "$W/hd/keep-me.txt"
chmod 644 "$W/hd/keep-me.txt"; umount "$W/hd"; losetup -d "$LO"; LO=""

echo "== boot (UEFI, KVM if available, no key pressed)"
ACCEL=(-accel tcg); [ -w /dev/kvm ] && ACCEL=(-accel kvm -cpu host)
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$W/vars.fd"
SER=$W/serial.log; MON=$W/qmon.sock; : > "$SER"
qemu-system-x86_64 "${ACCEL[@]}" -m 6144 -smp 4 -machine q35 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive if=pflash,format=raw,file="$W/vars.fd" \
  -cdrom "$ISO" -boot d -vga virtio -display none \
  -drive file="$W/results.img",if=none,format=raw,id=res -device virtio-blk-pci,drive=res,serial=RESULTS \
  -drive file="$W/scratch.img",if=none,format=raw,id=scr -device virtio-blk-pci,drive=scr,serial=SCRATCH \
  -drive file="$W/hostdata.img",if=none,format=raw,id=hd -device virtio-blk-pci,drive=hd,serial=HOSTDATA \
  -netdev user,id=n0,hostfwd=tcp:127.0.0.1:18080-:8080,hostfwd=tcp:127.0.0.1:19090-:9090,hostfwd=tcp:127.0.0.1:14445-:445 \
  -device virtio-net-pci,netdev=n0,id=nic0 \
  -serial file:"$SER" -monitor unix:"$MON",server,nowait > "$W/qemu.log" 2>&1 &
QPID=$!
mon() { echo "$1" | socat - UNIX-CONNECT:"$MON" >/dev/null 2>&1; }

phase=boot; seen=""; start=$(date +%s)
probes=$OUT/host-probes.txt; : > "$probes"
while kill -0 $QPID 2>/dev/null; do
    if [ $(( $(date +%s) - start )) -gt 2400 ]; then echo "TIMEOUT"; mon quit; break; fi
    for mk in $(grep -o 'ORVTEST [A-Z0-9-]*\( [a-z]*\)\?' "$SER" | tr ' ' '_'); do
        case " $seen " in *" $mk "*) continue ;; esac
        seen="$seen $mk"; echo "$(date +%T) guest: $mk" | tee -a "$probes"
        case "$mk" in
            ORVTEST_FW-ON-1|ORVTEST_FW-OFF|ORVTEST_FW-ON-2) phase=${mk#ORVTEST_} ;;
            ORVTEST_LINK-TEST) phase="link"
                ( sleep 8; mon "set_link nic0 off"; echo "$(date +%T) host: link off" >> "$probes"
                  sleep 20; mon "set_link nic0 on"; echo "$(date +%T) host: link on" >> "$probes" ) & ;;
            ORVTEST_SHOT_*) mon "screendump $W/${mk#ORVTEST_SHOT_}.ppm" ;;
            ORVTEST_DONE) phase="done" ;;
        esac
    done
    case "$phase" in FW-ON-1|FW-OFF|FW-ON-2)
        for p in 18080 19090 14445; do
            if [ -n "$(curl -s -m 3 "http://127.0.0.1:$p/" 2>/dev/null | head -c 200)" ]; then r=REACHED; else r=blocked; fi
            echo "$(date +%T) $phase port $p: $r" >> "$probes"
        done ;;
    esac
    sleep 3
done
wait $QPID 2>/dev/null
echo "QEMU exited after $(( $(date +%s) - start )) s"

for f in "$W"/*.ppm; do
    [ -e "$f" ] || continue
    QT_QPA_PLATFORM=offscreen python3 -c 'import sys
from PySide6.QtGui import QImage
QImage(sys.argv[1]).save(sys.argv[2])' "$f" "$OUT/screenshots/$(basename "${f%.ppm}").png"
done
mount -o loop,ro "$W/results.img" "$W/res" && cp -r "$W/res/." "$OUT/" && umount "$W/res"
cp "$SER" "$OUT/serial.log"

fail=0
{
    echo "Host probes (port 18080 has a live listener in the guest; 19090/14445 have none):"
    for ph in FW-ON-1 FW-OFF FW-ON-2; do
        for p in 18080 19090 14445; do
            n=$(grep -c "$ph port $p:" "$probes"); r=$(grep -c "$ph port $p: REACHED" "$probes")
            printf '%-8s port %s: %s reached / %s probes\n' "$ph" "$p" "$r" "$n"
        done
    done
} | tee "$OUT/host-probe-summary.txt"
# firewall on: nothing reachable; firewall off (control): the listener must be reachable
grep -qE '^FW-ON-[12] .*: [1-9][0-9]* reached' "$OUT/host-probe-summary.txt" && { echo "FAIL: port reachable with firewall on"; fail=1; }
grep -qE '^FW-OFF   port 18080: [1-9]' "$OUT/host-probe-summary.txt" || { echo "FAIL: control probe never reached the listener (test invalid)"; fail=1; }
[ -f "$OUT/selftest.log" ] || { echo "FAIL: no guest results"; exit 1; }
tail -1 "$OUT/selftest.log"
grep -q '^FAIL' "$OUT/selftest.log" && fail=1
grep '^FAIL' "$OUT/selftest.log"
echo "results: $OUT"
exit $fail

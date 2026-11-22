#!/bin/sh
# Build the ORVANTA live ISO. Run as a normal user on Debian 13 amd64; uses sudo
# only for the live-build stages that need root.
set -eu
cd "$(dirname "$0")/.."

./scripts/check-host.sh

missing=""
for tool in lb debootstrap xorriso mksquashfs dpkg-buildpackage dh; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
if [ -n "$missing" ]; then
    echo "Missing build tools:$missing"
    echo "Install them with:"
    echo "sudo apt install live-build debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin mtools dosfstools build-essential debhelper"
    exit 1
fi

# Fix the timestamp used inside the image to the last commit, so rebuilding the
# same commit gives the same file dates (bit-for-bit reproducibility is not claimed).
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
    SOURCE_DATE_EPOCH="$(git log -1 --format=%ct 2>/dev/null || date +%s)"
fi
export SOURCE_DATE_EPOCH

# Build the ORVANTA Control Center package and hand it to live-build as a local
# package (everything in config/packages.chroot/ is installed into the image).
echo "== Building orvanta-control-center .deb"
rm -f orvanta-control-center_*.deb orvanta-control-center_*.buildinfo orvanta-control-center_*.changes
(cd orvanta-control-center && dpkg-buildpackage -b --no-sign)
mkdir -p config/packages.chroot
rm -f config/packages.chroot/orvanta-control-center_*.deb
cp orvanta-control-center_*_all.deb config/packages.chroot/

echo "== Building ISO (SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH)"
sudo lb clean
sudo lb config
sudo env SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" lb build

# live-build names the image <LB_IMAGE_NAME>-<arch>.hybrid.iso (see auto/config).
image_name="$(sed -n 's/^LB_IMAGE_NAME="\(.*\)"$/\1/p' config/common)"
iso="${image_name:?LB_IMAGE_NAME not found in config/common}-amd64.hybrid.iso"
if [ ! -s "$iso" ]; then
    echo "ERROR: build finished but $iso was not produced. See build.log."
    exit 1
fi
sha256sum "$iso" > "$iso.sha256"
echo
echo "Build finished: $iso"
cat "$iso.sha256"

#!/bin/sh
# Static validation that needs no root and no ISO build. Run locally or in CI.
set -eu
cd "$(dirname "$0")/.."

SHELL_SCRIPTS="auto/build auto/clean auto/config scripts/build.sh scripts/check-host.sh \
scripts/check-packages.sh scripts/clean.sh scripts/validate.sh windows/bootstrap-and-build.sh \
config/hooks/normal/0100-orvanta-live-hardening.hook.chroot"

echo "== Executable bits"
for f in $SHELL_SCRIPTS orvanta-control-center/debian/rules orvanta-control-center/src/orvanta_control_center.py; do
    [ -x "$f" ] || { echo "ERROR: $f is not executable"; exit 1; }
done

echo "== Shell syntax"
for f in $SHELL_SCRIPTS; do
    case "$(head -n1 "$f")" in
        *bash*) bash -n "$f" ;;
        *) sh -n "$f" ;;
    esac
done

echo "== ShellCheck"
# shellcheck disable=SC2086
shellcheck $SHELL_SCRIPTS

echo "== Python syntax"
python3 -m py_compile orvanta-control-center/src/orvanta_control_center.py tests/test_control_center.py

echo "== Python unit tests"
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v

echo "== Desktop entry"
desktop-file-validate orvanta-control-center/data/orvanta-control-center.desktop

echo "== nftables ruleset syntax"
# "nft -c" needs CAP_NET_ADMIN (it queries the kernel). CI grants it to the
# container and sets ORVANTA_REQUIRE_NFT=1 so the check cannot be skipped there.
if command -v nft >/dev/null 2>&1 && nft list tables >/dev/null 2>&1; then
    nft -c -f config/includes.chroot/etc/nftables.conf
    echo "ruleset OK"
elif [ "${ORVANTA_REQUIRE_NFT:-0}" = 1 ]; then
    echo "ERROR: nft check required but nft is missing or lacks CAP_NET_ADMIN"
    exit 1
else
    echo "skipped (needs nft and CAP_NET_ADMIN, e.g. run as root)"
fi

echo "== live-build configuration"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -a auto config "$tmp/"
(cd "$tmp" && lb config >/dev/null)
for f in binary bootstrap chroot common; do
    [ -s "$tmp/config/$f" ] || { echo "ERROR: lb config did not generate config/$f"; exit 1; }
done
grep -q 'LB_DISTRIBUTION="trixie"' "$tmp/config/bootstrap"
grep -q 'LB_ARCHIVE_AREAS="main contrib non-free-firmware"' "$tmp/config/bootstrap"
echo "lb config generated a trixie amd64 configuration"

echo "All static checks passed."

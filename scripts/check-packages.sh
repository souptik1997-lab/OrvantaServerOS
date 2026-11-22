#!/bin/sh
# Verify that every package in config/package-lists/*.list.chroot resolves and
# is installable together on a clean Debian 13 Trixie amd64 system, using the
# same archive areas as auto/config. Uses an isolated APT state directory, so the
# host's own APT configuration and installed packages do not affect the result.
# Signature verification stays enabled (debian-archive-keyring).
set -eu
cd "$(dirname "$0")/.."

MIRROR="${ORVANTA_MIRROR:-http://deb.debian.org/debian}"
SECURITY_MIRROR="${ORVANTA_SECURITY_MIRROR:-http://security.debian.org/debian-security}"
KEYRING=/usr/share/keyrings/debian-archive-keyring.gpg
AREAS="main contrib non-free-firmware"

[ -r "$KEYRING" ] || { echo "ERROR: $KEYRING missing (install debian-archive-keyring)."; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/lists/partial" "$work/cache/archives/partial" "$work/etc/preferences.d" "$work/etc/apt.conf.d"
: > "$work/status"
chmod 0755 "$work"
if [ "$(id -u)" -eq 0 ] && id _apt >/dev/null 2>&1; then
    chown -R _apt "$work/lists/partial" "$work/cache/archives/partial"
fi
cat > "$work/etc/sources.list" <<SOURCES
deb [signed-by=$KEYRING] $MIRROR trixie $AREAS
deb [signed-by=$KEYRING] $MIRROR trixie-updates $AREAS
deb [signed-by=$KEYRING] $SECURITY_MIRROR trixie-security $AREAS
SOURCES

apt_isolated() {
    apt-get \
        -o Dir::Etc="$work/etc" \
        -o Dir::Etc::SourceList="$work/etc/sources.list" \
        -o Dir::Etc::SourceParts="$work/etc/sources.list.d" \
        -o Dir::Etc::Preferences="$work/etc/preferences" \
        -o Dir::Etc::PreferencesParts="$work/etc/preferences.d" \
        -o Dir::Etc::Parts="$work/etc/apt.conf.d" \
        -o Dir::State::Lists="$work/lists" \
        -o Dir::State::status="$work/status" \
        -o Dir::Cache="$work/cache" \
        -o APT::Architecture=amd64 \
        -o APT::Architectures::=amd64 \
        -o APT::Install-Recommends=true \
        -o Debug::NoLocking=true \
        "$@"
}

apt_isolated -qq update

packages="$(cat config/package-lists/*.list.chroot | sed 's/#.*//' | tr -s ' \t' '\n' | sed '/^$/d' | sort -u)"
count="$(printf '%s\n' "$packages" | wc -l)"
echo "Checking $count packages from config/package-lists/ against Debian 13 trixie amd64 ($AREAS)..."

missing=""
for pkg in $packages; do
    if ! apt_isolated -s -qq install "$pkg" >/dev/null 2>&1; then
        missing="$missing $pkg"
    fi
done
if [ -n "$missing" ]; then
    echo "ERROR: not installable individually:$missing"
    exit 1
fi

# shellcheck disable=SC2086 # word splitting of the package list is intended
plan="$(apt_isolated -s install $packages)"
total="$(printf '%s\n' "$plan" | grep -c '^Inst ' || true)"
echo "All $count packages are installable together ($total packages in the full dependency closure, recommends included)."

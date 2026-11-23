#!/bin/sh
# Static validation that needs no root and no ISO build. Run locally or in CI.
set -eu
cd "$(dirname "$0")/.."

SHELL_SCRIPTS="auto/build auto/clean auto/config scripts/build.sh scripts/check-host.sh \
scripts/check-packages.sh scripts/clean.sh scripts/qemu-smoke-test.sh scripts/validate.sh \
windows/bootstrap-and-build.sh \
config/hooks/normal/0100-orvanta-live-hardening.hook.chroot \
config/hooks/normal/0200-orvanta-branding.hook.chroot \
tests/live/run-live-test.sh tests/live/guest/orvanta-selftest"

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
python3 -m py_compile orvanta-control-center/src/orvanta_control_center.py tests/test_control_center.py \
    scripts/render-artwork.py

echo "== Python unit tests"
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v

echo "== Desktop entries"
desktop-file-validate orvanta-control-center/data/orvanta-control-center.desktop
desktop-file-validate config/includes.chroot/usr/share/plasma/plasma-welcome/intro-customization.desktop

echo "== Branding images"
# ORVANTA_REQUIRE_BRANDING=1 (CI) makes the rsvg/grub checks mandatory.
need_tool() {
    if command -v "$1" >/dev/null 2>&1; then return 0; fi
    if [ "${ORVANTA_REQUIRE_BRANDING:-0}" = 1 ]; then
        echo "ERROR: $1 is required"; exit 1
    fi
    echo "skipped: $1 not installed"; return 1
}
tmp_brand="$(mktemp -d)"
if need_tool rsvg-convert; then
    for svg in config/bootloaders/grub-pc/splash.svg \
               config/includes.chroot/usr/share/icons/hicolor/scalable/apps/orvanta.svg; do
        # Same conversion live-build runs for the GRUB background.
        rsvg-convert --format png --width 800 --height 600 "$svg" -o "$tmp_brand/out.png"
        [ -s "$tmp_brand/out.png" ] || { echo "ERROR: $svg did not render"; exit 1; }
        echo "$svg renders"
    done
fi

echo "== Plasma global theme"
# Cross-checks the ORVANTA look-and-feel package, colour scheme, wallpaper
# and the /etc/xdg/kdeglobals entry that selects them.
python3 - <<'PY'
import base64, configparser, json, pathlib, re, struct, sys
root = pathlib.Path("config/includes.chroot")
lnf = root / "usr/share/plasma/look-and-feel/org.orvanta.desktop"
errors = []

def jpeg_size(data):
    """(width, height) from a baseline/progressive JPEG's SOF marker."""
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None
        marker, seglen = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + seglen
    return None

# Rendered artwork (scripts/render-artwork.py): wallpaper JPEGs named WxH, and
# the GRUB background embedded in splash.svg at live-build's 800x600.
for img in (root / "usr/share/wallpapers/Orvanta/contents/images").iterdir():
    m = re.fullmatch(r"(\d+)x(\d+)\.jpg", img.name)
    if not m or jpeg_size(img.read_bytes()) != (int(m.group(1)), int(m.group(2))):
        errors.append(f"{img}: not a JPEG matching its WxH name")
splash = pathlib.Path("config/bootloaders/grub-pc/splash.svg").read_text()
emb = re.search(r'href="data:image/jpeg;base64,([A-Za-z0-9+/=]+)"', splash)
if not emb or jpeg_size(base64.b64decode(emb.group(1))) != (800, 600):
    errors.append("splash.svg: embedded 800x600 JPEG background missing or invalid")
meta = json.loads((lnf / "metadata.json").read_text())
if meta.get("KPackageStructure") != "Plasma/LookAndFeel" or meta["KPlugin"]["Id"] != lnf.name:
    errors.append("look-and-feel metadata.json: wrong KPackageStructure or Id")
defaults = (lnf / "contents/defaults").read_text()
scheme = re.search(r"^\[kdeglobals\]\[General\]\nColorScheme=(\S+)$", defaults, re.M)
wall = re.search(r"^\[Wallpaper\]\nImage=(\S+)$", defaults, re.M)
if not scheme or not wall:
    errors.append("defaults: ColorScheme or Wallpaper Image missing")
else:
    colors = root / f"usr/share/color-schemes/{scheme.group(1)}.colors"
    cp = configparser.ConfigParser(interpolation=None, strict=True)
    cp.optionxform = str
    cp.read_string(colors.read_text())
    if cp.get("General", "ColorScheme", fallback="") != scheme.group(1):
        errors.append(f"{colors}: [General] ColorScheme does not match its file name")
    keys = ["BackgroundAlternate", "BackgroundNormal", "DecorationFocus", "DecorationHover",
            "ForegroundActive", "ForegroundInactive", "ForegroundLink", "ForegroundNegative",
            "ForegroundNeutral", "ForegroundNormal", "ForegroundPositive", "ForegroundVisited"]
    for group in ["Button", "Complementary", "Header", "Header][Inactive", "Selection",
                  "Tooltip", "View", "Window"]:
        sec = f"Colors:{group}"
        for k in keys:
            v = cp.get(sec, k, fallback=None)
            if v is None or not re.fullmatch(r"\d{1,3},\d{1,3},\d{1,3}", v) \
                    or max(map(int, v.split(","))) > 255:
                errors.append(f"{colors}: [{sec}] {k}={v!r}")
    wdir = root / f"usr/share/wallpapers/{wall.group(1)}"
    wmeta = json.loads((wdir / "metadata.json").read_text())
    if wmeta["KPlugin"]["Id"] != wall.group(1) or not list((wdir / "contents/images").glob("*.jpg")):
        errors.append(f"{wdir}: Id mismatch or no images")
if not (lnf / "contents/layouts/org.kde.plasma.desktop-layout.js").is_file():
    errors.append("layout script missing")
kg = (root / "etc/xdg/kdeglobals").read_text()
if "LookAndFeelPackage=org.orvanta.desktop" not in kg.splitlines():
    errors.append("/etc/xdg/kdeglobals does not select org.orvanta.desktop")
if errors:
    print("\n".join("ERROR: " + e for e in errors)); sys.exit(1)
print("org.orvanta.desktop: metadata, defaults, colour scheme, wallpaper and kdeglobals consistent")
PY

echo "== Boot splash, login screen and Plasma splash"
python3 - <<'PY'
import configparser, pathlib, re, struct, sys
root = pathlib.Path("config/includes.chroot")
errors = []

def png_size(path):
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])

# Plymouth theme: the .plymouth file must point at this theme's script and
# images, and the script may only load images that exist.
pt = root / "usr/share/plymouth/themes/orvanta"
cp = configparser.ConfigParser(interpolation=None); cp.optionxform = str
cp.read(pt / "orvanta.plymouth")
if cp.get("Plymouth Theme", "ModuleName", fallback="") != "script":
    errors.append("orvanta.plymouth: ModuleName must be script")
if cp.get("script", "ImageDir", fallback="") != "/usr/share/plymouth/themes/orvanta" or \
   cp.get("script", "ScriptFile", fallback="") != "/usr/share/plymouth/themes/orvanta/orvanta.script":
    errors.append("orvanta.plymouth: ImageDir/ScriptFile do not point at the theme")
script = (pt / "orvanta.script").read_text()
for name in re.findall(r'Image\("([^"]+)"\)', script):
    if not png_size(pt / name):
        errors.append(f"orvanta.script loads missing or non-PNG image {name}")
for o, c in ("()", "{}"):
    if script.count(o) != script.count(c):
        errors.append(f"orvanta.script: unbalanced {o}{c}")
for fn in ("SetRefreshFunction", "SetDisplayPasswordFunction", "SetDisplayNormalFunction"):
    if f"Plymouth.{fn}(" not in script:
        errors.append(f"orvanta.script: no Plymouth.{fn}")
if png_size(pt / "background.png") != (1920, 1080):
    errors.append("plymouth background.png must be 1920x1080")

# SDDM: theme selected and every path in theme.conf.user exists in the image
conf = (root / "etc/sddm.conf.d/10-orvanta.conf").read_text()
if "Current=breeze" not in conf.splitlines():
    errors.append("10-orvanta.conf: Current=breeze missing")
for line in (root / "usr/share/sddm/themes/breeze/theme.conf.user").read_text().splitlines():
    if line.startswith(("background=", "logo=")):
        target = root / line.split("=", 1)[1].lstrip("/")
        if not target.is_file():
            errors.append(f"theme.conf.user: {line} does not exist in includes")

# Plasma splash: selected in the global theme; every file:// it loads exists
lnf = root / "usr/share/plasma/look-and-feel/org.orvanta.desktop/contents"
if not re.search(r"^\[KSplash\]\nTheme=org\.orvanta\.desktop$", (lnf / "defaults").read_text(), re.M):
    errors.append("defaults: [KSplash] Theme is not org.orvanta.desktop")
for url in re.findall(r'"file:///([^"]+)"', (lnf / "splash/Splash.qml").read_text()):
    if not (root / url).is_file():
        errors.append(f"Splash.qml loads missing file /{url}")

# Kernel command line asks for the splash
if "quiet splash" not in pathlib.Path("auto/config").read_text():
    errors.append("auto/config: --bootappend-live lacks 'quiet splash'")
dropin = root / "etc/systemd/system/sddm.service.d/orvanta-after-plymouth.conf"
if "After=plymouth-quit.service" not in dropin.read_text().splitlines():
    errors.append(f"{dropin}: After=plymouth-quit.service missing")
if (root / "etc/systemd/system/plymouth-quit.service.d").exists():
    errors.append("plymouth-quit override present: --retain-splash leaves the SDDM greeter black")
if not png_size(root / "usr/share/sddm/faces/orvanta.face.icon"):
    errors.append("usr/share/sddm/faces/orvanta.face.icon missing or not a PNG")

if errors:
    print("\n".join("ERROR: " + e for e in errors)); sys.exit(1)
print("Plymouth theme, SDDM configuration, Plasma splash and kernel command line consistent")
PY

echo "== Kernel hardening (sysctl.d)"
sysctl_conf=config/includes.chroot/etc/sysctl.d/60-orvanta-hardening.conf
grep -vE '^[[:space:]]*(#|$)' "$sysctl_conf" | while IFS= read -r line; do
    case "$line" in
        *" = "*) ;;
        *) echo "ERROR: $sysctl_conf: not 'key = value': $line"; exit 1 ;;
    esac
    key=${line%% = *}
    [ -e "/proc/sys/$(echo "$key" | tr . /)" ] || { echo "ERROR: unknown sysctl $key"; exit 1; }
done
echo "$sysctl_conf: all keys exist"

echo "== Boot menu (GRUB)"
grub_dir=config/bootloaders/grub-pc
grep -qx 'set timeout=5' "$grub_dir/config.cfg" || { echo "ERROR: GRUB timeout is not 5 s"; exit 1; }
for marker in @KERNEL_LIVE@ @INITRD_LIVE@ @APPEND_LIVE@ @LB_BOOTAPPEND_LIVE_FAILSAFE@; do
    grep -q "$marker" "$grub_dir/grub.cfg" || { echo "ERROR: $marker missing from grub.cfg"; exit 1; }
done
if need_tool grub-script-check; then
    # Fill the live-build placeholders with sample values, then parse.
    for cfg in "$grub_dir/config.cfg" "$grub_dir/grub.cfg"; do
        # shellcheck disable=SC2016 # ${iso_path} is GRUB syntax, kept literal
        sed -e 's|@KERNEL_LIVE@|/live/vmlinuz|g; s|@INITRD_LIVE@|/live/initrd.img|g' \
            -e 's|@APPEND_LIVE@|boot=live findiso=${iso_path}|g' \
            -e 's|@LB_BOOTAPPEND_LIVE_FAILSAFE@|boot=live nosplash|g' \
            -e 's|@APPEND_VERIFY_CHECKSUMS@|boot=live verify-checksums|g' \
            -e 's|@ENABLE_[A-Z_]*@|false|g' "$cfg" > "$tmp_brand/check.cfg"
        grub-script-check "$tmp_brand/check.cfg"
        echo "$cfg parses"
    done
fi
rm -rf "$tmp_brand"

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

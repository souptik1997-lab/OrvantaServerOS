# ORVANTA OS — Foundation 0.1

An initial, reproducible Debian 13 (Trixie) live-image configuration for the ORVANTA project.

**This is a development prototype, not a production-ready installer or a security-certified operating system.**
It creates a bootable live ISO so the desktop, hardware support and initial package selection can be tested before building the installed-system installer and ORVANTA Control Center.

## Design decisions

- Base: Debian 13 Trixie
- Architecture: amd64
- Desktop: KDE Plasma
- Init: systemd
- Packages: APT / DEB
- Security baseline: AppArmor, nftables, unattended-upgrades
- Server management: Cockpit
- Windows interoperability: Samba
- No virtual-machine dependency

## Build host

Use a clean Debian 13 amd64 machine or a Debian 13 build environment. Building on the target Debian release reduces cross-release build surprises.

Suggested minimum build-host resources:
- 4 CPU cores
- 8 GB RAM (16 GB preferred)
- 30 GB free disk space
- Working internet connection

Do not run the build on the target server that contains important data. The build requires root privileges for live-build stages.

## Build

```bash
sudo apt update
sudo apt install -y git live-build debootstrap xorriso squashfs-tools \
  grub-pc-bin grub-efi-amd64-bin mtools dosfstools build-essential debhelper

git clone https://github.com/souptik1997-lab/OrvantaServerOS
cd OrvantaServerOS
./scripts/build.sh
```

`scripts/build.sh` builds the Control Center `.deb`, places it in
`config/packages.chroot/` so it is installed into the image, and runs
`lb clean`, `lb config` and `lb build` with `SOURCE_DATE_EPOCH` set to the last
commit time. Outputs in the project root:

- `orvanta-0.1-amd64.hybrid.iso` and `orvanta-0.1-amd64.hybrid.iso.sha256`
- `orvanta-0.1-amd64.packages` — every package and version in the image
- `build.log` — the full live-build log

Check the checksum before writing the ISO to USB. `./scripts/clean.sh` removes
all build state. On Windows, see `windows/README-WINDOWS.md` (WSL2).

## Live-session security defaults

- nftables enabled with `/etc/nftables.conf`: inbound traffic dropped except
  replies, loopback, essential ICMP/ICMPv6 and DHCPv6.
- Cockpit, Samba, Docker and containerd are installed but **masked** in the
  live session. Enable them explicitly (`systemctl unmask …`) and open the
  firewall only on a trusted network.
- The live user (`orvanta`) has live-config's well-known password and
  passwordless sudo, as in every Debian live image. Never leave the live
  session connected to an untrusted network.
- Automatic updates are off in the live session.

## Automated validation

Run locally on Debian 13 (no root needed except for the `nft -c` check):

```bash
./scripts/validate.sh        # shell, Python, unit tests, desktop entry, firewall, lb config
./scripts/check-packages.sh  # every listed package installable on trixie amd64
```

GitHub Actions (`.github/workflows/validate.yml`) runs both scripts in a
`debian:trixie` container, then builds the Control Center package, runs
lintian and installs and launches it. A full ISO build is available as a
workflow (`build-iso.yml`), which also runs on pull requests that change build
inputs and on pushes to `main`. Verified results are recorded in
`docs/BUILD-STATUS.md` and `docs/REVIEW-2026-11-22.md`; nothing is claimed
there until it has actually run.

## Test safely

1. Optional quick check: `sudo ./scripts/qemu-smoke-test.sh orvanta-0.1-amd64.hybrid.iso`
   boots the ISO in QEMU (UEFI and BIOS) and saves screenshots. QEMU is only a
   test tool here; ORVANTA itself needs no VM.
2. Test in a disposable test machine or spare PC.
3. Boot from USB using UEFI. The ORVANTA boot menu starts the live system
   automatically after 5 seconds; press any arrow key to stop the countdown.
4. Check KDE, networking, audio, display scaling, Intel Wi-Fi/Ethernet, USB and storage.
5. Confirm no remote administration services listen: `sudo ss -tlnp` and `sudo nft list ruleset`.
6. Do not use this prototype as a production server or store important data on it.

## Current limitations

- This is a live ISO prototype; it is not yet a polished installed-system installer.
- ORVANTA branding covers the boot menu, the Plasma Welcome Center, the logo,
  `/etc/os-release` (`NAME="ORVANTA OS"`, `ID_LIKE=debian`; Debian's own
  `/usr/lib/os-release` is unchanged) and the desktop: the default Plasma
  global theme is "ORVANTA" (`org.orvanta.desktop`: ORVANTA Dark colours, the
  ORVANTA wallpaper, Breeze widgets and icons). The login screen (SDDM), the
  Plasma startup splash and the kernel boot splash are still KDE/Debian
  defaults. The Control Center is a read-only prototype.
- Automatic updates are not activated in the live session. The installed-system update policy will be implemented and tested separately.
- No custom kernel, custom init system or custom package manager is being introduced.
- No update rollback guarantee exists yet.
- Secure Boot support depends on the boot chain and signing configuration; verify it on real hardware before claiming support.
- Debian packages are consumed directly from Debian repositories. ORVANTA-specific packages will later live in a separately signed ORVANTA repository.

## Project structure

- `auto/config` — canonical live-build configuration
- `auto/build` — build entry point with logging
- `config/package-lists/` — package selection
- `config/bootloaders/grub-pc/` — ORVANTA GRUB menu, theme, splash and 5 s timeout (BIOS and UEFI)
- `config/includes.chroot/` — files included in the live filesystem (firewall, logo, Welcome Center text, Plasma global theme, colour scheme, wallpaper)
- `config/hooks/normal/` — ORVANTA chroot hooks (live-session hardening, branding)
- `scripts/` — host checks, build, clean, validation, package checks and QEMU smoke test
- `orvanta-control-center/` — read-only Control Center and its Debian packaging
- `tests/` — unit tests
- `docs/` — architecture and release notes

## Next milestones

1. Produce and boot the first ISO.
2. Test on the intended Intel N150 hardware and at least one other x86-64 PC.
3. Add ORVANTA KDE theme, branding and desktop defaults.
4. Design the installed-system partitioning and installer.
5. Implement ORVANTA Control Center with a narrow privileged API.
6. Implement signed ORVANTA repositories and staged update policy.
7. Add recovery, backup and rollback workflows.

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
sudo apt install -y live-build debootstrap xorriso squashfs-tools \
  grub-pc-bin grub-efi-amd64-bin mtools dosfstools

chmod +x auto/*.sh scripts/*.sh
./scripts/build.sh
```

The ISO should appear in the project root. Check the build log and verify the ISO checksum before writing it to USB.

## Test safely

1. First test in a disposable test machine or spare PC (no VM is required).
2. Boot from USB using UEFI.
3. Check KDE, networking, audio, display scaling, Intel Wi-Fi/Ethernet, USB and storage.
4. Confirm the live session does not expose remote administration services unexpectedly.
5. Do not use this prototype as a production server or store important data on it.

## Current limitations

- This is a live ISO prototype; it is not yet a polished installed-system installer.
- ORVANTA branding is minimal and the custom Control Center has not been implemented.
- Automatic updates are not activated in the live session. The installed-system update policy will be implemented and tested separately.
- No custom kernel, custom init system or custom package manager is being introduced.
- No update rollback guarantee exists yet.
- Secure Boot support depends on the boot chain and signing configuration; verify it on real hardware before claiming support.
- Debian packages are consumed directly from Debian repositories. ORVANTA-specific packages will later live in a separately signed ORVANTA repository.

## Project structure

- `auto/config` — canonical live-build configuration
- `auto/build` — build entry point with logging
- `config/package-lists/` — package selection
- `config/includes.chroot/` — files included in the live filesystem
- `scripts/` — host checks, build and clean helpers
- `docs/` — architecture and release notes

## Next milestones

1. Produce and boot the first ISO.
2. Test on the intended Intel N150 hardware and at least one other x86-64 PC.
3. Add ORVANTA KDE theme, branding and desktop defaults.
4. Design the installed-system partitioning and installer.
5. Implement ORVANTA Control Center with a narrow privileged API.
6. Implement signed ORVANTA repositories and staged update policy.
7. Add recovery, backup and rollback workflows.

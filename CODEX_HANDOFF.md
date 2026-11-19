# Codex handoff — ORVANTA OS

## Mission

Continue development of ORVANTA, an independent Debian-derived Linux distribution.
The current baseline is Debian 13 Trixie amd64 with KDE Plasma, systemd, APT/DEB,
AppArmor, nftables and a staged automatic-update design.

This repository is an early development scaffold. Do not describe it as a finished,
secure or production-ready operating system.

## Product requirements

- Native Linux OS; no Windows VM or hypervisor requirement.
- Windows-familiar KDE Plasma desktop and graphical administration.
- Debian Stable as the upstream base.
- Use official Debian packages directly wherever practical.
- Maintain ORVANTA-specific packages in a separate signed repository.
- Security-first defaults and least privilege.
- Do not enable unattended broad upgrades without a tested deployment/recovery policy.
- No direct graphical root login and no unrestricted sudo for GUI applications.

## Current project contents

- `auto/` and `config/`: Debian live-build configuration for an initial live ISO.
- `scripts/`: host checks, build and clean helpers.
- `orvanta-control-center/`: PySide6 read-only dashboard prototype and Debian packaging metadata.
- `windows/`: WSL2 setup and build guidance.
- `docs/`: architecture and build status.

## First Codex task

1. Inspect the entire repository and identify build blockers, packaging errors and security concerns.
2. Verify the Debian 13 live-build configuration against the actual Debian live-build version and correct it.
3. Verify every package name in `config/package-lists/` exists in Debian 13 Trixie amd64 repositories. Remove or replace unavailable packages and document changes.
4. Validate the Control Center Debian packaging (`debian/control`, `debian/rules`, changelog, copyright and desktop entry). Ensure it builds cleanly using `dpkg-buildpackage`.
5. Add automated static checks and a CI workflow that can validate shell syntax, Python syntax and Debian package metadata without requiring privileged ISO build steps.
6. Preserve the read-only nature of the Control Center. Do not implement privileged system changes yet.
7. Update `README.md` and `docs/BUILD-STATUS.md` with exact verified results. Never claim an ISO was built unless the build actually completed.

## Required engineering rules

- Prefer small, reviewable commits.
- Keep Debian base packages sourced from signed official Debian repositories.
- Never disable APT signature verification.
- Do not embed credentials, tokens or default admin passwords.
- Do not add arbitrary shell execution to the GUI.
- Any future privileged backend must use narrowly scoped Polkit actions, input validation,
  fixed operations, audit logging and tests.
- Document any WSL2 limitation; use native Debian 13 for definitive live-build validation
  if WSL2 mount/chroot behaviour blocks the build.
- Do not claim Secure Boot support until the actual boot chain has been tested on hardware.

## Definition of done for this first task

- A review report lists confirmed issues and fixes.
- Python and shell syntax checks pass.
- Debian package metadata is valid.
- Control Center `.deb` builds successfully on Debian 13, or exact remaining blocker is documented.
- ISO build instructions are accurate and reproducible; ISO build status is reported honestly.

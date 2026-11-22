# Build status — 0.1

- [x] Select Debian 13 Trixie amd64 base
- [x] Select KDE Plasma desktop task
- [x] Define initial package list
- [x] Add live-build configuration
- [x] Add host/build/clean scripts
- [x] Verify every listed package is installable on Debian 13 amd64 (2026-11-22, `scripts/check-packages.sh`)
- [x] Live-session hardening: default-deny firewall, remote-admin services masked (2026-11-22)
- [ ] Complete a first ISO build (local WSL2 attempt stopped 2026-11-22, see below; GitHub Actions `build-iso.yml` pending)
- [ ] Boot-test on physical x86-64 hardware
- [ ] Validate UEFI and Secure Boot behaviour
- [x] Add a Debian 13 CI validation workflow
- [ ] Confirm the CI workflows pass on GitHub Actions (updated 2026-11-22; not yet run)
- [ ] Add ORVANTA desktop branding
- [ ] Design installed-system installer
- [ ] Implement Control Center and update agent

- [x] Create ORVANTA Control Center 0.1 read-only Qt prototype
- [x] Confirm `python3-pyside6.qtwidgets` is published for Debian 13 Trixie amd64
- [x] Build, lintian-check and install the Control Center .deb on Debian 13 (0.1.1, 2026-11-22, WSL2)
- [x] Include the Control Center in the ISO (`config/packages.chroot/`)
- [ ] Test on KDE Plasma physical hardware
- [ ] Implement Polkit-mediated privileged backend (separate security review)

## Verification record — 2026-11-22

Environment: Debian GNU/Linux 13 (trixie) amd64 under WSL2 on Windows 11,
live-build 1:20250505+deb13u1, debhelper 13.24.2, lintian 2.122.0+deb13u1,
shellcheck 0.10.0. Full issue list and per-check results:
`docs/REVIEW-2026-11-22.md`.

| Check | Result |
|-------|--------|
| `scripts/validate.sh` (exec bits, sh/bash syntax, shellcheck, py_compile, 6 unit tests, desktop-file-validate, `nft -c`, `lb config`) | Passed |
| `scripts/check-packages.sh` — 37 packages, trixie main/contrib/non-free-firmware | Passed: all installable together (2192-package closure) |
| `dpkg-buildpackage --no-sign` → `orvanta-control-center_0.1.1_all.deb` | Passed |
| `lintian --pedantic` | No tags |
| Install, offscreen launch (5 s), remove | Passed |
| `scripts/build.sh` ISO build (WSL2) | **Not completed.** Control Center `.deb` built, `lb config` and debootstrap completed, package installation started. Stopped manually after ~1.5 h at about 110 of ~2200 packages unpacked: the WSL2 disk image sits on a SATA hard disk with ~70 % I/O stall time. No error was reported up to that point. |

The ISO build moved to GitHub Actions (`build-iso.yml`). Its result will be
recorded here once a run has completed.

Not executed: GitHub Actions runs, hardware boot, UEFI/Secure Boot, the
installed-system path (no installer exists yet).

## Verification record — 2026-11-19

The live-build configuration was corrected to use the current `--binary-images`
option. The unsupported/unverified Secure Boot auto-selection was removed; this
does not add Secure Boot support. A Debian 13 GitHub Actions validation workflow
was added. That record did not claim the workflow, an ISO build or a hardware
boot test had completed. (The 2026-11-22 review found the workflow could not
have passed as written: scripts lacked exec bits and the firmware packages were
checked with only `main` enabled.)

# Build status — 0.1

- [x] Select Debian 13 Trixie amd64 base
- [x] Select KDE Plasma desktop task
- [x] Define initial package list
- [x] Add live-build configuration
- [x] Add host/build/clean scripts
- [x] Verify every listed package is installable on Debian 13 amd64 (2026-11-22, `scripts/check-packages.sh`)
- [x] Live-session hardening: default-deny firewall, remote-admin services masked (2026-11-22)
- [x] Complete a first ISO build (2026-11-22, GitHub Actions run 45052055224, commit 839116c; see below)
- [ ] Boot-test the ISO (not yet booted anywhere, VM or hardware)
- [ ] Boot-test on physical x86-64 hardware
- [ ] Validate UEFI and Secure Boot behaviour
- [x] Add a Debian 13 CI validation workflow
- [x] CI workflows pass on GitHub Actions (2026-11-22, PR #1, commit 839116c)
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

### GitHub Actions — PR #1 (commit 839116c)

| Workflow | Run | Result |
|----------|-----|--------|
| Validate ORVANTA source | [45052055222](https://github.com/souptik1997-lab/OrvantaServerOS/actions/runs/45052055222) | Passed: validate.sh (firewall check required), check-packages.sh, Control Center build, lintian, install + launch |
| Build ORVANTA ISO | [45052055224](https://github.com/souptik1997-lab/OrvantaServerOS/actions/runs/45052055224) | **Passed.** 17:54–18:10 UTC (~16 min, ~13 min of it live-build). Checksum verified by the workflow before upload. |

ISO produced by run 45052055224 (artifact `orvanta-0.1-amd64`, kept until 2026-11-29):

- File: `orvanta-0.1-amd64.hybrid.iso`, 2 996 387 840 bytes
- SHA-256: `1bc4ba9079702ddc8da35419efbd6c689e7e42554be0279aebb3f4c3934c2e73`
- Packages in image: 2267 (`orvanta-0.1-amd64.packages`)
- Kernel: `linux-image-6.12.117+deb13-amd64` 6.12.117-1
- `orvanta-control-center` 0.1.1 installed in the image

The image was built from the live Debian archive; a rebuild on another day
will pick up newer package versions and a different checksum.

Earlier ISO runs on PR #1, in order:

1. 45046185013 (33d4322): failed after `lb build`; log not readable without sign-in.
2. 45048965188 (5e075d5): reported success but produced **no ISO** — the build
   output was piped through `tee` without pipefail. Not a valid result.
3. 45050477378 (55f8311): failed; the new failure annotation showed
   `P: Build completed successfully` followed by `build.sh` not finding the
   ISO: live-build had written `orvanta-0.1-amd64-amd64.hybrid.iso`.
4. 45052055224 (839116c): image name fixed — passed (above).

Details in `docs/REVIEW-2026-11-22.md`, issues 15–17.

Not executed: booting the ISO (VM or hardware), UEFI/Secure Boot, the
installed-system path (no installer exists yet).

## Verification record — 2026-11-19

The live-build configuration was corrected to use the current `--binary-images`
option. The unsupported/unverified Secure Boot auto-selection was removed; this
does not add Secure Boot support. A Debian 13 GitHub Actions validation workflow
was added. That record did not claim the workflow, an ISO build or a hardware
boot test had completed. (The 2026-11-22 review found the workflow could not
have passed as written: scripts lacked exec bits and the firmware packages were
checked with only `main` enabled.)

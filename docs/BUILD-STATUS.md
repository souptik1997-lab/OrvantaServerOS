# Build status — 0.1

- [x] Select Debian 13 Trixie amd64 base
- [x] Select KDE Plasma desktop task
- [x] Define initial package list
- [x] Add live-build configuration
- [x] Add host/build/clean scripts
- [ ] Run first ISO build on Debian 13 build host
- [ ] Boot-test on physical x86-64 hardware
- [ ] Validate UEFI and Secure Boot behaviour
- [x] Add a Debian 13 CI package-availability simulation
- [ ] Add ORVANTA desktop branding
- [ ] Design installed-system installer
- [ ] Implement Control Center and update agent

- [x] Create ORVANTA Control Center 0.1 read-only Qt prototype
- [x] Confirm `python3-pyside6.qtwidgets` is published for Debian 13 Trixie amd64 (repository metadata, 2026-11-19)
- [ ] Build and install Control Center .deb on Debian 13 CI (workflow added; result pending)
- [ ] Test on KDE Plasma physical hardware
- [ ] Implement Polkit-mediated privileged backend (separate security review)

## Verification record — 2026-11-19

The live-build configuration was corrected to use the current `--binary-images`
option. The unsupported/unverified Secure Boot auto-selection was removed; this
does not add Secure Boot support. A Debian 13 GitHub Actions validation workflow
now checks shell syntax/style, Python syntax, desktop metadata, live-build
configuration, APT package availability, and builds/installs the Control Center
package. This record does **not** claim that the workflow, an ISO build, or a
hardware boot test has completed; results must be recorded after execution.

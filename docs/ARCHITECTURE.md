# ORVANTA Foundation Architecture

## Distribution model

ORVANTA is a Debian-derived distribution with its own release identity, installer experience, desktop defaults, management software and signed repository. Debian remains the upstream provider for the general-purpose kernel, libraries and applications.

## Repository separation

1. Debian Trixie repositories: upstream base packages and security maintenance.
2. ORVANTA repository (future): ORVANTA branding, control center, update policy, configuration defaults and integration packages.

Do not fork or rebuild Debian packages without a specific technical reason. Avoid replacing Debian package metadata or disabling APT signature verification.

## Update policy (design target; not yet implemented)

- Security updates: automatic after validation of repository signatures and package origin.
- Stable maintenance updates: staged deployment, initially to development and pilot devices.
- Major distribution upgrades: explicit operator approval.
- Kernel updates: install signed Debian kernel packages; schedule reboot and report pending restart.
- Update failures: preserve logs and provide a recovery procedure. Do not claim automatic rollback until it is implemented and tested.

## Security boundaries

- No direct graphical root login.
- Administrative actions require Polkit authorization.
- Keep SSH disabled unless explicitly enabled by the administrator.
- Firewall defaults deny unsolicited inbound connections, with explicit service rules.
- AppArmor enabled and enforcing where profiles are available and tested.
- Minimise enabled services.
- Never ship a shared default administrative password.
- Do not expose Cockpit or Docker API to untrusted networks.

## Data and filesystem

The initial prototype uses Debian's normal live filesystem. Installed-system partitioning is a separate milestone. ext4 is the conservative default candidate; Btrfs may be offered later after testing snapshot and recovery workflows.

## Support boundary

Debian's lifecycle does not automatically cover every third-party or ORVANTA package. ORVANTA must publish a package support matrix and security response process before a production release.

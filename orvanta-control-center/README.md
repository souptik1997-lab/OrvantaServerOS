
# ORVANTA Control Center 0.1.0

First native Qt for Python graphical shell for ORVANTA.

## Status

This is a **read-only UI prototype**. It displays local system information:
- Distribution name
- Hostname
- System load average
- Memory use
- Root filesystem use
- Uptime

Navigation entries for Storage, Network, Security, Updates, Applications, Users and Backup are placeholders. They do not change system state.

## Install dependencies on Debian 13

```bash
sudo apt update
sudo apt install python3 python3-pyside6.qtwidgets
```

If the PySide6 package name differs on your selected Debian mirror, search with:
`apt-cache search pyside6`

## Run from source

```bash
python3 src/orvanta_control_center.py
```

## Build a Debian package

Install packaging tools:

```bash
sudo apt install build-essential devscripts debhelper
```

From this directory:

```bash
dpkg-buildpackage -us -uc -b
```

The resulting `.deb` will be written to the parent directory.

## Security architecture before enabling administrative controls

Do not run this GUI as root. Do not grant it unrestricted sudo access. Future privileged actions must be implemented by a small, auditable backend with:
- Polkit authorization for each operation
- Strict input validation
- Fixed command/API allowlists (never arbitrary shell strings)
- Structured logging and clear user confirmation
- Safe failure handling and documented recovery
- Tests for authorization bypass and malformed input

The GUI should communicate with that backend over a narrow local interface. This prototype intentionally has no privileged backend.

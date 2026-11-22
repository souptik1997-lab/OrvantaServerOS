# Build ORVANTA from Windows using WSL2

## 1. Install WSL2 and Debian

Open **PowerShell as Administrator** and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows\Install-ORVANTA-WSL.ps1
```

Alternatively, run:

```powershell
wsl --install -d Debian
```

Restart if Windows requests it. Launch Debian from the Start menu and create your Linux username and password.
Check that the distribution is Debian 13 (trixie): `grep VERSION_CODENAME /etc/os-release`.

## 2. Put the project inside the Linux filesystem

Build inside the Debian home directory, not under `/mnt/c` or `/mnt/e`. Windows
drives mounted in WSL do not keep Linux file permissions and ownership reliably,
and live-build needs real Linux permissions inside the image.

Inside Debian:

```bash
sudo apt-get update
sudo apt-get install -y git ca-certificates
git clone https://github.com/souptik1997-lab/OrvantaServerOS ~/OrvantaServerOS
cd ~/OrvantaServerOS
```

## 3. Install build dependencies and build

```bash
./windows/bootstrap-and-build.sh
```

The helper installs Debian live-build tools and runs `scripts/build.sh`, which
builds the Control Center package and then the ISO.

## 4. Locate the ISO

After a successful build the project root contains:

- `orvanta-0.1-amd64.hybrid.iso` — the live image
- `orvanta-0.1-amd64.hybrid.iso.sha256` — its SHA-256 checksum
- `orvanta-0.1-amd64.packages` — the list of packages in the image
- `build.log` — the full build log

To copy the ISO to Windows (for writing to USB with a tool such as Rufus):

```bash
cp orvanta-0.1-amd64.hybrid.iso* /mnt/c/Users/$USER/Downloads/
```

(Replace `$USER` with your Windows user name if it differs from the Linux one.)

## WSL2 caveats

- Use WSL2, not WSL1.
- Some live-build operations use mounts, chroots and loop devices. WSL2 support can vary by Windows/WSL version. If the build fails with mount, loop-device or privileged-operation errors, use a native Debian 13 build host or a dedicated Linux build machine.
- WSL2 is only the build environment. The resulting ISO is intended to boot on physical x86-64 hardware.
- Do not treat a successful ISO build as proof of Secure Boot compatibility or production security.

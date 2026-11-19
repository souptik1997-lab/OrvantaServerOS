
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

## 2. Put the project inside the Linux filesystem

For best performance, do not build from `/mnt/c/...`. Extract/copy the project into the Debian home directory.

From PowerShell, if the ZIP is in Downloads:

```powershell
wsl -d Debian
```

Then inside Debian:

```bash
mkdir -p ~/orvanta
cd ~/orvanta
```

Copy the ZIP from Windows Downloads (replace `YOUR_WINDOWS_USERNAME`):

```bash
cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/ORVANTA-Foundation-0.1.zip ~/
sudo apt-get update
sudo apt-get install -y unzip
unzip ~/ORVANTA-Foundation-0.1.zip -d ~/orvanta
cd ~/orvanta/ORVANTA-Foundation-0.1
```

## 3. Install build dependencies and build

```bash
chmod +x windows/bootstrap-and-build.sh
./windows/bootstrap-and-build.sh
```

The build helper installs Debian live-build tools and invokes the project build.

## 4. Locate the ISO

After a successful build, locate the ISO:

```bash
find . -maxdepth 2 -type f -name '*.iso' -ls
```

Create a checksum:

```bash
sha256sum ./*.iso
```

## WSL2 caveats

- Use WSL2, not WSL1.
- Build inside the Linux filesystem (`~/orvanta`), not `/mnt/c`, for better filesystem performance.
- Some live-build operations use mounts, chroots and loop devices. WSL2 support can vary by Windows/WSL version. If the build fails with mount, loop-device or privileged-operation errors, use a native Debian 13 build host or a dedicated Linux build machine.
- WSL2 is only the build environment. The resulting ISO is intended to boot on physical x86-64 hardware.
- Do not treat a successful ISO build as proof of Secure Boot compatibility or production security.

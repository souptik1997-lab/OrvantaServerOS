# Run in PowerShell as Administrator.
# Installs WSL2 and the Debian distribution. A restart may be required.
$ErrorActionPreference = "Stop"

Write-Host "Enabling WSL2 and installing Debian..." -ForegroundColor Cyan
wsl --install -d Debian

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Restart Windows if requested."
Write-Host "2. Launch Debian from the Start menu."
Write-Host "3. Complete the first-run Linux username/password setup."
Write-Host "4. Copy/extract the ORVANTA project into your Debian home directory."
Write-Host "5. In Debian, run: bash windows/bootstrap-and-build.sh"

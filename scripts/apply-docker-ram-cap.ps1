#Requires -Version 5.1
<#
Apply WSL memory cap and restart Docker Desktop so Cursor + Docker coexist.
Run once after installing/updating .wslconfig. Close heavy apps first.
#>
$ErrorActionPreference = "Stop"
Write-Host "[cursor-stack] Applying .wslconfig (4 GB Docker/WSL cap)..."
if (-not (Test-Path "$env:USERPROFILE\.wslconfig")) {
  throw ".wslconfig missing at $env:USERPROFILE\.wslconfig"
}
Get-Content "$env:USERPROFILE\.wslconfig"

Write-Host "[cursor-stack] Shutting down WSL (this stops Docker)..."
wsl --shutdown
Start-Sleep -Seconds 5

$exe = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
Write-Host "[cursor-stack] Starting Docker Desktop with capped memory..."
Start-Process -FilePath $exe

$deadline = (Get-Date).AddMinutes(4)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 5
  try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "[cursor-stack] Docker ready under WSL memory cap."
      wsl -d docker-desktop -- free -m
      exit 0
    }
  } catch {}
}
throw "Docker did not become ready"
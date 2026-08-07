#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$ComposeFile = "docker-compose.cursor.yml"

function Write-Step([string]$msg) {
  Write-Host "[cursor-build] $msg" -ForegroundColor Cyan
}

Write-Step "Building API image (novaflow-api:latest)..."
docker compose -f $ComposeFile build api
if ($LASTEXITCODE -ne 0) { throw "API build failed" }

Write-Step "Building web image (host Next build + Dockerfile.web)..."
powershell -NoProfile -ExecutionPolicy Bypass -File "$Root\scripts\rebuild-web-safe.ps1"

Write-Host "[cursor-build] Done. Open http://localhost:3000" -ForegroundColor Green
Write-Host "  Login: admin / NovaFlowLocalDevAdmin1" -ForegroundColor Gray

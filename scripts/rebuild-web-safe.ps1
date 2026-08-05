#Requires -Version 5.1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
function Write-Step([string]$m) { Write-Host "[rebuild-web] $m" -ForegroundColor Cyan }
Write-Step "Stopping web container..."
cmd /c "docker stop novaflow-web >nul 2>&1"
Write-Step "Cleaning old Next build output..."
if (Test-Path ".next") { Remove-Item -Recurse -Force ".next" -ErrorAction SilentlyContinue }
if (-not (Test-Path "node_modules")) {
  Write-Step "npm ci..."
  npm ci
  if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
}
Write-Step "Building Next.js on host (webpack)..."
$env:NEXT_TELEMETRY_DISABLED = "1"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:3001"
$env:NEXT_PUBLIC_APP_NAME = "NovaFlow AI"
$env:NODE_OPTIONS = "--max-old-space-size=3072"
npm run build -- --webpack
if ($LASTEXITCODE -ne 0) { throw "next build failed" }
if (-not (Test-Path ".next\standalone\server.js")) { throw "Missing .next/standalone/server.js" }
Write-Step "Packaging runtime Docker image..."
docker build -f Dockerfile.web -t novaflow-web:local .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
Write-Step "Restarting Cursor-safe stack..."
powershell -NoProfile -ExecutionPolicy Bypass -File "$Root\scripts\cursor-stack-up.ps1"
Write-Host "[rebuild-web] Done. Hard-refresh http://localhost:3000" -ForegroundColor Green

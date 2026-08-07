#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$m) { Write-Host "[full-stack] $m" -ForegroundColor Cyan }

Write-Step "Building Next.js on host (avoids Docker OOM)..."
if (-not (Test-Path "node_modules")) {
  npm ci
  if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
}
$env:NEXT_TELEMETRY_DISABLED = "1"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:3001"
$env:NEXT_PUBLIC_APP_NAME = "NovaFlow AI"
$env:NODE_OPTIONS = "--max-old-space-size=3072"
npm run build -- --webpack
if ($LASTEXITCODE -ne 0) { throw "next build failed" }

Write-Step "Packaging web image..."
docker build -f Dockerfile.web -t novaflow-web:local .
if ($LASTEXITCODE -ne 0) { throw "docker build web failed" }

Write-Step "Starting full stack (API + Milvus + web)..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

Write-Host ""
Write-Host "OK — NovaFlow full stack is starting" -ForegroundColor Green
Write-Host "  Web:   http://localhost:3000"
Write-Host "  API:   http://localhost:3001/health"
Write-Host "  Login: admin / NovaFlowLocalDevAdmin1"

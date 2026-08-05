# Start NovaFlow API — own stack (MySQL + Redis + API on port 3001)
# Run from novaflow-ai root: .\deploy\start-backend.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"

function Test-NovaApi {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:3001/health" -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -ne 200) { return $false }
    $j = $r.Content | ConvertFrom-Json
    return $j.status_code -eq 200
  } catch {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:3001/api/v1/user/public_key" -UseBasicParsing -TimeoutSec 10
      return $r.StatusCode -eq 200
    } catch {
      return $false
    }
  }
}

if (Test-NovaApi) {
  Write-Host "NovaFlow API is already running at http://localhost:3001" -ForegroundColor Green
  exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker not found. Run API locally instead:" -ForegroundColor Yellow
  Write-Host "  cd backend && pip install -r requirements.txt && python -m uvicorn app.main:app --port 3001" -ForegroundColor Gray
  exit 1
}

Write-Host "Starting NovaFlow stack (MySQL + Redis + API)..." -ForegroundColor Cyan
Push-Location $PSScriptRoot
docker compose -f docker-compose.yml up -d --build
Pop-Location

Write-Host "Waiting for NovaFlow API (up to 120s)..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
  if (Test-NovaApi) {
    Write-Host ""
    Write-Host "NovaFlow API is online at http://localhost:3001" -ForegroundColor Green
    Write-Host "Default login: set NOVAFLOW_ADMIN_PASSWORD" -ForegroundColor Gray
    Write-Host "Frontend:  cd novaflow-ai && npm run dev" -ForegroundColor Gray
    exit 0
  }
  Start-Sleep -Seconds 5
}

Write-Host "API not ready yet. Check logs: docker logs novaflow-api --tail 40" -ForegroundColor Yellow
exit 1

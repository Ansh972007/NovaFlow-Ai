# Start NovaFlow API (local backend on port 3001)
# Run from the novaflow-ai project root: .\deploy\start-backend.ps1

$ErrorActionPreference = "Stop"

try {
  $ping = Invoke-WebRequest -Uri "http://localhost:3001/api/v1/user/public_key" -UseBasicParsing -TimeoutSec 5
  if ($ping.StatusCode -eq 200) {
    Write-Host "NovaFlow API is already running at http://localhost:3001" -ForegroundColor Green
    exit 0
  }
} catch {
  # not running — continue to start
}

$composePaths = @(
  "$PSScriptRoot\..\..\bisheng-main\docker",
  "$PSScriptRoot\..\..\docker",
  "$env:USERPROFILE\Downloads\bisheng-main\bisheng-main\docker"
)

$composeDir = $composePaths | Where-Object { Test-Path "$_\docker-compose.yml" } | Select-Object -First 1

if (-not $composeDir) {
  Write-Host "NovaFlow API: could not find docker-compose.yml." -ForegroundColor Red
  Write-Host "Set NEXT_PUBLIC_API_URL in .env.local to your running API."
  exit 1
}

Write-Host "Starting NovaFlow API from $composeDir ..." -ForegroundColor Cyan
Push-Location $composeDir
docker compose -f docker-compose.yml -p novaflow-api up -d
Pop-Location

Write-Host ""
Write-Host "NovaFlow API should be available at http://localhost:3001" -ForegroundColor Green
Write-Host "Then run: npm run dev" -ForegroundColor Green

# Start NovaFlow production stack (web + API + MySQL + Redis + Milvus)
# Run from novaflow-ai root: .\deploy\start-prod.ps1

$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
$EnvFile = Join-Path $DeployDir ".env.production"
$Example = Join-Path $DeployDir ".env.production.example"

if (-not (Test-Path $EnvFile)) {
  Write-Host "Creating deploy/.env.production from example — edit secrets before real production!" -ForegroundColor Yellow
  Copy-Item $Example $EnvFile
}

function Test-NovaWeb {
  try {
    $port = if ($env:WEB_PORT) { $env:WEB_PORT } else { "3000" }
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port" -UseBasicParsing -TimeoutSec 10
    return $r.StatusCode -ge 200 -and $r.StatusCode -lt 400
  } catch {
    return $false
  }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker is required for the production stack." -ForegroundColor Red
  exit 1
}

Write-Host "Building and starting NovaFlow production stack..." -ForegroundColor Cyan
Push-Location $DeployDir
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
Pop-Location

Write-Host "Waiting for web app (up to 180s)..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(180)
while ((Get-Date) -lt $deadline) {
  if (Test-NovaWeb) {
    Write-Host ""
    Write-Host "NovaFlow is online:" -ForegroundColor Green
    Write-Host "  Web:  http://localhost:3000" -ForegroundColor Gray
    Write-Host "  API:  http://localhost:3001/health" -ForegroundColor Gray
    Write-Host "  Login credentials are in deploy/.env.production" -ForegroundColor Gray
    exit 0
  }
  Start-Sleep -Seconds 5
}

Write-Host "Web not ready. Check: docker logs novaflow-web --tail 40" -ForegroundColor Yellow
exit 1

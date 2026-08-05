# Start NovaFlow full stack (web + API + MySQL + Redis + Milvus) - one command
# Run from novaflow-ai root: .\deploy\start.ps1
# Or: docker compose up -d --build

$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
$Root = Split-Path $DeployDir -Parent
$NovaContainers = @("novaflow-web", "novaflow-api", "novaflow-mysql", "novaflow-redis", "novaflow-milvus")

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

function Test-NovaWeb {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 10
    return $r.StatusCode -ge 200 -and $r.StatusCode -lt 400
  } catch {
    return $false
  }
}

function Remove-OrphanNovaContainers {
  foreach ($name in $NovaContainers) {
    $existing = docker ps -aq -f "name=^/${name}$" 2>$null
    if ($existing) {
      Write-Host "Removing orphan container: $name" -ForegroundColor Yellow
      docker rm -f $name 2>$null | Out-Null
    }
  }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker is required. Install Docker Desktop, then run:" -ForegroundColor Red
  Write-Host "  docker compose up -d --build" -ForegroundColor Gray
  exit 1
}

if ((Test-NovaApi) -and (Test-NovaWeb)) {
  Write-Host "NovaFlow is already running:" -ForegroundColor Green
  Write-Host "  Web:  http://localhost:3000" -ForegroundColor Gray
  Write-Host "  API:  http://localhost:3001" -ForegroundColor Gray
  Write-Host "  Login: set NOVAFLOW_ADMIN_PASSWORD" -ForegroundColor Gray
  exit 0
}

Write-Host "Preparing NovaFlow stack..." -ForegroundColor Cyan
Push-Location $Root
try {
  docker compose down --remove-orphans 2>$null | Out-Null
  Remove-OrphanNovaContainers

  Write-Host "Building and starting (web + API + MySQL + Redis + Milvus)..." -ForegroundColor Cyan
  Write-Host "First run may take several minutes. Milvus alone can need ~90s." -ForegroundColor Gray
  docker compose up -d --build --remove-orphans
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Compose failed - retrying after cleanup..." -ForegroundColor Yellow
    docker compose down --remove-orphans 2>$null | Out-Null
    Remove-OrphanNovaContainers
    docker compose up -d --build --remove-orphans
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
} finally {
  Pop-Location
}

Write-Host "Waiting for API and web (up to 240s)..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(240)
while ((Get-Date) -lt $deadline) {
  $apiOk = Test-NovaApi
  $webOk = Test-NovaWeb
  if ($apiOk -and $webOk) {
    Write-Host ""
    Write-Host "NovaFlow is online:" -ForegroundColor Green
    Write-Host "  Web:  http://127.0.0.1:3000  (use 127.0.0.1 on Windows; localhost may fail)" -ForegroundColor Gray
    Write-Host "  API:  http://127.0.0.1:3001" -ForegroundColor Gray
    Write-Host "  Login: set NOVAFLOW_ADMIN_PASSWORD" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Stop:  docker compose down" -ForegroundColor DarkGray
    Write-Host "Logs:  docker compose logs -f web api" -ForegroundColor DarkGray
    exit 0
  }
  Start-Sleep -Seconds 5
}

Write-Host "Stack not fully ready yet. Check status:" -ForegroundColor Yellow
Write-Host "  docker compose ps" -ForegroundColor Gray
Write-Host "  docker compose logs milvus --tail 20" -ForegroundColor Gray
Write-Host "  docker compose logs api --tail 20" -ForegroundColor Gray
Write-Host "  docker compose logs web --tail 20" -ForegroundColor Gray
exit 1

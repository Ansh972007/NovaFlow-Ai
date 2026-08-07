#Requires -Version 5.1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$ComposeFile = "docker-compose.cursor.yml"

function Write-Step([string]$msg) {
  Write-Host "[cursor-stack] $msg" -ForegroundColor Cyan
}

function Ensure-Docker {
  docker info 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { return }
  Write-Step "Starting Docker Desktop..."
  $exe = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
  if (-not (Test-Path $exe)) { throw "Docker Desktop not found at $exe" }
  Start-Process -FilePath $exe
  $deadline = (Get-Date).AddMinutes(4)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 4
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Step "Docker is ready"
      return
    }
  }
  throw "Docker Desktop did not become ready in time"
}

function Test-Image([string]$name) {
  $id = @(docker images -q $name 2>$null)
  return ($id.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($id[0]))
}

Write-Step "Ensuring Docker is running..."
Ensure-Docker

Write-Step "Stopping Milvus if running (saves RAM)..."
cmd /c "docker stop novaflow-milvus >nul 2>&1"
cmd /c "docker rm -f novaflow-milvus >nul 2>&1"

if (-not (Test-Image "novaflow-web:local")) {
  Write-Host "[cursor-stack] ERROR: Image novaflow-web:local is missing." -ForegroundColor Yellow
  Write-Host "Do NOT rebuild while Cursor is open on 16 GB RAM." -ForegroundColor Yellow
  Write-Host "Close Cursor, run: docker compose build web" -ForegroundColor Yellow
  throw "Missing novaflow-web:local"
}

$hasApi = (Test-Image "novaflow-api:latest") -or (Test-Image "novaflow-api")
if (-not $hasApi) {
  Write-Host "[cursor-stack] ERROR: Image novaflow-api is missing." -ForegroundColor Yellow
  Write-Host "Close Cursor if needed, then: docker compose build api" -ForegroundColor Yellow
  throw "Missing novaflow-api"
}

Write-Step "Starting Cursor-safe stack (no rebuild, no Milvus)..."
docker compose -f $ComposeFile up -d --pull never
if ($LASTEXITCODE -ne 0) { throw "compose up failed" }

Write-Step "Waiting for health..."
$okApi = $false
$okWeb = $false
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Seconds 3
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:3001/health" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { $okApi = $true }
  } catch {}
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { $okWeb = $true }
  } catch {}
  if ($okApi -and $okWeb) { break }
  Write-Host "  ... waiting api=$okApi web=$okWeb ($i)"
}

Write-Step "Container memory:"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

if (-not $okApi) { throw "API health check failed" }
if (-not $okWeb) {
  Write-Host "[cursor-stack] WARNING: Web not responding yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "OK - NovaFlow Cursor-safe stack is up" -ForegroundColor Green
Write-Host "  Web:   http://localhost:3000"
Write-Host "  API:   http://localhost:3001/health"
Write-Host "  Login: admin / NovaFlowLocalDevAdmin1"
Write-Host "  Mode:  no Milvus, memory-capped, no rebuild"
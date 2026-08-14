#Requires -Version 5.1
<#
.SYNOPSIS
  Start ngrok tunnel to API port 3001, write public URL to .env, then docker compose up.

.EXAMPLE
  .\scripts\start-with-ngrok.ps1
.EXAMPLE
  .\scripts\start-with-ngrok.ps1 -ComposeFile docker-compose.cursor.yml
#>
param(
  [string]$ComposeFile = "docker-compose.yml",
  [string]$Region = "in",
  [int]$ApiPort = 3001,
  [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$msg) {
  Write-Host "[ngrok+nova] $msg" -ForegroundColor Cyan
}

function Load-DotEnv([string]$path) {
  if (-not (Test-Path $path)) { return }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $name = $line.Substring(0, $idx).Trim()
    $val = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    if ($name) { Set-Item -Path "env:$name" -Value $val }
  }
}

function Get-NgrokHttpsUrl() {
  $resp = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
  $tunnel = @($resp.tunnels | Where-Object { $_.public_url -like "https:*" } | Select-Object -First 1)
  if ($tunnel) { return $tunnel.public_url.TrimEnd("/") }
  return $null
}

function Set-EnvPublicBase([string]$url) {
  $envFile = Join-Path $Root ".env"
  $lines = @()
  if (Test-Path $envFile) {
    $lines = @(Get-Content $envFile | Where-Object { $_ -notmatch '^\s*NOVAFLOW_PUBLIC_BASE_URL\s*=' })
  }
  $lines += "NOVAFLOW_PUBLIC_BASE_URL=$url"
  Set-Content -Path $envFile -Value $lines -Encoding UTF8
  $env:NOVAFLOW_PUBLIC_BASE_URL = $url
}

function Ensure-NgrokCmd() {
  $cmd = Get-Command ngrok -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "ngrok not found. Install from https://ngrok.com/download" }
  return $cmd.Source
}

Load-DotEnv (Join-Path $Root ".env")

$ngrokExe = Ensure-NgrokCmd
$token = $env:NGROK_AUTHTOKEN
if ($token) {
  & $ngrokExe config add-authtoken $token 2>$null | Out-Null
}

Write-Step "Checking ngrok tunnel on port $ApiPort..."
$publicUrl = Get-NgrokHttpsUrl

if (-not $publicUrl) {
  Write-Step "Starting ngrok (new window) — keep it open while testing Telegram..."
  Start-Process -FilePath $ngrokExe -ArgumentList @("http", "$ApiPort", "--region=$Region")
  for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 1
    $publicUrl = Get-NgrokHttpsUrl
    if ($publicUrl) { break }
  }
}

if (-not $publicUrl) {
  throw "Could not get ngrok HTTPS URL. Run manually: ngrok http $ApiPort --region=$Region"
}

Write-Step "Public API URL: $publicUrl"
Set-EnvPublicBase $publicUrl

Write-Step "Starting Docker ($ComposeFile)..."
$composeArgs = @("-f", $ComposeFile, "up", "-d")
if (-not $NoBuild) { $composeArgs += "--build" }
docker compose @composeArgs
if ($LASTEXITCODE -ne 0) { throw "docker compose failed" }

Write-Step "Waiting for API health..."
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Seconds 3
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/health" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { $ok = $true; break }
  } catch {}
}

Write-Host ""
Write-Host "NovaFlow + ngrok ready" -ForegroundColor Green
Write-Host "  Web (browser):     http://localhost:3000"
Write-Host "  API (local):       http://127.0.0.1:$ApiPort"
Write-Host "  API (public/ngrok): $publicUrl"
Write-Host "  Telegram webhook:  $publicUrl/api/v1/integrations/telegram/webhook/{workflow_id}"
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "  1. Credentials -> Messaging -> bot token + label"
Write-Host "  2. Workflow: Trigger (Telegram) -> logic -> Notify (to: {{chat_id}})"
Write-Host "  3. Publish workflow (webhook auto-registers with ngrok URL)"
Write-Host ""
if (-not $ok) {
  Write-Host "API health not confirmed yet — wait a minute and open http://127.0.0.1:$ApiPort/health" -ForegroundColor Yellow
}

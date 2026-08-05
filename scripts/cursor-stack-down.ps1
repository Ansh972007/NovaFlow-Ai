#Requires -Version 5.1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
Write-Host "[cursor-stack] Stopping NovaFlow Cursor-safe stack..."
docker compose -f docker-compose.cursor.yml down
docker stop novaflow-milvus 2>$null | Out-Null
Write-Host "[cursor-stack] Stopped."
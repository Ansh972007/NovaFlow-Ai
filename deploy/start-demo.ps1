# Start NovaFlow demo environment — production stack + seeded sample data
# Run from novaflow-ai root: .\deploy\start-demo.ps1

$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
$EnvFile = Join-Path $DeployDir ".env.production"
$Example = Join-Path $DeployDir ".env.production.example"

if (-not (Test-Path $EnvFile)) {
  Copy-Item $Example $EnvFile
}

$content = Get-Content $EnvFile -Raw
if ($content -notmatch "NOVAFLOW_DEMO_SEED=1") {
  $content = $content -replace "NOVAFLOW_DEMO_SEED=0", "NOVAFLOW_DEMO_SEED=1"
  if ($content -notmatch "NOVAFLOW_DEMO_SEED=") {
    $content += "`nNOVAFLOW_DEMO_SEED=1`n"
  }
  Set-Content -Path $EnvFile -Value $content -NoNewline
}

Write-Host "Starting NovaFlow DEMO stack (sample assistants + handbook)..." -ForegroundColor Cyan
& (Join-Path $DeployDir "start-prod.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Demo accounts:" -ForegroundColor Green
Write-Host "  Admin:  admin / (see NOVAFLOW_ADMIN_PASSWORD in deploy/.env.production)" -ForegroundColor Gray
Write-Host "  Viewer: demo / demo123" -ForegroundColor Gray
Write-Host ""
Write-Host "Try: Chat -> Support Assistant | Workflows -> Handbook Q&A pipeline" -ForegroundColor Gray

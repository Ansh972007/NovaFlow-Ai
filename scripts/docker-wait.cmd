@echo off
REM Wait for Docker Desktop daemon (run this BEFORE docker compose)
echo Checking Docker...
docker info >nul 2>&1
if %errorlevel%==0 (
  echo Docker is already running.
  exit /b 0
)

echo Docker is NOT running.
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
  echo Starting Docker Desktop...
  start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
) else (
  echo ERROR: Docker Desktop not installed.
  echo Install from https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)

echo Waiting for Docker engine (up to 3 minutes)...
set /a n=0
:waitloop
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if %errorlevel%==0 goto ready
set /a n+=1
if %n% geq 36 (
  echo.
  echo ERROR: Docker did not start in time.
  echo 1. Open Docker Desktop manually from Start menu
  echo 2. Wait until whale icon stops animating
  echo 3. Settings - Resources - Memory: set 3-4 GB if low RAM
  echo 4. Run this script again
  pause
  exit /b 1
)
echo   still waiting... (%n%)
goto waitloop

:ready
echo.
echo Docker is ready.
docker version --format "  Engine: {{.Server.Version}}"
exit /b 0

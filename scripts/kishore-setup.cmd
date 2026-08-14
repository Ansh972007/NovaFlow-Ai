@echo off
REM Low-RAM NovaFlow + seed credentials/workflows for kishorevekariya70@gmail.com
cd /d "%~dp0.."

call "%~dp0docker-wait.cmd"
if errorlevel 1 exit /b 1

echo === Docker stack (cursor / no Milvus) ===
docker compose -f docker-compose.cursor.yml up -d --build
if errorlevel 1 (
  echo ERROR: Start Docker Desktop first, then run this script again.
  pause
  exit /b 1
)

echo === Restart API (pick up .env Google OAuth) ===
docker compose -f docker-compose.cursor.yml up -d --build api
timeout /t 20 /nobreak >nul

echo === Seed credentials + workflows ===
docker compose -f docker-compose.cursor.yml exec -T api python scripts/seed_kishore_setup.py

echo.
echo === Done ===
echo Web:  http://localhost:3000
echo Login with kishorevekariya70@gmail.com
echo.
echo Gmail: open Credentials, click Oauth2, then Connect with Google once.
echo Telegram: message your bot after ngrok is running.
pause

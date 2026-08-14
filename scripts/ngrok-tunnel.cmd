@echo off
REM Start ngrok only (run BEFORE docker compose if you prefer two steps)
REM Tunnel: host port 3001 -> your Docker API
cd /d "%~dp0.."
echo Starting ngrok to http://localhost:3001 ...
echo Keep this window open. Copy the https URL into .env as NOVAFLOW_PUBLIC_BASE_URL=
echo.
ngrok http 3001 --region=in

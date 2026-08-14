@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

echo [1/4] ngrok authtoken...
ngrok config add-authtoken 38nkL12CeMSvxZzWasDuEUvpuXk_ZPdE9wuFseSNfysGsday

echo [2/4] Starting ngrok (new window) - keep it open...
start "ngrok" ngrok http 3001 --region=in

echo [3/4] Waiting for ngrok URL...
set NGROK_URL=
for /L %%i in (1,1,45) do (
  timeout /t 2 /nobreak >nul
  for /f "delims=" %%u in ('powershell -NoProfile -Command "(Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels | Where-Object { $_.public_url -like 'https:*' } | Select-Object -First 1 -ExpandProperty public_url"') do set NGROK_URL=%%u
  if not "!NGROK_URL!"=="" goto got_url
)
echo ERROR: ngrok URL not found. Check the ngrok window.
pause
exit /b 1

:got_url
echo Public URL: %NGROK_URL%

(echo NOVAFLOW_PUBLIC_BASE_URL=%NGROK_URL%)> .env.ngrok
echo [4/4] docker compose up...
docker compose --env-file .env --env-file .env.ngrok up -d --build

echo.
echo OK
echo   Web:  http://localhost:3000
echo   API:  %NGROK_URL%
echo   Login: admin / NovaFlowLocalDevAdmin1
endlocal

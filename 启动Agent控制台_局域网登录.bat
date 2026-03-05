@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%LLM_PROVIDER%"=="" set "LLM_PROVIDER=minimax"
if "%MINIMAX_MODEL%"=="" set "MINIMAX_MODEL=MiniMax-M2.5"
if "%MINIMAX_BASE_URL%"=="" set "MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic"

if "%WEB_AUTH_ENABLED%"=="" set "WEB_AUTH_ENABLED=1"
if "%WEB_USERNAME%"=="" set "WEB_USERNAME=admin"
if "%WEB_PASSWORD%"=="" set "WEB_PASSWORD=ChangeMe_2026"

if "%MINIMAX_API_KEY%"=="" (
  echo [WARN] MINIMAX_API_KEY is empty, model calls may fail.
)

for /f "tokens=2 delims=: " %%i in ('ipconfig ^| findstr /c:"IPv4"') do set LOCAL_IP=%%i
set LOCAL_IP=%LOCAL_IP: =%
echo.
echo ???????: http://%LOCAL_IP%:8787
echo ????: %WEB_USERNAME%
echo ????: %WEB_PASSWORD%
echo.
start "" cmd /c "timeout /t 2 >nul & start "" http://127.0.0.1:8787"
python server.py --host 0.0.0.0 --port 8787

pause

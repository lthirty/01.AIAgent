@echo off
chcp 65001 >nul
cd /d "%~dp0"

where cloudflared >nul 2>nul
if errorlevel 1 (
  echo ???? cloudflared?
  echo ???? cloudflared ??? PATH???????????
  echo ??: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
  pause
  exit /b 1
)

set "LLM_PROVIDER=minimax"
set "MINIMAX_API_KEY=sk-cp-P_pLFgeDMgueE5Pq5tmMUilomS5eVaSzlWJVSXnlP6O5duQt4Nl-LaeYA97qEiMLSPubUCtiOw5WO54eZDmM7r-3qtyCFhlAh9ttgGNJjGvVZKlOo4tFxj0"
set "MINIMAX_MODEL=MiniMax-M2.5"
set "MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic"

set "WEB_AUTH_ENABLED=1"
set "WEB_USERNAME=admin"
set "WEB_PASSWORD=ChangeMe_2026"

echo ????: %WEB_USERNAME%
echo ????: %WEB_PASSWORD%
echo.
echo ????????? Cloudflare Tunnel...

start "AgentServer" cmd /k "cd /d %~dp0 && python server.py --host 127.0.0.1 --port 8787"
timeout /t 2 >nul
cloudflared tunnel --url http://127.0.0.1:8787

pause

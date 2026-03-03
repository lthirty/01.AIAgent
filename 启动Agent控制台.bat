@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "LLM_PROVIDER=minimax"
set "MINIMAX_API_KEY=sk-cp-P_pLFgeDMgueE5Pq5tmMUilomS5eVaSzlWJVSXnlP6O5duQt4Nl-LaeYA97qEiMLSPubUCtiOw5WO54eZDmM7r-3qtyCFhlAh9ttgGNJjGvVZKlOo4tFxj0"
set "MINIMAX_MODEL=MiniMax-M2.5"
set "MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic"

set "WEB_AUTH_ENABLED=1"
set "WEB_USERNAME=admin"
set "WEB_PASSWORD=ChangeMe_2026"

start "" cmd /c "timeout /t 2 >nul & start "" http://127.0.0.1:8787"
python server.py --host 127.0.0.1 --port 8787

pause

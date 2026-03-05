@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist scripts\start_cloudflare_quick_tunnel.ps1 (
  echo Missing script: scripts\start_cloudflare_quick_tunnel.ps1
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start_cloudflare_quick_tunnel.ps1" -HostAddress "127.0.0.1" -Port 8787

pause

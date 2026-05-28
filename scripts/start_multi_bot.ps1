# Start all bots as a single multi-bot server on port 8080.
# This mirrors the production Cloud Run setup (one service, all bots).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start_multi_bot.ps1
#
# The gateway's DOMAIN_MAP_JSON should point to:
#   http://127.0.0.1:8080/bot/<slug>/chat
#
# Update fastapi_server/.env:
#   DOMAIN_MAP_JSON={"religious":"http://127.0.0.1:8080/bot/religious","education":"http://127.0.0.1:8080/bot/education","digital-literacy":"http://127.0.0.1:8080/bot/digital-literacy","design-thinking":"http://127.0.0.1:8080/bot/design-thinking","wellbeing":"http://127.0.0.1:8080/bot/wellbeing","sustainability":"http://127.0.0.1:8080/bot/sustainability","global-citizenship":"http://127.0.0.1:8080/bot/global-citizenship","entrepreneurship":"http://127.0.0.1:8080/bot/entrepreneurship","emotional-intelligence":"http://127.0.0.1:8080/bot/emotional-intelligence","financial-literacy":"http://127.0.0.1:8080/bot/financial-literacy"}

param(
    [switch] $InstallDeps
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BotsRoot = Join-Path $Root "tekurious-chatbot-main\bots"
$MultiBot = Join-Path $BotsRoot "multi_bot_server"

if ($InstallDeps) {
    Write-Host "Installing shared bot dependencies..." -ForegroundColor Yellow
    py -3.12 -m pip install -r "$BotsRoot\requirements-shared.txt"
}

$cmd = "Set-Location '$BotsRoot'; `$env:PORT='8080'; py -3.12 -m uvicorn multi_bot_server.main:app --host 127.0.0.1 --port 8080"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $cmd) | Out-Null

Write-Host "Started multi-bot server on http://127.0.0.1:8080" -ForegroundColor Green
Write-Host ""
Write-Host "Bot endpoints:" -ForegroundColor Cyan
Write-Host "  http://127.0.0.1:8080/bot/religious/chat"
Write-Host "  http://127.0.0.1:8080/bot/education/chat"
Write-Host "  http://127.0.0.1:8080/bot/wellbeing/chat"
Write-Host "  ... (all 10 bots)"
Write-Host ""
Write-Host "Health check: Invoke-WebRequest http://127.0.0.1:8080/health -UseBasicParsing" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Update fastapi_server/.env DOMAIN_MAP_JSON to use port 8080 paths." -ForegroundColor Yellow

# Start domain bots on 127.0.0.1:8101–8110 (must match fastapi_server/.env DOMAIN_MAP_JSON).
#
# By default this does NOT run pip (avoids WinError 32: uvicorn.exe locked while gateway/bots run).
#
#   All bots:
#     powershell -ExecutionPolicy Bypass -File .\scripts\start_local_domain_bots.ps1
#
#   Single bot:
#     powershell -ExecutionPolicy Bypass -File .\scripts\start_local_domain_bots.ps1 -Only wellbeing
#
# One-time / rare: install or upgrade deps — stop ALL uvicorn/Python servers first, then:
#     powershell -ExecutionPolicy Bypass -File .\scripts\start_local_domain_bots.ps1 -InstallDeps -Only wellbeing

param(
    [string] $Only = "",
    [switch] $InstallDeps
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BotsRoot = Join-Path $Root "tekurious-chatbot-main\bots"

$SlugToDir = [ordered]@{
    "religious"                = "religious-ai"
    "education"                = "education-ai"
    "digital-literacy"         = "digital-literacy-ai"
    "design-thinking"          = "design-thinking-ai"
    "wellbeing"                = "wellbeing-ai"
    "sustainability"           = "sustainability-ai"
    "global-citizenship"       = "global-citizenship-ai"
    "entrepreneurship"         = "entrepreneurship-ai"
    "emotional-intelligence"   = "emotional-intelligence-ai"
    "financial-literacy"       = "financial-literacy-ai"
}

$bots = @(
    @{ dir = "religious-ai";              port = 8101 }
    @{ dir = "education-ai";              port = 8102 }
    @{ dir = "digital-literacy-ai";       port = 8103 }
    @{ dir = "design-thinking-ai";       port = 8104 }
    @{ dir = "wellbeing-ai";              port = 8105 }
    @{ dir = "sustainability-ai";         port = 8106 }
    @{ dir = "global-citizenship-ai";     port = 8107 }
    @{ dir = "entrepreneurship-ai";       port = 8108 }
    @{ dir = "emotional-intelligence-ai"; port = 8109 }
    @{ dir = "financial-literacy-ai";     port = 8110 }
)

if ($Only.Trim().Length -gt 0) {
    $key = $Only.Trim().ToLowerInvariant()
    $targetDir = $SlugToDir[$key]
    if (-not $targetDir) {
        if ($key.EndsWith("-ai")) {
            $targetDir = $key
        }
    }
    if (-not $targetDir -or -not ($bots | Where-Object { $_.dir -eq $targetDir })) {
        Write-Error "Unknown -Only '$Only'. Try: wellbeing, education, digital-literacy, ... or folder name e.g. wellbeing-ai."
        exit 1
    }
    $bots = @($bots | Where-Object { $_.dir -eq $targetDir })
    Write-Host "Starting single bot: $targetDir (port $($bots[0].port))" -ForegroundColor Cyan
} else {
    Write-Host "Starting all $($bots.Count) domain bots..." -ForegroundColor Cyan
}

if ($InstallDeps) {
    Write-Host "InstallDeps: upgrading pip packages (stop all uvicorn first if you see WinError 32)..." -ForegroundColor Yellow
    py -3.12 -m pip install --upgrade pip
    py -3.12 -m pip install --upgrade fastapi uvicorn pydantic pydantic-core langchain langgraph langchain-google-genai qdrant-client httpx
}

foreach ($b in $bots) {
    $botDir = Join-Path $BotsRoot $b.dir
    $src = Join-Path $botDir "src"

    if (-not (Test-Path $src)) {
        Write-Warning "Skip missing: $src"
        continue
    }

    if ($InstallDeps) {
        $reqPath = Join-Path $botDir "requirements.txt"
        if (-not (Test-Path $reqPath)) {
            $reqPath = Join-Path $src "requirements.txt"
        }
        if (Test-Path $reqPath) {
            Write-Host "pip install -r for $($b.dir)..." -ForegroundColor DarkCyan
            py -3.12 -m pip install -r "$reqPath"
        }
    }

    $cmd = "Set-Location '$src'; `$env:PORT='$($b.port)'; py -3.12 -m uvicorn server.main:app --host 127.0.0.1 --port $($b.port)"
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $cmd) | Out-Null
    Write-Host "Started $($b.dir) on http://127.0.0.1:$($b.port)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next: start gateway (if not running):" -ForegroundColor Yellow
Write-Host "  cd fastapi_server" -ForegroundColor Yellow
Write-Host "  py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor Yellow
Write-Host "Smoke test:  Invoke-WebRequest http://127.0.0.1:$($bots[0].port)/health -UseBasicParsing" -ForegroundColor DarkGray

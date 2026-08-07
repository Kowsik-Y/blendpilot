`# ==============================================================================
#  BlendPilot AI - All-in-One Services Launcher (Next.js + FastAPI + Blender)
#  Windows PowerShell Version
# ==============================================================================

$ErrorActionPreference = "Stop"
$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR

Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "       ____  _                 _ ____  _ _       _      _    ___ " -ForegroundColor Cyan
Write-Host "      | __ )| | ___ _ __   __| |  _ \(_) | ___ | |_   / \  |_ _| " -ForegroundColor Cyan
Write-Host "      |  _ \| |/ _ \ '_ \ / _` | |_) | | |/ _ \| __| / _ \  | |  " -ForegroundColor Cyan
Write-Host "      | |_) | |  __/ | | | (_| |  __/| | | (_) | |_ / ___ \ | |  " -ForegroundColor Cyan
Write-Host "      |____/|_|\___|_| |_|\__,_|_|   |_|_|\___/ \__/_/   \_\___| " -ForegroundColor Cyan
Write-Host "      " -ForegroundColor Cyan
Write-Host "     Autonomous 10-Agent Copilot for Blender 3D Modeling" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan

# -- 1. Python Environment Check --------------------------------------
$VENV_PYTHON = Join-Path $PROJECT_DIR ".venv\Scripts\python.exe"
if (-Not (Test-Path $VENV_PYTHON)) {
    Write-Host "[!] Python virtual environment (.venv) not found. Setting up..." -ForegroundColor Yellow
    python -m venv "$PROJECT_DIR\.venv"
    & "$PROJECT_DIR\.venv\Scripts\python.exe" -m pip install --upgrade pip
    if (Test-Path "$PROJECT_DIR\pyproject.toml") {
        & "$PROJECT_DIR\.venv\Scripts\python.exe" -m pip install -e .
    }
}

# -- 2. Node.js & Next.js Dependencies Check --------------------------
if (Test-Path "$PROJECT_DIR\ui") {
    if (-Not (Test-Path "$PROJECT_DIR\ui\node_modules")) {
        Write-Host "[!] Node modules not found in ui\. Installing..." -ForegroundColor Yellow
        Push-Location "$PROJECT_DIR\ui"
        npm install
        Pop-Location
    }
}

$Jobs = @()

# Cleanup function for exit
function Cleanup {
    Write-Host "`n[*] Shutting down all BlendPilot services..." -ForegroundColor Yellow
    foreach ($Job in $Jobs) {
        Stop-Job -Job $Job
        Remove-Job -Job $Job -Force
    }
    Write-Host "[OK] All services stopped cleanly. Goodbye!" -ForegroundColor Green
}

# -- 3. Start Blender Bridge Server -----------------------------------
Write-Host "[+] Starting Blender Bridge Server..." -ForegroundColor Green
$BlenderJob = Start-Job -Name "BlenderBridge" -ScriptBlock {
    param($Python, $ProjectDir)
    Set-Location $ProjectDir
    & $Python "$ProjectDir\scripts\start_blender_bridge.py" --host 127.0.0.1 --port 9876
} -ArgumentList $VENV_PYTHON, $PROJECT_DIR
$Jobs += $BlenderJob
Write-Host "[OK] Blender Bridge starting on http://127.0.0.1:9876" -ForegroundColor Green

# -- 4. Start FastAPI Backend API ------------------------------------
Write-Host "[+] Starting BlendPilot FastAPI Backend API on port 8000..." -ForegroundColor Green
$BackendJob = Start-Job -Name "FastAPI" -ScriptBlock {
    param($Python, $ProjectDir)
    Set-Location $ProjectDir
    & $Python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $VENV_PYTHON, $PROJECT_DIR
$Jobs += $BackendJob

# -- 5. Start Next.js Frontend ---------------------------------------
if (Test-Path "$PROJECT_DIR\ui") {
    Write-Host "[+] Starting Next.js Frontend Dev Server on port 3000..." -ForegroundColor Green
    $FrontendJob = Start-Job -Name "NextJS" -ScriptBlock {
        param($ProjectDir)
        Set-Location "$ProjectDir\ui"
        npm run dev
    } -ArgumentList $PROJECT_DIR
    $Jobs += $FrontendJob
}

Start-Sleep -Seconds 5

Write-Host "`n===============================================================" -ForegroundColor Green
Write-Host " [OK] All BlendPilot Services are Live and Connected!" -ForegroundColor Green
Write-Host "   -> Next.js Frontend UI:   http://localhost:3000" -ForegroundColor Cyan
Write-Host "   -> 3D Studio Workspace:  http://localhost:3000/studio" -ForegroundColor Cyan
Write-Host "   -> FastAPI Backend API:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   -> Blender Bridge:       http://127.0.0.1:9876" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Green
Write-Host "Press [Ctrl+C] anytime to stop all services.`n" -ForegroundColor Yellow

Start-Process "http://localhost:3000/studio"

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Cleanup
}

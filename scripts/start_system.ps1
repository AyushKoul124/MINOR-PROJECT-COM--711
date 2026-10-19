# ==============================================================================
# SOCMINT Intelligence Framework — PowerShell Startup Script
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  SOCMINT Academic Research Prototype — PowerShell Launcher" -ForegroundColor Cyan
Write-Host "  NTRO Problem Statement Inspiration | December 2026 Viva Defense" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$workspace = Split-Path -Parent $PSScriptRoot

# 1. Check Python
$pyExe = Join-Path $workspace ".venv\Scripts\python.exe"
if (-not (Test-Path $pyExe)) {
    Write-Host "[ERROR] Virtualenv Python not found at $pyExe" -ForegroundColor Red
    exit 1
}
Write-Host "[1/4] Found Python virtualenv at $pyExe" -ForegroundColor Green

# 2. Check Database Port 5432
$pgConn = Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
if ($pgConn) {
    Write-Host "[2/4] PostgreSQL is listening on port 5432." -ForegroundColor Green
} else {
    Write-Host "[WARNING] PostgreSQL not detected on port 5432. Make sure your Docker container or Postgres service is running." -ForegroundColor Yellow
}

# 3. Offline seed timestamp alignment
Write-Host "[3/4] Aligning seed posts with active 48-hour observation window..." -ForegroundColor Cyan
& $pyExe -m ingestion_a.backfill --offline

# 4. Spawn Backend & Frontend in new windows
Write-Host "[4/4] Starting FastAPI backend (port 8000) and React frontend (port 5173)..." -ForegroundColor Cyan

# Start Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workspace'; & '$pyExe' -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

# Start Frontend
$frontendDir = Join-Path $workspace "frontend"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "All services initiated! Opening browser..." -ForegroundColor Green
Start-Process "http://localhost:5173"

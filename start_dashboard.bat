@echo off
title SOCMINT Intelligence Framework Launcher
color 0b
echo ==============================================================================
echo   SOCMINT Academic Research Prototype - Local Environment Launcher
echo   NTRO Problem Statement Inspiration ^| December 2026 Viva Defense
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python Virtual Environment...
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe!
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)
echo       Found Python environment.

echo.
echo [2/4] Aligning Historical Seed Data with Active Trailing Window (Offline Replay)...
.venv\Scripts\python.exe -m ingestion_a.backfill --offline
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Offline backfill encountered a non-critical notice. Continuing...
)

echo.
echo [3/4] Launching FastAPI Backend Server on port 8000...
start "SOCMINT Backend API (Port 8000)" cmd /k "title SOCMINT Backend API && .venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo [4/4] Launching React 18 Operations Dashboard on port 5173...
start "SOCMINT Frontend Dashboard (Port 5173)" cmd /k "title SOCMINT React Dashboard && cd frontend && npm run dev"

echo.
echo ==============================================================================
echo   All services launched! Opening browser at http://localhost:5173...
echo ==============================================================================
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo Press any key to close this launcher window (services will stay running).
pause >nul

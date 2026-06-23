@echo off
title copilot-azure-proxy — Environment Setup
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================
echo  copilot-azure-proxy — Init Environment
echo ============================================
echo.

:: ── Check Python ─────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [OK] Python %%v detected.

:: ── Create .venv ─────────────────────────────────────────────────────────────
if exist ".venv\Scripts\python.exe" (
    echo [SKIP] .venv already exists.
) else (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv. See output above for details.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: ── Install dependencies ─────────────────────────────────────────────────────
echo [INFO] Installing dependencies from requirements.txt...
.venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. See output above for details.
    echo         Try running manually: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo [OK] Dependencies installed.

echo.
echo ============================================
echo  Setup complete! You can now run:
echo    run.bat
echo ============================================
echo.

pause


@echo off
title Support Copilot Server
set PYTHONUTF8=1
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python and check 'Add Python to PATH'.
    echo.
    pause
    exit /b 1
)
python -u server.py 8000
if errorlevel 1 pause

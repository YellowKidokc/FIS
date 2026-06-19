@echo off
setlocal

cd /d "%~dp0"
title River FIS Launcher
set "FIS_PORT=61845"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo [River FIS] Working directory: %CD%
echo [River FIS] Using interpreter: %PYTHON%
echo [River FIS] Starting server...
echo [River FIS] Port: %FIS_PORT%
echo [River FIS] UI will be at http://127.0.0.1:%FIS_PORT%/
echo.

"%PYTHON%" scripts\start.py %FIS_PORT%

if errorlevel 1 (
    echo.
    echo [River FIS] Startup failed with exit code %errorlevel%.
    echo [River FIS] Run troubleshoot_fis.bat to diagnose and install local dependencies.
    pause
)

endlocal

@echo off
setlocal

cd /d "%~dp0"
set "FIS_PORT=61845"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

start "FIS Server" /min cmd /c ""%PYTHON%" scripts\start.py %FIS_PORT%"
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:%FIS_PORT%/"

endlocal

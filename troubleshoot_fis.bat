@echo off
setlocal

cd /d "%~dp0"
title River FIS Troubleshooter
set "FIS_PORT=61845"

echo [River FIS] Starting diagnostics...
echo [River FIS] Repo: %CD%
echo [River FIS] Expected port: %FIS_PORT%
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "BOOTSTRAP=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "BOOTSTRAP=python"
    ) else (
        echo [ERROR] Python was not found on PATH.
        echo Install Python 3 and rerun this script.
        pause
        exit /b 1
    )
)

echo [River FIS] Bootstrap interpreter: %BOOTSTRAP%

if not exist ".venv\Scripts\python.exe" (
    echo [River FIS] Creating local virtual environment...
    %BOOTSTRAP% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv
        pause
        exit /b 1
    )
) else (
    echo [River FIS] Reusing existing .venv
)

set "VENV_PY=.venv\Scripts\python.exe"

echo.
echo [River FIS] Python version:
"%VENV_PY%" --version

echo.
echo [River FIS] Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARN] pip upgrade failed. Continuing...
)

echo.
echo [River FIS] Installing developer dependency: pytest
"%VENV_PY%" -m pip install pytest
if errorlevel 1 (
    echo [WARN] pytest install failed. Continuing...
)

echo.
echo [River FIS] Running syntax/import compile pass...
"%VENV_PY%" -m compileall app core engines learning scripts workers tests
if errorlevel 1 (
    echo [WARN] compileall reported issues.
) else (
    echo [OK] compileall passed.
)

echo.
echo [River FIS] Checking startup entrypoint...
"%VENV_PY%" scripts\start.py --help 1>nul 2>nul
if errorlevel 1 (
    echo [INFO] start.py does not expose --help, checking direct import instead...
    "%VENV_PY%" -c "from app.server import run; print('app.server import OK')"
    if errorlevel 1 (
        echo [ERROR] app.server import failed.
        pause
        exit /b 1
    )
) else (
    echo [OK] start.py responded to --help.
)

echo.
echo [River FIS] Running UI contract smoke check...
"%VENV_PY%" scripts\ui_smoke_check.py
if errorlevel 1 (
    echo [WARN] UI smoke check failed.
) else (
    echo [OK] UI smoke check passed.
)

echo.
echo [River FIS] Running test server startup check...
"%VENV_PY%" -m pytest -q tests\test_server_starts.py
if errorlevel 1 (
    echo [WARN] Server startup test failed.
) else (
    echo [OK] Server startup test passed.
)

echo.
echo [River FIS] Diagnostics complete.
echo [River FIS] Next step: run start_fis.bat
pause

endlocal

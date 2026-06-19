@echo off
setlocal

cd /d "%~dp0"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP_DIR%\START_FILE_INTELLIGENCE_SYSTEM.bat"
set "REPO_DIR=%~dp0"

> "%TARGET%" echo @echo off
>> "%TARGET%" echo setlocal
>> "%TARGET%" echo cd /d "%REPO_DIR%"
>> "%TARGET%" echo call start_fis_boot.bat
>> "%TARGET%" echo endlocal

echo [FIS] Startup launcher installed:
echo [FIS] %TARGET%
echo [FIS] On sign-in, Windows will start the server and open http://127.0.0.1:61845/

endlocal

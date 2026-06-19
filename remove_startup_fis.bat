@echo off
setlocal

set "TARGET=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\START_FILE_INTELLIGENCE_SYSTEM.bat"

if exist "%TARGET%" (
    del "%TARGET%"
    echo [FIS] Removed startup launcher.
) else (
    echo [FIS] No startup launcher was installed.
)

endlocal

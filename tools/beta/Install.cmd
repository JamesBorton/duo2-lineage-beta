@echo off
setlocal
set "NoDefaultCurrentDirectoryInExePath=1"
cd /d "%~dp0"
"%SystemRoot%\System32\where.exe" py >nul 2>nul
if not errorlevel 1 (
  py -3 -I "%~dp0installer.py"
) else (
  "%SystemRoot%\System32\where.exe" python >nul 2>nul
  if errorlevel 1 (
    echo Install Python 3.11 or newer from python.org, then open Install.cmd again.
    echo See START-HERE.html for the short setup checklist.
    pause
    exit /b 1
  )
  python -I "%~dp0installer.py"
)
if errorlevel 1 pause
endlocal

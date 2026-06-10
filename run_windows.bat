@echo off
rem Launches the Revolut -> E-conomic connector on Windows.
rem Creates a local virtual environment on first run, installs the
rem dependencies, and starts the GUI without a console window.

setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 goto :nopython
    set "PYTHON=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :error
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :error

echo Starting the app...
start "" ".venv\Scripts\pythonw.exe" Main.py
exit /b 0

:nopython
echo Python was not found. Install Python 3.9 or newer from https://www.python.org/downloads/
echo (make sure to tick "Add python.exe to PATH" during installation), then run this file again.
pause
exit /b 1

:error
echo.
echo Setup failed. See the messages above for details.
pause
exit /b 1

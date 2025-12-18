@echo off
setlocal
REM Halo Wars Coordinate Guider - Startup Script
REM This script launches the Halo Wars Coordinate Guider application

echo Starting Halo Wars Coordinate Guider...
echo.

REM Check if Python is installed
where python >nul 2>&1 || goto :nopython

REM Display Python version
echo Found Python:
call python --version
echo.

REM Check if Halo_Wars_XY_Guider_3.6.12.pyw exists
if not exist "Halo_Wars_XY_Guider_3.6.12.pyw" goto :nofile

REM Check if maps directory exists
if not exist "maps" (
    echo WARNING: maps directory not found
    echo.
)

REM Check if scn directory exists
if not exist "scn" (
    echo WARNING: scn directory not found
    echo Auto Populate feature may not work without SCN files
    echo.
)

REM Launch the application
echo Launching application...
start "" "Halo_Wars_XY_Guider_3.6.12.pyw"

echo Application started successfully!
echo If the application doesn't appear, try running: python Halo_Wars_XY_Guider_3.6.12.pyw
echo.
timeout /t 3 >nul
goto :eof

:nopython
echo ERROR: Python is not installed or not in PATH
echo Please install Python 3.x from https://www.python.org/downloads/
echo.
pause
exit /b 1

:nofile
echo ERROR: Halo_Wars_XY_Guider_3.6.12.pyw not found in current directory
echo Please run this script from the project root directory
echo.
pause
exit /b 1


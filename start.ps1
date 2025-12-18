# Halo Wars Coordinate Guider - Startup Script
# This script launches the Halo Wars Coordinate Guider application

Write-Host "Starting Halo Wars Coordinate Guider..." -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.x from https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Halo_Wars_Coordinate_Guider.pyw exists
if (-Not (Test-Path "Halo_Wars_Coordinate_Guider.pyw")) {
    Write-Host "ERROR: Halo_Wars_Coordinate_Guider.pyw not found in current directory" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if maps directory exists
if (-Not (Test-Path "maps")) {
    Write-Host "WARNING: maps directory not found" -ForegroundColor Yellow
}

# Check if scn directory exists
if (-Not (Test-Path "scn")) {
    Write-Host "WARNING: scn directory not found" -ForegroundColor Yellow
    Write-Host "Auto Populate feature may not work without SCN files" -ForegroundColor Yellow
}

# Launch the application using pythonw (no console window)
Write-Host "Launching application..." -ForegroundColor Green
Start-Process pythonw -ArgumentList "Halo_Wars_Coordinate_Guider.pyw" -NoNewWindow

Write-Host "Application started successfully!" -ForegroundColor Green
Write-Host "If the application doesn't appear, try running: python Halo_Wars_Coordinate_Guider.pyw" -ForegroundColor Yellow


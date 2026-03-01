@echo off
title Build schedule_app.exe
echo.
echo ========================================
echo   Build Tool - schedule_app.exe
echo ========================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python found. Installing PyInstaller...
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller. Check your internet connection.
    pause
    exit /b 1
)

echo [2/3] Building exe, please wait (30-60 seconds)...
echo.
python -m PyInstaller --onefile --windowed --name "schedule" schedule_app.py

echo.
if exist "dist\schedule.exe" (
    copy "dist\schedule.exe" "schedule.exe" >nul
    echo [3/3] Done!
    echo.
    echo   Generated: schedule.exe
    echo   Data file: schedule_data.json (auto-created next to exe)
    echo.
    echo   You can delete the build\ dist\ folders and schedule.spec file.
) else (
    echo [ERROR] Build failed. See error messages above.
)

echo.
pause

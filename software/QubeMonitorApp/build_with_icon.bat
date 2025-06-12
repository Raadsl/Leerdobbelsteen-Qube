@echo off
REM Build script for QubeMonitor using PyInstaller spec file
REM This ensures proper icon embedding for Windows

echo Building QubeMonitor with embedded icon...

REM Check if pyinstaller is installed
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Check if icon file exists
if not exist "dice_icon_160194.ico" (
    echo Error: Icon file 'dice_icon_160194.ico' not found!
    echo Please ensure the icon file is in the same directory as this script.
    pause
    exit /b 1
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM Build using spec file
echo Building executable with spec file...
pyinstaller qubeMonitor.spec

REM Check if build was successful
if exist "dist\QubeMonitor.exe" (
    echo Build completed successfully!
    echo Executable location: dist\QubeMonitor.exe
    echo.
    echo The icon should now be properly embedded in the executable.
    echo You can distribute the executable without needing the .ico file.
) else (
    echo Build failed!
    pause
    exit /b 1
)

pause

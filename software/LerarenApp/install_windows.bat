@echo off
echo Installing LerarenApp...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is not available. Please reinstall Python with pip.
    pause
    exit /b 1
)

:: Install required packages
echo Installing required packages...
python -m pip install pyserial

:: Check if the main script exists
if not exist "lerarenApp.py" (
    echo lerarenApp.py not found in current directory.
    echo Please make sure this installer is in the same folder as lerarenApp.py
    pause
    exit /b 1
)

:: Create a batch file to run the app
echo @echo off > run_lerarenapp.bat
echo cd /d "%~dp0" >> run_lerarenapp.bat
echo python lerarenApp.py >> run_lerarenapp.bat
echo pause >> run_lerarenapp.bat

echo.
echo Installation complete!
echo.
echo To run the app, double-click on "run_lerarenapp.bat"
echo or run "python lerarenApp.py" in this folder.
echo.
pause

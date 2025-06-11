@echo off
echo Installing Qube Monitor...
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
if not exist "qubeMonitor.py" (
    echo qubeMonitor.py not found in current directory.
    echo Please make sure this installer is in the same folder as qubeMonitor.py
    pause
    exit /b 1
)

:: Create a batch file to run the app
echo @echo off > run_qubemonitor.bat
echo cd /d "%~dp0" >> run_qubemonitor.bat
echo python qubeMonitor.py >> run_qubemonitor.bat
echo pause >> run_qubemonitor.bat

echo.
echo Installation complete!
echo.
echo To run the app, double-click on "run_qubemonitor.bat"
echo or run "python qubeMonitor.py" in this folder.
echo.
pause

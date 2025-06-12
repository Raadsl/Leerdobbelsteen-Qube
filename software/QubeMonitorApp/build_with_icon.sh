#!/bin/bash

# Build script for QubeMonitor using PyInstaller spec file
# This ensures proper icon embedding for all platforms

echo "Building QubeMonitor with embedded icon..."

# Check if pyinstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Check if icon file exists
if [ ! -f "dice_icon_160194.ico" ]; then
    echo "Error: Icon file 'dice_icon_160194.ico' not found!"
    echo "Please ensure the icon file is in the same directory as this script."
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/

# Build using spec file
echo "Building executable with spec file..."
pyinstaller qubeMonitor.spec

# Check if build was successful
if [ -d "dist" ]; then
    echo "Build completed successfully!"
    echo "Executable location:"
    if [ -f "dist/QubeMonitor" ]; then
        echo "  Linux/macOS: dist/QubeMonitor"
    elif [ -f "dist/QubeMonitor.exe" ]; then
        echo "  Windows: dist/QubeMonitor.exe"
    elif [ -d "dist/QubeMonitor.app" ]; then
        echo "  macOS App: dist/QubeMonitor.app"
    fi
    
    echo ""
    echo "The icon should now be properly embedded in the executable."
    echo "You can distribute the executable without needing the .ico file."
else
    echo "Build failed!"
    exit 1
fi

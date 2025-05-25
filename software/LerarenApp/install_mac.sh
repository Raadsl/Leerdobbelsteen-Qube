#!/bin/bash

echo "Installing LerarenApp for Mac..."
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed."
    echo "Please install Python 3 from https://python.org"
    echo "Or install via Homebrew: brew install python3"
    exit 1
fi

# Check if pip is available
if ! python3 -m pip --version &> /dev/null; then
    echo "pip is not available. Please reinstall Python with pip."
    exit 1
fi

# Install required packages
echo "Installing required packages..."
python3 -m pip install pyserial

# Check if the main script exists
if [ ! -f "lerarenApp.py" ]; then
    echo "lerarenApp.py not found in current directory."
    echo "Please make sure this installer is in the same folder as lerarenApp.py"
    exit 1
fi

# Create a shell script to run the app
cat > run_lerarenapp.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
python3 lerarenApp.py
EOF

chmod +x run_lerarenapp.sh

echo
echo "Installation complete!"
echo
echo "To run the app, double-click on 'run_lerarenapp.sh'"
echo "or run 'python3 lerarenApp.py' in this folder."
echo

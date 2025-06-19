"""
Configuration module for Qube Monitor application.
Contains global settings and constants.
"""

# Serial communication settings
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 1.0
SERIAL_RECONNECT_INTERVAL = 180  # seconds (3 minutes)
SERIAL_HEARTBEAT_TIMEOUT = 40    # seconds
SERIAL_HEARTBEAT_RECONNECT = 90  # seconds

# GUI settings
WINDOW_TITLE = "Qube Monitor - Docent Dashboard"
WINDOW_SIZE = "1000x700"
ICON_FILE = "qube_monitor.ico"

# Student number validation
MIN_STUDENT_NUMBER = 100000
MAX_STUDENT_NUMBER = 999999

# HIER KUN JE NIEUWE STATUS CODES TOEVOEGEN
STATUS_MAP = {
    'G': ('Beschikbaar', 'green'),
    'V': ('Vraag', 'orange'), 
    'R': ('Hulp nodig', 'red')
}

# Log settings
MAX_LOG_ENTRIES = 1000
LOG_DISPLAY_ENTRIES = 200

# Log types and colors
LOG_COLORS = {
    "STATUS": "#0066CC",
    "ERROR": "#CC0000",
    "HEALTH": "#FF6600",
    "INFO": "#000000"
}

# Threading settings
SERIAL_THREAD_SLEEP = 0.1  # seconds
HEALTH_CHECK_INTERVAL = 10000  # milliseconds
DURATION_UPDATE_INTERVAL = 1000  # milliseconds
PERIODIC_REFRESH_INTERVAL = 30000  # milliseconds

# Status duration color thresholds (seconds)
DURATION_WARNING_THRESHOLD = 120  # 2 minutes - orange
DURATION_CRITICAL_THRESHOLD = 300  # 5 minutes - red

# Duplicate message filtering
DUPLICATE_MESSAGE_THRESHOLD = 5  # seconds

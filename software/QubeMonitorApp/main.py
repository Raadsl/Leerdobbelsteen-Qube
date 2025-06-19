"""
Main entry point for the Qube Monitor application.
"""

import sys
import os
import signal
import atexit
import traceback
from gui import QubeMonitorGUI
from support.crash_reporter import report_crash


def setup_signal_handlers():
    """Set up signal handlers to catch fatal crashes."""
    
    def signal_handler(signum, frame):
        """Handle fatal signals."""
        signal_names = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT",
        }
        
        # Add platform-specific signals
        if hasattr(signal, 'SIGSEGV'):
            signal_names[signal.SIGSEGV] = "SIGSEGV (Segmentation Fault)"
        if hasattr(signal, 'SIGABRT'):
            signal_names[signal.SIGABRT] = "SIGABRT (Abort)"
        if hasattr(signal, 'SIGFPE'):
            signal_names[signal.SIGFPE] = "SIGFPE (Floating Point Exception)"
        if hasattr(signal, 'SIGILL'):
            signal_names[signal.SIGILL] = "SIGILL (Illegal Instruction)"
        
        signal_name = signal_names.get(signum, f"Signal {signum}")
        
        print(f"Fatal signal received: {signal_name}")
        
        # Exit gracefully
        sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Register platform-specific signals if available
    if hasattr(signal, 'SIGSEGV'):
        signal.signal(signal.SIGSEGV, signal_handler)
    if hasattr(signal, 'SIGABRT'):
        signal.signal(signal.SIGABRT, signal_handler)
    if hasattr(signal, 'SIGFPE'):
        signal.signal(signal.SIGFPE, signal_handler)
    if hasattr(signal, 'SIGILL'):
        signal.signal(signal.SIGILL, signal_handler)


def setup_exit_handler():
    """Set up exit handler to catch unexpected exits."""
    
    def exit_handler():
        """Handle unexpected exits."""
        # Only log if we're exiting unexpectedly
        if not getattr(exit_handler, 'normal_exit', False):
            print("Application exited unexpectedly")
    
    atexit.register(exit_handler)
    return exit_handler


def main():
    """Main function to start the application."""
    # Set up crash handling
    setup_signal_handlers()
    exit_handler = setup_exit_handler()
    
    try:
        print("Starting Qube Monitor...")
        
        app = QubeMonitorGUI()
        app.run()
        
        # Mark as normal exit
        exit_handler.normal_exit = True
        print("Application exited normally")
        
    except KeyboardInterrupt:
        print("Application interrupted by user")
        exit_handler.normal_exit = True
        
    except Exception as e:
        # Get full traceback
        tb_str = traceback.format_exc()
        
        # Print to console
        print(f"Fatal error: {e}")
        print("Full traceback:")
        print(tb_str)
        
        # Keep console open if running as exe
        if getattr(sys, 'frozen', False):
            input("\nPress Enter to exit...")
        
        # Mark as handled exit
        exit_handler.normal_exit = True


if __name__ == "__main__":
    setup_signal_handlers()
    setup_exit_handler()
    main()

"""
Crash reporting module for Qube Monitor application.
Uses Sentry SDK for comprehensive crash reporting.
Requires sentry-sdk package to be installed.
"""

import os
import sys
import tempfile
import json
import datetime
import platform
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

import sentry_sdk
from sentry_sdk.integrations.threading import ThreadingIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration


class CrashReporter:
    """Professional crash reporting system using Sentry."""
    
    def __init__(self, app_name: str = "QubeMonitor", version: str = "1.1.0"):
        """Initialize the crash reporter."""
        self.app_name = app_name
        self.version = version
        self.app_dir = self._get_application_directory()
        self.crash_dir = self.app_dir / "crash_reports"
        self.crash_dir.mkdir(exist_ok=True)
        
        # Initialize Sentry
        self.sentry_enabled = False
        self._setup_sentry()
    
    def _get_application_directory(self) -> Path:
        """Get the directory where the application is running from."""
        if getattr(sys, 'frozen', False):
            # Running as exe (PyInstaller)
            return Path(sys.executable).parent
        else:
            # Running as script
            return Path(__file__).parent.parent  # Adjusted for support directory
    
    def _setup_sentry(self):
        """Set up Sentry crash reporting (optional)."""
        try:
            sentry_sdk.init(
                # dsn="YOUR_SENTRY_DSN_HERE",  # Uncomment and add real DSN for production
                integrations=[
                    ThreadingIntegration(propagate_hub=True),
                    StdlibIntegration(),
                ],
                traces_sample_rate=0.0,  # Disable performance monitoring
                send_default_pii=False,  # Don't send personally identifiable information
                before_send=self._before_send_sentry,
                transport=self._custom_transport  # Use local file transport
            )
            self.sentry_enabled = True
            print("Sentry crash reporting initialized")
        except Exception as e:
            print(f"Failed to initialize Sentry: {e}")
            self.sentry_enabled = False
    
    def _before_send_sentry(self, event, hint):
        """Filter and modify events before sending to Sentry."""
        # Add custom context
        event['contexts']['app'] = {
            'name': self.app_name,
            'version': self.version,
            'frozen': getattr(sys, 'frozen', False)
        }
        return event
    
    def _custom_transport(self, envelope):
        """Custom transport to save crash reports locally instead of sending to Sentry."""
        try:
            # Parse the envelope to extract crash data
            crash_data = self._parse_sentry_envelope(envelope)
            self._write_crash_file(crash_data)
        except Exception as e:
            print(f"Failed to process crash report: {e}")
    
    def _parse_sentry_envelope(self, envelope) -> Dict[str, Any]:
        """Parse Sentry envelope to extract crash information."""
        # This is a simplified parser - in production you might want more robust parsing
        try:
            # Convert envelope to string and try to extract JSON
            envelope_str = str(envelope)
            # For now, create a basic crash data structure
            return {
                'timestamp': datetime.datetime.now().isoformat(),
                'envelope_data': envelope_str[:1000],  # Truncate for safety
                'app_info': {
                    'name': self.app_name,
                    'version': self.version,
                    'frozen': getattr(sys, 'frozen', False)
                }
            }
        except Exception:
            return {'error': 'Failed to parse crash data'}
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect comprehensive system information."""
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'app': {
                'name': self.app_name,
                'version': self.version,
                'frozen': getattr(sys, 'frozen', False),
                'executable': sys.executable,
                'argv': sys.argv,
                'working_directory': os.getcwd(),
                'app_directory': str(self.app_dir)
            },
            'system': {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'architecture': platform.architecture(),
                'python_version': sys.version,
                'python_version_info': {
                    'major': sys.version_info.major,
                    'minor': sys.version_info.minor,
                    'micro': sys.version_info.micro
                }
            },
            'environment': dict(os.environ) if len(os.environ) < 100 else {'note': 'Environment too large to include'}
        }
    
    def _write_crash_file(self, crash_data: Dict[str, Any]) -> Optional[str]:
        """Write crash report to file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            crash_filename = f"crash_report_{timestamp}.json"
            crash_path = self.crash_dir / crash_filename
            
            # Ensure crash directory exists
            self.crash_dir.mkdir(exist_ok=True)
            
            with open(crash_path, 'w', encoding='utf-8') as f:
                json.dump(crash_data, f, indent=2, default=str)
            
            # Also create a human-readable version
            txt_filename = f"crash_report_{timestamp}.txt"
            txt_path = self.crash_dir / txt_filename
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"QUBE MONITOR CRASH REPORT\n")
                f.write("="*80 + "\n")
                f.write(f"Timestamp: {crash_data.get('timestamp', 'Unknown')}\n")
                f.write(f"App: {self.app_name} v{self.version}\n")
                f.write("\n")
                
                if 'exception' in crash_data:
                    f.write("EXCEPTION:\n")
                    f.write("-"*40 + "\n")
                    f.write(f"Type: {crash_data['exception'].get('type', 'Unknown')}\n")
                    f.write(f"Message: {crash_data['exception'].get('message', 'Unknown')}\n")
                    f.write("\n")
                
                if 'traceback' in crash_data:
                    f.write("TRACEBACK:\n")
                    f.write("-"*40 + "\n")
                    f.write(crash_data['traceback'])
                    f.write("\n")
                
                system_info = crash_data.get('system_info', {})
                if system_info:
                    f.write("SYSTEM INFORMATION:\n")
                    f.write("-"*40 + "\n")
                    for section, data in system_info.items():
                        f.write(f"{section.upper()}:\n")
                        if isinstance(data, dict):
                            for key, value in data.items():
                                f.write(f"  {key}: {value}\n")
                        else:
                            f.write(f"  {data}\n")
                        f.write("\n")
            
            print(f"Crash report written to: {txt_path}")
            return str(txt_path)
            
        except Exception as e:
            print(f"Failed to write crash report: {e}")
            return None
    
    def report_exception(self, exception: Exception, tb_str: Optional[str] = None) -> Optional[str]:
        """Report an exception with full context."""
        try:
            if tb_str is None:
                tb_str = traceback.format_exc()
            
            crash_data = {
                'exception': {
                    'type': type(exception).__name__,
                    'message': str(exception),
                },
                'traceback': tb_str,
                'system_info': self._collect_system_info()
            }
            
            # Use Sentry
            if self.sentry_enabled:
                with sentry_sdk.push_scope() as scope:
                    scope.set_context("app_info", crash_data['system_info']['app'])
                    scope.set_context("system_info", crash_data['system_info']['system'])
                    sentry_sdk.capture_exception(exception)
            
            # Write local crash file 
            return self._write_crash_file(crash_data)
            
        except Exception as e:
            print(f"Failed to report exception: {e}")
            return None
    
    def report_message(self, message: str, level: str = "error") -> Optional[str]:
        """Report a custom message/crash."""
        try:
            crash_data = {
                'message': {
                    'text': message,
                    'level': level
                },
                'traceback': ''.join(traceback.format_stack()),
                'system_info': self._collect_system_info()
            }
            
            # Use Sentry
            if self.sentry_enabled:
                with sentry_sdk.push_scope() as scope:
                    scope.set_context("app_info", crash_data['system_info']['app'])
                    scope.set_level(level)
                    sentry_sdk.capture_message(message)
            
            return self._write_crash_file(crash_data)
            
        except Exception as e:
            print(f"Failed to report message: {e}")
            return None
    
    def test_crash_reporting(self):
        """Test the crash reporting system."""
        print("Testing crash reporting system...")
        
        # Test exception reporting
        try:
            raise ValueError("This is a test exception for crash reporting")
        except Exception as e:
            crash_file = self.report_exception(e)
            print(f"Test exception reported: {crash_file}")
        
        # Test message reporting
        crash_file = self.report_message("This is a test crash message", "warning")
        print(f"Test message reported: {crash_file}")
        
        return True


# Global crash reporter instance
_crash_reporter = None

def get_crash_reporter() -> CrashReporter:
    """Get the global crash reporter instance."""
    global _crash_reporter
    if _crash_reporter is None:
        _crash_reporter = CrashReporter()
    return _crash_reporter

def report_crash(exception: Exception, tb_str: Optional[str] = None) -> Optional[str]:
    """Convenience function to report a crash."""
    return get_crash_reporter().report_exception(exception, tb_str)

def report_message(message: str, level: str = "error") -> Optional[str]:
    """Convenience function to report a message."""
    return get_crash_reporter().report_message(message, level)

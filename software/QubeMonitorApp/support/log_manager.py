"""
Logging module for Qube Monitor application.
Handles activity logging with filtering and export capabilities.
"""

import time
from typing import List, Dict, Optional, Callable
from support.config import *


class LogManager:
    """Manages application logging with filtering and export capabilities."""
    
    def __init__(self):
        """Initialize LogManager."""
        self.log_entries: List[Dict] = []
        self.filter_settings: Dict[str, bool] = {
            'STATUS': False,
            'ERROR': True,
            'HEALTH': False,
            'INFO': False
        }
        self.display_callback: Optional[Callable] = None
    
    def set_display_callback(self, callback: Callable) -> None:
        """
        Set callback function for updating log display.
        
        Args:
            callback: Function to call when log display needs updating
        """
        self.display_callback = callback
    
    def log(self, message: str, log_type: str = "INFO", is_error: bool = False) -> None:
        """
        Add a message to the log.
        
        Args:
            message: Message to log
            log_type: Type of log entry ("STATUS", "ERROR", "HEALTH", "INFO")
            is_error: Backwards compatibility flag
        """
        try:
            # Backwards compatibility: if is_error=True, use ERROR type
            if is_error:
                log_type = "ERROR"
            
            current_time = time.strftime("%H:%M:%S")
            
            # Create log entry
            log_entry = {
                'time': current_time,
                'type': log_type,
                'message': message,
                'color': LOG_COLORS.get(log_type, "#000000")
            }
            
            # Add to log entries
            self.log_entries.append(log_entry)
            
            # Keep log limited to maximum entries
            if len(self.log_entries) > MAX_LOG_ENTRIES:
                self.log_entries = self.log_entries[-MAX_LOG_ENTRIES:]
            
            # Also print to console for debugging
            print(f"[{current_time}] {log_type}: {message}")
            
            # Update display if callback is set
            if self.display_callback:
                self.display_callback()
                
        except Exception as e:
            print(f"Error adding to log: {e}")
    
    def get_filtered_entries(self) -> List[Dict]:
        """
        Get log entries filtered by current filter settings.
        
        Returns:
            List of filtered log entries
        """
        filtered_entries = []
        
        for entry in self.log_entries:
            entry_type = entry['type']
            if self.filter_settings.get(entry_type, False):
                filtered_entries.append(entry)
        
        # Return last LOG_DISPLAY_ENTRIES entries
        return filtered_entries[-LOG_DISPLAY_ENTRIES:]
    
    def set_filter(self, log_type: str, enabled: bool) -> None:
        """
        Set filter for a specific log type.
        
        Args:
            log_type: Type of log to filter
            enabled: Whether to show this log type
        """
        if log_type in self.filter_settings:
            self.filter_settings[log_type] = enabled
            if self.display_callback:
                self.display_callback()
    
    def get_filter_settings(self) -> Dict[str, bool]:
        """
        Get current filter settings.
        
        Returns:
            Dict of filter settings
        """
        return self.filter_settings.copy()
    
    def clear_log(self) -> None:
        """Clear all log entries."""
        self.log_entries = []
        self.log("Activity log cleared", log_type="INFO")
        if self.display_callback:
            self.display_callback()
    
    def export_log(self, filename: str) -> bool:
        """
        Export all log entries to a file.
        
        Args:
            filename: File to export to
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Qube Monitor Log Export - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for entry in self.log_entries:
                    f.write(f"[{entry['time']}] {entry['type']}: {entry['message']}\n")
            
            self.log(f"Log exported to {filename}", log_type="INFO")
            return True
            
        except Exception as e:
            self.log(f"Log export failed: {e}", log_type="ERROR")
            return False
    
    def get_log_text(self) -> str:
        """
        Get all log entries as formatted text.
        
        Returns:
            str: Formatted log text
        """
        lines = []
        for entry in self.log_entries:
            lines.append(f"[{entry['time']}] {entry['type']}: {entry['message']}")
        return '\n'.join(lines)
    
    def get_log_stats(self) -> Dict[str, int]:
        """
        Get statistics about log entries.
        
        Returns:
            Dict with counts for each log type
        """
        stats = {'STATUS': 0, 'ERROR': 0, 'HEALTH': 0, 'INFO': 0}
        
        for entry in self.log_entries:
            entry_type = entry['type']
            if entry_type in stats:
                stats[entry_type] += 1
        
        return stats

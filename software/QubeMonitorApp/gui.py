"""
Main GUI module for Qube Monitor application.
Contains the main application window and all GUI components.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import sys
import os
import traceback
import datetime
import platform
from pathlib import Path
from typing import Dict, Optional

from support.config import *
from support.serial_manager import SerialManager
from support.student_manager import StudentManager
from support.log_manager import LogManager
from support.crash_reporter import report_crash, report_message


class QubeMonitorGUI:
    """Main GUI class for Qube Monitor application."""
    
    def __init__(self):
        """Initialize the GUI application."""
        # Set up global exception handler first
        self._setup_global_exception_handler()
        
        # Initialize managers
        self.student_manager = StudentManager()
        self.log_manager = LogManager()
        self.serial_manager = SerialManager(
            data_callback=self._handle_serial_data,
            status_callback=self._update_connection_status
        )
        
        # GUI state
        self.duration_labels: Dict[int, tk.Label] = {}
        self.log_filter_vars: Dict[str, tk.BooleanVar] = {}
        
        # Set up the main window
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        
        # Set up logging callback
        self.log_manager.set_display_callback(self._update_activity_log_display)
        
        # Set window icon
        self._set_window_icon()
        
        # Create GUI components
        self._create_widgets()
        
        # Start periodic updates
        self._start_periodic_updates()
        
        # Initialize with example data
        self._initialize_example_data()
    
    def _get_application_directory(self):
        """Get the directory where the application is running from."""
        if getattr(sys, 'frozen', False):
            # Running as exe (PyInstaller)
            return Path(sys.executable).parent
        else:
            # Running as script
            return Path(__file__).parent
    
    def _write_crash_file(self, exception, tb_str):
        """Write crash information to a file."""
        try:
            app_dir = self._get_application_directory()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            crash_filename = f"gui_crash_report_{timestamp}.txt"
            crash_path = app_dir / crash_filename
            
            # Collect system information
            system_info = {
                "Python Version": sys.version,
                "Platform": platform.platform(),
                "Architecture": platform.architecture()[0],
                "Machine": platform.machine(),
                "Processor": platform.processor(),
                "Executable": sys.executable,
                "Frozen": getattr(sys, 'frozen', False),
            }
            
            with open(crash_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("QUBE MONITOR GUI CRASH REPORT\n")
                f.write("="*80 + "\n")
                f.write(f"Crash Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Exception: {type(exception).__name__}: {str(exception)}\n")
                f.write("\n")
                
                f.write("SYSTEM INFORMATION:\n")
                f.write("-"*40 + "\n")
                for key, value in system_info.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                f.write("FULL TRACEBACK:\n")
                f.write("-"*40 + "\n")
                f.write(tb_str)
                f.write("\n")
                
                # Try to get additional runtime info
                f.write("RUNTIME INFORMATION:\n")
                f.write("-"*40 + "\n")
                f.write(f"Working Directory: {os.getcwd()}\n")
                f.write(f"Application Directory: {app_dir}\n")
                f.write(f"Command Line: {' '.join(sys.argv)}\n")
                f.write("\n")
                
                f.write("="*80 + "\n")
            
            print(f"GUI crash report written to: {crash_path}")
            return str(crash_path)
            
        except Exception as e:
            print(f"Failed to write GUI crash report: {e}")
            return None
    
    def _setup_global_exception_handler(self) -> None:
        """Set up a global exception handler for the application."""
        def handle_exception(exc_type, exc_value, exc_traceback):
            """Handle uncaught exceptions globally."""
            if issubclass(exc_type, KeyboardInterrupt):
                # Allow program to exit gracefully on Ctrl+C
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Log the exception details
            error_message = f"Unhandled exception: {exc_value}"
            print(error_message, file=sys.stderr)
            
            # Get traceback string
            tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            print(tb_str, file=sys.stderr)
            
            try:
                self.log_manager.log(error_message, log_type="ERROR")
            except:
                pass  # Don't let logging errors crash the crash handler
            
            # Write crash file
            crash_file = self._write_crash_file(exc_value, tb_str)
            
            # Show an error message box
            error_msg = f"Er is een onverwachte fout opgetreden:\n\n{str(exc_value)}"
            if crash_file:
                error_msg += f"\n\nEen crash rapport is opgeslagen in:\n{crash_file}"
            
            messagebox.showerror("Onbekende Fout", error_msg)
        
        # Install the global exception handler
        sys.excepthook = handle_exception
    
    def _set_window_icon(self) -> None:
        """Set the window icon."""
        try:
            icon_path = self._resource_path(ICON_FILE)
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print(f"Icon set successfully: {icon_path}")
            else:
                print(f"Icon file not found: {icon_path}")
                # Try relative path as fallback
                try:
                    self.root.iconbitmap(ICON_FILE)
                    print("Icon set using relative path")
                except Exception:
                    print("Could not set window icon")
        except Exception as e:
            print(f"Could not set window icon: {e}")
    
    def _resource_path(self, relative_path: str) -> str:
        """Get absolute path to resource, works for dev and PyInstaller."""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    
    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Create main frames
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.content_frame = tk.Frame(self.root)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create control components
        self._create_connection_controls()
        self._create_display_controls()
        
        # Create content components
        self._create_student_config()
        self._create_main_content()
    
    def _create_connection_controls(self) -> None:
        """Create serial connection control widgets."""
        connection_frame = tk.LabelFrame(self.control_frame, text="Seriële Verbinding")
        connection_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X)
        
        # Port selector
        self.port_selector = ttk.Combobox(connection_frame, state='readonly', width=20)
        self.port_selector.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Control buttons
        refresh_btn = tk.Button(connection_frame, text="Poorten Verversen", 
                               command=self._refresh_ports)
        refresh_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        connect_btn = tk.Button(connection_frame, text="Verbinden", 
                               command=self._connect_to_port, bg="lightgreen")
        connect_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        disconnect_btn = tk.Button(connection_frame, text="Verbreken", 
                                  command=self._disconnect_from_port, bg="lightcoral")
        disconnect_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Status label
        self.connection_status_label = tk.Label(connection_frame, 
                                               text="Status: Niet verbonden", fg="gray")
        self.connection_status_label.pack(side=tk.LEFT, padx=10, pady=5)
    
    def _create_display_controls(self) -> None:
        """Create display control widgets."""
        log_control_frame = tk.LabelFrame(self.control_frame, text="Weergave")
        log_control_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.toggle_log_button = tk.Button(log_control_frame, text="▲ Toon Log", 
                                          command=self._toggle_log_panel, bg="lightgray")
        self.toggle_log_button.pack(padx=5, pady=5)
    
    def _create_student_config(self) -> None:
        """Create student configuration widgets."""
        student_config_frame = tk.LabelFrame(self.content_frame, 
                                            text="Leerlinglijst (Formaat: 123456:LeerlingNaam, één per regel)")
        student_config_frame.pack(fill=tk.X, pady=5)
        
        # Text entry for student numbers
        self.student_numbers_entry = scrolledtext.ScrolledText(student_config_frame, 
                                                              height=4, width=50)
        self.student_numbers_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # Update button
        student_config_buttons = tk.Frame(student_config_frame)
        student_config_buttons.pack(side=tk.RIGHT, padx=5, pady=5)
        
        update_btn = tk.Button(student_config_buttons, text="Leerlinglijst\nBijwerken", 
                              command=self._update_allowed_students, bg="lightblue")
        update_btn.pack(pady=2)
    
    def _create_main_content(self) -> None:
        """Create main content area widgets."""
        self.main_content = tk.Frame(self.content_frame)
        self.main_content.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Student status display
        self._create_student_status_display()
        
        # Activity log panel (initially hidden)
        self._create_activity_log_panel()
    
    def _create_student_status_display(self) -> None:
        """Create student status display widgets."""
        status_frame = tk.LabelFrame(self.main_content, text="Leerling Status")
        status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create scrollable canvas for student display
        self.student_canvas = tk.Canvas(status_frame)
        student_scrollbar = ttk.Scrollbar(status_frame, orient="vertical", 
                                         command=self.student_canvas.yview)
        self.student_frame = tk.Frame(self.student_canvas)
        
        self.student_frame.bind(
            "<Configure>",
            lambda e: self.student_canvas.configure(
                scrollregion=self.student_canvas.bbox("all")
            )
        )
        
        self.student_canvas.create_window((0, 0), window=self.student_frame, anchor="nw")
        self.student_canvas.configure(yscrollcommand=student_scrollbar.set)
        
        self.student_canvas.pack(side="left", fill="both", expand=True)
        student_scrollbar.pack(side="right", fill="y")
    
    def _create_activity_log_panel(self) -> None:
        """Create activity log panel widgets."""
        self.log_panel = tk.LabelFrame(self.main_content, text="Activiteitenlog")
        # Log panel is not packed initially (hidden)
        
        # Log filters
        self._create_log_filters()
        
        # Activity log text widget
        self.activity_log = scrolledtext.ScrolledText(self.log_panel, height=20, width=40, 
                                                     wrap=tk.WORD)
        self.activity_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log control buttons
        self._create_log_buttons()
    
    def _create_log_filters(self) -> None:
        """Create log filter controls."""
        log_filters_frame = tk.Frame(self.log_panel)
        log_filters_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(log_filters_frame, text="Toon:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
        
        # Create filter checkboxes
        filter_configs = [
            ('STATUS', 'Status', "#0066CC", False),
            ('ERROR', 'Fouten', "#CC0000", True),
            ('HEALTH', 'Health', "#FF6600", False),
            ('INFO', 'Info', "#000000", False)
        ]
        
        for log_type, label, color, default in filter_configs:
            self.log_filter_vars[log_type] = tk.BooleanVar(value=default)
            self.log_manager.set_filter(log_type, default)
            
            cb = tk.Checkbutton(log_filters_frame, text=label, 
                               variable=self.log_filter_vars[log_type],
                               command=lambda lt=log_type: self._filter_changed(lt),
                               fg=color)
            cb.pack(side=tk.LEFT, padx=2)
    
    def _create_log_buttons(self) -> None:
        """Create log control buttons."""
        log_buttons_frame = tk.Frame(self.log_panel)
        log_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        clear_btn = tk.Button(log_buttons_frame, text="Log Wissen", 
                             command=self._clear_activity_log)
        clear_btn.pack(side=tk.LEFT, padx=2)
        
        export_btn = tk.Button(log_buttons_frame, text="Log Exporteren", 
                              command=self._export_log)
        export_btn.pack(side=tk.LEFT, padx=2)
    
    def _handle_serial_data(self, data: str) -> None:
        """
        Handle incoming serial data.
        
        Args:
            data: Processed data from serial manager (format: "123456,G")
        """
        try:
            print(f"[GUI] Received data: {data}")
            parts = data.split(',')
            if len(parts) != 2:
                print(f"[GUI] Invalid data format: expected 2 parts, got {len(parts)}")
                return
            
            student_number = int(parts[0])
            status_code = parts[1]
            print(f"[GUI] Processing student {student_number} with status {status_code}")
            
            # Update student status
            status_info = self.student_manager.update_student_status(student_number, status_code)
            
            if status_info:
                print(f"[GUI] Status updated successfully: {status_info}")
                # Schedule GUI update in main thread
                self.root.after(0, self._refresh_student_display)
                
                # Log the status change
                student_name = self.student_manager.get_student_name(student_number)
                log_message = f"{student_name} ({student_number}): {status_info['status']}"
                self.log_manager.log(log_message, log_type="STATUS")
            else:
                print(f"[GUI] Status update ignored (no change or duplicate for student {student_number})")
        
        except Exception as e:
            error_msg = f"Error handling serial data '{data}': {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _update_connection_status(self, status: str, color: str) -> None:
        """
        Update connection status display.
        
        Args:
            status: Status text
            color: Status color
        """
        def update():
            self.connection_status_label.config(text=f"Status: {status}", fg=color)
        
        self.root.after(0, update)
    
    def _refresh_ports(self) -> None:
        """Refresh the list of available serial ports."""
        try:
            ports = self.serial_manager.get_available_ports()
            self.port_selector['values'] = ports
            print(f"Available ports: {ports}")
            self.log_manager.log(f"Available ports refreshed: {len(ports)} found", log_type="INFO")
        except Exception as e:
            error_msg = f"Error refreshing ports: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _connect_to_port(self) -> None:
        """Connect to the selected serial port."""
        try:
            selected_port = self.port_selector.get()
            if not selected_port:
                messagebox.showwarning("Waarschuwing", "Selecteer eerst een poort")
                return
            
            self.serial_manager.set_port(selected_port)
            
            if self.serial_manager.connect():
                self.log_manager.log(f"Connected to {selected_port}", log_type="INFO")
            else:
                messagebox.showerror("Verbindingsfout", f"Verbinden met {selected_port} mislukt")
        
        except Exception as e:
            error_msg = f"Error connecting to port: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
            messagebox.showerror("Fout", error_msg)
    
    def _disconnect_from_port(self) -> None:
        """Disconnect from the serial port."""
        try:
            self.serial_manager.disconnect()
            self.log_manager.log("Manually disconnected from serial port", log_type="INFO")
        except Exception as e:
            error_msg = f"Error disconnecting: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _update_allowed_students(self) -> None:
        """Update the list of allowed students."""
        try:
            student_text = self.student_numbers_entry.get("1.0", tk.END).strip()
            self.student_manager.update_allowed_students(student_text)
            self._refresh_student_display()
            
            allowed_count, active_count = self.student_manager.get_student_count()
            self.log_manager.log(f"Student list updated: {allowed_count} allowed, {active_count} active", 
                               log_type="INFO")
        
        except Exception as e:
            error_msg = f"Error updating student list: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
            messagebox.showerror("Fout", error_msg)
    
    def _refresh_student_display(self) -> None:
        """Refresh the student status display."""
        try:
            # Clear current display
            for widget in self.student_frame.winfo_children():
                widget.destroy()
            self.duration_labels.clear()
            
            # Create headers
            headers = ["Leerlingnummer", "Naam", "Status", "Tijd", "Duur", "Actie"]
            for col, header in enumerate(headers):
                tk.Label(self.student_frame, text=header, 
                        font=("Arial", 10, "bold")).grid(row=0, column=col, padx=5, pady=2, sticky='w')
            
            # Get sorted students
            sorted_students = self.student_manager.get_sorted_students()
            
            # Display students
            for row, (student_number, info) in enumerate(sorted_students, start=1):
                self._create_student_row(row, student_number, info)
                
        except Exception as e:
            error_msg = f"Error refreshing student display: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _create_student_row(self, row: int, student_number: int, info: Dict) -> None:
        """
        Create a single student row in the display.
        
        Args:
            row: Row number in the grid
            student_number: Student number
            info: Student status information
        """
        try:
            # Student number
            tk.Label(self.student_frame, text=str(student_number), 
                    font=("Arial", 9)).grid(row=row, column=0, padx=5, pady=1, sticky='w')
            
            # Student name
            student_name = self.student_manager.get_student_name(student_number)
            tk.Label(self.student_frame, text=student_name, 
                    font=("Arial", 9)).grid(row=row, column=1, padx=5, pady=1, sticky='w')
            
            # Status with color
            status_label = tk.Label(self.student_frame, text=info['status'], 
                                   fg=info['color'], font=("Arial", 9, "bold"))
            status_label.grid(row=row, column=2, padx=5, pady=1, sticky='w')
            
            # Time
            tk.Label(self.student_frame, text=info['time'], 
                    font=("Arial", 8)).grid(row=row, column=3, padx=5, pady=1, sticky='w')
            
            # Duration (for V and R statuses)
            duration_result = self.student_manager.calculate_status_duration(student_number)
            if duration_result:
                duration_text, duration_color = duration_result
                duration_label = tk.Label(self.student_frame, text=duration_text, 
                                         font=("Arial", 8, "bold"), fg=duration_color)
                duration_label.grid(row=row, column=4, padx=5, pady=1, sticky='w')
                
                # Store reference for real-time updates
                self.duration_labels[student_number] = duration_label
            
            # Action button (for V and R statuses)
            if info['code'] in ['V', 'R']:
                action_btn = tk.Button(self.student_frame, text="Oplossen",
                                      command=lambda sn=student_number: self._resolve_student_issue(sn),
                                      bg="lightblue", font=("Arial", 8))
                action_btn.grid(row=row, column=5, padx=5, pady=1, sticky='w')
        
        except Exception as e:
            error_msg = f"Error creating student row for {student_number}: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _resolve_student_issue(self, student_number: int) -> None:
        """
        Resolve a student's issue.
        
        Args:
            student_number: Student number
        """
        try:
            if self.student_manager.resolve_student_issue(student_number):
                self._refresh_student_display()
                
                student_name = self.student_manager.get_student_name(student_number)
                log_message = f"{student_name} ({student_number}): Problem resolved by teacher"
                self.log_manager.log(log_message, log_type="STATUS")
        
        except Exception as e:
            error_msg = f"Error resolving student issue: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _toggle_log_panel(self) -> None:
        """Toggle the visibility of the log panel."""
        try:
            if self.log_panel.winfo_viewable():
                self.log_panel.pack_forget()
                self.toggle_log_button.config(text="▲ Toon Log")
            else:
                self.log_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
                self.toggle_log_button.config(text="▼ Verberg Log")
                self._update_activity_log_display()
        except Exception as e:
            error_msg = f"Error toggling log panel: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
    
    def _filter_changed(self, log_type: str) -> None:
        """
        Handle log filter change.
        
        Args:
            log_type: Log type that was changed
        """
        enabled = self.log_filter_vars[log_type].get()
        self.log_manager.set_filter(log_type, enabled)
    
    def _update_activity_log_display(self) -> None:
        """Update the activity log display."""
        try:
            if not hasattr(self, 'activity_log') or not self.root.winfo_exists():
                return
            
            # Get filtered entries
            filtered_entries = self.log_manager.get_filtered_entries()
            
            # Clear current content
            self.activity_log.delete(1.0, tk.END)
            
            # Add filtered entries
            for entry in filtered_entries:
                log_message = f"[{entry['time']}] {entry['type']}: {entry['message']}\n"
                self.activity_log.insert(tk.END, log_message)
                
                # Color the line
                start_line = self.activity_log.index(tk.END).split('.')[0]
                line_num = int(start_line) - 1
                self.activity_log.tag_add(f"color_{line_num}", f"{line_num}.0", f"{line_num}.end")
                self.activity_log.tag_config(f"color_{line_num}", foreground=entry['color'])
            
            # Scroll to bottom
            self.activity_log.see(tk.END)
            
        except Exception as e:
            print(f"Error updating log display: {e}")
    
    def _clear_activity_log(self) -> None:
        """Clear the activity log."""
        try:
            self.log_manager.clear_log()
        except Exception as e:
            error_msg = f"Error clearing log: {e}"
            print(error_msg)
            messagebox.showerror("Fout", error_msg)
    
    def _export_log(self) -> None:
        """Export the activity log to a file."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Tekstbestanden", "*.txt"), ("Alle bestanden", "*.*")]
            )
            
            if filename:
                if self.log_manager.export_log(filename):
                    messagebox.showinfo("Succes", f"Log geëxporteerd naar {filename}")
                else:
                    messagebox.showerror("Fout", "Log exporteren mislukt")
        
        except Exception as e:
            error_msg = f"Error exporting log: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
            messagebox.showerror("Fout", error_msg)
    
    def _update_duration_labels(self) -> None:
        """Update duration labels for active statuses."""
        try:
            has_active_statuses = False
            
            for student_number in list(self.duration_labels.keys()):
                if student_number in self.duration_labels:
                    duration_label = self.duration_labels[student_number]
                    
                    try:
                        # Check if label still exists
                        if duration_label.winfo_exists():
                            duration_result = self.student_manager.calculate_status_duration(student_number)
                            if duration_result:
                                duration_text, duration_color = duration_result
                                duration_label.config(text=duration_text, fg=duration_color)
                                has_active_statuses = True
                            else:
                                # Status no longer active, remove from tracking
                                del self.duration_labels[student_number]
                        else:
                            # Label was destroyed, remove from tracking
                            del self.duration_labels[student_number]
                    except tk.TclError:
                        # Label was destroyed, remove from tracking
                        del self.duration_labels[student_number]
            
            # Schedule next update
            if has_active_statuses:
                self.root.after(DURATION_UPDATE_INTERVAL, self._update_duration_labels)
            else:
                # No active statuses, check again in 5 seconds
                self.root.after(5000, self._update_duration_labels)
                
        except Exception as e:
            error_msg = f"Error updating duration labels: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
            # Schedule next update despite error
            self.root.after(DURATION_UPDATE_INTERVAL, self._update_duration_labels)
    
    def _periodic_refresh(self) -> None:
        """Periodic refresh of the student display."""
        try:
            # Full refresh less frequently (structural changes only)
            self.root.after(PERIODIC_REFRESH_INTERVAL, self._periodic_refresh)
        except Exception as e:
            error_msg = f"Error in periodic refresh: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
            # Schedule next refresh despite error
            self.root.after(PERIODIC_REFRESH_INTERVAL, self._periodic_refresh)
    
    def _start_periodic_updates(self) -> None:
        """Start periodic update timers."""
        # Start duration updates
        self.root.after(DURATION_UPDATE_INTERVAL, self._update_duration_labels)
        
        # Start periodic refresh
        self.root.after(PERIODIC_REFRESH_INTERVAL, self._periodic_refresh)
    
    def _initialize_example_data(self) -> None:
        """Initialize with example student data."""
        self.student_numbers_entry.insert("1.0", "123456:Voornaam Achternaam")
        self.student_manager.update_allowed_students(self.student_numbers_entry.get("1.0", tk.END).strip())
        self._refresh_ports()
        self._refresh_student_display()
    
    # Test crash functionality has been removed
    


    def run(self) -> None:
        """Start the GUI application."""
        try:
            self.log_manager.log("Qube Monitor started", log_type="INFO")
            self.root.mainloop()
        except Exception as e:
            error_msg = f"Error running application: {e}"
            print(error_msg)
            self.log_manager.log(error_msg, log_type="ERROR")
        finally:
            # Clean shutdown
            try:
                self.serial_manager.disconnect()
            except Exception:
                pass

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import threading
import time
import serial.tools.list_ports

def process_serial_data():
    global ser
    while True:
        if ser is None:
            time.sleep(0.1)
            continue
        try:
            if not ser.is_open:
                time.sleep(0.1)
                continue
                
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            print(f"Received: {line}")
            
            # Handle multiple possible formats and prevent crashes
            try:
                parts = line.split(',')
                
                # Check for minimum parts (should be at least 3)
                if len(parts) < 3:
                    print(f"Invalid message format - not enough parts: {line}")
                    continue

                role = parts[0].strip()
                student_number_str = parts[1].strip()
                status_code = parts[2].strip()

                # Handle new format starting with "L" (L, LRL, etc.)
                if not role.startswith('L'):
                    print(f"Ignoring message with role: {role}")
                    continue

                # Validate and parse student number
                try:
                    student_number = int(student_number_str)
                    if student_number < 100000 or student_number > 999999:
                        print(f"Invalid student number range: {student_number}")
                        continue
                except ValueError:
                    print(f"Invalid student number format: {student_number_str}")
                    continue

                # Check if student is in allowed list
                if student_number not in allowed_students:
                    print(f"Student {student_number} not in allowed list, ignoring")
                    continue

                # Validate status code
                if status_code not in ['G', 'V', 'R']:
                    print(f"Unknown status code: {status_code}, keeping previous status")
                    continue

                # Process the status update safely
                try:
                    root.after(0, update_student_status, student_number, status_code)
                except Exception as e:
                    print(f"Error scheduling GUI update: {e}")

            except Exception as e:
                print(f"Error parsing message '{line}': {e}")
                continue

        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            # Try to reconnect after a delay
            time.sleep(1)
            try:
                reconnect_serial()
            except Exception as reconnect_error:
                print(f"Reconnection failed: {reconnect_error}")
                time.sleep(5)  # Wait longer before next attempt
        except UnicodeDecodeError as e:
            print(f"Unicode decode error: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error in serial processing: {e}")
            time.sleep(0.1)  # Small delay to prevent tight error loops

def reconnect_serial():
    global ser
    try:
        if ser:
            try:
                ser.close()
            except Exception as e:
                print(f"Error closing serial port: {e}")
            ser = None
        
        # Try to reconnect to the last selected port
        selected_port = port_selector.get()
        if selected_port:
            try:
                ser = serial.Serial(selected_port, 115200, timeout=1)
                print(f"Reconnected to {selected_port}")
                root.after(0, update_connection_status, "Connected", "green")
            except Exception as e:
                print(f"Failed to reconnect: {e}")
                root.after(0, update_connection_status, "Disconnected", "red")
        else:
            print("No port selected for reconnection")
            root.after(0, update_connection_status, "No Port Selected", "red")
    except Exception as e:
        print(f"Error in reconnect_serial: {e}")
        root.after(0, update_connection_status, "Reconnection Failed", "red")

def update_student_status(student_number, status_code):
    """Update the student's status in the GUI"""
    try:
        current_time = time.strftime("%H:%M:%S")
        
        # Map status codes to readable text and colors
        status_map = {
            'G': ('Available', 'green'),
            'V': ('Question', 'orange'), 
            'R': ('Help Needed', 'red')
        }
        
        status_info = status_map.get(status_code)
        if not status_info:
            print(f"Unknown status code: {status_code}, keeping previous status")
            return
            
        status_text, color = status_info
        
        # Check if this is a duplicate message (same status within 2 seconds)
        if student_number in student_statuses:
            prev_status = student_statuses[student_number]
            if (prev_status.get('code') == status_code and 
                time.time() - prev_status.get('last_update', 0) < 2):
                print(f"Duplicate message for student {student_number}, ignoring")
                return
        
        # Update or add student in the display
        student_statuses[student_number] = {
            'status': status_text,
            'color': color,
            'time': current_time,
            'code': status_code,
            'last_update': time.time()
        }
        
        # Refresh the display safely
        try:
            refresh_student_display()
        except Exception as e:
            print(f"Error refreshing display: {e}")
        
        # Get student name for logging and notifications
        student_name = student_names.get(student_number, f"Student {student_number}")
        
        # Add to activity log safely
        try:
            log_message = f"[{current_time}] {student_name} ({student_number}): {status_text}"
            activity_log.insert(tk.END, log_message)
            activity_log.see(tk.END)  # Auto-scroll to bottom
        except Exception as e:
            print(f"Error updating activity log: {e}")
        
        # Show notification for questions or help requests
        if status_code in ['V', 'R']:
            try:
                notification_text = f"{student_name} has a {'question' if status_code == 'V' else 'help request'}!"
                show_notification(notification_text)
            except Exception as e:
                print(f"Error showing notification: {e}")
                
    except Exception as e:
        print(f"Error in update_student_status: {e}")

def refresh_student_display():
    """Refresh the student status display"""
    try:
        # Clear current display
        for widget in student_frame.winfo_children():
            widget.destroy()
        
        # Sort students by number
        sorted_students = sorted(student_statuses.items())
        
        # Create headers
        tk.Label(student_frame, text="Student #", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Name", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Status", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Time", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Action", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=5, pady=2, sticky='w')
        
        row = 1
        for student_number, info in sorted_students:
            try:
                # Student number
                tk.Label(student_frame, text=str(student_number), font=("Arial", 9)).grid(row=row, column=0, padx=5, pady=1, sticky='w')
                
                # Student name
                student_name = student_names.get(student_number, f"Student {student_number}")
                tk.Label(student_frame, text=student_name, font=("Arial", 9)).grid(row=row, column=1, padx=5, pady=1, sticky='w')
                
                # Status with color
                status_label = tk.Label(student_frame, text=info['status'], fg=info['color'], font=("Arial", 9, "bold"))
                status_label.grid(row=row, column=2, padx=5, pady=1, sticky='w')
                
                # Time
                tk.Label(student_frame, text=info['time'], font=("Arial", 8)).grid(row=row, column=3, padx=5, pady=1, sticky='w')
                
                # Action button for questions/help
                if info['code'] in ['V', 'R']:
                    action_btn = tk.Button(student_frame, text="Resolve", 
                                         command=lambda sn=student_number: resolve_student_issue(sn),
                                         bg="lightblue", font=("Arial", 8))
                    action_btn.grid(row=row, column=4, padx=5, pady=1, sticky='w')
                
                row += 1
            except Exception as e:
                print(f"Error creating display row for student {student_number}: {e}")
                continue
                
    except Exception as e:
        print(f"Error in refresh_student_display: {e}")

def resolve_student_issue(student_number):
    """Mark a student's issue as resolved"""
    try:
        if student_number in student_statuses:
            student_statuses[student_number]['status'] = 'Resolved'
            student_statuses[student_number]['color'] = 'blue'
            student_statuses[student_number]['code'] = 'G'
            student_statuses[student_number]['last_update'] = time.time()
            refresh_student_display()
            
            current_time = time.strftime("%H:%M:%S")
            student_name = student_names.get(student_number, f"Student {student_number}")
            log_message = f"[{current_time}] {student_name} ({student_number}): Issue resolved by teacher"
            activity_log.insert(tk.END, log_message)
            activity_log.see(tk.END)
    except Exception as e:
        print(f"Error resolving student issue: {e}")

def show_notification(message):
    """Show a notification popup"""
    notification_window = tk.Toplevel(root)
    notification_window.title("Student Notification")
    notification_window.geometry("300x100")
    notification_window.attributes('-topmost', True)
    
    tk.Label(notification_window, text=message, font=("Arial", 11), wraplength=280).pack(pady=20)
    tk.Button(notification_window, text="OK", command=notification_window.destroy).pack()
    
    # Auto-close after 5 seconds
    notification_window.after(5000, notification_window.destroy)

def update_allowed_students():
    """Update the list of allowed student numbers and names"""
    global allowed_students, student_names
    try:
        # Get text from entry and parse student numbers and names
        student_text = student_numbers_entry.get("1.0", tk.END).strip()
        if not student_text:
            allowed_students = set()
            student_names = {}
            return
            
        # Parse numbers and names (format: 123456:StudentName)
        student_numbers = []
        new_student_names = {}
        
        for line in student_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if ':' in line:
                # Format: 123456:StudentName
                try:
                    num_str, name = line.split(':', 1)
                    num = int(num_str.strip())
                    name = name.strip()
                    
                    if 100000 <= num <= 999999:  # 6-digit numbers
                        student_numbers.append(num)
                        new_student_names[num] = name
                    else:
                        print(f"Invalid student number (not 6 digits): {num}")
                except ValueError:
                    print(f"Invalid student entry format: {line}")
            else:
                # Just a number without name
                try:
                    num = int(line)
                    if 100000 <= num <= 999999:  # 6-digit numbers
                        student_numbers.append(num)
                        new_student_names[num] = f"Student {num}"
                    else:
                        print(f"Invalid student number (not 6 digits): {num}")
                except ValueError:
                    print(f"Invalid student number format: {line}")
        
        allowed_students = set(student_numbers)
        student_names = new_student_names
        print(f"Updated allowed students: {sorted(allowed_students)}")
        print(f"Student names: {student_names}")
        
        # Clear student statuses for students no longer in the list
        students_to_remove = []
        for student_num in student_statuses:
            if student_num not in allowed_students:
                students_to_remove.append(student_num)
        
        for student_num in students_to_remove:
            del student_statuses[student_num]
        
        refresh_student_display()
        
    except Exception as e:
        messagebox.showerror("Error", f"Error updating student list: {e}")

def refresh_ports():
    """Refresh the list of available serial ports"""
    ports = serial.tools.list_ports.comports()
    port_list = [port.device for port in ports]
    port_selector['values'] = port_list
    print(f"Available ports: {port_list}")

def connect_to_port():
    """Connect to the selected serial port"""
    global ser
    selected_port = port_selector.get()
    if not selected_port:
        messagebox.showwarning("Warning", "Please select a port first")
        return
        
    if ser is not None:
        try:
            ser.close()
        except:
            pass
    
    try:
        ser = serial.Serial(selected_port, 115200, timeout=1)
        print(f"Connected to {selected_port}")
        update_connection_status("Connected", "green")
    except Exception as e:
        print(f"Error connecting to port {selected_port}: {e}")
        messagebox.showerror("Connection Error", f"Failed to connect to {selected_port}: {e}")
        ser = None
        update_connection_status("Disconnected", "red")

def disconnect_from_port():
    """Disconnect from the serial port"""
    global ser
    if ser is not None:
        try:
            ser.close()
            ser = None
            print("Disconnected from serial port")
            update_connection_status("Disconnected", "gray")
        except Exception as e:
            print(f"Error disconnecting: {e}")

def update_connection_status(status, color):
    """Update the connection status display"""
    connection_status_label.config(text=f"Status: {status}", fg=color)

def clear_activity_log():
    """Clear the activity log"""
    activity_log.delete(1.0, tk.END)

def export_log():
    """Export the activity log to a file"""
    from tkinter import filedialog
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(activity_log.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Log exported to {filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export log: {e}")

# Initialize global variables
allowed_students = set()
student_names = {}  # Dictionary to store student names
student_statuses = {}
ser = None

# Set up the tkinter GUI
root = tk.Tk()
root.title("Student Monitor - Teacher Dashboard")
root.geometry('1000x700')

# Create main frames
control_frame = tk.Frame(root)
control_frame.pack(fill=tk.X, padx=10, pady=5)

content_frame = tk.Frame(root)
content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# Connection controls
connection_frame = tk.LabelFrame(control_frame, text="Serial Connection")
connection_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X)

port_selector = ttk.Combobox(connection_frame, state='readonly', width=20)
port_selector.pack(side=tk.LEFT, padx=5, pady=5)

refresh_ports_button = tk.Button(connection_frame, text="Refresh Ports", command=refresh_ports)
refresh_ports_button.pack(side=tk.LEFT, padx=2, pady=5)

connect_button = tk.Button(connection_frame, text="Connect", command=connect_to_port, bg="lightgreen")
connect_button.pack(side=tk.LEFT, padx=2, pady=5)

disconnect_button = tk.Button(connection_frame, text="Disconnect", command=disconnect_from_port, bg="lightcoral")
disconnect_button.pack(side=tk.LEFT, padx=2, pady=5)

connection_status_label = tk.Label(connection_frame, text="Status: Disconnected", fg="gray")
connection_status_label.pack(side=tk.LEFT, padx=10, pady=5)

# Student numbers configuration
student_config_frame = tk.LabelFrame(content_frame, text="Student List (Format: 123456:StudentName, one per line)")
student_config_frame.pack(fill=tk.X, pady=5)

student_numbers_entry = scrolledtext.ScrolledText(student_config_frame, height=4, width=50)
student_numbers_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

student_config_buttons = tk.Frame(student_config_frame)
student_config_buttons.pack(side=tk.RIGHT, padx=5, pady=5)

update_students_button = tk.Button(student_config_buttons, text="Update\nStudent List", 
                                 command=update_allowed_students, bg="lightblue")
update_students_button.pack(pady=2)

# Main content area
main_content = tk.Frame(content_frame)
main_content.pack(fill=tk.BOTH, expand=True, pady=5)

# Student status display
status_frame = tk.LabelFrame(main_content, text="Student Status")
status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

student_canvas = tk.Canvas(status_frame)
student_scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=student_canvas.yview)
student_frame = tk.Frame(student_canvas)

student_frame.bind(
    "<Configure>",
    lambda e: student_canvas.configure(scrollregion=student_canvas.bbox("all"))
)

student_canvas.create_window((0, 0), window=student_frame, anchor="nw")
student_canvas.configure(yscrollcommand=student_scrollbar.set)

student_canvas.pack(side="left", fill="both", expand=True)
student_scrollbar.pack(side="right", fill="y")

# Activity log
log_frame = tk.LabelFrame(main_content, text="Activity Log")
log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

activity_log = scrolledtext.ScrolledText(log_frame, height=20, width=40)
activity_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

log_buttons_frame = tk.Frame(log_frame)
log_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

clear_log_button = tk.Button(log_buttons_frame, text="Clear Log", command=clear_activity_log)
clear_log_button.pack(side=tk.LEFT, padx=2)

export_log_button = tk.Button(log_buttons_frame, text="Export Log", command=export_log)
export_log_button.pack(side=tk.LEFT, padx=2)

# Start the serial processing in a separate thread
thread = threading.Thread(target=process_serial_data)
thread.daemon = True
thread.start()

# Initialize
refresh_ports()
refresh_student_display()

# Add some example student numbers
student_numbers_entry.insert("1.0", "123456:Alice Johnson\n234567:Bob Smith\n345678:Carol Davis")

root.mainloop()
"""
Serial communication module for Qube Monitor application.
Handles all serial port operations including connection, data processing, and health monitoring.
"""

import serial
import serial.tools.list_ports
import threading
import time
import queue
from typing import Optional, Callable, List, Tuple
from support.config import *


class SerialManager:
    """Manages serial communication with proper error handling and connection management."""
    
    def __init__(self, data_callback: Callable[[str], None], 
                 status_callback: Callable[[str, str], None]):
        """
        Initialize SerialManager.
        
        Args:
            data_callback: Function to call when data is received
            status_callback: Function to call when connection status changes
        """
        self.serial_port: Optional[serial.Serial] = None
        self.data_callback = data_callback
        self.status_callback = status_callback
        
        # Threading and synchronization
        self.data_thread: Optional[threading.Thread] = None
        self.health_thread: Optional[threading.Thread] = None
        self.data_queue = queue.Queue()
        self.running = False
        self.manual_disconnect = False
        
        # Connection monitoring
        self.last_heartbeat = time.time()
        self.last_reconnect_time = time.time()
        self.last_connection_test = time.time()
        
        # Thread-safe port selection
        self._selected_port = None
        self._port_lock = threading.Lock()
    
    def get_available_ports(self) -> List[str]:
        """Get list of available serial ports."""
        try:
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except Exception as e:
            print(f"Error getting ports: {e}")
            return []
    
    def set_port(self, port: str) -> None:
        """Thread-safe port selection."""
        with self._port_lock:
            self._selected_port = port
    
    def get_port(self) -> Optional[str]:
        """Thread-safe port retrieval."""
        with self._port_lock:
            return self._selected_port
    
    def connect(self) -> bool:
        """
        Connect to the selected serial port.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        port = self.get_port()
        if not port:
            self.status_callback("Geen poort geselecteerd", "red")
            return False
        
        try:
            # Close existing connection
            self.disconnect()
            
            # Create new connection
            self.serial_port = serial.Serial(port, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
            
            if not self.serial_port or not self.serial_port.is_open:
                raise Exception("Failed to open serial port")
            
            self.manual_disconnect = False
            self.last_heartbeat = time.time()
            self.last_reconnect_time = time.time()
            self.last_connection_test = time.time()
            
            # Start threads
            self.running = True
            self._start_threads()
            
            self.status_callback("Verbonden", "green")
            print(f"Connected to {port}")
            return True
            
        except Exception as e:
            self.serial_port = None
            self.status_callback(f"Verbinding mislukt: {e}", "red")
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from serial port."""
        self.running = False
        self.manual_disconnect = True
        
        # Wait for threads to finish
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2.0)
        
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        # Close serial port
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception as e:
                print(f"Error closing serial port: {e}")
            finally:
                self.serial_port = None
        
        self.status_callback("Niet verbonden", "gray")
        print("Disconnected from serial port")
    
    def _start_threads(self) -> None:
        """Start data processing and health monitoring threads."""
        # Start data processing thread
        self.data_thread = threading.Thread(target=self._data_processing_thread, daemon=True)
        self.data_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._health_monitoring_thread, daemon=True)
        self.health_thread.start()
    
    def _data_processing_thread(self) -> None:
        """Thread for processing incoming serial data."""
        print("Data processing thread started")
        
        while self.running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    time.sleep(SERIAL_THREAD_SLEEP)
                    continue
                
                # Non-blocking read with timeout
                if self.serial_port.in_waiting > 0:
                    try:
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.last_heartbeat = time.time()
                            # Put data in queue for thread-safe processing
                            self.data_queue.put(line)
                            # Process data immediately to avoid blocking
                            self._process_queued_data()
                    except (UnicodeDecodeError, OSError, serial.SerialException) as e:
                        print(f"Error reading serial data: {e}")
                        time.sleep(SERIAL_THREAD_SLEEP)
                else:
                    time.sleep(SERIAL_THREAD_SLEEP)
                    
            except Exception as e:
                print(f"Unexpected error in data processing: {e}")
                time.sleep(SERIAL_THREAD_SLEEP)
        
        print("Data processing thread stopped")
    
    def _process_queued_data(self) -> None:
        """Process all queued data messages."""
        while not self.data_queue.empty():
            try:
                line = self.data_queue.get_nowait()
                self._process_serial_message(line)
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error processing queued data: {e}")
    
    def _process_serial_message(self, line: str) -> None:
        """
        Process a single serial message.
        
        Args:
            line: Raw message from serial port
        """
        try:
            print(f"Received: {line}")
            
            # Parse message format: L,123456,G
            parts = line.split(',')
            
            if len(parts) < 3:
                print(f"Invalid message format: {line}")
                return
            
            role = parts[0].strip()
            student_number_str = parts[1].strip()
            status_code = parts[2].strip()
            
            # Validate role (must start with 'L')
            if not role.startswith('L'):
                print(f"Invalid role: {role}")
                return
            
            # Validate student number
            try:
                student_number = int(student_number_str)
                if not (MIN_STUDENT_NUMBER <= student_number <= MAX_STUDENT_NUMBER):
                    print(f"Invalid student number range: {student_number}")
                    return
            except ValueError:
                print(f"Invalid student number format: {student_number_str}")
                return
            
            # Validate status code
            if status_code not in STATUS_MAP:
                print(f"Invalid status code: {status_code}")
                return
            
            
            # Call data callback with processed data
            self.data_callback(f"{student_number},{status_code}")
            
        except Exception as e:
            print(f"Error processing serial message '{line}': {e}")
    
    def _health_monitoring_thread(self) -> None:
        """Thread for monitoring connection health and automatic reconnection."""
        print("Health monitoring thread started")
        
        while self.running:
            try:
                if self.manual_disconnect:
                    time.sleep(10)  # Check every 10 seconds during manual disconnect
                    continue
                
                current_time = time.time()
                
                # Force reconnect every 3 minutes regardless of status
                if current_time - self.last_reconnect_time > SERIAL_RECONNECT_INTERVAL:
                    print("Forced reconnection due to time interval")
                    self._attempt_reconnection()
                    continue
                
                # Check if connection is lost
                if not self.serial_port or not self.serial_port.is_open:
                    print("Connection lost, attempting reconnection")
                    self._attempt_reconnection()
                    continue
                
                # Test connection every minute
                if current_time - self.last_connection_test > 60:
                    if not self._test_connection():
                        print("Connection test failed, attempting reconnection")
                        self._attempt_reconnection()
                        continue
                    self.last_connection_test = current_time
                
                # Check heartbeat
                if current_time - self.last_heartbeat > SERIAL_HEARTBEAT_RECONNECT:
                    print(f"No heartbeat for {current_time - self.last_heartbeat:.0f} seconds, reconnecting")
                    self._attempt_reconnection()
                    continue
                elif current_time - self.last_heartbeat > SERIAL_HEARTBEAT_TIMEOUT:
                    print(f"Heartbeat warning: {current_time - self.last_heartbeat:.0f} seconds since last message")
                
                time.sleep(10)  # Health check every 10 seconds
                
            except Exception as e:
                print(f"Error in health monitoring: {e}")
                time.sleep(10)
        
        print("Health monitoring thread stopped")
    
    def _attempt_reconnection(self) -> None:
        """Attempt to reconnect to the serial port."""
        try:
            port = self.get_port()
            if not port:
                return
            
            print(f"Attempting reconnection to {port}")
            
            # Close current connection
            if self.serial_port:
                try:
                    self.serial_port.close()
                except:
                    pass
                self.serial_port = None
            
            # Try to reconnect
            self.serial_port = serial.Serial(port, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
            
            if self.serial_port and self.serial_port.is_open:
                self.last_heartbeat = time.time()
                self.last_reconnect_time = time.time()
                self.last_connection_test = time.time()
                print(f"Reconnection successful to {port}")
                self.status_callback("Herverbonden", "green")
            else:
                raise Exception("Failed to open port after reconnection attempt")
                
        except Exception as e:
            print(f"Reconnection failed: {e}")
            self.serial_port = None
            self.status_callback("Herverbinding mislukt", "red")
    
    def _test_connection(self) -> bool:
        """
        Test the serial connection.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            if not self.serial_port or not self.serial_port.is_open:
                return False
            
            # Check if port is still available in system
            available_ports = self.get_available_ports()
            current_port = self.get_port()
            
            if current_port not in available_ports:
                print(f"Port {current_port} no longer available")
                return False
            
            # Try a simple write operation to test communication
            try:
                self.serial_port.write(b"HEALTH_CHECK\n")
                self.serial_port.flush()
            except (OSError, serial.SerialException):
                return False
            
            return True
            
        except Exception as e:
            print(f"Connection test error: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if currently connected to a serial port."""
        return (self.serial_port is not None and 
                hasattr(self.serial_port, 'is_open') and 
                self.serial_port.is_open)
    
    def inject_simulated_data(self, data: str) -> None:
        """
        Inject simulated data directly into the processing pipeline.
        This allows the radio simulator to send data directly to the serial manager
        without going through the physical serial port.
        
        Args:
            data: The simulated data message to process
        """
        try:
            print(f"[SIMULATED] Received: {data}")
            self.last_heartbeat = time.time()  # Update heartbeat for simulated data
            self._process_serial_message(data)
        except Exception as e:
            print(f"Error processing simulated data '{data}': {e}")

    def get_connection_info(self) -> Tuple[Optional[str], bool]:
        """
        Get current connection information.
        
        Returns:
            Tuple of (port_name, is_connected)
        """
        port = self.get_port()
        connected = self.is_connected()
        return port, connected

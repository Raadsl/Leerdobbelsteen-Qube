import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import threading
import time
import serial.tools.list_ports
import sys
import os

def log_to_activity(message, is_error=False, log_type="INFO"):
    """Voeg een bericht toe aan het activiteitenlog met categorisatie
    
    Args:
        message: Het te loggen bericht
        is_error: Of het een foutbericht is (voor backwards compatibility)
        log_type: Type log - "STATUS", "ERROR", "HEALTH", "INFO"
    """
    try:
        # Backwards compatibility: als is_error=True, gebruik ERROR type
        if is_error:
            log_type = "ERROR"
            
        current_time = time.strftime("%H:%M:%S")
        
        # Kleur mapping voor verschillende logtypen
        color_map = {
            "STATUS": "#0066CC",  # Blauw voor statuswijzigingen
            "ERROR": "#CC0000",   # Rood voor fouten
            "HEALTH": "#FF6600",  # Oranje voor gezondheidscontroles
            "INFO": "#000000"     # Zwart voor algemene informatie
        }
        
        # Voeg bericht toe aan de lijst voor filtering
        log_entry = {
            'time': current_time,
            'type': log_type,
            'message': message,
            'color': color_map.get(log_type, "#000000")
        }
        
        # Voeg toe aan globale log lijst (voor filtering)
        if 'activity_log_entries' not in globals():
            global activity_log_entries
            activity_log_entries = []
        
        activity_log_entries.append(log_entry)
        
        # Houd log beperkt tot laatste 1000 entries
        if len(activity_log_entries) > 1000:
            activity_log_entries = activity_log_entries[-1000:]
        
        # Update de weergave als het log paneel zichtbaar is
        root.after(0, lambda: update_activity_log_display())
        
    except Exception as e:
        print(f"Fout bij toevoegen aan activiteitenlog: {e}")

def update_activity_log_display():
    """Update de weergave van het activiteitenlog gebaseerd op filters"""
    try:
        if 'activity_log' not in globals() or not hasattr(root, 'winfo_exists') or not root.winfo_exists():
            return
            
        # Controleer welke logtypen getoond moeten worden
        show_status = log_filter_vars['STATUS'].get()
        show_errors = log_filter_vars['ERROR'].get()
        show_health = log_filter_vars['HEALTH'].get()
        show_info = log_filter_vars['INFO'].get()
        
        # Filter entries
        filtered_entries = []
        for entry in activity_log_entries:
            if ((entry['type'] == 'STATUS' and show_status) or
                (entry['type'] == 'ERROR' and show_errors) or
                (entry['type'] == 'HEALTH' and show_health) or
                (entry['type'] == 'INFO' and show_info)):
                filtered_entries.append(entry)
        
        # Wis huidige inhoud
        activity_log.delete(1.0, tk.END)
        
        # Voeg gefilterde entries toe
        for entry in filtered_entries[-200:]:  # Toon laatste 200 entries
            log_message = f"[{entry['time']}] {entry['type']}: {entry['message']}\n"
            activity_log.insert(tk.END, log_message)
            
            # Kleur de regel
            start_line = activity_log.index(tk.END).split('.')[0]
            line_num = int(start_line) - 1
            activity_log.tag_add(f"color_{line_num}", f"{line_num}.0", f"{line_num}.end")
            activity_log.tag_config(f"color_{line_num}", foreground=entry['color'])
        
        # Scroll naar beneden
        activity_log.see(tk.END)
        
    except Exception as e:
        print(f"Fout bij updaten logweergave: {e}")

def clear_activity_log():
    """Wis het activiteitenlog"""
    try:
        global activity_log_entries
        activity_log_entries = []
        activity_log.delete(1.0, tk.END)
        log_to_activity("Activiteitenlog gewist", log_type="INFO")
    except Exception as e:
        print(f"Fout bij wissen log: {e}")

def export_log():
    """Exporteer het activiteitenlog naar een bestand"""
    from tkinter import filedialog
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Tekstbestanden", "*.txt"), ("Alle bestanden", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Qube Monitor Log Export - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                
                for entry in activity_log_entries:
                    f.write(f"[{entry['time']}] {entry['type']}: {entry['message']}\n")
                    
            messagebox.showinfo("Succes", f"Log geëxporteerd naar {filename}")
            log_to_activity(f"Log geëxporteerd naar {filename}", log_type="INFO")
    except Exception as e:
        messagebox.showerror("Fout", f"Log exporteren mislukt: {e}")
        log_to_activity(f"Log exporteren mislukt: {e}", is_error=True)

def toggle_log_panel():
    """Schakel de zichtbaarheid van het log paneel"""
    try:
        if log_panel.winfo_viewable():
            log_panel.pack_forget()
            toggle_log_button.config(text="▲ Toon Log")
        else:
            log_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            toggle_log_button.config(text="▼ Verberg Log")
            update_activity_log_display()
    except Exception as e:
        print(f"Fout bij schakelen log paneel: {e}")

def process_serial_data():
    global ser, last_heartbeat
    while True:
        if ser is None:
            time.sleep(0.1)
            continue
        try:
            # Extra null check and connection validation
            if ser is None or not hasattr(ser, 'is_open'):
                time.sleep(0.1)
                continue
                
            if not ser.is_open:
                time.sleep(0.1)
                continue
                
            # Safe readline with additional error handling
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
            except (AttributeError, OSError) as read_error:
                error_msg = f"Fout bij lezen van seriële poort: {read_error}"
                print(error_msg)
                log_to_activity(error_msg, is_error=True)
                # Reset connection on read error
                ser = None
                time.sleep(1)
                continue
                
            if not line:
                continue

            print(f"Ontvangen: {line}")
            last_heartbeat = time.time()  # Update heartbeat op elk ontvangen bericht
            
            # Behandel meerdere mogelijke formaten en voorkom crashes
            try:
                parts = line.split(',')
                
                # Controleer op minimum aantal delen (moet minimaal 3 zijn)
                if len(parts) < 3:
                    error_msg = f"Ongeldig berichtformaat - niet genoeg delen: {line}"
                    print(error_msg)
                    log_to_activity(error_msg, is_error=True)
                    continue

                role = parts[0].strip()
                student_number_str = parts[1].strip()
                status_code = parts[2].strip()

                # Behandel nieuw formaat dat begint met "L" (L, LRL, etc.)
                if not role.startswith('L'):
                    error_msg = f"Bericht met rol genegeerd: {role}"
                    print(error_msg)
                    log_to_activity(error_msg, is_error=True)
                    continue

                # Valideer en parseer leerlingnummer
                try:
                    student_number = int(student_number_str)
                    if student_number < 100000 or student_number > 999999:
                        error_msg = f"Ongeldig leerlingnummer bereik: {student_number}"
                        print(error_msg)
                        log_to_activity(error_msg, is_error=True)
                        continue
                except ValueError:
                    error_msg = f"Ongeldig leerlingnummer formaat: {student_number_str}"
                    print(error_msg)
                    log_to_activity(error_msg, is_error=True)
                    continue

                # Controleer of leerling in toegestane lijst staat
                if student_number not in allowed_students:
                    error_msg = f"Leerling {student_number} niet in toegestane lijst, genegeerd"
                    print(error_msg)
                    log_to_activity(error_msg, is_error=True)
                    continue

                # Valideer statuscode
                if status_code not in ['G', 'V', 'R']:
                    error_msg = f"Onbekende statuscode: {status_code}, vorige status behouden"
                    print(error_msg)
                    log_to_activity(error_msg, is_error=True)
                    continue

                # Verwerk de statusupdate veilig
                try:
                    root.after(0, update_student_status, student_number, status_code)
                except Exception as e:
                    error_msg = f"Fout bij plannen GUI-update: {e}"
                    print(error_msg)
                    log_to_activity(error_msg, is_error=True)

            except Exception as e:
                error_msg = f"Fout bij parseren van bericht '{line}': {e}"
                print(error_msg)
                log_to_activity(error_msg, is_error=True)
                continue

        except serial.SerialException as e:
            error_msg = f"Seriële verbindingsfout: {e}"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)
            # Probeer opnieuw te verbinden na een vertraging
            time.sleep(1)
            try:
                reconnect_serial()
            except Exception as reconnect_error:
                error_msg = f"Herverbinden mislukt: {reconnect_error}"
                print(error_msg)
                log_to_activity(error_msg, is_error=True)
                time.sleep(5)  # Wacht langer voor volgende poging
        except UnicodeDecodeError as e:
            error_msg = f"Unicode decodeer fout: {e}"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)
            continue
        except Exception as e:
            error_msg = f"Onverwachte fout in seriële verwerking: {e}"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)
            time.sleep(0.1)  # Kleine vertraging

def check_connection_health():
    """Controleer de gezondheid van de seriële verbinding en herverbind indien nodig"""
    global ser, last_heartbeat, last_reconnect_time, last_connection_test
    
    try:
        current_time = time.time()
        
        # Log health check start
        print(f"[HEALTH] Gezondheidscontrole gestart om {time.strftime('%H:%M:%S')}")
        
        # Initialize global variables if they don't exist
        if 'last_reconnect_time' not in globals() or last_reconnect_time is None:
            last_reconnect_time = current_time
            print(f"[HEALTH] Initialiseer last_reconnect_time: {time.strftime('%H:%M:%S', time.localtime(last_reconnect_time))}")
        
        if 'last_connection_test' not in globals() or last_connection_test is None:
            last_connection_test = current_time
            print(f"[HEALTH] Initialiseer last_connection_test: {time.strftime('%H:%M:%S', time.localtime(last_connection_test))}")
        
        if 'last_heartbeat' not in globals() or last_heartbeat is None:
            last_heartbeat = current_time
            print(f"[HEALTH] Initialiseer last_heartbeat: {time.strftime('%H:%M:%S', time.localtime(last_heartbeat))}")
        
        # Check if user manually disconnected
        if manual_disconnect:
            print("[HEALTH] Handmatige verbinding verbroken - sla gezondheidscontrole over")
            root.after(10000, check_connection_health)
            return
        
        # Check if we have a port selected
        selected_port = port_selector.get()
        if not selected_port:
            print("[HEALTH] Geen poort geselecteerd - sla gezondheidscontrole over")
            root.after(10000, check_connection_health)
            return
        
        # FORCE RECONNECT EVERY 3 MINUTES (180 seconds) REGARDLESS OF STATUS
        time_since_reconnect = current_time - last_reconnect_time
        print(f"[HEALTH] Tijd sinds laatste herverbinding: {time_since_reconnect:.1f} seconden")
        
        if time_since_reconnect > 180:  # 3 minuten = 180 seconden
            log_to_activity(f"3 minuten verstreken ({time_since_reconnect:.0f}s), geforceerde herverbinding...", log_type="HEALTH")
            print(f"[HEALTH] Geforceerde herverbinding na {time_since_reconnect:.0f} seconden")
            try:
                reconnect_serial()
                last_reconnect_time = current_time
                print(f"[HEALTH] Geforceerde herverbinding succesvol om {time.strftime('%H:%M:%S')}")
            except Exception as e:
                error_msg = f"Geforceerde herverbinding mislukt: {e}"
                log_to_activity(error_msg, is_error=True)
                print(f"[HEALTH] {error_msg}")
            
            # Schedule next health check
            root.after(10000, check_connection_health)
            return
        
        # Check if connection is lost
        if ser is None or not ser.is_open:
            print("[HEALTH] Verbinding verloren - poging tot herverbinding")
            log_to_activity("Verbinding verloren, poging tot herverbinding...", is_error=True)
            try:
                reconnect_serial()
                last_reconnect_time = current_time
                print(f"[HEALTH] Herverbinding na verlies succesvol om {time.strftime('%H:%M:%S')}")
            except Exception as e:
                error_msg = f"Auto-herverbind na verlies mislukt: {e}"
                log_to_activity(error_msg, is_error=True)
                print(f"[HEALTH] {error_msg}")
            
            root.after(5000, check_connection_health)
            return
        
        # Test connection every minute
        time_since_test = current_time - last_connection_test
        print(f"[HEALTH] Tijd sinds laatste verbindingstest: {time_since_test:.1f} seconden")
        
        if time_since_test > 60:  # 1 minuut
            print("[HEALTH] Voer verbindingstest uit...")
            if not test_serial_connection():
                print("[HEALTH] Verbindingstest mislukt - poging tot herverbinding")
                log_to_activity("Verbindingstest mislukt, poging tot herverbinding...", is_error=True)
                try:
                    reconnect_serial()
                    last_reconnect_time = current_time
                    print(f"[HEALTH] Herverbinding na mislukte test succesvol om {time.strftime('%H:%M:%S')}")
                except Exception as e:
                    error_msg = f"Herverbind na mislukte test mislukt: {e}"
                    log_to_activity(error_msg, is_error=True)
                    print(f"[HEALTH] {error_msg}")
            last_connection_test = current_time
        
        # Check heartbeat (30 seconds without messages)
        time_since_heartbeat = current_time - last_heartbeat
        print(f"[HEALTH] Tijd sinds laatste heartbeat: {time_since_heartbeat:.1f} seconden")
        
        if time_since_heartbeat > 40:  # 40 seconden zonder bericht
            warning_msg = f"Geen berichten ontvangen sinds {time_since_heartbeat:.0f} seconden."
            log_to_activity(warning_msg, log_type="HEALTH")
            print(f"[HEALTH] {warning_msg}")
            
            # Only reconnect due to heartbeat if it's been a really long time
            if time_since_heartbeat > 90:  # 1,5 minuten zonder berichten
                print("[HEALTH] Lange tijd zonder berichten - herverbind...")
                try:
                    reconnect_serial()
                    last_reconnect_time = current_time
                    print(f"[HEALTH] Herverbinding na lange stilte succesvol om {time.strftime('%H:%M:%S')}")
                except Exception as e:
                    error_msg = f"Heartbeat herverbind mislukt: {e}"
                    log_to_activity(error_msg, is_error=True)
                    print(f"[HEALTH] {error_msg}")
        
        print(f"[HEALTH] Gezondheidscontrole voltooid om {time.strftime('%H:%M:%S')}")
        
        # Schedule next health check
        root.after(10000, check_connection_health)  # Check every 10 seconds
        
    except Exception as e:
        error_msg = f"Fout in gezondheidscontrole: {e}"
        print(f"[HEALTH] {error_msg}")
        log_to_activity(error_msg, is_error=True)
        root.after(10000, check_connection_health)  # Always retry in 10 seconds

def reconnect_serial():
    global ser, manual_disconnect, last_heartbeat
    
    print(f"[RECONNECT] Start herverbinding om {time.strftime('%H:%M:%S')}")
    
    try:
        if ser:
            try:
                print("[RECONNECT] Sluit bestaande verbinding...")
                # Safe close with error handling
                if hasattr(ser, 'close'):
                    ser.close()
                else:
                    print("[RECONNECT] Seriële object heeft geen close methode")
            except Exception as e:
                error_msg = f"Fout bij sluiten seriële poort: {e}"
                print(f"[RECONNECT] {error_msg}")
                log_to_activity(error_msg, is_error=True)
            finally:
                ser = None  # Always reset to None
        
        # Get the selected port
        try:
            selected_port = port_selector.get()
        except Exception as e:
            error_msg = f"Fout bij ophalen geselecteerde poort: {e}"
            print(f"[RECONNECT] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            root.after(0, update_connection_status, "Poort selectie fout", "red")
            return
            
        if not selected_port:
            error_msg = "Geen poort geselecteerd voor herverbinding"
            print(f"[RECONNECT] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            root.after(0, update_connection_status, "Geen poort geselecteerd", "red")
            return
        
        print(f"[RECONNECT] Probeer verbinding met poort {selected_port}...")
        
        try:
            # Create new serial connection with error handling
            ser = serial.Serial(selected_port, 115200, timeout=1)
            
            # Verify the connection was created properly
            if ser is None:
                raise Exception("Serial object creation failed - returned None")
                
            if not hasattr(ser, 'is_open'):
                raise Exception("Serial object missing is_open attribute")
                
            if not ser.is_open:
                raise Exception("Serial port failed to open")
                
            manual_disconnect = False  # Reset manual disconnect flag
            last_heartbeat = time.time()  # Reset heartbeat timer
            
            success_msg = f"Herverbonden met {selected_port}"
            print(f"[RECONNECT] {success_msg}")
            log_to_activity(success_msg, log_type="INFO")
            root.after(0, update_connection_status, "Verbonden", "green")
            
        except Exception as e:
            error_msg = f"Herverbinden mislukt: {e}"
            print(f"[RECONNECT] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            root.after(0, update_connection_status, "Herverbinding mislukt", "red")
            ser = None  # Ensure ser is None on failure
            raise e  # Re-raise to be caught by caller
            
    except Exception as e:
        error_msg = f"Fout in reconnect_serial: {e}"
        print(f"[RECONNECT] {error_msg}")
        log_to_activity(error_msg, is_error=True)
        root.after(0, update_connection_status, "Herverbinding mislukt", "red")
        ser = None  # Ensure ser is None on failure
        raise e  # Re-raise to be caught by caller

def test_serial_connection():
    """Test de seriële verbinding door eigenschappen te controleren en communicatie te testen"""
    global ser
    
    print(f"[TEST] Start verbindingstest om {time.strftime('%H:%M:%S')}")
    
    try:
        # Extra null checks
        if ser is None:
            error_msg = "Geen seriële verbinding om te testen (ser is None)"
            print(f"[TEST] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            return False
            
        if not hasattr(ser, 'is_open'):
            error_msg = "Seriële object heeft geen is_open eigenschap"
            print(f"[TEST] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            return False
            
        if not ser.is_open:
            error_msg = "Seriële poort is niet open"
            print(f"[TEST] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            return False
            
        try:
            # Test 1: Check basic properties
            baudrate = getattr(ser, 'baudrate', 'Onbekend')
            port_name = getattr(ser, 'port', 'Onbekend')
            timeout = getattr(ser, 'timeout', 'Onbekend')
            
            print(f"[TEST] Poort eigenschappen - Poort: {port_name}, Baudrate: {baudrate}, Timeout: {timeout}")
            
            # Test 2: Check if methods exist
            if not (hasattr(ser, 'write') and hasattr(ser, 'flush') and hasattr(ser, 'read')):
                error_msg = "Seriële object mist essentiële methoden (write/flush/read)"
                print(f"[TEST] {error_msg}")
                log_to_activity(error_msg, is_error=True)
                return False
            
            # Test 3: Check buffer status
            try:
                in_waiting = getattr(ser, 'in_waiting', 0)
                out_waiting = getattr(ser, 'out_waiting', 0)
                print(f"[TEST] Buffer status - In: {in_waiting}, Out: {out_waiting}")
            except Exception as buffer_err:
                print(f"[TEST] Waarschuwing: Kan buffer status niet lezen: {buffer_err}")
            
            # Test 4: Try to write and flush (basic communication test)
            try:
                ser.write(b"HEALTH_CHECK\n")
                ser.flush()
                print(f"[TEST] Schrijftest geslaagd")
            except (OSError, serial.SerialException) as write_err:
                error_msg = f"Schrijftest mislukt: {write_err}"
                print(f"[TEST] {error_msg}")
                log_to_activity(error_msg, is_error=True)
                return False
            
            # Test 5: Check if port is still accessible (OS level check)
            try:
                # Try to get port info to verify it's still connected
                import serial.tools.list_ports
                available_ports = [port.device for port in serial.tools.list_ports.comports()]
                if port_name not in available_ports:
                    error_msg = f"Poort {port_name} niet meer beschikbaar in systeem"
                    print(f"[TEST] {error_msg}")
                    log_to_activity(error_msg, is_error=True)
                    return False
            except Exception as port_check_err:
                print(f"[TEST] Waarschuwing: Kan poortstatus niet controleren: {port_check_err}")
            
            # Test 6: Try reading with timeout to check responsiveness
            try:
                # Clear any existing buffer first
                if ser.in_waiting > 0:
                    ser.read(ser.in_waiting)
                
                # Set a short timeout for this test
                original_timeout = ser.timeout
                ser.timeout = 0.1
                
                # Try to read (this will timeout quickly if no data)
                test_read = ser.read(1)
                
                # Restore original timeout
                ser.timeout = original_timeout
                
                print(f"[TEST] Leestest voltooid (ontvangen: {len(test_read)} bytes)")
                
            except Exception as read_err:
                error_msg = f"Leestest fout: {read_err}"
                print(f"[TEST] {error_msg}")
                log_to_activity(error_msg, is_error=True)
                return False
            
            success_msg = f"Verbindingstest volledig geslaagd - Poort: {port_name}, Baudrate: {baudrate}"
            print(f"[TEST] {success_msg}")
            log_to_activity(success_msg, log_type="HEALTH")
            return True
            
        except (OSError, serial.SerialException, AttributeError) as serial_err:
            error_msg = f"Seriële verbinding gefaald tijdens test: {serial_err}"
            print(f"[TEST] {error_msg}")
            log_to_activity(error_msg, is_error=True)
            return False
            
    except Exception as e:
        error_msg = f"Onverwachte fout bij verbindingstest: {e}"
        print(f"[TEST] {error_msg}")
        log_to_activity(error_msg, is_error=True)
        return False

def connect_to_port():
    """Verbind met de geselecteerde seriële poort"""
    global ser, manual_disconnect, last_reconnect_time, last_heartbeat
    
    selected_port = port_selector.get()
    if not selected_port:
        messagebox.showwarning("Waarschuwing", "Selecteer eerst een poort")
        return
        
    if ser is not None:
        try:
            if hasattr(ser, 'close'):
                ser.close()
        except:
            pass
        finally:
            ser = None
    
    try:
        print(f"[CONNECT] Handmatige verbinding met {selected_port}")
        ser = serial.Serial(selected_port, 115200, timeout=1)
        
        # Verify the connection was created properly
        if ser is None:
            raise Exception("Serial object creation failed - returned None")
            
        if not hasattr(ser, 'is_open'):
            raise Exception("Serial object missing is_open attribute")
            
        if not ser.is_open:
            raise Exception("Serial port failed to open")
        
        manual_disconnect = False
        last_reconnect_time = time.time()  # Initialize reconnect timer
        last_heartbeat = time.time()  # Initialize heartbeat timer
        
        success_msg = f"Verbonden met {selected_port}"
        print(f"[CONNECT] {success_msg}")
        log_to_activity(success_msg, log_type="INFO")
        update_connection_status("Verbonden", "green")
        
    except Exception as e:
        error_msg = f"Fout bij verbinden met poort {selected_port}: {e}"
        print(f"[CONNECT] {error_msg}")
        log_to_activity(error_msg, is_error=True)
        messagebox.showerror("Verbindingsfout", f"Verbinden met {selected_port} mislukt: {e}")
        ser = None
        update_connection_status("Niet verbonden", "red")

def disconnect_from_port():
    """Verbreek verbinding met de seriële poort"""
    global ser, manual_disconnect
    
    if ser is not None:
        try:
            print("[DISCONNECT] Handmatige verbinding verbreken")
            if hasattr(ser, 'close'):
                ser.close()
            else:
                print("[DISCONNECT] Seriële object heeft geen close methode")
            manual_disconnect = True  # Mark as manual disconnect
            
            success_msg = "Verbinding met seriële poort handmatig verbroken"
            print(f"[DISCONNECT] {success_msg}")
            log_to_activity(success_msg, log_type="INFO")
            update_connection_status("Niet verbonden", "gray")
            
        except Exception as e:
            error_msg = f"Fout bij verbreken verbinding: {e}"
            print(f"[DISCONNECT] {error_msg}")
            log_to_activity(error_msg, is_error=True)
        finally:
            ser = None  # Always reset to None


def update_student_status(student_number, status_code):
    """Update de status van de leerling in de GUI"""
    try:
        current_time = time.strftime("%H:%M:%S")
        
        # Vertaal statuscodes naar leesbare tekst en kleuren
        status_map = {
            'G': ('Beschikbaar', 'green'),
            'V': ('Vraag', 'orange'), 
            'R': ('Hulp nodig', 'red')
        }
        
        status_info = status_map.get(status_code)
        if not status_info:
            print(f"Onbekende statuscode: {status_code}, vorige status behouden")
            return
            
        status_text, color = status_info
        
        # Controleer of dit een duplicaat bericht is (zelfde status binnen 2 seconden)
        if student_number in student_statuses:
            prev_status = student_statuses[student_number]
            if (prev_status.get('code') == status_code and 
                time.time() - prev_status.get('last_update', 0) < 2):
                print(f"Duplicaat bericht voor leerling {student_number}, genegeerd")
                return
        
        # Bewaar vorige status start tijd als de status niet verandert
        status_start_time = time.time()
        if student_number in student_statuses:
            prev_status = student_statuses[student_number]
            if prev_status.get('code') == status_code:
                # Status is hetzelfde, behoud de oorspronkelijke start tijd
                status_start_time = prev_status.get('status_start_time', time.time())
        
        # Update of voeg leerling toe in de weergave
        student_statuses[student_number] = {
            'status': status_text,
            'color': color,
            'time': current_time,
            'code': status_code,
            'last_update': time.time(),
            'status_start_time': status_start_time  # Wanneer deze status begon
        }
        
        # Ververs de weergave veilig
        try:
            refresh_student_display()
        except Exception as e:
            print(f"Fout bij verversen weergave: {e}")
        
        # Krijg leerlingnaam voor logging
        student_name = student_names.get(student_number, f"Leerling {student_number}")
        
        # Voeg toe aan activiteitenlog veilig
        try:
            log_message = f"{student_name} ({student_number}): {status_text}"
            log_to_activity(log_message, log_type="STATUS")
        except Exception as e:
            error_msg = f"Fout bij updaten activiteitenlog: {e}"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)
        

    except Exception as e:
        print(f"Fout in update_student_status: {e}")

def refresh_student_display():
    """Ververs de leerlingstatusweergave"""
    try:
        # Wis huidige weergave en referenties
        for widget in student_frame.winfo_children():
            widget.destroy()
        duration_labels.clear()  # Wis oude label referenties
        
        # Sorteer leerlingen op prioriteit: eerste hulp nodig (R) op tijd, dan vragen (V) op tijd, dan anderen
        def sort_priority(item):
            student_number, info = item
            status_code = info.get('code', 'G')
            status_start_time = info.get('status_start_time', time.time())
            
            if status_code == 'R':  # Hulp nodig - hoogste prioriteit
                return (0, -status_start_time)  # Negatief voor langste tijd eerst
            elif status_code == 'V':  # Vraag - tweede prioriteit
                return (1, -status_start_time)  # Negatief voor langste tijd eerst
            else:  # Andere statussen - laagste prioriteit
                return (2, student_number)  # Sorteer op leerlingnummer
        
        sorted_students = sorted(student_statuses.items(), key=sort_priority)
        
        # Maak headers
        tk.Label(student_frame, text="Leerlingnummer", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Naam", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Status", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Tijd", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Duur", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=5, pady=2, sticky='w')
        tk.Label(student_frame, text="Actie", font=("Arial", 10, "bold")).grid(row=0, column=5, padx=5, pady=2, sticky='w')
        
        row = 1
        current_time = time.time()
        for student_number, info in sorted_students:
            try:
                # Leerlingnummer
                tk.Label(student_frame, text=str(student_number), font=("Arial", 9)).grid(row=row, column=0, padx=5, pady=1, sticky='w')
                
                # Leerlingnaam
                student_name = student_names.get(student_number, f"Leerling {student_number}")
                tk.Label(student_frame, text=student_name, font=("Arial", 9)).grid(row=row, column=1, padx=5, pady=1, sticky='w')
                
                # Status met kleur
                status_label = tk.Label(student_frame, text=info['status'], fg=info['color'], font=("Arial", 9, "bold"))
                status_label.grid(row=row, column=2, padx=5, pady=1, sticky='w')
                
                # Tijd
                tk.Label(student_frame, text=info['time'], font=("Arial", 8)).grid(row=row, column=3, padx=5, pady=1, sticky='w')
                
                # Duur (alleen voor V en R statussen)
                duration_text = ""
                duration_color = "black"
                if info['code'] in ['V', 'R']:
                    status_start_time = info.get('status_start_time', current_time)
                    duration_seconds = int(current_time - status_start_time)
                    
                    if duration_seconds < 60:
                        duration_text = f"{duration_seconds}s"
                    elif duration_seconds < 3600:
                        minutes = duration_seconds // 60
                        seconds = duration_seconds % 60
                        duration_text = f"{minutes}m {seconds}s"
                    else:
                        hours = duration_seconds // 3600
                        minutes = (duration_seconds % 3600) // 60
                        duration_text = f"{hours}h {minutes}m"
                    
                    # Bepaal kleur afhankelijk van de tijd
                    if duration_seconds > 300:  # Meer dan 5 minuten
                        duration_color = "red"
                    elif duration_seconds > 120:  # Meer dan 2 minuten
                        duration_color = "orange"
                
                # Maak de duur label en sla referentie op
                duration_label = tk.Label(student_frame, text=duration_text, font=("Arial", 8, "bold"), fg=duration_color)
                duration_label.grid(row=row, column=4, padx=5, pady=1, sticky='w')
                
                # Sla referentie op voor real-time updates (alleen voor V en R statussen)
                if info['code'] in ['V', 'R']:
                    duration_labels[student_number] = duration_label
                
                # Actieknop voor vragen/hulp
                if info['code'] in ['V', 'R']:
                    action_btn = tk.Button(student_frame, text="Oplossen", 
                                         command=lambda sn=student_number: resolve_student_issue(sn),
                                         bg="lightblue", font=("Arial", 8))
                    action_btn.grid(row=row, column=5, padx=5, pady=1, sticky='w')
                
                row += 1
            except Exception as e:
                print(f"Fout bij maken weergaverij voor leerling {student_number}: {e}")
                log_to_activity(f"Fout bij maken weergaverij voor leerling {student_number}: {e}", is_error=True)
                continue
                
    except Exception as e:
        error_msg = f"Fout in refresh_student_display: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)

def resolve_student_issue(student_number):
    """Markeer het probleem van een leerling als opgelost"""
    try:
        if student_number in student_statuses:
            student_statuses[student_number]['status'] = 'Opgelost'
            student_statuses[student_number]['color'] = 'blue'
            student_statuses[student_number]['code'] = 'G'
            student_statuses[student_number]['last_update'] = time.time()
            refresh_student_display()
            
            current_time = time.strftime("%H:%M:%S")
            student_name = student_names.get(student_number, f"Leerling {student_number}")
            log_message = f"{student_name} ({student_number}): Probleem opgelost door docent"
            log_to_activity(log_message, log_type="STATUS")
    except Exception as e:
        error_msg = f"Fout bij oplossen leerlingprobleem: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)

def update_allowed_students():
    """Update de lijst van toegestane leerlingnummers en namen"""
    global allowed_students, student_names
    try:
        # Krijg tekst uit invoerveld en parseer leerlingnummers en namen
        student_text = student_numbers_entry.get("1.0", tk.END).strip()
        if not student_text:
            allowed_students = set()
            student_names = {}
            return
            
        # Parseer nummers en namen (formaat: 123456:Leerling naam)
        student_numbers = []
        new_student_names = {}
        
        for line in student_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if ':' in line:
                # Formaat: 123456:LeerlingNaam
                try:
                    num_str, name = line.split(':', 1)
                    num = int(num_str.strip())
                    name = name.strip()
                    
                    if 100000 <= num <= 999999:  # 6-cijferige nummers
                        student_numbers.append(num)
                        new_student_names[num] = name
                    else:
                        print(f"Ongeldig leerlingnummer (geen 6 cijfers): {num}")
                except ValueError:
                    print(f"Ongeldig leerling invoerformaat: {line}")
            else:
                # Alleen een nummer zonder naam
                try:
                    num = int(line)
                    if 100000 <= num <= 999999:  # 6-cijferige nummers
                        student_numbers.append(num)
                        new_student_names[num] = f"Leerling {num}"
                    else:
                        print(f"Ongeldig leerlingnummer (geen 6 cijfers): {num}")
                except ValueError:
                    print(f"Ongeldig leerlingnummer formaat: {line}")
        
        allowed_students = set(student_numbers)
        student_names = new_student_names
        print(f"Leerlingen om te ontvangen bijgewerkt: {sorted(allowed_students)}")
        print(f"Leerlingnamen: {student_names}")
        
        # Wis leerlingstatussen voor leerlingen die niet meer in de lijst staan
        students_to_remove = []
        for student_num in student_statuses:
            if student_num not in allowed_students:
                students_to_remove.append(student_num)
        
        for student_num in students_to_remove:
            del student_statuses[student_num]
        
        refresh_student_display()
        
    except Exception as e:
        messagebox.showerror("Fout", f"Fout bij updaten leerlinglijst: {e}")

def refresh_ports():
    """Ververs de lijst van beschikbare seriële poorten"""
    ports = serial.tools.list_ports.comports()
    port_list = [port.device for port in ports]
    port_selector['values'] = port_list
    print(f"Beschikbare poorten: {port_list}")



def update_connection_status(status, color):
    """Update de verbindingsstatusweergave"""
    connection_status_label.config(text=f"Status: {status}", fg=color)

def clear_activity_log():
    """Wis het activiteitenlog"""
    activity_log.delete(1.0, tk.END)

def export_log():
    """Exporteer het activiteitenlog naar een bestand"""
    from tkinter import filedialog
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Tekstbestanden", "*.txt"), ("Alle bestanden", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(activity_log.get(1.0, tk.END))
            messagebox.showinfo("Succes", f"Log geëxporteerd naar {filename}")
    except Exception as e:
        messagebox.showerror("Fout", f"Log exporteren mislukt: {e}")

def update_duration_labels():
    """Update alleen de duur labels zonder de hele weergave te verversen"""
    try:
        current_time = time.time()
        has_updates = False
        
        for student_number, info in student_statuses.items():
            if info.get('code') in ['V', 'R'] and student_number in duration_labels:
                duration_label = duration_labels[student_number]
                
                # Controleer of het label nog bestaat
                try:
                    if duration_label.winfo_exists():
                        status_start_time = info.get('status_start_time', current_time)
                        duration_seconds = int(current_time - status_start_time)
                        
                        # Bereken duration tekst
                        if duration_seconds < 60:
                            duration_text = f"{duration_seconds}s"
                        elif duration_seconds < 3600:
                            minutes = duration_seconds // 60
                            seconds = duration_seconds % 60
                            duration_text = f"{minutes}m {seconds}s"
                        else:
                            hours = duration_seconds // 3600
                            minutes = (duration_seconds % 3600) // 60
                            duration_text = f"{hours}h {minutes}m"
                        
                        # Bepaal kleur afhankelijk van de tijd
                        duration_color = "black"
                        if duration_seconds > 300:  # Meer dan 5 minuten
                            duration_color = "red"
                        elif duration_seconds > 120:  # Meer dan 2 minuten
                            duration_color = "orange"
                        
                        # Update het label
                        duration_label.config(text=duration_text, fg=duration_color)
                        has_updates = True
                    else:
                        # Label bestaat niet meer, verwijder uit dictionary
                        del duration_labels[student_number]
                except tk.TclError:
                    # Label is vernietigd, verwijder uit dictionary
                    del duration_labels[student_number]
        
        # Plan de volgende update over 1 seconde alleen als er actieve statussen zijn
        if any(info.get('code') in ['V', 'R'] for info in student_statuses.values()):
            root.after(1000, update_duration_labels)
        else:
            # Geen actieve statussen, probeer weer over 5 seconden
            root.after(5000, update_duration_labels)
            
    except Exception as e:
        error_msg = f"Fout in update_duration_labels: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)
        # Plan opnieuw ondanks fout
        root.after(1000, update_duration_labels)

def periodic_refresh():
    """Periodiek verversen van de studentenweergave voor structurele wijzigingen"""
    try:
        # Deze functie wordt nu minder frequent gebruikt, alleen voor volledige refresh
        # De duration updates worden nu gedaan door update_duration_labels()
        
        # Plan de volgende volledige refresh over 30 seconden (minder frequent dan voorheen)
        root.after(30000, periodic_refresh)
    except Exception as e:
        error_msg = f"Fout in periodic_refresh: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)
        # Plan opnieuw ondanks fout
        root.after(30000, periodic_refresh)

# Initialiseer globale variabelen
allowed_students = set()
student_names = {}  # dict om leerlingnamen op te slaan
student_statuses = {}
duration_labels = {}  # dict om referenties naar duration labels op te slaan
ser = None
last_heartbeat = None
last_reconnect_time = None
last_connection_test = None
manual_disconnect = False  # Track if user manually disconnected
activity_log_entries = []  # Lijst voor log entries met filtering
log_filter_vars = {}  # Variabelen voor log filtering

# Stel de tkinter GUI in
root = tk.Tk()
root.title("Qube Monitor - Docent Dashboard")

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Set icon with proper path handling for both development and .exe
def set_window_icon():
    try:
        # Get the correct path to the icon file
        icon_path = resource_path('dice_icon_160194.ico')
        
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
            print(f"Icon set successfully: {icon_path}")
        else:
            print(f"Icon file not found: {icon_path}")
            # Try alternative path for development
            dev_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dice_icon_160194.ico')
            if os.path.exists(dev_icon_path):
                root.iconbitmap(dev_icon_path)
                print(f"Icon set successfully (dev path): {dev_icon_path}")
            else:
                print(f"Icon file not found in dev path: {dev_icon_path}")
            
    except Exception as e:
        print(f"Could not set window icon: {e}")
        # Try to set without path as fallback
        try:
            root.iconbitmap('dice_icon_160194.ico')
            print("Icon set using relative path")
        except Exception as e2:
            print(f"Fallback icon setting also failed: {e2}")

set_window_icon()
root.geometry('1000x700')

# Maak hoofdframes
control_frame = tk.Frame(root)
control_frame.pack(fill=tk.X, padx=10, pady=5)

content_frame = tk.Frame(root)
content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# Verbindingsbesturing
connection_frame = tk.LabelFrame(control_frame, text="Seriële Verbinding")
connection_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X)

port_selector = ttk.Combobox(connection_frame, state='readonly', width=20)
port_selector.pack(side=tk.LEFT, padx=5, pady=5)

refresh_ports_button = tk.Button(connection_frame, text="Poorten Verversen", command=refresh_ports)
refresh_ports_button.pack(side=tk.LEFT, padx=2, pady=5)

connect_button = tk.Button(connection_frame, text="Verbinden", command=connect_to_port, bg="lightgreen")
connect_button.pack(side=tk.LEFT, padx=2, pady=5)

disconnect_button = tk.Button(connection_frame, text="Verbreken", command=disconnect_from_port, bg="lightcoral")
disconnect_button.pack(side=tk.LEFT, padx=2, pady=5)

connection_status_label = tk.Label(connection_frame, text="Status: Niet verbonden", fg="gray")
connection_status_label.pack(side=tk.LEFT, padx=10, pady=5)

# Leerlingnummers configuratie
student_config_frame = tk.LabelFrame(content_frame, text="Leerlinglijst (Formaat: 123456:LeerlingNaam, één per regel)")
student_config_frame.pack(fill=tk.X, pady=5)

student_numbers_entry = scrolledtext.ScrolledText(student_config_frame, height=4, width=50)
student_numbers_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

student_config_buttons = tk.Frame(student_config_frame)
student_config_buttons.pack(side=tk.RIGHT, padx=5, pady=5)

update_students_button = tk.Button(student_config_buttons, text="Leerlinglijst\nBijwerken", 
                                 command=update_allowed_students, bg="lightblue")
update_students_button.pack(pady=2)

# Hoofdinhoud gebied
main_content = tk.Frame(content_frame)
main_content.pack(fill=tk.BOTH, expand=True, pady=5)

# Leerlingstatusweergave
status_frame = tk.LabelFrame(main_content, text="Leerling Status")
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

# Log toggle knop in control frame
log_control_frame = tk.LabelFrame(control_frame, text="Weergave")
log_control_frame.pack(side=tk.RIGHT, padx=5, pady=5)

toggle_log_button = tk.Button(log_control_frame, text="▲ Toon Log", command=toggle_log_panel, bg="lightgray")
toggle_log_button.pack(padx=5, pady=5)

# Activiteitenlog panel (initieel verborgen)
log_panel = tk.LabelFrame(main_content, text="Activiteitenlog")
# Log panel wordt niet gepack bij start (verborgen)

# Log filters frame
log_filters_frame = tk.Frame(log_panel)
log_filters_frame.pack(fill=tk.X, padx=5, pady=2)

tk.Label(log_filters_frame, text="Toon:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)

# Maak filter checkboxes
log_filter_vars['STATUS'] = tk.BooleanVar(value=True)
log_filter_vars['ERROR'] = tk.BooleanVar(value=True) 
log_filter_vars['HEALTH'] = tk.BooleanVar(value=False)  # Health logs standaard uit
log_filter_vars['INFO'] = tk.BooleanVar(value=True)

status_cb = tk.Checkbutton(log_filters_frame, text="Status", variable=log_filter_vars['STATUS'], 
                          command=update_activity_log_display, fg="#0066CC")
status_cb.pack(side=tk.LEFT, padx=2)

error_cb = tk.Checkbutton(log_filters_frame, text="Fouten", variable=log_filter_vars['ERROR'], 
                         command=update_activity_log_display, fg="#CC0000")
error_cb.pack(side=tk.LEFT, padx=2)

health_cb = tk.Checkbutton(log_filters_frame, text="Health", variable=log_filter_vars['HEALTH'], 
                          command=update_activity_log_display, fg="#FF6600")
health_cb.pack(side=tk.LEFT, padx=2)

info_cb = tk.Checkbutton(log_filters_frame, text="Info", variable=log_filter_vars['INFO'], 
                        command=update_activity_log_display, fg="#000000")
info_cb.pack(side=tk.LEFT, padx=2)

# Activity log text widget
activity_log = scrolledtext.ScrolledText(log_panel, height=20, width=40, wrap=tk.WORD)
activity_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# Log buttons frame
log_buttons_frame = tk.Frame(log_panel)
log_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

clear_log_button = tk.Button(log_buttons_frame, text="Log Wissen", command=clear_activity_log)
clear_log_button.pack(side=tk.LEFT, padx=2)

export_log_button = tk.Button(log_buttons_frame, text="Log Exporteren", command=export_log)
export_log_button.pack(side=tk.LEFT, padx=2)

# Start de seriële verwerking in een aparte thread
thread = threading.Thread(target=process_serial_data)
thread.daemon = True
thread.start()

# Start de gezondheidscontrole
root.after(10000, check_connection_health)  # Start na 10 seconden

# Start periodieke refresh voor structurele wijzigingen (minder frequent)
root.after(30000, periodic_refresh)  # Start na 30 seconden

# Start real-time duration updates (elke seconde)
root.after(1000, update_duration_labels)  # Start na 1 seconde

# Initialiseer
refresh_ports()
refresh_student_display()

# Voeg enkele voorbeeldleerlingnummers toe
student_numbers_entry.insert("1.0", "123456:Voornaam Achternaam")

root.mainloop()

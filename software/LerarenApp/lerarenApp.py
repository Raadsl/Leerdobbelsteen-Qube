import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import threading
import time
import serial.tools.list_ports

def log_to_activity(message, is_error=False):
    """Voeg een bericht toe aan het activiteitenlog"""
    try:
        current_time = time.strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}\n"
        if is_error:
            log_message = f"[{current_time}] ERROR: {message}\n"
        root.after(0, lambda: activity_log.insert(tk.END, log_message))
        root.after(0, lambda: activity_log.see(tk.END))
    except Exception as e:
        print(f"Fout bij toevoegen aan activiteitenlog: {e}")

def process_serial_data():
    global ser, last_heartbeat
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

def reconnect_serial():
    global ser, manual_disconnect
    try:
        if ser:
            try:
                ser.close()
            except Exception as e:
                error_msg = f"Fout bij sluiten seriële poort: {e}"
                print(error_msg)
                log_to_activity(error_msg, is_error=True)
            ser = None
        
        # Probeer opnieuw te verbinden met de laatst geselecteerde poort
        selected_port = port_selector.get()
        if selected_port:
            try:
                ser = serial.Serial(selected_port, 115200, timeout=1)
                manual_disconnect = False  # Reset manual disconnect flag on successful reconnection
                success_msg = f"Opnieuw verbonden met {selected_port}"
                print(success_msg)
                log_to_activity(success_msg)
                root.after(0, update_connection_status, "Verbonden", "green")
            except Exception as e:
                error_msg = f"Herverbinden mislukt: {e}"
                print(error_msg)
                log_to_activity(error_msg, is_error=True)
                root.after(0, update_connection_status, "Niet verbonden", "red")
        else:
            error_msg = "Geen poort geselecteerd voor herverbinding"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)
            root.after(0, update_connection_status, "Geen poort geselecteerd", "red")
    except Exception as e:
        error_msg = f"Fout in reconnect_serial: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)
        root.after(0, update_connection_status, "Herverbinding mislukt", "red")

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
            log_to_activity(log_message)
        except Exception as e:
            error_msg = f"Fout bij updaten activiteitenlog: {e}"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)
        

    except Exception as e:
        print(f"Fout in update_student_status: {e}")

def refresh_student_display():
    """Ververs de leerlingstatusweergave"""
    try:
        # Wis huidige weergave
        for widget in student_frame.winfo_children():
            widget.destroy()
        
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
                
                # Maak de duur label met kleur afhankelijk van de tijd
                duration_color = "black"
                if info['code'] in ['V', 'R']:
                    if duration_seconds > 300:  # Meer dan 5 minuten
                        duration_color = "red"
                    elif duration_seconds > 120:  # Meer dan 2 minuten
                        duration_color = "orange"
                
                duration_label = tk.Label(student_frame, text=duration_text, font=("Arial", 8, "bold"), fg=duration_color)
                duration_label.grid(row=row, column=4, padx=5, pady=1, sticky='w')
                
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
            log_to_activity(log_message)
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

def connect_to_port():
    """Verbind met de geselecteerde seriële poort"""
    global ser, manual_disconnect
    selected_port = port_selector.get()
    if not selected_port:
        messagebox.showwarning("Waarschuwing", "Selecteer eerst een poort")
        return
        
    if ser is not None:
        try:
            ser.close()
        except:
            pass
    
    try:
        ser = serial.Serial(selected_port, 115200, timeout=1)
        manual_disconnect = False  # Reset manual disconnect flag on successful connection
        success_msg = f"Verbonden met {selected_port}"
        print(success_msg)
        log_to_activity(success_msg)
        update_connection_status("Verbonden", "green")
    except Exception as e:
        error_msg = f"Fout bij verbinden met poort {selected_port}: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)
        messagebox.showerror("Verbindingsfout", f"Verbinden met {selected_port} mislukt: {e}")
        ser = None
        update_connection_status("Niet verbonden", "red")

def disconnect_from_port():
    """Verbreek verbinding met de seriële poort"""
    global ser, manual_disconnect
    if ser is not None:
        try:
            ser.close()
            ser = None
            manual_disconnect = True  # Mark as manual disconnect to prevent auto-reconnect
            success_msg = "Verbinding met seriële poort handmatig verbroken"
            print(success_msg)
            log_to_activity(success_msg)
            update_connection_status("Niet verbonden", "gray")
        except Exception as e:
            error_msg = f"Fout bij verbreken verbinding: {e}"
            print(error_msg)
            log_to_activity(error_msg, is_error=True)

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

def test_serial_connection():
    """Test de seriële verbinding door eigenschappen te controleren"""
    global ser
    try:
        if ser is not None and ser.is_open:
            # Test de verbinding door seriële eigenschappen te controleren
            try:
                # Probeer toegang tot baudrate en andere eigenschappen
                baudrate = ser.baudrate
                port_name = ser.port
                timeout = ser.timeout
                
                # Test of we kunnen schrijven zonder fout
                ser.write(b"TEST\n")
                ser.flush()
                
                log_to_activity(f"Verbindingstest geslaagd - Poort: {port_name}, Baudrate: {baudrate}")
                return True
            except (OSError, serial.SerialException) as serial_err:
                error_msg = f"Seriële verbinding niet beschikbaar: {serial_err}"
                log_to_activity(error_msg, is_error=True)
                return False
        else:
            log_to_activity("Geen actieve seriële verbinding voor test", is_error=True)
            return False
    except Exception as e:
        error_msg = f"Fout bij verbindingstest: {e}"
        log_to_activity(error_msg, is_error=True)
        return False

def check_connection_health():
    """Controleer de gezondheid van de seriële verbinding en herverbind indien nodig"""
    global ser, last_heartbeat, last_reconnect_time
    
    try:
        current_time = time.time()
        
        # Skip health check if user manually disconnected
        if manual_disconnect:
            root.after(10000, check_connection_health)  # Check again in 10 seconds
            return
        
        # Controleer of we een actieve verbinding hebben
        if ser is None or not ser.is_open:
            if port_selector.get():  # Alleen herverbinden als er een poort geselecteerd is
                log_to_activity("Verbinding verloren, poging tot herverbinding...", is_error=True)
                try:
                    reconnect_serial()
                    last_reconnect_time = current_time
                except Exception as e:
                    error_msg = f"Auto-herverbind mislukt: {e}"
                    log_to_activity(error_msg, is_error=True)
            root.after(5000, check_connection_health)  # Controleer opnieuw over 5 seconden
            return
        
        # Automatische herverbinding elke 5 minuten
        if hasattr(globals(), 'last_reconnect_time') and last_reconnect_time is not None:
            time_since_reconnect = current_time - last_reconnect_time
            if time_since_reconnect > 300:  # 5 minuten = 300 seconden
                log_to_activity("5 minuten verstreken, automatische herverbinding...")
                try:
                    reconnect_serial()
                    last_reconnect_time = current_time
                except Exception as e:
                    error_msg = f"5-minuten herverbind mislukt: {e}"
                    log_to_activity(error_msg, is_error=True)
        else:
            # Initialiseer de laatste herverbindingstijd
            last_reconnect_time = current_time
        
        # Test de verbinding elke minuut
        if hasattr(globals(), 'last_connection_test') and last_connection_test is not None:
            time_since_test = current_time - last_connection_test
            if time_since_test > 60:  # 1 minuut
                test_serial_connection()
                last_connection_test = current_time
        else:
            # Initialiseer de laatste test tijd
            last_connection_test = current_time
        
        # Controleer heartbeat (als we al lang niets ontvangen hebben)
        if hasattr(globals(), 'last_heartbeat') and last_heartbeat is not None:
            time_since_heartbeat = current_time - last_heartbeat
            if time_since_heartbeat > 30:  # 30 seconden zonder bericht
                log_to_activity(f"Geen berichten ontvangen sinds {time_since_heartbeat:.0f} seconden, controleer verbinding", is_error=True)
                # Test de verbinding
                if not test_serial_connection():
                    log_to_activity("Verbindingstest mislukt, poging tot herverbinding...", is_error=True)
                    try:
                        reconnect_serial()
                        last_reconnect_time = current_time
                    except Exception as e:
                        error_msg = f"Heartbeat herverbind mislukt: {e}"
                        log_to_activity(error_msg, is_error=True)
        
        # Plan de volgende gezondheidscontrole
        root.after(10000, check_connection_health)  # Controleer elke 10 seconden
        
    except Exception as e:
        error_msg = f"Fout in gezondheidscontrole: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)
        root.after(10000, check_connection_health)  # Probeer altijd opnieuw over 10 seconden

def periodic_refresh():
    """Periodiek verversen van de studentenweergave om durations bij te werken"""
    try:
        # Alleen verversen als er leerlingen met V of R status zijn
        has_active_status = any(info.get('code') in ['V', 'R'] for info in student_statuses.values())
        if has_active_status:
            refresh_student_display()
        
        # Plan de volgende refresh over 10 seconden
        root.after(10000, periodic_refresh)
    except Exception as e:
        error_msg = f"Fout in periodic_refresh: {e}"
        print(error_msg)
        log_to_activity(error_msg, is_error=True)
        # Plan opnieuw ondanks fout
        root.after(10000, periodic_refresh)

# Initialiseer globale variabelen
allowed_students = set()
student_names = {}  # dict om leerlingnamen op te slaan
student_statuses = {}
ser = None
last_heartbeat = None
last_reconnect_time = None
last_connection_test = None
manual_disconnect = False  # Track if user manually disconnected

# Stel de tkinter GUI in
root = tk.Tk()
root.title("LeerlingDobbelsteen Monitor - Docent Dashboard")
#root.iconbitmap(r'./dice_icon_160194.ico')
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

# Activiteitenlog
log_frame = tk.LabelFrame(main_content, text="Activiteitenlog")
log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

activity_log = scrolledtext.ScrolledText(log_frame, height=20, width=40)
activity_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

log_buttons_frame = tk.Frame(log_frame)
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

# Start periodieke refresh voor real-time duration updates
root.after(5000, periodic_refresh)  # Start na 5 seconden

# Initialiseer
refresh_ports()
refresh_student_display()

# Voeg enkele voorbeeldleerlingnummers toe
student_numbers_entry.insert("1.0", "123456:Voornaam Achternaam")

root.mainloop()

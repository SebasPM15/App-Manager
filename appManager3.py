#!/home/formos1/venv/bin/python
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import threading
import re
from datetime import datetime
from tkcalendar import DateEntry

from tkinterdnd2 import TkinterDnD, DND_FILES

# ===================== CONFIG =====================
APPS = {
    "KP Drink": "com.perfect.kpdrink",
    "KP Grill": "com.perfect.kpgrill",
    "KP Fry": "com.perfect.kpfry",
    "KP Prep C": "com.perfect.kpprepc",
    "KP Make": "com.perfect.kpmake",
    "KP Pack": "com.perfect.pack",
    "KP Prep TB": "com.perfect.kppreptb",
    "KP Queue": "com.perfect.kpqueue"
}

DEVICE_MAP = {}

# ===================== HELPERS =====================
def set_readonly(widget, value):
    widget.config(state="normal")
    widget.delete(1.0, tk.END)
    if value:
        widget.insert(tk.END, value)
    widget.config(state="disabled")

def run_adb_command(command):
    set_readonly(command_text, " ".join(command))
    set_readonly(output_text, "Ejecutando...\n")
    try:
        result = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=True
        )
        set_readonly(output_text, result or "Success")
    except subprocess.CalledProcessError as e:
        set_readonly(output_text, e.output)

def run_adb_thread(command):
    threading.Thread(
        target=run_adb_command,
        args=(command,),
        daemon=True
    ).start()

def run_raw_thread(command):
    threading.Thread(
        target=lambda: subprocess.Popen(command),
        daemon=True
    ).start()

def clear_views():
    set_readonly(command_text, "")
    set_readonly(output_text, "")

# ===================== DEVICE INFO =====================
def get_foreground_app(device):
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "shell", "dumpsys", "window"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        match = re.search(r"mCurrentFocus.*? (\S+)/", result)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "unknown"

def get_connected_devices():
    try:
        result = subprocess.check_output(["adb", "devices"], text=True)
        lines = result.strip().split("\n")[1:]
        return [line.split()[0] for line in lines if "device" in line]
    except Exception:
        return []

def refresh_devices():
    DEVICE_MAP.clear()
    devices = get_connected_devices()
    display_list = []

    for dev in devices:
        app = get_foreground_app(dev)
        label = f"{dev}  |  {app}"
        DEVICE_MAP[label] = dev
        display_list.append(label)

    device_combo["values"] = display_list

    if display_list:
        device_combo.current(0)
        status_label.config(text="Device conectado ✔", foreground="green")
    else:
        status_label.config(text="No hay devices conectados", foreground="red")

def get_selected_device():
    label = device_combo.get()
    if not label or label not in DEVICE_MAP:
        messagebox.showerror("Error", "Selecciona un device")
        return None
    return DEVICE_MAP[label]

def get_selected_app():
    app = app_combo.get()
    if not app:
        messagebox.showerror("Error", "Selecciona una aplicación")
        return None
    return APPS[app]

def on_device_change(event=None):
    """Detecta la app corriendo cuando cambia el device seleccionado"""
    device = get_selected_device()
    if not device:
        return
    
    current_app = get_foreground_app(device)
    
    # Buscar si la app actual coincide con alguna de las apps conocidas
    for app_name, package in APPS.items():
        if package == current_app:
            app_combo.set(app_name)
            return
    
    # Si no se encuentra, limpiar selección
    app_combo.set("")

# ===================== ACTIONS =====================
def uninstall_app():
    device = get_selected_device()
    package = get_selected_app()
    if not device or not package:
        return
    run_adb_thread(["adb", "-s", device, "uninstall", package])

def force_stop_app():
    device = get_selected_device()
    package = get_selected_app()
    if not device or not package:
        return
    run_adb_thread(["adb", "-s", device, "shell", "am", "force-stop", package])

def clear_app_data():
    device = get_selected_device()
    package = get_selected_app()
    if not device or not package:
        return
    run_adb_thread(["adb", "-s", device, "shell", "pm", "clear", package])

def launch_app():
    device = get_selected_device()
    package = get_selected_app()
    if not device or not package:
        return
    run_adb_thread([
        "adb", "-s", device, "shell",
        "monkey", "-p", package,
        "-c", "android.intent.category.LAUNCHER", "1"
    ])

def clean_and_start():
    device = get_selected_device()
    package = get_selected_app()
    if not device or not package:
        return

    def task():
        run_adb_command(["adb", "-s", device, "shell", "pm", "clear", package])
        run_adb_command([
            "adb", "-s", device, "shell",
            "monkey", "-p", package,
            "-c", "android.intent.category.LAUNCHER", "1"
        ])

    threading.Thread(target=task, daemon=True).start()

def open_scrcpy():
    device = get_selected_device()
    if not device:
        return
    run_raw_thread(["scrcpy", "-s", device])

# ===================== DEVICE COMMANDS =====================
def disable_wifi():
    device = get_selected_device()
    if not device:
        return
    
    response = messagebox.askyesno(
        "Desactivar WiFi",
        "¿Estás seguro de que quieres desactivar el WiFi?\nEl dispositivo se desconectará."
    )
    if response:
        run_adb_thread(["adb", "-s", device, "shell", "svc", "wifi", "disable"])

def apply_date_time():
    device = get_selected_device()
    if not device:
        return

    try:
        date_str = date_entry.get_date().strftime("%Y-%m-%d")
        hour = hour_spin.get().zfill(2)
        minute = minute_spin.get().zfill(2)
        second = second_spin.get().zfill(2)
        time_str = f"{hour}:{minute}:{second}"
        
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"No se pudo obtener la fecha/hora: {str(e)}"
        )
        return

    adb_format = dt.strftime("%m%d%H%M%Y.%S")

    def task():
        run_adb_command([
            "adb", "-s", device, "shell",
            "settings", "put", "global", "auto_time", "0"
        ])
        run_adb_command([
            "adb", "-s", device, "shell",
            "date", adb_format
        ])

    threading.Thread(target=task, daemon=True).start()

# ===================== APK INSTALL =====================
def install_apk(apk_path):
    device = get_selected_device()
    if not device:
        return

    apk_path = apk_path.strip("{}")

    if not apk_path.lower().endswith(".apk"):
        messagebox.showerror("Error", "El archivo no es un APK")
        return

    if not os.path.exists(apk_path):
        messagebox.showerror("Error", "Archivo APK no encontrado")
        return

    run_adb_thread(["adb", "-s", device, "install", "-r", apk_path])

def on_drop(event):
    install_apk(event.data)

# ===================== UI =====================
root = TkinterDnD.Tk()
root.title("ADB App Manager")
root.geometry("620x820")

frame = ttk.Frame(root, padding=15)
frame.pack(fill="both", expand=True)

# Device
ttk.Label(frame, text="Device conectado (app activa):").pack(anchor="w")
device_combo = ttk.Combobox(frame, state="readonly")
device_combo.pack(fill="x")
device_combo.bind("<<ComboboxSelected>>", on_device_change)

ttk.Button(frame, text="Refresh devices", command=refresh_devices).pack(pady=5)
status_label = ttk.Label(frame, text="")
status_label.pack()

# ===================== COMMAND DEVICES =====================
ttk.Separator(frame).pack(fill="x", pady=15)
ttk.Label(frame, text="Command Devices", font=("Segoe UI", 10, "bold")).pack(anchor="w")

tk.Button(
    frame,
    text="🔴 Apagar WiFi",
    bg="#e74c3c",
    fg="white",
    font=("Segoe UI", 9, "bold"),
    command=disable_wifi,
    cursor="hand2"
).pack(fill="x", pady=5)

date_time_frame = ttk.Frame(frame)
date_time_frame.pack(fill="x", pady=10)

# Fecha con calendario
ttk.Label(date_time_frame, text="Fecha:").grid(row=0, column=0, sticky="w", pady=5)
date_entry = DateEntry(
    date_time_frame,
    width=18,
    background='darkblue',
    foreground='white',
    borderwidth=2,
    date_pattern='yyyy-mm-dd',
    locale='es_ES'
)
date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Hora con spinboxes
ttk.Label(date_time_frame, text="Hora:").grid(row=1, column=0, sticky="w", pady=5)

time_frame = ttk.Frame(date_time_frame)
time_frame.grid(row=1, column=1, sticky="w", padx=5, pady=5)

hour_spin = tk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f")
hour_spin.pack(side="left")
hour_spin.delete(0, "end")
hour_spin.insert(0, datetime.now().strftime("%H"))

tk.Label(time_frame, text=":").pack(side="left")

minute_spin = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
minute_spin.pack(side="left")
minute_spin.delete(0, "end")
minute_spin.insert(0, datetime.now().strftime("%M"))

tk.Label(time_frame, text=":").pack(side="left")

second_spin = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
second_spin.pack(side="left")
second_spin.delete(0, "end")
second_spin.insert(0, datetime.now().strftime("%S"))

ttk.Button(
    date_time_frame,
    text="Aplicar Fecha y Hora",
    command=apply_date_time
).grid(row=2, column=0, columnspan=2, pady=10)

# App
ttk.Label(frame, text="Aplicación:").pack(anchor="w", pady=(15, 0))
app_combo = ttk.Combobox(frame, state="readonly", values=list(APPS.keys()))
app_combo.pack(fill="x")

# Buttons
btn_frame = ttk.Frame(frame)
btn_frame.pack(pady=15, fill="x")

tk.Button(btn_frame, text="Uninstall", bg="#e74c3c", fg="white",
          command=uninstall_app).grid(row=0, column=0, padx=5, sticky="ew")

tk.Button(btn_frame, text="Force Stop", bg="#e67e22", fg="white",
          command=force_stop_app).grid(row=0, column=1, padx=5, sticky="ew")

tk.Button(btn_frame, text="Clear Storage", bg="#f1c40f",
          command=clear_app_data).grid(row=0, column=2, padx=5, sticky="ew")

tk.Button(btn_frame, text="Launch App", bg="#2ecc71", fg="white",
          command=launch_app).grid(row=0, column=3, padx=5, sticky="ew")

tk.Button(btn_frame, text="Clean & Start", bg="#3498db", fg="white",
          command=clean_and_start).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

tk.Button(btn_frame, text="SCRCPY", bg="#9b59b6", fg="white",
          command=open_scrcpy).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="ew")

btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

# Drag & Drop APK
ttk.Label(frame, text="Instalar APK (Drag & Drop):").pack(anchor="w", pady=(15, 5))

apk_drop = tk.Label(
    frame,
    text="Arrastra aquí el archivo APK",
    relief="ridge",
    height=3,
    background="#ecf0f1"
)
apk_drop.pack(fill="x")
apk_drop.drop_target_register(DND_FILES)
apk_drop.dnd_bind("<<Drop>>", on_drop)

# Clear
ttk.Button(frame, text="Clear command & output", command=clear_views).pack(pady=10)

# Command
ttk.Label(frame, text="ADB Command executed:").pack(anchor="w")
command_text = tk.Text(frame, height=2, bg="#f4f4f4", state="disabled")
command_text.pack(fill="x", pady=5)

# Output
ttk.Label(frame, text="Output:").pack(anchor="w")
output_text = tk.Text(frame, height=10, state="disabled")
output_text.pack(fill="both", expand=True)

refresh_devices()
root.mainloop()


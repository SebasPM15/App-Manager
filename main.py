#!/usr/bin/env python3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import re
import json
import os
from pathlib import Path
from datetime import datetime
from queue import Queue
import time

# ===================== CONFIGURACIÓN DE RUTAS =====================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

# Resolviendo ejecutables en macOS
ADB_PATH = "/usr/local/bin/adb" if os.path.exists("/usr/local/bin/adb") else "adb"
SCRCPY_PATH = "/usr/local/bin/scrcpy" if os.path.exists("/usr/local/bin/scrcpy") else "scrcpy"

# Cargar y guardar config.json
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("apps", {})
        except Exception:
            return {}
    return {}

def save_config(apps_dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"apps": apps_dict}, f, indent=4)
        return True
    except Exception:
        return False

# Inicializar apps
APPS = load_config()

# Tema de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ===================== LÓGICA ADB (THREAD-SAFE) =====================
class ADBManager:
    @staticmethod
    def run_command(cmd):
        """Ejecuta un comando subprocess de forma síncrona y segura."""
        # Reemplazar adb/scrcpy con rutas completas si es necesario
        if cmd[0] == "adb":
            cmd[0] = ADB_PATH
        elif cmd[0] == "scrcpy":
            cmd[0] = SCRCPY_PATH
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "Tiempo de espera agotado", -1
        except FileNotFoundError:
            return "", "ADB o Scrcpy no encontrados en el sistema", -2
        except Exception as e:
            return "", str(e), -3

    @staticmethod
    def get_devices():
        try:
            result = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')[1:]
            devices = []
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    devices.append(parts[0])
            return devices
        except Exception:
            return []

    @staticmethod
    def get_device_details(device):
        details = {
            "model": "Desconocido",
            "android_ver": "Desconocida",
            "sdk_ver": "Desconocida",
            "ip": "Desconocida",
            "battery_level": 0,
            "battery_temp": "Desconocida",
            "battery_status": "Desconocido",
            "connection_type": "USB",
            "foreground_app": "Ninguna / Pantalla apagada"
        }
        if not device:
            return details
        
        # Modelo
        out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "getprop", "ro.product.model"])
        if out: details["model"] = out
        
        # Marca
        brand, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "getprop", "ro.product.brand"])
        if brand: details["model"] = f"{brand.capitalize()} {details['model']}"
        
        # Android Ver
        out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "getprop", "ro.build.version.release"])
        if out: details["android_ver"] = out
        
        # SDK Ver
        out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "getprop", "ro.build.version.sdk"])
        if out: details["sdk_ver"] = out

        # IP wlan0 y tipo de conexión
        if ":" in device:
            details["connection_type"] = "WiFi"
            details["ip"] = device.split(":")[0]
        else:
            details["connection_type"] = "USB"
            out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "ip", "addr", "show", "wlan0"])
            match = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out)
            if match:
                details["ip"] = match.group(1)
            else:
                # Fallback general
                out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "ip", "addr"])
                matches = re.findall(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out)
                for ip in matches:
                    if not ip.startswith("127."):
                        details["ip"] = ip
                        break

        # Batería
        out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "dumpsys", "battery"])
        if out:
            level_match = re.search(r"level:\s+(\d+)", out)
            if level_match: details["battery_level"] = int(level_match.group(1))
            temp_match = re.search(r"temperature:\s+(\d+)", out)
            if temp_match: details["battery_temp"] = f"{float(temp_match.group(1))/10.0} °C"
            status_match = re.search(r"status:\s+(\d+)", out)
            if status_match:
                status_code = int(status_match.group(1))
                if status_code == 2: details["battery_status"] = "Cargando"
                elif status_code == 3: details["battery_status"] = "Descargando"
                elif status_code == 5: details["battery_status"] = "Llena"
                else: details["battery_status"] = "Desconectada"

        # Foreground App
        out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "dumpsys", "activity", "activities"])
        match = re.search(r"mResumedActivity:.*? (\S+)/", out)
        if not match:
            out, _, _ = ADBManager.run_command(["adb", "-s", device, "shell", "dumpsys", "window", "windows"])
            match = re.search(r"mCurrentFocus.*? (\S+)/", out)
        if match:
            details["foreground_app"] = match.group(1)
            
        return details

# ===================== INTERFAZ PRINCIPAL =====================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ADB Nexus Manager Pro")
        self.geometry("950x850")
        self.minsize(900, 750)
        
        # Gestión de colas e hilos
        self.log_queue = Queue()
        self.device_map = {}
        self.installed_packages = []
        self.current_device_details = {}
        
        # Hilo del Logcat
        self.logcat_process = None
        self.logcat_thread = None
        self.logcat_running = False
        self.logcat_filter_app = False
        
        # Hilo de grabación de video
        self.record_process = None
        self.is_recording = False
        
        self._build_ui()
        self._refresh_devices()
        self._process_log_queue()
        
    def _build_ui(self):
        # Grid principal: 1 fila, 2 columnas (Sidebar y Contenido)
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ----------------- SIDEBAR -----------------
        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color="#1e1e24")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(6, weight=1) # Espacio intermedio
        
        # Título del software
        ctk.CTkLabel(sidebar, text="ADB NEXUS PRO", font=ctk.CTkFont(size=20, weight="bold", family="Helvetica"), text_color="#9b59b6").grid(row=0, column=0, padx=20, pady=(25, 20))
        
        # Selector de Dispositivo
        ctk.CTkLabel(sidebar, text="Dispositivo:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#b2bec3").grid(row=1, column=0, padx=20, pady=(10, 2), sticky="w")
        self.combo_dev = ctk.CTkComboBox(sidebar, state="readonly", command=self._on_device_change)
        self.combo_dev.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_refresh = ctk.CTkButton(sidebar, text="🔄 Refrescar", fg_color="#2c3e50", hover_color="#34495e", command=self._refresh_devices)
        self.btn_refresh.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        # Badge de estado
        self.lbl_status_badge = ctk.CTkLabel(sidebar, text="DESCONECTADO", font=ctk.CTkFont(size=11, weight="bold"), text_color="white", fg_color="#e74c3c", corner_radius=6, height=25)
        self.lbl_status_badge.grid(row=4, column=0, padx=20, pady=(15, 5), sticky="ew")
        
        # Auto-Wireless rápido
        self.btn_sidebar_wifi = ctk.CTkButton(sidebar, text="⚡ Auto-Wireless", fg_color="#27ae60", hover_color="#218c53", command=self._auto_wireless_connect)
        self.btn_sidebar_wifi.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        # Selector de Tema
        self.switch_theme = ctk.CTkSwitch(sidebar, text="Modo Claro", command=self._toggle_theme, font=ctk.CTkFont(size=12))
        self.switch_theme.grid(row=7, column=0, padx=20, pady=20, sticky="s")
        
        # ----------------- CONTENIDO PRINCIPAL (TABS) -----------------
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color="#9b59b6", segmented_button_selected_hover_color="#8e44ad")
        self.tabview.grid(row=0, column=1, padx=15, pady=(5, 15), sticky="nsew")
        
        self.tab_dash = self.tabview.add("Dashboard")
        self.tab_apps = self.tabview.add("Control de Apps")
        self.tab_remote = self.tabview.add("Control Remoto")
        self.tab_wifi = self.tabview.add("Conexión Inalámbrica")
        self.tab_logs = self.tabview.add("Consola y Logs")
        
        self._build_dashboard_tab()
        self._build_apps_tab()
        self._build_remote_tab()
        self._build_wifi_tab()
        self._build_logs_tab()

    # ===================== PESTAÑA 1: DASHBOARD =====================
    def _build_dashboard_tab(self):
        self.tab_dash.grid_columnconfigure(0, weight=1)
        self.tab_dash.grid_columnconfigure(1, weight=1)
        
        # Panel Izquierdo: Info del Dispositivo
        frame_info = ctk.CTkFrame(self.tab_dash)
        frame_info.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        frame_info.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_info, text="Información General", font=ctk.CTkFont(size=15, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, columnspan=2, padx=15, pady=15, sticky="w")
        
        labels = [
            ("Marca y Modelo:", "dash_model", "Cargando..."),
            ("Versión Android:", "dash_android", "Cargando..."),
            ("IP en Red local:", "dash_ip", "Cargando..."),
            ("Conexión:", "dash_conn", "Cargando..."),
            ("App Foreground:", "dash_foreground", "Cargando..."),
            ("Servidor ADB:", "dash_adb", "Online")
        ]
        
        self.dash_labels = {}
        for idx, (title, key, default) in enumerate(labels, start=1):
            ctk.CTkLabel(frame_info, text=title, font=ctk.CTkFont(weight="bold")).grid(row=idx, column=0, padx=15, pady=10, sticky="w")
            lbl = ctk.CTkLabel(frame_info, text=default, text_color="#bdc3c7")
            lbl.grid(row=idx, column=1, padx=15, pady=10, sticky="w")
            self.dash_labels[key] = lbl
            
        # Panel Derecho: Batería y Acciones Rápidas
        frame_right = ctk.CTkFrame(self.tab_dash)
        frame_right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        frame_right.grid_columnconfigure(0, weight=1)
        
        # Batería
        ctk.CTkLabel(frame_right, text="Estado de Batería", font=ctk.CTkFont(size=15, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.lbl_battery_pct = ctk.CTkLabel(frame_right, text="Batería: 0%", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_battery_pct.grid(row=1, column=0, padx=15, pady=(5, 2), sticky="w")
        
        self.bar_battery = ctk.CTkProgressBar(frame_right, progress_color="#2ecc71")
        self.bar_battery.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.bar_battery.set(0)
        
        self.lbl_battery_detail = ctk.CTkLabel(frame_right, text="Temp: -- | Estado: --", text_color="#bdc3c7")
        self.lbl_battery_detail.grid(row=3, column=0, padx=15, pady=5, sticky="w")
        
        # Separador / Acciones
        ctk.CTkLabel(frame_right, text="Acciones Rápidas", font=ctk.CTkFont(size=15, weight="bold"), text_color="#9b59b6").grid(row=4, column=0, padx=15, pady=(20, 10), sticky="w")
        
        self.btn_scrcpy_dash = ctk.CTkButton(frame_right, text="🖥️ Abrir Espejo de Pantalla (Scrcpy)", fg_color="#9b59b6", hover_color="#8e44ad", font=ctk.CTkFont(weight="bold"), height=40, command=self._scrcpy)
        self.btn_scrcpy_dash.grid(row=5, column=0, padx=15, pady=10, sticky="ew")
        
        self.btn_sync_time_dash = ctk.CTkButton(frame_right, text="⏰ Sincronizar Reloj de Mac", fg_color="#34495e", hover_color="#2c3e50", command=self._apply_mac_datetime)
        self.btn_sync_time_dash.grid(row=6, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_ss_dash = ctk.CTkButton(frame_right, text="📸 Capturar Pantalla a Escritorio", fg_color="#1abc9c", hover_color="#16a085", command=self._take_screenshot)
        self.btn_ss_dash.grid(row=7, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_reboot_dash = ctk.CTkButton(frame_right, text="🔄 Reiniciar Dispositivo", fg_color="#e67e22", hover_color="#d35400", command=self._reboot_device)
        self.btn_reboot_dash.grid(row=8, column=0, padx=15, pady=5, sticky="ew")

    # ===================== PESTAÑA 2: CONTROL DE APPS =====================
    def _build_apps_tab(self):
        self.tab_apps.grid_columnconfigure(0, weight=1) # Columna Izquierda: Favoritas
        self.tab_apps.grid_columnconfigure(1, weight=1) # Columna Derecha: Todas las Instaladas
        self.tab_apps.grid_rowconfigure(0, weight=1)
        
        # ----- COLUMNA IZQUIERDA: FAVORITAS -----
        frame_favs = ctk.CTkFrame(self.tab_apps)
        frame_favs.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        frame_favs.grid_columnconfigure(0, weight=1)
        frame_favs.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_favs, text="Aplicaciones Favoritas (config.json)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        # Scrollable list for favorites
        self.scroll_favs = ctk.CTkScrollableFrame(frame_favs)
        self.scroll_favs.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_favs.grid_columnconfigure(0, weight=1)
        
        # ----- COLUMNA DERECHA: INSTALADAS Y CONTROL -----
        frame_inst = ctk.CTkFrame(self.tab_apps)
        frame_inst.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        frame_inst.grid_columnconfigure(0, weight=1)
        frame_inst.grid_rowconfigure(3, weight=1) # El scroll de instaladas toma peso
        
        ctk.CTkLabel(frame_inst, text="Todas las Instaladas en Dispositivo", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        # Buscador
        self.entry_search = ctk.CTkEntry(frame_inst, placeholder_text="Buscar aplicación...")
        self.entry_search.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.entry_search.bind("<KeyRelease>", self._filter_installed_apps)
        
        # Segmented button for filter type
        self.seg_app_type = ctk.CTkSegmentedButton(frame_inst, values=["Terceros (-3)", "Sistema (-s)", "Todas"], command=self._refresh_installed_list)
        self.seg_app_type.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.seg_app_type.set("Terceros (-3)")
        
        # Scrollable list for installed packages
        self.scroll_installed = ctk.CTkScrollableFrame(frame_inst)
        self.scroll_installed.grid(row=3, column=0, padx=15, pady=5, sticky="nsew")
        self.scroll_installed.grid_columnconfigure(0, weight=1)
        
        # Botón Add to Favorites
        self.btn_add_fav = ctk.CTkButton(frame_inst, text="⭐ Agregar a Favoritas", fg_color="#9b59b6", hover_color="#8e44ad", state="disabled", command=self._add_selected_to_favorites)
        self.btn_add_fav.grid(row=4, column=0, padx=15, pady=10, sticky="ew")
        
        # ----- ACCIONES DE APLICACIÓN Y CARGA DE APK -----
        frame_actions = ctk.CTkFrame(self.tab_apps, fg_color="transparent")
        frame_actions.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        for i in range(5): frame_actions.grid_columnconfigure(i, weight=1)
        
        # Etiqueta de App Seleccionada
        self.lbl_selected_app_action = ctk.CTkLabel(frame_actions, text="App Seleccionada: Ninguna", font=ctk.CTkFont(weight="bold"), text_color="#9b59b6")
        self.lbl_selected_app_action.grid(row=0, column=0, columnspan=5, padx=10, pady=5, sticky="w")
        self.selected_package = None
        
        # Fila de botones de acción
        self.btn_act_launch = ctk.CTkButton(frame_actions, text="🚀 Launch", fg_color="#2ecc71", hover_color="#27ae60", state="disabled", command=self._launch)
        self.btn_act_launch.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_act_stop = ctk.CTkButton(frame_actions, text="🛑 Force Stop", fg_color="#e67e22", hover_color="#d35400", state="disabled", command=self._force_stop)
        self.btn_act_stop.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_act_clear = ctk.CTkButton(frame_actions, text="🧹 Clear Data", fg_color="#f1c40f", text_color="black", hover_color="#f39c12", state="disabled", command=self._clear_data)
        self.btn_act_clear.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        self.btn_act_uninstall = ctk.CTkButton(frame_actions, text="🗑️ Uninstall", fg_color="#e74c3c", hover_color="#c0392b", state="disabled", command=self._uninstall)
        self.btn_act_uninstall.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        
        self.btn_act_clean_start = ctk.CTkButton(frame_actions, text="✨ Clean & Start", fg_color="#3498db", hover_color="#2980b9", state="disabled", command=self._clean_start)
        self.btn_act_clean_start.grid(row=1, column=4, padx=5, pady=5, sticky="ew")
        
        # Fila de permisos y APK
        self.btn_perm_window = ctk.CTkButton(frame_actions, text="🔒 Permiso Pantalla (Overlay)", fg_color="#34495e", hover_color="#2c3e50", state="disabled", command=self._grant_overlay_permission)
        self.btn_perm_window.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Zona interactiva para APK
        self.btn_install_apk_zone = ctk.CTkButton(frame_actions, text="📦 Seleccionar e Instalar archivo APK...", fg_color="#16a085", hover_color="#117a65", command=self._install_apk)
        self.btn_install_apk_zone.grid(row=2, column=2, columnspan=3, padx=5, pady=5, sticky="ew")
        
        self.prog_install = ctk.CTkProgressBar(frame_actions, height=8, progress_color="#1abc9c")
        self.prog_install.grid(row=3, column=0, columnspan=5, padx=5, pady=(5, 10), sticky="ew")
        self.prog_install.set(0)

    # ===================== PESTAÑA 3: CONTROL REMOTO =====================
    def _build_remote_tab(self):
        self.tab_remote.grid_columnconfigure(0, weight=1)
        self.tab_remote.grid_columnconfigure(1, weight=1)
        
        # Columna Izquierda: Botones de Hardware y Control
        frame_hw = ctk.CTkFrame(self.tab_remote)
        frame_hw.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        frame_hw.grid_columnconfigure(0, weight=1)
        frame_hw.grid_columnconfigure(1, weight=1)
        frame_hw.grid_columnconfigure(2, weight=1)
        
        ctk.CTkLabel(frame_hw, text="Controles de Navegación", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, columnspan=3, padx=15, pady=15, sticky="w")
        
        # Fila de navegación tipo dispositivo
        ctk.CTkButton(frame_hw, text="◀️ Volver\n(Back)", fg_color="#2c3e50", hover_color="#34495e", height=50, command=lambda: self._remote_key(4)).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(frame_hw, text="⚫ Inicio\n(Home)", fg_color="#2c3e50", hover_color="#34495e", height=50, command=lambda: self._remote_key(3)).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(frame_hw, text="⏹️ Menú\n(Apps)", fg_color="#2c3e50", hover_color="#34495e", height=50, command=lambda: self._remote_key(82)).grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(frame_hw, text="Controles de Dispositivo", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=2, column=0, columnspan=3, padx=15, pady=15, sticky="w")
        
        # Fila 2 de botones
        ctk.CTkButton(frame_hw, text="🔌 Encendido\n(Power)", fg_color="#c0392b", hover_color="#962d22", height=50, command=lambda: self._remote_key(26)).grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(frame_hw, text="🔊 Vol+\n(Volume Up)", fg_color="#27ae60", hover_color="#218c53", height=50, command=lambda: self._remote_key(24)).grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(frame_hw, text="🔉 Vol-\n(Volume Down)", fg_color="#27ae60", hover_color="#218c53", height=50, command=lambda: self._remote_key(25)).grid(row=3, column=2, padx=5, pady=5, sticky="ew")
        
        # Deslizador de brillo
        ctk.CTkLabel(frame_hw, text="Brillo de Pantalla:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=15, pady=(20, 5), sticky="w")
        self.slider_brightness = ctk.CTkSlider(frame_hw, from_=0, to=255, command=self._on_brightness_change)
        self.slider_brightness.grid(row=4, column=1, columnspan=2, padx=15, pady=(20, 5), sticky="ew")
        self.slider_brightness.set(128)
        
        # Columna Derecha: Entrada de Texto y Grabación
        frame_utils = ctk.CTkFrame(self.tab_remote)
        frame_utils.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        frame_utils.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame_utils, text="Teclado Remoto (Enviar Texto)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        self.entry_remote_text = ctk.CTkEntry(frame_utils, placeholder_text="Escribe texto para enviar al dispositivo...")
        self.entry_remote_text.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.entry_remote_text.bind("<Return>", lambda e: self._send_remote_text())
        
        ctk.CTkButton(frame_utils, text="✈ Enviar Texto", fg_color="#9b59b6", hover_color="#8e44ad", command=self._send_remote_text).grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        
        # Grabadora de Video y Capturas avanzadas
        ctk.CTkLabel(frame_utils, text="Captura y Grabación de Pantalla", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=3, column=0, padx=15, pady=(25, 10), sticky="w")
        
        ctk.CTkButton(frame_utils, text="📸 Capturar y abrir imagen", fg_color="#1abc9c", hover_color="#16a085", height=40, command=self._take_screenshot).grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_record_video = ctk.CTkButton(frame_utils, text="🎥 Iniciar Grabación de Pantalla (Máx 3m)", fg_color="#e74c3c", hover_color="#c0392b", height=40, command=self._toggle_screen_record)
        self.btn_record_video.grid(row=5, column=0, padx=15, pady=5, sticky="ew")

    # ===================== PESTAÑA 4: CONEXIÓN INALÁMBRICA =====================
    def _build_wifi_tab(self):
        self.tab_wifi.grid_columnconfigure(0, weight=1)
        self.tab_wifi.grid_columnconfigure(1, weight=1)
        
        # Panel Izquierdo: Auto WiFi
        frame_auto = ctk.CTkFrame(self.tab_wifi)
        frame_auto.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        frame_auto.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame_auto, text="Auto-Conexión Inalámbrica", font=ctk.CTkFont(size=15, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        instructions = (
            "Para conectar un dispositivo sin cables de forma automática:\n\n"
            "1. Conecte el dispositivo a la Mac usando el cable USB.\n"
            "2. Asegúrese de que ambos estén en la misma red WiFi.\n"
            "3. Haga clic en el botón de abajo.\n"
            "4. Cuando la consola confirme la conexión, desconecte el cable."
        )
        ctk.CTkLabel(frame_auto, text=instructions, justify="left", text_color="#bdc3c7", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=10, sticky="w")
        
        self.btn_auto_wifi = ctk.CTkButton(frame_auto, text="⚡ Activar ADB WiFi Automático", fg_color="#27ae60", hover_color="#218c53", height=45, command=self._auto_wireless_connect)
        self.btn_auto_wifi.grid(row=2, column=0, padx=15, pady=20, sticky="ew")
        
        # Panel Derecho: Conexiones Manuales y Pairing
        frame_manual = ctk.CTkFrame(self.tab_wifi)
        frame_manual.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        frame_manual.grid_columnconfigure(1, weight=1)
        
        # Conexión Manual
        ctk.CTkLabel(frame_manual, text="Conexión Inalámbrica Manual", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=0, column=0, columnspan=2, padx=15, pady=15, sticky="w")
        
        ctk.CTkLabel(frame_manual, text="Dirección IP:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.entry_wifi_ip = ctk.CTkEntry(frame_manual, placeholder_text="192.168.x.x")
        self.entry_wifi_ip.grid(row=1, column=1, padx=15, pady=5, sticky="ew")
        
        ctk.CTkLabel(frame_manual, text="Puerto:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.entry_wifi_port = ctk.CTkEntry(frame_manual, placeholder_text="5555")
        self.entry_wifi_port.grid(row=2, column=1, padx=15, pady=5, sticky="ew")
        
        btn_wifi_frame = ctk.CTkFrame(frame_manual, fg_color="transparent")
        btn_wifi_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        btn_wifi_frame.grid_columnconfigure(0, weight=1)
        btn_wifi_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(btn_wifi_frame, text="🔌 Conectar", fg_color="#3498db", hover_color="#2980b9", command=self._manual_connect).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(btn_wifi_frame, text="❌ Desconectar Todo", fg_color="#e74c3c", hover_color="#c0392b", command=self._disconnect_all).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Vinculación Android 11+ (Pairing)
        ctk.CTkLabel(frame_manual, text="Emparejar Dispositivo (Android 11+)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").grid(row=4, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="w")
        
        ctk.CTkLabel(frame_manual, text="IP y Puerto:").grid(row=5, column=0, padx=15, pady=5, sticky="w")
        self.entry_pair_ip_port = ctk.CTkEntry(frame_manual, placeholder_text="192.168.x.x:xxxxx")
        self.entry_pair_ip_port.grid(row=5, column=1, padx=15, pady=5, sticky="ew")
        
        ctk.CTkLabel(frame_manual, text="Código Emp.:").grid(row=6, column=0, padx=15, pady=5, sticky="w")
        self.entry_pair_code = ctk.CTkEntry(frame_manual, placeholder_text="Código de 6 dígitos")
        self.entry_pair_code.grid(row=6, column=1, padx=15, pady=5, sticky="ew")
        
        ctk.CTkButton(frame_manual, text="🔑 Emparejar (ADB Pair)", fg_color="#9b59b6", hover_color="#8e44ad", command=self._manual_pair).grid(row=7, column=0, columnspan=2, padx=15, pady=10, sticky="ew")

    # ===================== PESTAÑA 5: CONSOLA Y LOGS =====================
    def _build_logs_tab(self):
        self.tab_logs.grid_columnconfigure(0, weight=1)
        self.tab_logs.grid_rowconfigure(1, weight=1)
        self.tab_logs.grid_rowconfigure(3, weight=0) # Caja ejecutora
        
        # Panel superior de controles Logcat
        frame_controls = ctk.CTkFrame(self.tab_logs)
        frame_controls.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        self.btn_logcat_toggle = ctk.CTkButton(frame_controls, text="▶ Iniciar Logcat", fg_color="#27ae60", hover_color="#218c53", width=120, command=self._toggle_logcat)
        self.btn_logcat_toggle.grid(row=0, column=0, padx=10, pady=10)
        
        self.btn_logcat_clear = ctk.CTkButton(frame_controls, text="🗑 Limpiar Logs", fg_color="#2c3e50", hover_color="#34495e", width=110, command=self._clear_logs_screen)
        self.btn_logcat_clear.grid(row=0, column=1, padx=10, pady=10)
        
        self.btn_logcat_save = ctk.CTkButton(frame_controls, text="💾 Guardar Log", fg_color="#34495e", hover_color="#2c3e50", width=110, command=self._save_logcat_to_file)
        self.btn_logcat_save.grid(row=0, column=2, padx=10, pady=10)
        
        # Filtro de nivel
        ctk.CTkLabel(frame_controls, text="Nivel:").grid(row=0, column=3, padx=(10, 5), pady=10)
        self.combo_log_level = ctk.CTkComboBox(frame_controls, values=["Verbose (V)", "Debug (D)", "Info (I)", "Warning (W)", "Error (E)"], width=130, state="readonly", command=self._change_logcat_level)
        self.combo_log_level.grid(row=0, column=4, padx=5, pady=10)
        self.combo_log_level.set("Verbose (V)")
        
        # Filtro por App activa
        self.check_log_filter_app = ctk.CTkCheckBox(frame_controls, text="Filtrar por App activa", command=self._toggle_logcat_app_filter)
        self.check_log_filter_app.grid(row=0, column=5, padx=10, pady=10)
        
        # Terminal externa
        self.btn_ext_terminal = ctk.CTkButton(frame_controls, text="🐚 Abrir Terminal Shell", fg_color="#9b59b6", hover_color="#8e44ad", width=140, command=self._open_external_shell)
        self.btn_ext_terminal.grid(row=0, column=6, padx=10, pady=10)
        
        # Visualizador de Logs
        self.text_logs = ctk.CTkTextbox(self.tab_logs, state="disabled", font=ctk.CTkFont(family="Menlo", size=11), fg_color="#1a1a24")
        self.text_logs.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # Buscador / Filtro rápido por texto
        frame_filter = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        frame_filter.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        frame_filter.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_filter, text="Filtro rápido (texto):").grid(row=0, column=0, padx=(5, 10))
        self.entry_log_filter_txt = ctk.CTkEntry(frame_filter, placeholder_text="Filtrar logs desplegados...")
        self.entry_log_filter_txt.grid(row=0, column=1, sticky="ew")
        
        # Consola ejecutora de comandos ADB libres
        frame_terminal = ctk.CTkFrame(self.tab_logs)
        frame_terminal.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")
        frame_terminal.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_terminal, text="ADB Command:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.entry_custom_cmd = ctk.CTkEntry(frame_terminal, placeholder_text="Escribe tu comando sin 'adb' (ej. shell getprop)")
        self.entry_custom_cmd.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.entry_custom_cmd.bind("<Return>", lambda e: self._execute_custom_command())
        
        ctk.CTkButton(frame_terminal, text="Ejecutar", fg_color="#9b59b6", hover_color="#8e44ad", command=self._execute_custom_command).grid(row=0, column=2, padx=15, pady=10)

    # ===================== LOGICA DE CONSOLA Y COLAS =====================
    def _log(self, msg):
        """Añade logs formateados a la consola local de la UI."""
        self.text_logs.configure(state="normal")
        self.text_logs.insert("end", msg + "\n")
        
        # Autoscroll si está al final o cerca
        self.text_logs.see("end")
        self.text_logs.configure(state="disabled")

    def _process_log_queue(self):
        """Monitorea la cola para pintar eventos sin colgar la UI."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._log(msg)
        except Exception:
            pass
        self.after(100, self._process_log_queue)

    def _run_task(self, cmd, success_msg=None):
        """Ejecuta un comando en un hilo asíncrono y reporta a la consola."""
        def task():
            cmd_str = " ".join(cmd)
            self.log_queue.put(f"▶ Ejecutando: {cmd_str}")
            stdout, stderr, code = ADBManager.run_command(cmd)
            if code == 0:
                self.log_queue.put(stdout or success_msg or "✅ Operación Exitosa")
            else:
                self.log_queue.put(f"❌ Error ({code}): {stderr or stdout}")
        threading.Thread(target=task, daemon=True).start()

    # ===================== ACCIONES DE DISPOSITIVOS =====================
    def _refresh_devices(self):
        """Actualiza el listado de dispositivos conectados."""
        devices = ADBManager.get_devices()
        self.device_map.clear()
        
        display_list = []
        for dev in devices:
            # Trae detalles sencillos en segundo plano o rápido
            # Para evitar lentitud, leemos modelo e IP
            model = "Dispositivo"
            out_model, _, _ = ADBManager.run_command(["adb", "-s", dev, "shell", "getprop", "ro.product.model"])
            if out_model: model = out_model
            
            label = f"{dev} | {model}"
            self.device_map[label] = dev
            display_list.append(label)
            
        self.combo_dev.configure(values=display_list)
        
        if display_list:
            # Obtener el actual
            curr = self.combo_dev.get()
            if curr not in display_list:
                self.combo_dev.set(display_list[0])
            self.lbl_status_badge.configure(text="CONECTADO", fg_color="#2ecc71")
            self._on_device_change()
        else:
            self.combo_dev.set("")
            self.lbl_status_badge.configure(text="SIN DISPOSITIVOS", fg_color="#e74c3c")
            self._clear_device_ui()

    def _on_device_change(self, choice=None):
        """Se activa al cambiar o refrescar el dispositivo."""
        dev = self._get_active_device()
        if not dev:
            self._clear_device_ui()
            return
        
        # Desactivar logcat actual
        if self.logcat_running:
            self._stop_logcat()
            
        # Cargar detalles en hilo para evitar congelamientos de UI
        def load_details():
            details = ADBManager.get_device_details(dev)
            self.current_device_details = details
            
            # Cargar listado de apps instaladas del dispositivo
            apps_out, _, _ = ADBManager.run_command(["adb", "-s", dev, "shell", "pm", "list", "packages"])
            packages = [line.replace("package:", "").strip() for line in apps_out.strip().split("\n") if line.strip()]
            self.installed_packages = sorted(packages)
            
            # Ejecutar actualización de UI en el hilo principal
            self.after(0, lambda: self._update_device_ui(details))
            
        threading.Thread(target=load_details, daemon=True).start()

    def _get_active_device(self):
        label = self.combo_dev.get()
        return self.device_map.get(label)

    def _clear_device_ui(self):
        # Limpiar Dashboard
        for lbl in self.dash_labels.values():
            lbl.configure(text="Desconectado")
        self.lbl_battery_pct.configure(text="Batería: --")
        self.bar_battery.set(0)
        self.lbl_battery_detail.configure(text="Temp: -- | Estado: --")
        
        # Limpiar listados de apps
        for w in self.scroll_favs.winfo_children(): w.destroy()
        for w in self.scroll_installed.winfo_children(): w.destroy()
        self.lbl_selected_app_action.configure(text="App Seleccionada: Ninguna")
        self.selected_package = None
        self._toggle_action_buttons(False)

    def _update_device_ui(self, details):
        # Actualizar Dashboard
        self.dash_labels["dash_model"].configure(text=details["model"])
        self.dash_labels["dash_android"].configure(text=f"Android {details['android_ver']} (SDK {details['sdk_ver']})")
        self.dash_labels["dash_ip"].configure(text=details["ip"])
        self.dash_labels["dash_conn"].configure(text=details["connection_type"])
        self.dash_labels["dash_foreground"].configure(text=details["foreground_app"])
        self.dash_labels["dash_adb"].configure(text="Online")
        
        # Actualizar Batería
        pct = details["battery_level"]
        self.lbl_battery_pct.configure(text=f"Batería: {pct}%")
        self.bar_battery.set(pct / 100.0)
        
        # Color dinámico de la batería
        if pct < 20: self.bar_battery.configure(progress_color="#e74c3c")
        elif pct < 50: self.bar_battery.configure(progress_color="#f1c40f")
        else: self.bar_battery.configure(progress_color="#2ecc71")
        
        self.lbl_battery_detail.configure(text=f"Temp: {details['battery_temp']} | Estado: {details['battery_status']}")
        
        # Leer brillo
        dev = self._get_active_device()
        brightness_out, _, _ = ADBManager.run_command(["adb", "-s", dev, "shell", "settings", "get", "system", "screen_brightness"])
        try:
            val = int(brightness_out)
            self.slider_brightness.set(val)
        except ValueError:
            self.slider_brightness.set(128)
            
        # Dibujar listados de Apps
        self._refresh_favorites_list()
        self._refresh_installed_list()

    # ===================== LOGICA DE APPS (FAVORITAS E INSTALADAS) =====================
    def _refresh_favorites_list(self):
        """Dibuja la lista de aplicaciones favoritas en el panel izquierdo."""
        # Limpiar
        for w in self.scroll_favs.winfo_children():
            w.destroy()
            
        global APPS
        APPS = load_config()
        
        dev = self._get_active_device()
        
        # Crear filas en la lista de favoritas
        for name, package in APPS.items():
            # Crear contenedor
            row = ctk.CTkFrame(self.scroll_favs, fg_color="transparent")
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=1)
            
            # Indicador de punto verde/rojo
            is_installed = package in self.installed_packages
            dot = "🟢" if is_installed else "🔴"
            status_text = f"{dot} {name}"
            
            # Nombre de la app
            btn_select = ctk.CTkButton(
                row, 
                text=status_text, 
                anchor="w", 
                fg_color="transparent", 
                hover_color="#2c3e50", 
                text_color="white",
                command=lambda p=package, n=name: self._select_app_for_action(p, n)
            )
            btn_select.grid(row=0, column=0, sticky="ew", padx=5)
            
            # Botón eliminar de favoritas
            btn_del = ctk.CTkButton(
                row,
                text="🗑",
                width=30,
                fg_color="transparent",
                hover_color="#c0392b",
                text_color="#e74c3c",
                command=lambda n=name: self._remove_from_favorites(n)
            )
            btn_del.grid(row=0, column=1, padx=5)

    def _refresh_installed_list(self, filter_type=None):
        """Pinta las apps instaladas obtenidas dinámicamente con filtros."""
        for w in self.scroll_installed.winfo_children():
            w.destroy()
            
        dev = self._get_active_device()
        if not dev:
            return
            
        ftype = self.seg_app_type.get()
        search_q = self.entry_search.get().strip().lower()
        
        # Filtrar apps
        def task():
            cmd = ["adb", "-s", dev, "shell", "pm", "list", "packages"]
            if ftype == "Terceros (-3)":
                cmd.append("-3")
            elif ftype == "Sistema (-s)":
                cmd.append("-s")
                
            out, _, _ = ADBManager.run_command(cmd)
            pkgs = [line.replace("package:", "").strip() for line in out.strip().split("\n") if line.strip()]
            pkgs = sorted(pkgs)
            
            # Filtrar por búsqueda de texto
            if search_q:
                pkgs = [p for p in pkgs if search_q in p.lower()]
                
            self.after(0, lambda: self._draw_installed_packages(pkgs))
            
        threading.Thread(target=task, daemon=True).start()

    def _draw_installed_packages(self, pkgs):
        # Limpiar por seguridad
        for w in self.scroll_installed.winfo_children():
            w.destroy()
            
        for pkg in pkgs:
            row = ctk.CTkFrame(self.scroll_installed, fg_color="transparent")
            row.pack(fill="x", pady=1)
            row.grid_columnconfigure(0, weight=1)
            
            # Botón con nombre del paquete
            btn_pkg = ctk.CTkButton(
                row,
                text=pkg,
                anchor="w",
                fg_color="transparent",
                hover_color="#2c3e50",
                text_color="#bdc3c7",
                font=ctk.CTkFont(size=11),
                command=lambda p=pkg: self._select_app_for_action(p)
            )
            btn_pkg.grid(row=0, column=0, sticky="ew")

    def _filter_installed_apps(self, event=None):
        self._refresh_installed_list()

    def _select_app_for_action(self, package, friendly_name=None):
        self.selected_package = package
        display_name = friendly_name or package
        self.lbl_selected_app_action.configure(text=f"App Seleccionada: {display_name} ({package})")
        self._toggle_action_buttons(True)
        self.btn_add_fav.configure(state="normal")

    def _toggle_action_buttons(self, state):
        val = "normal" if state else "disabled"
        self.btn_act_launch.configure(state=val)
        self.btn_act_stop.configure(state=val)
        self.btn_act_clear.configure(state=val)
        self.btn_act_uninstall.configure(state=val)
        self.btn_act_clean_start.configure(state=val)
        self.btn_perm_window.configure(state=val)

    def _add_selected_to_favorites(self):
        pkg = self.selected_package
        if not pkg:
            return
            
        # Preguntar nombre amistoso para la app
        dialog = ctk.CTkInputDialog(text="Nombre amistoso para la aplicación:", title="Agregar a Favoritas")
        name = dialog.get_input()
        
        if name and name.strip():
            global APPS
            APPS[name.strip()] = pkg
            if save_config(APPS):
                self._refresh_favorites_list()
                messagebox.showinfo("Éxito", f"App '{name}' guardada en favoritas.")
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def _remove_from_favorites(self, name):
        global APPS
        if name in APPS:
            del APPS[name]
            if save_config(APPS):
                self._refresh_favorites_list()
                messagebox.showinfo("Éxito", f"App '{name}' eliminada de favoritas.")
            else:
                messagebox.showerror("Error", "No se pudo actualizar la configuración.")

    # Acciones de procesos en Apps
    def _launch(self):
        dev = self._get_active_device()
        pkg = self.selected_package
        if dev and pkg:
            self._run_task(["adb", "-s", dev, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"], f"🚀 App iniciada: {pkg}")

    def _force_stop(self):
        dev = self._get_active_device()
        pkg = self.selected_package
        if dev and pkg:
            self._run_task(["adb", "-s", dev, "shell", "am", "force-stop", pkg], f"🛑 App detenida: {pkg}")

    def _clear_data(self):
        dev = self._get_active_device()
        pkg = self.selected_package
        if dev and pkg:
            self._run_task(["adb", "-s", dev, "shell", "pm", "clear", pkg], f"🧹 Datos limpiados: {pkg}")

    def _uninstall(self):
        dev = self._get_active_device()
        pkg = self.selected_package
        if dev and pkg:
            confirm = messagebox.askyesno("Confirmar desinstalación", f"¿Estás seguro de que deseas desinstalar {pkg}?")
            if confirm:
                self._run_task(["adb", "-s", dev, "uninstall", pkg], f"🗑️ App desinstalada: {pkg}")
                # Refrescar listas
                self.after(2000, self._on_device_change)

    def _clean_start(self):
        dev = self._get_active_device()
        pkg = self.selected_package
        if dev and pkg:
            def task():
                self.log_queue.put(f"▶ Limpiando y arrancando: {pkg}")
                ADBManager.run_command(["adb", "-s", dev, "shell", "pm", "clear", pkg])
                time.sleep(0.5)
                stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
                if code == 0:
                    self.log_queue.put(f"✨ Éxito: App limpia y arrancada.")
                else:
                    self.log_queue.put(f"❌ Error al iniciar app: {stderr}")
            threading.Thread(target=task, daemon=True).start()

    def _grant_overlay_permission(self):
        dev = self._get_active_device()
        pkg = self.selected_package
        if dev and pkg:
            self._run_task([
                "adb", "-s", dev, "shell", "appops", "set", pkg, "SYSTEM_ALERT_WINDOW", "allow"
            ], f"🔒 Permiso de superposición (Overlay) otorgado a: {pkg}")

    def _install_apk(self):
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
            return
            
        filepath = filedialog.askopenfilename(
            title="Seleccionar APK para instalar",
            filetypes=[("APK files", "*.apk"), ("All files", "*.*")]
        )
        if not filepath:
            return
            
        # Animación progreso simulado
        self.prog_install.set(0.1)
        self.prog_install.configure(progress_color="#f1c40f")
        
        def task():
            self.log_queue.put(f"📦 Instalando APK: {os.path.basename(filepath)}")
            self.after(200, lambda: self.prog_install.set(0.4))
            
            stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "install", "-r", filepath])
            
            if code == 0:
                self.log_queue.put(f"✅ APK instalado con éxito: {os.path.basename(filepath)}")
                self.after(0, lambda: [self.prog_install.set(1.0), self.prog_install.configure(progress_color="#2ecc71")])
                self.after(1000, self._on_device_change)
            else:
                self.log_queue.put(f"❌ Fallo al instalar APK: {stderr or stdout}")
                self.after(0, lambda: [self.prog_install.set(1.0), self.prog_install.configure(progress_color="#e74c3c")])
                
        threading.Thread(target=task, daemon=True).start()

    # ===================== LOGICA CONTROL REMOTO (REMOTE TAB) =====================
    def _remote_key(self, keycode):
        dev = self._get_active_device()
        if dev:
            # Ejecución asíncrona rápida para no retrasar botones
            threading.Thread(
                target=lambda: ADBManager.run_command(["adb", "-s", dev, "shell", "input", "keyevent", str(keycode)]),
                daemon=True
            ).start()

    def _on_brightness_change(self, val):
        dev = self._get_active_device()
        if dev:
            brightness = int(val)
            # Actualiza en segundo plano
            threading.Thread(
                target=lambda: ADBManager.run_command(["adb", "-s", dev, "shell", "settings", "put", "system", "screen_brightness", str(brightness)]),
                daemon=True
            ).start()

    def _send_remote_text(self):
        dev = self._get_active_device()
        text = self.entry_remote_text.get()
        if not dev or not text:
            return
            
        def task():
            # ADB text input reemplaza espacios por %s
            escaped = text.replace(" ", "%s")
            # Escapar comillas
            escaped = escaped.replace("'", "\\'").replace('"', '\\"')
            ADBManager.run_command(["adb", "-s", dev, "shell", "input", "text", escaped])
            self.log_queue.put(f"⌨ Texto enviado: {text}")
            
        threading.Thread(target=task, daemon=True).start()
        self.entry_remote_text.delete(0, "end")

    def _take_screenshot(self):
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
            return
            
        def task():
            self.log_queue.put("📸 Tomando captura de pantalla...")
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            dest_path = os.path.expanduser(f"~/Desktop/{filename}")
            
            # Tomar captura
            stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "shell", "screencap", "-p", "/sdcard/screenshot.png"])
            if code != 0:
                self.log_queue.put(f"❌ Error al tomar captura en el dispositivo: {stderr}")
                return
                
            # Extraer archivo
            stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "pull", "/sdcard/screenshot.png", dest_path])
            if code == 0:
                self.log_queue.put(f"✅ Captura guardada en: {dest_path}")
                # Borrar temporal del dispositivo
                ADBManager.run_command(["adb", "-s", dev, "shell", "rm", "/sdcard/screenshot.png"])
                # Abrir archivo automáticamente en macOS
                subprocess.run(["open", dest_path])
            else:
                self.log_queue.put(f"❌ Error al extraer captura: {stderr}")
                
        threading.Thread(target=task, daemon=True).start()

    def _toggle_screen_record(self):
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
            return
            
        if self.is_recording:
            # Detener grabación
            self.is_recording = False
            self.btn_record_video.configure(text="🎥 Procesando video...", fg_color="#f1c40f", state="disabled")
            
            def stop_task():
                self.log_queue.put("⏹️ Deteniendo grabación...")
                # Enviar señal SIGINT al screenrecord en android
                ADBManager.run_command(["adb", "-s", dev, "shell", "pkill", "-2", "screenrecord"])
                time.sleep(2.0) # Esperar a que guarde correctamente
                
                filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                dest_path = os.path.expanduser(f"~/Desktop/{filename}")
                
                # Extraer video
                stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "pull", "/sdcard/video.mp4", dest_path])
                if code == 0:
                    self.log_queue.put(f"✅ Video guardado en: {dest_path}")
                    ADBManager.run_command(["adb", "-s", dev, "shell", "rm", "/sdcard/video.mp4"])
                    subprocess.run(["open", dest_path])
                else:
                    self.log_queue.put(f"❌ Error al extraer video: {stderr or stdout}")
                    
                self.after(0, lambda: [
                    self.btn_record_video.configure(text="🎥 Iniciar Grabación de Pantalla (Máx 3m)", fg_color="#e74c3c", state="normal")
                ])
                
            threading.Thread(target=stop_task, daemon=True).start()
            
        else:
            # Iniciar grabación
            self.is_recording = True
            self.btn_record_video.configure(text="⏹️ Detener Grabación", fg_color="#d35400")
            
            def record_task():
                self.log_queue.put("🎥 Grabación iniciada en el dispositivo móvil (máximo 3 minutos)...")
                # Limpiar archivo previo
                ADBManager.run_command(["adb", "-s", dev, "shell", "rm", "/sdcard/video.mp4"])
                
                # Inicia de forma persistente hasta 180 seg
                ADBManager.run_command(["adb", "-s", dev, "shell", "screenrecord", "--time-limit", "180", "/sdcard/video.mp4"])
                
                # Si termina solo por timeout
                if self.is_recording:
                    self.after(0, self._toggle_screen_record)
                    
            threading.Thread(target=record_task, daemon=True).start()

    def _reboot_device(self):
        dev = self._get_active_device()
        if dev:
            confirm = messagebox.askyesno("Confirmar Reinicio", "¿Estás seguro de que deseas reiniciar el dispositivo?")
            if confirm:
                self._run_task(["adb", "-s", dev, "reboot"], "🔄 Reiniciando dispositivo...")
                self.after(2000, self._refresh_devices)

    def _apply_mac_datetime(self):
        dev = self._get_active_device()
        if not dev:
            return
            
        dt = datetime.now()
        adb_format = dt.strftime("%m%d%H%M%Y.%S")
        
        def task():
            self.log_queue.put("⏰ Sincronizando fecha y hora con la Mac...")
            ADBManager.run_command(["adb", "-s", dev, "shell", "settings", "put", "global", "auto_time", "0"])
            stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "shell", "date", adb_format])
            if code == 0:
                self.log_queue.put(f"✅ Reloj sincronizado: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.log_queue.put(f"❌ Error al sincronizar hora: {stderr or stdout}")
                
        threading.Thread(target=task, daemon=True).start()

    # ===================== LOGICA CONEXION INALAMBRICA (WIFI TAB) =====================
    def _auto_wireless_connect(self):
        """Implementa la auto-conexión inalámbrica de un dispositivo USB."""
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo conectado por USB primero.")
            return
            
        if ":" in dev:
            messagebox.showwarning("Advertencia", "El dispositivo seleccionado ya está conectado de forma inalámbrica.")
            return
            
        def task():
            self.log_queue.put("⚡ Iniciando proceso de Auto-Wireless...")
            
            # 1. Obtener la IP
            details = ADBManager.get_device_details(dev)
            ip = details["ip"]
            if not ip or ip == "Desconocida":
                self.log_queue.put("❌ Error: No se pudo obtener la IP local del dispositivo. Asegúrate de estar en el mismo WiFi.")
                return
                
            self.log_queue.put(f"📡 IP del dispositivo detectada: {ip}")
            
            # 2. Configurar puerto TCP/IP
            self.log_queue.put("⚙️ Activando puerto de red ADB tcpip 5555...")
            stdout, stderr, code = ADBManager.run_command(["adb", "-s", dev, "tcpip", "5555"])
            if code != 0:
                self.log_queue.put(f"❌ Fallo al iniciar modo TCP/IP: {stderr or stdout}")
                return
                
            time.sleep(2.0)
            
            # 3. Conectarse inalámbricamente
            self.log_queue.put(f"🔌 Conectando a {ip}:5555...")
            stdout, stderr, code = ADBManager.run_command(["adb", "connect", f"{ip}:5555"])
            
            if "connected to" in stdout.lower() or code == 0:
                self.log_queue.put(f"🎉 ¡Conexión inalámbrica exitosa a {ip}:5555!")
                self.after(0, lambda: messagebox.showinfo(
                    "Auto-Wireless Completo",
                    f"Se ha conectado correctamente a {ip}:5555.\n\nYa puedes desconectar el cable USB del dispositivo."
                ))
                self.after(1000, self._refresh_devices)
            else:
                self.log_queue.put(f"❌ Fallo al conectar inalámbricamente: {stderr or stdout}")
                
        threading.Thread(target=task, daemon=True).start()

    def _manual_connect(self):
        ip = self.entry_wifi_ip.get().strip()
        port = self.entry_wifi_port.get().strip() or "5555"
        if not ip:
            messagebox.showerror("Error", "Introduce una dirección IP válida.")
            return
            
        self._run_task(["adb", "connect", f"{ip}:{port}"], f"🔌 Intentando conectar a {ip}:{port}")
        self.after(2000, self._refresh_devices)

    def _disconnect_all(self):
        self._run_task(["adb", "disconnect"], "❌ Todos los dispositivos desconectados.")
        self.after(2000, self._refresh_devices)

    def _manual_pair(self):
        ip_port = self.entry_pair_ip_port.get().strip()
        code = self.entry_pair_code.get().strip()
        if not ip_port or not code:
            messagebox.showerror("Error", "Ingresa la IP:Puerto y el Código de Emparejamiento.")
            return
            
        self._run_task(["adb", "pair", ip_port, code], f"🔑 Vinculando con {ip_port}...")
        self.after(2000, self._refresh_devices)

    # ===================== LOGICA LOGCAT Y TERMINAL (LOGS TAB) =====================
    def _toggle_logcat(self):
        if self.logcat_running:
            self._stop_logcat()
        else:
            self._start_logcat()

    def _start_logcat(self):
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
            return
            
        self.logcat_running = True
        self.btn_logcat_toggle.configure(text="⏸ Pausar Logcat", fg_color="#e67e22", hover_color="#d35400")
        self.log_queue.put("▶ Iniciar captura de logs Logcat...")
        
        # Obtener comandos de logcat
        level = self.combo_log_level.get().split("(")[1].split(")")[0] # Captura V, D, I, W, E
        
        def log_reader():
            # Construir comando
            cmd = [ADB_PATH, "-s", dev, "logcat", f"*:{level}", "-v", "time"]
            
            # Si filtramos por PID de app
            if self.logcat_filter_app and self.selected_package:
                # Buscar PID de la app activa
                pid_out, _, _ = ADBManager.run_command(["adb", "-s", dev, "shell", "pidof", self.selected_package])
                pid = pid_out.strip()
                if pid:
                    # ADB logcat en versiones modernas soporta --pid
                    self.log_queue.put(f"🔍 Filtrando Logs para paquete {self.selected_package} (PID: {pid})")
                    cmd = [ADB_PATH, "-s", dev, "logcat", f"*:{level}", "--pid", pid, "-v", "time"]
                else:
                    self.log_queue.put(f"⚠️ App {self.selected_package} no está corriendo. Desactivando filtro de PID.")
                    
            try:
                # Limpiar buffer de logcat antes
                subprocess.run([ADB_PATH, "-s", dev, "logcat", "-c"])
                
                self.logcat_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                
                while self.logcat_running:
                    line = self.logcat_process.stdout.readline()
                    if not line:
                        break
                        
                    # Aplicar filtro por texto si existe
                    txt_filter = self.entry_log_filter_txt.get().strip().lower()
                    if txt_filter and txt_filter not in line.lower():
                        continue
                        
                    self.log_queue.put(line.strip())
            except Exception as e:
                self.log_queue.put(f"❌ Error en lectura de logs: {str(e)}")
            finally:
                self._stop_logcat()
                
        self.logcat_thread = threading.Thread(target=log_reader, daemon=True)
        self.logcat_thread.start()

    def _stop_logcat(self):
        self.logcat_running = False
        if self.logcat_process:
            self.logcat_process.terminate()
            self.logcat_process = None
        self.after(0, lambda: self.btn_logcat_toggle.configure(text="▶ Iniciar Logcat", fg_color="#27ae60", hover_color="#218c53"))
        self.log_queue.put("⏸ Captura de logs pausada.")

    def _clear_logs_screen(self):
        self.text_logs.configure(state="normal")
        self.text_logs.delete("1.0", "end")
        self.text_logs.configure(state="disabled")

    def _change_logcat_level(self, event=None):
        if self.logcat_running:
            # Reiniciar lector para aplicar nivel
            self._stop_logcat()
            self.after(200, self._start_logcat)

    def _toggle_logcat_app_filter(self):
        self.logcat_filter_app = self.check_log_filter_app.get()
        if self.logcat_filter_app and not self.selected_package:
            messagebox.showwarning("Advertencia", "Por favor selecciona una aplicación en la pestaña de Apps primero para usar este filtro.")
            self.check_log_filter_app.deselect()
            self.logcat_filter_app = False
            return
            
        if self.logcat_running:
            self._stop_logcat()
            self.after(200, self._start_logcat)

    def _save_logcat_to_file(self):
        log_content = self.text_logs.get("1.0", "end").strip()
        if not log_content:
            messagebox.showwarning("Vacio", "No hay logs para guardar.")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="Guardar Logcat",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"logcat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filepath:
            try:
                with open(filepath, "w") as f:
                    f.write(log_content)
                messagebox.showinfo("Éxito", f"Logs guardados en:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{str(e)}")

    def _execute_custom_command(self):
        dev = self._get_active_device()
        cmd_text = self.entry_custom_cmd.get().strip()
        if not dev or not cmd_text:
            return
            
        # Limpiar prefijo "adb" si el usuario lo escribió
        if cmd_text.lower().startswith("adb "):
            cmd_text = cmd_text[4:]
        # Limpiar "-s device " si el usuario lo incluyó
        cmd_text = re.sub(r'^-s\s+\S+\s+', '', cmd_text)
        
        # Dividir argumentos de forma segura
        import shlex
        args = shlex.split(cmd_text)
        
        # Comando completo
        full_cmd = ["adb", "-s", dev] + args
        self._run_task(full_cmd)
        self.entry_custom_cmd.delete(0, "end")

    # ===================== TERMINAL NATIVA MACOS (APPLESCRIPT) =====================
    def _open_external_shell(self):
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
            return
            
        # Comando para abrir terminal de macOS corriendo adb shell
        script = f'tell application "Terminal" to do script "{ADB_PATH} -s {dev} shell"'
        self.log_queue.put("🐚 Abriendo Terminal externa macOS con ADB shell...")
        subprocess.run(["osascript", "-e", script])

    # ===================== SCRCPY (PANTALLA ESPEJO) =====================
    def _scrcpy(self):
        dev = self._get_active_device()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
            return
            
        # Iniciar scrcpy en hilo independiente
        def launch_scrcpy():
            self.log_queue.put(f"🖥️ Lanzando espejo de pantalla (scrcpy) para {dev}...")
            # Iniciamos scrcpy con algunos parámetros útiles para rendimiento en WiFi/USB
            cmd = [SCRCPY_PATH, "-s", dev, "--window-title", f"Espejo ADB - {dev}", "--always-on-top"]
            stdout, stderr, code = ADBManager.run_command(cmd)
            if code != 0:
                self.log_queue.put(f"❌ Fallo al iniciar Scrcpy: {stderr or stdout}")
                self.after(0, lambda: messagebox.showerror(
                    "Error de Scrcpy",
                    f"No se pudo iniciar Scrcpy:\n\n{stderr or stdout}\n\nVerifica que esté instalado en su Mac."
                ))
                
        threading.Thread(target=launch_scrcpy, daemon=True).start()

    # ===================== CONTROL DE TEMA Y EVENTOS =====================
    def _toggle_theme(self):
        if self.switch_theme.get():
            ctk.set_appearance_mode("Light")
            self.switch_theme.configure(text="Modo Oscuro")
        else:
            ctk.set_appearance_mode("Dark")
            self.switch_theme.configure(text="Modo Claro")

if __name__ == "__main__":
    app = App()
    app.mainloop()
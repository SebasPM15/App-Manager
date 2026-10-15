import customtkinter as ctk
import threading
import time
import os
import re
import shlex
from datetime import datetime
from queue import Queue
from tkinter import filedialog, messagebox

from core.adb_manager import ADBManager

from ui.theme import Colors, Fonts, Dims
from ui.widgets import Label, Box, font, make_button, make_eyebrow, make_status_dot
from ui.sidebar import Sidebar
from ui.scroll_area import ScrollArea
from ui.console_panel import ConsolePanel
from ui.tabs.dashboard import DashboardTab
from ui.tabs.apps_tab import AppsTab
from ui.tabs.remote_tab import RemoteTab

POLL_INTERVAL = 2.0
RESIZE_SETTLE_MS = 140
DEFAULT_PORT = "5555"
IP_PATTERN = re.compile(r"^\d{1,3}(\.\d{1,3}){3}(:\d{1,5})?$")
LAUNCHER_CATEGORY = "android.intent.category.LAUNCHER"


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("ADB Control · Device Manager")
        self.geometry("1280x900")
        self.minsize(900, 560)
        self.configure(fg_color=Colors.BG)

        self._log_queue = Queue()
        self._device_map: dict[str, str] = {}
        self._model_cache: dict[str, str] = {}
        self._scan_result = None
        self._last_signature = None
        self._last_scan_at = time.time()
        self._active_device: str | None = None
        self._current_view = "dashboard"
        self._last_size = None
        self._frozen = False
        self._thaw_job = None

        self._logcat_proc     = None
        self._logcat_running  = False
        self._logcat_filter   = False

        self._build_ui()
        self._process_queues()
        self._refresh_devices()
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=Dims.SIDEBAR_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=Dims.CONSOLE_H)

        self.sidebar = Sidebar(
            self,
            on_connect=self._connect_input,
            on_device_change=self._on_device_change,
            on_navigate=self._show_view,
            on_open_shell=self._open_adb_shell,
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        workspace = Box(self, fg_color="transparent", corner_radius=0)
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(2, weight=1)

        topbar = ctk.CTkFrame(workspace, fg_color="transparent", height=Dims.TOPBAR_H, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew", padx=Dims.PAD_LG)
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)
        self.lbl_breadcrumb = Label(topbar, text="", font=font(Fonts.SIZE_SM), text_color="#bac7d6", anchor="w")
        self.lbl_breadcrumb.grid(row=0, column=0, sticky="w", pady=16)
        sync = Box(topbar, fg_color="transparent")
        sync.grid(row=0, column=1, sticky="e")
        make_status_dot(sync, online=True).pack(side="left")
        self.lbl_sync = Label(sync, text="Sincronizado", font=font(Fonts.SIZE_XS), text_color="#708398")
        self.lbl_sync.pack(side="left", padx=(6, 0))
        Box(workspace, height=1, fg_color=Colors.LINE_SOFT, corner_radius=0).grid(row=0, column=0, sticky="sew")

        heading = Box(workspace, fg_color="transparent")
        heading.grid(row=1, column=0, sticky="ew", padx=Dims.PAD_LG, pady=(18, 16))
        heading.grid_columnconfigure(0, weight=1)
        copy = Box(heading, fg_color="transparent")
        copy.grid(row=0, column=0, sticky="w")
        make_eyebrow(copy, "Dispositivo activo").pack(anchor="w")
        self.lbl_title = Label(copy, text="", font=font(Fonts.SIZE_XL, "bold"), text_color=Colors.TEXT, anchor="w")
        self.lbl_title.pack(anchor="w", pady=(6, 4))
        self.lbl_subtitle = Label(copy, text="", font=font(Fonts.SIZE_XS), text_color="#8191a5", anchor="w")
        self.lbl_subtitle.pack(anchor="w")
        make_button(heading, " Actualizar", self._refresh_all, icon_name="refresh").grid(row=0, column=1, sticky="ne")

        self.content = Box(workspace, fg_color="transparent")
        self.content.grid(row=2, column=0, sticky="nsew", padx=Dims.PAD_LG, pady=(0, 16))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        dash_cb = {
            "scrcpy":     self._scrcpy,
            "screenshot": self._take_screenshot,
            "sync_time":  self._sync_time,
            "reboot":     self._reboot_device,
        }
        apps_cb = {
            "launch":            self._launch,
            "force_stop":        self._force_stop,
            "clear_data":        self._clear_data,
            "uninstall":         self._uninstall,
            "clean_start":       self._clean_start,
            "grant_overlay":     self._grant_overlay,
            "install_apk":       self._install_apk,
            "refresh_installed": self._load_installed_packages,
            "select_app":        self._select_app,
        }
        remote_cb = {
            "remote_key":        self._remote_key,
            "brightness_change": self._on_brightness_change,
            "screenshot":        self._take_screenshot,
            "sync_time":         self._sync_time,
            "open_settings":     self._open_settings,
            "power_off":         self._power_off,
            "set_wifi":          self._set_wifi,
            "set_data":          self._set_data,
        }

        self._views = {}
        factories = {
            "dashboard": (DashboardTab, dash_cb),
            "apps":      (AppsTab, apps_cb),
            "remote":    (RemoteTab, remote_cb),
        }
        tabs = {}
        for key, (factory, callbacks) in factories.items():
            area = ScrollArea(self.content, background=Colors.BG)
            tab = factory(area.body, callbacks)
            tab.pack(fill="both", expand=True)
            self._views[key] = area
            tabs[key] = tab
        self.tab_dashboard = tabs["dashboard"]
        self.tab_apps = tabs["apps"]
        self.tab_remote = tabs["remote"]
        self._show_view("dashboard")
        self.after(1000, self._tick_sync)
        self.bind("<Configure>", self._on_window_configure)
        self.bind_all("<MouseWheel>", self._on_mouse_wheel)
        console_cb = {
            "toggle_logcat":        self._toggle_logcat,
            "clear_logs":           self._clear_logs,
            "save_logs":            self._save_logs,
            "execute_cmd":          self._execute_cmd,
            "change_log_level":     self._change_log_level,
            "toggle_logcat_filter": self._toggle_logcat_filter,
            "on_expand_change":     self._on_console_expand,
        }
        self.console = ConsolePanel(self, console_cb)
        self.console.grid(row=1, column=1, sticky="nsew")

    def _emit(self, msg: str, raw: bool = False):
        self._emit((msg, raw))

    def _show_view(self, view_id: str):
        self._current_view = view_id
        for key, view in self._views.items():
            if key == view_id:
                view.grid(row=0, column=0, sticky="nsew")
            else:
                view.grid_remove()
        self.sidebar.set_active_view(view_id)
        self._update_heading()

    def _update_heading(self):
        titles = {
            "dashboard": ("Dashboard", "Resumen del dispositivo", "Estado general y acciones rápidas para tu dispositivo Android."),
            "apps":      ("Aplicaciones", "Aplicaciones instaladas", "Explora y administra los paquetes instalados en el dispositivo."),
            "remote":    ("Control remoto", "Control remoto", "Controla tu dispositivo de forma remota mediante ADB."),
        }
        crumb, title, subtitle = titles[self._current_view]
        self.lbl_breadcrumb.configure(text=f"ADB Control   ›   {crumb}")
        self.lbl_title.configure(text=title)
        self.lbl_subtitle.configure(text=subtitle)

    def _on_mouse_wheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            handler = getattr(widget, "handle_wheel", None)
            if handler is not None and handler(event.delta):
                return
            widget = widget.master

    def _on_window_configure(self, event):
        if event.widget is not self:
            return
        size = (event.width, event.height)
        if size == self._last_size:
            return
        self._last_size = size
        if not self._frozen:
            self._frozen = True
            self.content.grid_remove()
            self.console.body.grid_remove()
        if self._thaw_job is not None:
            self.after_cancel(self._thaw_job)
        self._thaw_job = self.after(RESIZE_SETTLE_MS, self._thaw)

    def _thaw(self):
        self._thaw_job = None
        self._frozen = False
        self.content.grid()
        if self.console.is_expanded():
            self.console.body.grid()

    def _tick_sync(self):
        elapsed = int(time.time() - self._last_scan_at)
        self.lbl_sync.configure(text=f"Sincronizado hace {elapsed} s")
        self.after(1000, self._tick_sync)

    def _refresh_all(self):
        self._refresh_devices()
        if self.sidebar.get_selected_device_id():
            self._on_device_change()

    def _process_queues(self):
        batch = []
        while len(batch) < 300 and not self._log_queue.empty():
            batch.append(self._log_queue.get_nowait())
        if batch:
            self.console.log_batch(batch)
        result, self._scan_result = self._scan_result, None
        if result is not None:
            self._apply_scan(*result)
        self.after(100, self._process_queues)

    def _run_task(self, cmd: list, success_msg: str = ""):
        def task():
            self._emit(f"$ {' '.join(cmd)}")
            out, err, code = ADBManager.run(cmd)
            if code == 0:
                self._emit(out or success_msg or "OK")
            else:
                self._emit(f"Error ({code}): {err or out}")
        threading.Thread(target=task, daemon=True).start()

    def _adb_shell(self, *args: str, success_msg: str = ""):
        dev = self._get_device()
        if dev:
            self._run_task(["adb", "-s", dev, "shell", *args], success_msg)

    def _get_device(self) -> str | None:
        dev = self.sidebar.get_selected_device_id()
        if not dev:
            messagebox.showerror("Error", "Selecciona un dispositivo activo.")
        return dev

    def _connect_input(self, text: str):
        tokens = [t for t in re.split(r"[\s,;]+", text.strip()) if t]
        if not tokens:
            return

        disconnect = tokens[0].lower() in ("disconnect", "desconectar")
        if disconnect:
            tokens = tokens[1:]

        targets = []
        for token in tokens:
            if not IP_PATTERN.match(token):
                self._emit(f"IP no válida: {token}")
                continue
            targets.append(token if ":" in token else f"{token}:{DEFAULT_PORT}")

        if disconnect:
            commands = [["disconnect", t] for t in targets] or [["disconnect"]]
            self._run_connection(commands, None)
        elif targets:
            self._run_connection([["connect", t] for t in targets], targets[0])

    def _run_connection(self, commands: list, select: str | None):
        def run_one(cmd: list):
            self._emit(f"$ adb {' '.join(cmd)}")
            out, err, code = ADBManager.run(["adb", *cmd], timeout=8)
            self._emit(out or err or f"Error ({code})")

        def task():
            threads = [threading.Thread(target=run_one, args=(cmd,), daemon=True) for cmd in commands]
            for th in threads:
                th.start()
            for th in threads:
                th.join()
            self._scan(select)

        threading.Thread(target=task, daemon=True).start()

    def _scan(self, select: str | None = None):
        states = ADBManager.list_devices()
        device_map = {}
        for dev, state in states.items():
            if state != "device":
                continue
            if dev not in self._model_cache:
                self._model_cache[dev] = ADBManager.get_device_model(dev)
            device_map[f"{dev}  │  {self._model_cache[dev]}"] = dev
        self._last_scan_at = time.time()
        self._scan_result = (states, device_map, select)

    def _refresh_devices(self, select: str | None = None):
        threading.Thread(target=self._scan, args=(select,), daemon=True).start()

    def _poll_loop(self):
        while True:
            time.sleep(POLL_INTERVAL)
            try:
                self._scan()
            except Exception:
                pass

    def _apply_scan(self, states: dict, device_map: dict, select: str | None):
        signature = tuple(sorted(states.items()))
        if signature == self._last_signature and select is None:
            return
        self._last_signature = signature
        self._device_map = device_map

        preferred = self.sidebar.combo_dev.get()
        if select:
            preferred = next((label for label, dev in device_map.items() if dev == select), preferred)
        self.sidebar.update_device_list(device_map, preferred_label=preferred)

        pending = [d for d, s in states.items() if s != "device"]
        if device_map:
            text = f"{len(device_map)} conectado" + ("s" if len(device_map) > 1 else "")
            if pending:
                text += f"  ·  sin autorizar: {len(pending)}"
            self.sidebar.set_status(text, ok=True)
        elif pending:
            self.sidebar.set_status("Autoriza la depuración en el dispositivo", ok=False)
        else:
            self.sidebar.set_status("Sin dispositivos", ok=False)

        current = self.sidebar.get_selected_device_id()
        if current != self._active_device:
            self._active_device = current
            if current:
                self._on_device_change()
            else:
                self.sidebar.set_device_summary("", "")
                self.sidebar.set_apps_count(0)
                self.tab_dashboard.clear()
                self.tab_apps.clear()
                self.tab_remote.set_device(None)

    def _on_device_change(self, choice=None):
        dev = self.sidebar.get_selected_device_id()
        if not dev:
            return
        self._active_device = dev
        if self._logcat_running:
            self._stop_logcat()

        def load():
            details = ADBManager.get_device_details(dev)
            pkgs = ADBManager.get_packages(dev)
            third_party = set(ADBManager.get_packages(dev, "-3"))
            brightness = ADBManager.get_screen_brightness(dev)
            self.after(0, lambda: self._update_ui(dev, details, pkgs, third_party, brightness))

        threading.Thread(target=load, daemon=True).start()

    def _update_ui(self, dev: str, details: dict, pkgs: list, third_party: set, brightness: int):
        if dev != self.sidebar.get_selected_device_id():
            return
        name = details.get("model", "")
        self.sidebar.set_device_summary(name, dev)
        self.sidebar.set_apps_count(len(pkgs))
        self.tab_dashboard.update(details, dev)
        self.tab_apps.set_packages(pkgs, third_party)
        self.tab_remote.set_brightness(brightness)
        self.tab_remote.set_device(name, dev)

        foreground = details.get("foreground_app", "")
        if foreground in pkgs:
            self._select_app(foreground)

    def _select_app(self, package: str, friendly_name: str = ""):
        self.tab_apps.set_selected(package, friendly_name)
        dev = self.sidebar.get_selected_device_id()
        if not dev:
            return

        def task():
            version = ADBManager.get_package_version(dev, package)
            self.after(0, lambda: self.tab_apps.set_version(package, version))

        threading.Thread(target=task, daemon=True).start()

    def _load_installed_packages(self, flag: str | None = None):
        dev = self.sidebar.get_selected_device_id()
        if not dev:
            return

        def task():
            pkgs = ADBManager.get_packages(dev)
            third_party = set(ADBManager.get_packages(dev, "-3"))
            self.after(0, lambda: self._apply_packages(dev, pkgs, third_party))

        threading.Thread(target=task, daemon=True).start()

    def _apply_packages(self, dev: str, pkgs: list, third_party: set):
        if dev == self.sidebar.get_selected_device_id():
            self.sidebar.set_apps_count(len(pkgs))
            self.tab_apps.set_packages(pkgs, third_party)

    def _selected(self) -> tuple[str | None, str | None]:
        return self.sidebar.get_selected_device_id(), self.tab_apps.selected_package

    def _launch(self):
        dev, pkg = self._selected()
        if dev and pkg:
            self._run_task(["adb", "-s", dev, "shell", "monkey", "-p", pkg, "-c", LAUNCHER_CATEGORY, "1"])

    def _force_stop(self):
        dev, pkg = self._selected()
        if dev and pkg:
            self._run_task(["adb", "-s", dev, "shell", "am", "force-stop", pkg])

    def _clear_data(self):
        dev, pkg = self._selected()
        if dev and pkg and messagebox.askyesno("Confirmar", f"¿Borrar los datos de {pkg}?"):
            self._run_task(["adb", "-s", dev, "shell", "pm", "clear", pkg])

    def _uninstall(self):
        dev, pkg = self._selected()
        if dev and pkg and messagebox.askyesno("Confirmar", f"¿Desinstalar {pkg}?"):
            self._run_task(["adb", "-s", dev, "uninstall", pkg])
            self.tab_apps.set_selected(None)
            self.after(2500, self._load_installed_packages)

    def _clean_start(self):
        dev, pkg = self._selected()
        if not (dev and pkg):
            return
        if not messagebox.askyesno("Confirmar", f"Se borrarán los datos de {pkg} antes de abrirla.\n\n¿Continuar?"):
            return

        def task():
            self._emit(f"Limpiando y abriendo: {pkg}")
            ADBManager.run(["adb", "-s", dev, "shell", "pm", "clear", pkg])
            time.sleep(0.5)
            _, err, code = ADBManager.run(["adb", "-s", dev, "shell", "monkey", "-p", pkg, "-c", LAUNCHER_CATEGORY, "1"])
            self._emit("Aplicación limpia y abierta." if code == 0 else f"Error: {err}")

        threading.Thread(target=task, daemon=True).start()

    def _grant_overlay(self):
        dev, pkg = self._selected()
        if dev and pkg:
            self._run_task(["adb", "-s", dev, "shell", "appops", "set", pkg, "SYSTEM_ALERT_WINDOW", "allow"])

    def _install_apk(self):
        dev = self._get_device()
        if not dev:
            return
        filepath = filedialog.askopenfilename(title="Seleccionar APK", filetypes=[("APK", "*.apk"), ("Todos", "*.*")])
        if not filepath:
            return
        name = os.path.basename(filepath)
        self.tab_apps.set_installing(True)

        def task():
            self._emit(f"Instalando: {name}")
            _, err, code = ADBManager.run(["adb", "-s", dev, "install", "-r", filepath], timeout=300)
            if code == 0:
                self._emit(f"APK instalado: {name}")
                self.after(0, lambda: self.tab_apps.set_installing(False, ok=True))
                self.after(1500, self._load_installed_packages)
            else:
                self._emit(f"Fallo al instalar: {err}")
                self.after(0, lambda: self.tab_apps.set_installing(False, ok=False))

        threading.Thread(target=task, daemon=True).start()

    def _take_screenshot(self):
        dev = self._get_device()
        if not dev:
            return

        def task():
            self._emit("Capturando pantalla...")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(ADBManager.get_desktop_path(), f"screenshot_{ts}.png")
            _, _, c1 = ADBManager.run(["adb", "-s", dev, "shell", "screencap", "-p", "/sdcard/screenshot.png"])
            if c1 != 0:
                self._emit("Error al capturar la pantalla.")
                return
            _, err, c2 = ADBManager.run(["adb", "-s", dev, "pull", "/sdcard/screenshot.png", dest])
            if c2 == 0:
                self._emit(f"Captura guardada: {dest}")
                ADBManager.run(["adb", "-s", dev, "shell", "rm", "/sdcard/screenshot.png"])
                ADBManager.open_file_cross_platform(dest)
            else:
                self._emit(f"Error al extraer la captura: {err}")

        threading.Thread(target=task, daemon=True).start()

    def _reboot_device(self):
        dev = self._get_device()
        if dev and messagebox.askyesno("Confirmar", "¿Reiniciar el dispositivo?"):
            self._run_task(["adb", "-s", dev, "reboot"])

    def _sync_time(self):
        dev = self._get_device()
        if not dev:
            return
        now = datetime.now()
        fmt = now.strftime("%m%d%H%M%Y.%S")

        def task():
            self._emit("Sincronizando reloj...")
            ADBManager.run(["adb", "-s", dev, "shell", "settings", "put", "global", "auto_time", "0"])
            _, _, code = ADBManager.run(["adb", "-s", dev, "shell", "date", fmt])
            if code == 0:
                self._emit(f"Reloj sincronizado: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self._emit("Error al sincronizar el reloj.")

        threading.Thread(target=task, daemon=True).start()

    def _scrcpy(self):
        dev = self._get_device()
        if not dev:
            return

        def task():
            self._emit(f"Lanzando Scrcpy para {dev}...")
            try:
                proc = ADBManager.popen(["scrcpy", "-s", dev, "--window-title", f"Espejo – {dev}"])
                time.sleep(2)
                if proc.poll() is not None and proc.returncode != 0:
                    err = proc.stderr.read()
                    self._emit(f"Scrcpy falló: {err}")
            except FileNotFoundError:
                self._emit("Scrcpy no encontrado. Instálalo primero.")

        threading.Thread(target=task, daemon=True).start()

    def _remote_key(self, keycode: int):
        dev = self.sidebar.get_selected_device_id()
        if dev:
            threading.Thread(
                target=lambda: ADBManager.run(["adb", "-s", dev, "shell", "input", "keyevent", str(keycode)]),
                daemon=True,
            ).start()

    def _on_brightness_change(self, val: float):
        dev = self.sidebar.get_selected_device_id()
        if dev:
            threading.Thread(
                target=lambda: ADBManager.run(["adb", "-s", dev, "shell", "settings", "put", "system", "screen_brightness", str(int(val))]),
                daemon=True,
            ).start()

    def _open_settings(self, action: str):
        self._adb_shell("am", "start", "-a", action)

    def _power_off(self):
        dev = self._get_device()
        if dev and messagebox.askyesno("Confirmar", "¿Apagar el dispositivo?"):
            self._run_task(["adb", "-s", dev, "shell", "reboot", "-p"])

    def _set_wifi(self, enabled: bool):
        dev = self._get_device()
        if not dev:
            return
        if not enabled and ":" in dev:
            if not messagebox.askyesno(
                "Confirmar",
                "Este dispositivo está conectado por WiFi. Desactivar el WiFi cortará la conexión ADB.\n\n¿Continuar?",
            ):
                return
        self.tab_remote.set_wifi_state(enabled)
        self._run_task(["adb", "-s", dev, "shell", "svc", "wifi", "enable" if enabled else "disable"])

    def _set_data(self, enabled: bool):
        self._adb_shell("svc", "data", "enable" if enabled else "disable")

    def _toggle_logcat(self):
        if self._logcat_running:
            self._stop_logcat()
        else:
            self._start_logcat()

    def _start_logcat(self):
        dev = self._get_device()
        if not dev:
            return
        self._logcat_running = True
        self.console.set_logcat_running(True)
        level = self.console.get_log_level_char()
        self._emit(f"Iniciando Logcat [{level}]...")

        def reader():
            process_map: dict[str, str] = {}
            ADBManager.run(["adb", "-s", dev, "logcat", "-c"])
            cmd = ["adb", "-s", dev, "logcat", f"*:{level}", "-v", "year", "-v", "threadtime"]
            self._logcat_proc = ADBManager.popen(cmd)
            pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(.*)$")
            while self._logcat_running:
                line = self._logcat_proc.stdout.readline()
                if not line:
                    break
                txt_filter = self.console.get_filter_text()
                if txt_filter and txt_filter not in line.lower():
                    continue
                fmt = line.strip()
                m = pattern.match(fmt)
                if m:
                    date, tstr, pid, tid, lv, rest = m.groups()
                    pname = process_map.get(pid)
                    if not pname:
                        po, _, _ = ADBManager.run(["adb", "-s", dev, "shell", "cat", f"/proc/{pid}/cmdline"])
                        pname = po.replace("\x00", "").strip() or "unknown"
                        process_map[pid] = pname
                    pkg_name = pname.split(":")[0]
                    if self._logcat_filter and self.tab_apps.selected_package:
                        if pkg_name != self.tab_apps.selected_package:
                            continue
                    fmt = f"{date} {tstr} {pid}-{tid:>5}  {pname[:22]:<22}  {lv}  {rest}"
                self._emit(fmt, raw=True)
            self._stop_logcat()

        threading.Thread(target=reader, daemon=True).start()

    def _stop_logcat(self):
        self._logcat_running = False
        if self._logcat_proc:
            self._logcat_proc.terminate()
            self._logcat_proc = None
        self.after(0, lambda: self.console.set_logcat_running(False))
        self._emit("Logcat pausado.")

    def _toggle_logcat_filter(self):
        self._logcat_filter = self.console.is_filter_app_active()
        if self._logcat_filter and not self.tab_apps.selected_package:
            messagebox.showwarning("Aviso", "Selecciona una aplicación en la pestaña Aplicaciones primero.")
            self.console.check_filter.deselect()
            self._logcat_filter = False
            return
        if self._logcat_running:
            self._stop_logcat()
            self.after(300, self._start_logcat)

    def _change_log_level(self, val: str):
        if self._logcat_running:
            self._stop_logcat()
            self.after(300, self._start_logcat)

    def _clear_logs(self):
        self.console.clear()

    def _save_logs(self):
        content = self.console.get_content()
        if not content:
            messagebox.showwarning("Vacío", "No hay logs para guardar.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Guardar logs",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
            initialfile=f"logcat_{ts}.txt",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Éxito", f"Guardado en:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _execute_cmd(self, cmd_text: str):
        dev = self.sidebar.get_selected_device_id()
        if not dev:
            return
        cmd_text = re.sub(r"^adb\s+", "", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"^-s\s+\S+\s+", "", cmd_text)
        try:
            args = shlex.split(cmd_text)
        except ValueError:
            args = cmd_text.split()
        self._run_task(["adb", "-s", dev] + args)

    def _open_adb_shell(self):
        dev = self._get_device()
        if not dev:
            return
        try:
            ADBManager.open_shell_terminal(dev)
            self._emit(f"Terminal ADB abierta para {dev}")
        except Exception as e:
            messagebox.showerror("Terminal ADB", str(e))

    def _on_console_expand(self, expanded: bool):
        h = Dims.CONSOLE_H if expanded else Dims.CONSOLE_H_BAR
        self.grid_rowconfigure(1, minsize=h)


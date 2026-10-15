"""
adb_manager.py — Toda la lógica de comunicación con ADB.
Separación de responsabilidades: este módulo NO conoce la UI.
"""
import subprocess
import re
import os
import sys
from pathlib import Path

# ─── Rutas de ejecutables (detección multiplataforma) ─────────────────────────
def _find_executable(name: str) -> str:
    """Retorna la ruta completa del ejecutable o el nombre si no se encuentra."""
    IS_MACOS  = sys.platform == "darwin"
    IS_WIN    = sys.platform == "win32"

    candidates = [name]

    if IS_MACOS:
        candidates = [
            f"/usr/local/bin/{name}",
            f"/opt/homebrew/bin/{name}",
            name,
        ]
    elif IS_WIN:
        # Android SDK en rutas comunes de Windows
        home = Path.home()
        candidates = [
            str(home / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / f"{name}.exe"),
            str(home / "scoop" / "apps" / name / "current" / f"{name}.exe"),
            name,
        ]

    for path in candidates:
        if os.path.isfile(path):
            return path
    return name  # fallback: espera que esté en PATH


ADB_PATH    = _find_executable("adb")
SCRCPY_PATH = _find_executable("scrcpy")


# ─── Clase principal ───────────────────────────────────────────────────────────
class ADBManager:

    @staticmethod
    def run(cmd: list, timeout: int = 12) -> tuple[str, str, int]:
        """
        Ejecuta un comando subprocess de forma síncrona y segura.
        Retorna (stdout, stderr, returncode).
        """
        resolved = list(cmd)
        if resolved[0] == "adb":
            resolved[0] = ADB_PATH
        elif resolved[0] == "scrcpy":
            resolved[0] = SCRCPY_PATH

        try:
            result = subprocess.run(
                resolved,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "Tiempo de espera agotado", -1
        except FileNotFoundError:
            return "", f"'{resolved[0]}' no encontrado en el sistema", -2
        except Exception as e:
            return "", str(e), -3

    # ─── Dispositivos ───────────────────────────────────────────────────────
    @staticmethod
    def popen(cmd: list) -> subprocess.Popen:
        resolved = list(cmd)
        if resolved[0] == "adb":
            resolved[0] = ADB_PATH
        elif resolved[0] == "scrcpy":
            resolved[0] = SCRCPY_PATH
        return subprocess.Popen(
            resolved,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    @staticmethod
    def list_devices() -> dict[str, str]:
        out, _, code = ADBManager.run(["adb", "devices"], timeout=6)
        if code != 0:
            return {}
        states = {}
        for line in out.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 2:
                states[parts[0]] = parts[1]
        return states

    @staticmethod
    def get_devices() -> list[str]:
        return [d for d, state in ADBManager.list_devices().items() if state == "device"]

    @staticmethod
    def get_device_model(device: str) -> str:
        """Retorna la cadena 'Marca Modelo' del dispositivo."""
        brand, _, _ = ADBManager.run(["adb", "-s", device, "shell", "getprop", "ro.product.brand"])
        model, _, _ = ADBManager.run(["adb", "-s", device, "shell", "getprop", "ro.product.model"])
        parts = []
        if brand: parts.append(brand.capitalize())
        if model: parts.append(model)
        return " ".join(parts) if parts else "Dispositivo"

    @staticmethod
    def get_device_details(device: str) -> dict:
        """Obtiene todos los detalles del dispositivo en un solo diccionario."""
        details = {
            "model":           "Desconocido",
            "android_ver":     "Desconocida",
            "sdk_ver":         "Desconocida",
            "ip":              "Desconocida",
            "battery_level":   0,
            "battery_temp":    "Desconocida",
            "battery_status":  "Desconocido",
            "connection_type": "USB",
            "foreground_app":  "Ninguna / Pantalla apagada",
        }
        if not device:
            return details

        brand, _, _ = ADBManager.run(["adb", "-s", device, "shell", "getprop", "ro.product.brand"])
        model, _, _ = ADBManager.run(["adb", "-s", device, "shell", "getprop", "ro.product.model"])
        details["brand"] = brand.capitalize() if brand else "Desconocido"
        details["model_name"] = model or "Desconocido"
        details["model"] = " ".join(p for p in (details["brand"] if brand else "", model) if p) or "Desconocido"

        # Versión Android / SDK
        out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "getprop", "ro.build.version.release"])
        if out: details["android_ver"] = out
        out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "getprop", "ro.build.version.sdk"])
        if out: details["sdk_ver"] = out

        # IP y tipo de conexión
        if ":" in device:
            details["connection_type"] = "WiFi"
            details["ip"] = device.split(":")[0]
        else:
            details["connection_type"] = "USB"
            out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "ip", "addr", "show", "wlan0"])
            match = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out)
            if match:
                details["ip"] = match.group(1)
            else:
                out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "ip", "addr"])
                for ip in re.findall(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out):
                    if not ip.startswith("127."):
                        details["ip"] = ip
                        break

        # Batería
        out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "dumpsys", "battery"])
        if out:
            m = re.search(r"level:\s+(\d+)", out)
            if m: details["battery_level"] = int(m.group(1))
            m = re.search(r"temperature:\s+(\d+)", out)
            if m: details["battery_temp"] = f"{float(m.group(1)) / 10.0:.1f} °C"
            m = re.search(r"status:\s+(\d+)", out)
            if m:
                codes = {2: "Cargando", 3: "Descargando", 5: "Carga completa"}
                details["battery_status"] = codes.get(int(m.group(1)), "Desconectada")

        # App en primer plano
        out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "dumpsys", "activity", "activities"])
        match = re.search(r"mResumedActivity:.*? (\S+)/", out)
        if not match:
            out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "dumpsys", "window", "windows"])
            match = re.search(r"mCurrentFocus.*? (\S+)/", out)
        if match:
            details["foreground_app"] = match.group(1)

        return details

    @staticmethod
    def get_packages(device: str, filter_flag: str = "") -> list[str]:
        """
        Retorna paquetes instalados.
        filter_flag: '' → todas, '-3' → terceros, '-s' → sistema
        """
        cmd = ["adb", "-s", device, "shell", "pm", "list", "packages"]
        if filter_flag:
            cmd.append(filter_flag)
        out, _, _ = ADBManager.run(cmd)
        pkgs = [line.replace("package:", "").strip() for line in out.split("\n") if line.strip()]
        return sorted(pkgs)

    @staticmethod
    def get_package_version(device: str, package: str) -> str:
        out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "dumpsys", "package", package])
        match = re.search(r"versionName=(\S+)", out)
        return match.group(1) if match else ""

    @staticmethod
    def get_screen_brightness(device: str) -> int:
        out, _, _ = ADBManager.run(["adb", "-s", device, "shell", "settings", "get", "system", "screen_brightness"])
        try:
            return int(out)
        except ValueError:
            return 128

    @staticmethod
    def get_desktop_path() -> str:
        """Ruta al Escritorio del usuario (multiplataforma)."""
        home = Path.home()
        desktop = home / "Desktop"
        if desktop.is_dir():
            return str(desktop)
        if sys.platform == "win32":
            onedrive = os.environ.get("OneDrive") or os.environ.get("USERPROFILE", "")
            if onedrive:
                candidate = Path(onedrive) / "Desktop"
                if candidate.is_dir():
                    return str(candidate)
        return str(home)

    @staticmethod
    def open_file_cross_platform(path: str):
        """Abre un archivo con la aplicación predeterminada del SO."""
        import subprocess, sys
        if sys.platform == "darwin":
            subprocess.run(["open", path])
        elif sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.run(["xdg-open", path])

    @staticmethod
    def open_shell_terminal(device: str):
        """Abre una terminal nativa con `adb shell` para el dispositivo dado."""
        if sys.platform == "darwin":
            script = f'tell application "Terminal" to do script "{ADB_PATH} -s {device} shell"'
            subprocess.run(["osascript", "-e", script])
        elif sys.platform == "win32":
            subprocess.Popen(
                ["cmd", "/k", ADB_PATH, "-s", device, "shell"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen(["x-terminal-emulator", "-e", ADB_PATH, "-s", device, "shell"])

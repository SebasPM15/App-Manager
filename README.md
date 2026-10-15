# ADB Nexus Manager Pro 📱✨

Una potente y moderna interfaz gráfica escrita en Python para controlar, automatizar y diagnosticar dispositivos y tablets Android en macOS utilizando comandos ADB de forma segura y eficiente.

---

## 🚀 Características Principales

### 📊 1. Dashboard
* **Información del dispositivo:** modelo, versión de Android, SDK, tipo de conexión (USB/WiFi) e IP.
* **Estado del sistema:** batería con color dinámico, temperatura, red y app en primer plano.
* **Acciones rápidas:** abrir **Scrcpy** (espejo de pantalla), tomar captura, sincronizar hora y reiniciar el dispositivo.

### 🔌 2. Conexión de dispositivos (barra lateral)
* **Selector de dispositivo** con estado de conexión y detección automática (sondeo periódico).
* **Conexión por IP:** campo para conectar con `IP[:puerto]` (puerto por defecto `5555`), varios destinos a la vez, y desconexión con `disconnect`/`desconectar`.
* **Shell ADB:** abre una terminal nativa con `adb shell` para el dispositivo seleccionado.

### 📦 3. Aplicaciones
* **Listado de paquetes** con buscador y filtros **Todas / Terceros / Sistema**.
* **Operaciones sobre la app seleccionada:** abrir, forzar detención, limpiar y abrir, borrar datos y desinstalar.
* **Permiso de superposición** (`SYSTEM_ALERT_WINDOW`) con un clic.
* **Instalador de APKs** con barra de progreso.

### 🎮 4. Control remoto
* **Navegación:** Volver, Inicio y Recientes, más cruceta direccional con OK.
* **Brillo:** slider para ajustar el brillo real del dispositivo.
* **Acciones rápidas:** ajustes de fecha y hora, sincronizar hora, activar/desactivar WiFi y datos móviles, captura de pantalla y apagado.

### 📝 5. Consola y Logcat
* **Logcat en vivo** en un hilo aparte, sin bloquear la interfaz.
* **Filtros:** nivel de severidad (Verbose, Debug, Info, Warning, Error), texto libre y "App seleccionada" (filtra por el proceso de la app).
* **Utilidades:** limpiar y guardar logs; la consola se puede contraer.
* **Comandos ADB:** caja de comandos para ejecutar instrucciones y ver su salida.

### 🔎 6. Zoom de Interfaz en Tiempo Real
* **Atajos:** `Cmd +` / `Cmd -` para acercar o alejar y `Cmd 0` para restablecer (en otros sistemas, `Ctrl`).
* **Rango:** de 0.8x a 1.6x en pasos de 0.1. Se aplica al instante, sin reiniciar la aplicación.
* **Persistente:** el valor se guarda como `ui_scale` en `config.json` y se restaura al abrir la app.

---

## 🛠️ Requisitos Previos

Antes de ejecutar el programa en tu Mac, asegúrate de tener instalado:

1. **Python 3** (Recomendado >= 3.10)
2. **Android Command Line Tools (ADB):**
   * Puedes instalarlo mediante Homebrew con: `brew install android-platform-tools`
3. **Scrcpy:**
   * Puedes instalarlo mediante Homebrew con: `brew install scrcpy`

*Nota: En macOS el programa busca `adb` y `scrcpy` en `/usr/local/bin/` y `/opt/homebrew/bin/`, y luego en el `$PATH`.*

---

## 📦 Instalación

1. Clona este repositorio o descarga los archivos en tu carpeta de trabajo.
2. Crea un entorno virtual de Python en la raíz del proyecto para mantener tus dependencias limpias:
   ```bash
   python3 -m venv venv
   ```
3. Activa el entorno virtual:
   ```bash
   source venv/bin/activate
   ```
4. Instala las dependencias necesarias indicadas en `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Uso de la Aplicación

Con el entorno virtual activado, inicia el programa ejecutando:

```bash
python3 main.py
```

### Primeros pasos recomendados:
1. Conecta tu dispositivo Android por USB y activa la **Depuración USB**.
2. Abre la app: el selector de la barra lateral cargará el dispositivo automáticamente.
3. Para usarlo por WiFi, escribe `IP:puerto` en el campo de conexión de la barra lateral y pulsa Enter.
4. Navega entre **Dashboard**, **Aplicaciones** y **Control remoto**, y usa la consola inferior para ver logs.

---

## 📁 Archivos del Proyecto

* **[main.py](file:///Users/formosecuador/Documents/AppManager/main.py):** Punto de entrada; aplica el zoom guardado y abre la ventana.
* **`ui/`:** Ventana principal, tema (colores, fuentes y dimensiones), paneles y pestañas (CustomTkinter).
* **`appManager3.py`:** Versión anterior en Tkinter, conservada como referencia.
* **`core/`:** Operaciones ADB/Scrcpy (`adb_manager.py`) y ajustes de interfaz (`ui_settings.py`).
* **[config.json](file:///Users/formosecuador/Documents/AppManager/config.json):** Guarda el nivel de zoom (`ui_scale`) y el listado de aplicaciones de la versión anterior.
* **[requirements.txt](file:///Users/formosecuador/Documents/AppManager/requirements.txt):** Contiene las librerías necesarias de Python.
* **[.gitignore](file:///Users/formosecuador/Documents/AppManager/.gitignore):** Archivo de exclusión para evitar subir archivos locales (`venv/`, capturas, logs temporales) a Git.

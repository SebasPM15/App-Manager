# ADB Nexus Manager Pro 📱✨

Una potente y moderna interfaz gráfica escrita en Python para controlar, automatizar y diagnosticar dispositivos y tablets Android en macOS utilizando comandos ADB de forma segura y eficiente.

---

## 🚀 Características Principales

### 📊 1. Dashboard de Control (Pantalla de Inicio)
* **Información Detallada del Hardware:** Modelo, versión de Android, SDK e IP local de red.
* **Estado de Batería:** Porcentaje (barra gráfica dinámica de color), temperatura exacta y estado de carga.
* **Control Remoto Visual (Espejo):** Abre de forma instantánea la pantalla del dispositivo físico con **Scrcpy** para interactuar directamente desde tu Mac usando mouse y teclado.
* **Acciones Rápidas:** Capturas de pantalla, reinicios del dispositivo y sincronización de hora.

### 🔌 2. Conexión Inalámbrica Inteligente (WiFi Hub)
* **Auto-Wireless:** Configura la tablet por WiFi de forma automática en un clic. Detecta la IP del dispositivo conectado por USB, abre el puerto de red `5555` y establece el enlace para que puedas desconectar el cable de inmediato.
* **Conexión Manual:** Permite asociar o desconectar dispositivos por su IP y Puerto.
* **ADB Pairing (Android 11+):** Soporte integrado para emparejar nuevos dispositivos utilizando códigos de vinculación de seguridad inalámbrica.

### 📦 3. Gestión y Separación de Apps
* **Aplicaciones Favoritas:** Sección rápida para las aplicaciones cargadas desde `config.json`.
  * **Indicadores Visuales (🟢/🔴):** Muestra al vuelo si cada una de las apps favoritas está o no instalada en el dispositivo seleccionado.
* **Buscador General:** Permite buscar y listar todos los paquetes instalados de terceros o del sistema.
* **Agregar a Favoritas (`[⭐]`):** Añade cualquier paquete detectado en el dispositivo a tu listado de favoritos con un nombre personalizado en caliente.
* **Operaciones de App:** Launch (🚀), Force Stop (🛑), Clear Data (🧹), Uninstall (🗑️) y Clean & Start (✨).
* **Permisos Especiales:** Concede rápidamente accesos avanzados como Superposición de Pantalla (`Overlay`).
* **Instalador de APKs:** Permite seleccionar cualquier APK local en tu Mac e instalarlo con barra de progreso interactiva.

### 🎮 4. Control Remoto Avanzado
* **Navegación de Hardware:** Emulación física de los botones Volver (◀️), Inicio (⚫) y Apps Recientes (⏹️).
* **Teclas Especiales:** Power (🔌), Vol+ (🔊) y Vol- (🔉).
* **Ajuste de Brillo:** Slider para calibrar el brillo real de la pantalla del dispositivo Android.
* **Teclado Remoto:** Envía texto escrito en la Mac directamente al dispositivo móvil (ideal para contraseñas o campos de texto complejos).
* **Grabador de Pantalla:** Graba hasta 3 minutos de video MP4 en la tablet, detén la grabación y el archivo se transferirá automáticamente a tu Escritorio (`~/Desktop`) y se abrirá.

### 📝 5. Consola y Diagnóstico Logcat
* **Logcat en Vivo (Multihilo):** Lectura continua de logs de Android sin colgar la interfaz gráfica de usuario.
* **Filtro Inteligente por App (PID):** Filtra los logs en tiempo real para mostrar exclusivamente lo que ocurre dentro de la aplicación seleccionada, buscando su ID de proceso (PID) de forma automática.
* **Filtros Adicionales:** Filtros de severidad (Verbose, Debug, Info, Warning, Error) y filtro rápido por texto de búsqueda.
* **Terminales macOS Nativas:** Abre ventanas externas del Terminal nativo de macOS ejecutando `adb shell` o `adb logcat` a través de AppleScript.
* **Consola ADB Libre:** Caja de comandos para escribir y ejecutar cualquier instrucción de ADB y ver su respuesta estructurada.

---

## 🛠️ Requisitos Previos

Antes de ejecutar el programa en tu Mac, asegúrate de tener instalado:

1. **Python 3** (Recomendado >= 3.10)
2. **Android Command Line Tools (ADB):**
   * Puedes instalarlo mediante Homebrew con: `brew install android-platform-tools`
3. **Scrcpy:**
   * Puedes instalarlo mediante Homebrew con: `brew install scrcpy`

*Nota: El programa buscará automáticamente los ejecutables `adb` y `scrcpy` en `/usr/local/bin/`. Si se instalaron en otra ubicación global, asegúrate de que estén mapeados en tu `$PATH`.*

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
1. Conecta tu tablet Android por USB y asegúrate de que la **Depuración USB** esté activa en el dispositivo.
2. Abre la app, el selector cargará automáticamente tu dispositivo móvil como `Conectado` (con indicador verde en la barra lateral).
3. Si deseas usarlo de forma inalámbrica, ve a la pestaña **Conexión Inalámbrica** o haz clic en **⚡ Auto-Wireless** en la barra lateral.
4. El programa detectará la IP de tu red, habilitará el modo WiFi y te indicará cuando sea seguro retirar el cable USB.

---

## 📁 Archivos del Proyecto

* **[main.py](file:///Users/formosecuador/Documents/AppManager/main.py):** Código fuente de la interfaz gráfica y la lógica ADB multihilo.
* **[config.json](file:///Users/formosecuador/Documents/AppManager/config.json):** Almacena las aplicaciones favoritas que deseas controlar. Se actualiza dinámicamente desde la interfaz.
* **[requirements.txt](file:///Users/formosecuador/Documents/AppManager/requirements.txt):** Contiene las librerías necesarias de Python.
* **[.gitignore](file:///Users/formosecuador/Documents/AppManager/.gitignore):** Archivo de exclusión para evitar subir archivos locales (`venv/`, capturas, logs temporales) a Git.

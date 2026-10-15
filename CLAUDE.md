# Instrucciones para Claude Code

## Idioma y estilo

- Comunícate en español: respuestas, explicaciones y documentación nueva.
- Escribe el código en inglés: nombres de variables, funciones, clases, módulos y otros identificadores.
- Mantén en español los textos de la interfaz que ya estén en español; no los traduzcas salvo que se solicite.
- No agregues comentarios al código. Inclúyelos únicamente cuando sean imprescindibles para explicar algo no evidente y mantenlos breves.
- Conserva el estilo y la estructura existentes. Evita cambios ajenos a la tarea solicitada.

## Proyecto

- Aplicación de escritorio Python para gestionar dispositivos Android mediante ADB.
- La interfaz usa CustomTkinter.
- `main.py` inicia la aplicación.
- `ui/` contiene la ventana, el tema, los paneles y las pestañas.
- `core/` contiene la gestión de configuración y las operaciones ADB.
- `config.json` almacena la configuración de favoritos de la aplicación. No reemplaces ni borres los datos del usuario.
- `requirements.txt` declara las dependencias Python.

## Cambios

- Antes de modificar algo, revisa los módulos relacionados y sigue sus patrones existentes.
- Mantén la lógica de interfaz en `ui/` y la lógica de ADB o configuración en `core/`, según corresponda.
- Considera que ADB y Scrcpy son herramientas externas; no supongas que están instaladas ni fijes rutas específicas sin comprobar cómo las busca el proyecto.
- No añadas dependencias si la tarea se puede resolver con las existentes.
- No ejecutes pruebas ni agregues pruebas salvo que el usuario lo pida. Si haces una verificación solicitada, informa qué ejecutaste y el resultado.
- Al terminar, resume en español los archivos modificados y cualquier limitación relevante.

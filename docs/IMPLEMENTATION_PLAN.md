# Plan de implementación y modernización

## Objetivo

Convertir ytdwpl en una aplicación de escritorio fiable para colas grandes de
descargas, con estados consistentes, reanudación segura, UI fluida y una
arquitectura que permita añadir formatos, proveedores y funciones sin mezclar
lógica de negocio con Flet o SQLite.

## Alcance

Incluye correcciones funcionales, robustez del proceso yt-dlp, persistencia,
rendimiento de UI, validación de configuración, pruebas y documentación.
No incluye todavía sincronización con cuentas de YouTube, autenticación,
servicio cloud ni edición avanzada de metadatos.

## Criterios globales de aceptación

- Ningún elemento desaparece de la UI por una transición de estado.
- Pausar, reanudar, cancelar y cerrar la app dejan estados persistentes válidos.
- La ruta final guardada es la ruta real del archivo producido.
- Un fallo de yt-dlp nunca se marca silenciosamente como completado.
- La UI no reconstruye toda la cola en cada evento de progreso.
- La aplicación puede manejar al menos 10.000 elementos persistidos sin que las
  consultas principales hagan un escaneo completo de la tabla.
- Toda funcionalidad nueva tiene pruebas unitarias y, cuando afecte a procesos,
  una prueba de integración con subprocess simulado.
- `ruff`, `mypy`, `pytest` y el build de PyInstaller se ejecutan en CI.

## Fases y orden de ejecución

### Fase 0 — Preparación y baseline

Objetivo: fijar el comportamiento actual antes de refactorizar.

Tareas:

- Mantener los cambios locales existentes y revisar cada diff antes de mezclar.
- Crear una rama de trabajo `codex/queue-reliability`.
- Instalar las dependencias del proyecto en un entorno virtual reproducible.
- Ejecutar y registrar `pytest`, `ruff`, `mypy` y una prueba de empaquetado.
- Añadir una matriz de compatibilidad para Windows, macOS y Linux.
- Crear un pequeño conjunto de fixtures para SQLite y subprocess.

Salida:

- Baseline documentado en `docs/DEVELOPMENT.md`.
- Lista de fallos reproducibles con pasos y resultado esperado.

### Fase 1 — Modelo de estados y ciclo de vida

Objetivo: eliminar estados ambiguos y hacer que la cola sea determinista.

Cambios:

- Añadir `PAUSED`, `EXPANDING` y `PARTIAL` a `ItemStatus` si el diseño final
  confirma que son necesarios.
- Definir transiciones válidas en un módulo de dominio, no dispersas por UI.
- Separar `cancel()` de `pause()`.
- Hacer que `start()` sea idempotente y que `stop()` pueda ejecutarse varias
  veces sin errores.
- Al arrancar, recuperar `DOWNLOADING` y `QUEUED` según la política definida.
- Al cerrar, detener scheduler, workers y procesos yt-dlp antes de cerrar DB.
- Añadir una señal de parada basada en `Condition` o `Event`, evitando polling
  innecesario.

Transiciones mínimas:

```text
PENDING -> QUEUED -> DOWNLOADING -> COMPLETED
                         |              |
                         +-> PAUSED     +-> PARTIAL
                         |              |
                         +-> FAILED     +-> CANCELLED
PAUSED -> QUEUED
FAILED/CANCELLED -> QUEUED mediante reintento
EXPANDING -> PENDING o FAILED
```

Pruebas:

- Tabla de transiciones permitidas y rechazadas.
- Pausa de una descarga activa y posterior reanudación.
- Cancelación definitiva de una descarga.
- Recuperación tras cierre durante cada estado activo.

### Fase 2 — Scheduler y concurrencia

Objetivo: controlar concurrencia sin carreras ni hilos acumulados.

Cambios:

- Sustituir la creación manual indefinida de hilos por un scheduler controlado,
  preferiblemente `ThreadPoolExecutor` para trabajo bloqueante.
- Registrar cada tarea activa con un objeto de control que contenga proceso,
  evento de cancelación y estado.
- Evitar iniciar el mismo item dos veces con una transición atómica en DB.
- Limpiar tareas terminadas automáticamente.
- Hacer dinámico `max_concurrent` sin iniciar duplicados.
- Añadir timeout de extracción de playlist y timeout de terminación de yt-dlp.
- Tras `terminate()`, usar `kill()` solo si el proceso no finaliza dentro del
  margen establecido.
- Proteger el acceso a progreso, rutas y tareas activas con estructuras claras
  y locks pequeños.

Pruebas:

- Límite exacto de concurrencia.
- Dos llamadas concurrentes que intentan iniciar el mismo item.
- Stop con cero, uno y varios workers.
- Worker que termina por error, cancelación y timeout.

### Fase 3 — Downloader robusto

Objetivo: obtener resultados y metadatos fiables de yt-dlp.

Cambios:

- Crear tipos explícitos para `DownloadResult`, `DownloadError` y eventos de
  progreso.
- Centralizar la construcción de argumentos yt-dlp.
- Capturar la ruta final de vídeo fusionado mediante `[Merger]` y la ruta final
  de audio mediante `[ExtractAudio]`.
- Actualizar `downloaded_mb`, velocidad, ETA y porcentaje de forma consistente.
- Distinguir éxito total, éxito parcial, cancelación y error real.
- No aceptar código de salida 2 automáticamente: validar evidencias de éxito y
  mensajes de error.
- Capturar stderr con límite de tamaño y conservar los últimos errores útiles.
- Comprobar que yt-dlp está disponible antes de añadir una playlist.
- Resolver ffmpeg y ffprobe de forma común y validar que son ejecutables.
- Sanitizar títulos vacíos y nombres reservados por plataforma.
- Usar timeouts y devolver errores accionables al usuario.

Pruebas:

- Parser de progreso con distintas unidades y formatos.
- Parser de merger y extracción de audio.
- Archivo ya descargado.
- Salidas 0, 2 y códigos de error.
- yt-dlp ausente, ffmpeg ausente y proceso bloqueado.

### Fase 4 — Playlist y persistencia transaccional

Objetivo: que añadir y recargar playlists sea seguro y repetible.

Cambios:

- Crear una entidad de playlist o una tabla `playlists` separada de los vídeos.
- Usar `video_id` como identidad estable, con URL como dato mutable.
- Insertar la expansión completa dentro de una transacción.
- Guardar errores reales de expansión y permitir reintento.
- Implementar sincronización de playlist: añadir nuevos vídeos, conservar
  estados existentes y marcar ausentes sin borrar historial automáticamente.
- Resolver duplicados de playlist y permitir una opción explícita de duplicar.
- Elegir una política para `download-archive`: archive por item, lock por
  playlist o serialización por playlist. Documentarla antes de implementarla.
- Añadir índices `status`, `playlist_id`, `created_at` y combinaciones usadas
  por el scheduler.
- Versionar migraciones con `PRAGMA user_version`.

Pruebas:

- Expansión completa y expansión interrumpida.
- Playlist vacía y playlist con entradas inválidas.
- Recarga con vídeos añadidos, eliminados y renombrados.
- Dos descargas simultáneas de una misma playlist.
- Migración desde una base de datos antigua.

### Fase 5 — Configuración y validación

Objetivo: que los ajustes sean válidos y se apliquen sin reinicio.

Cambios:

- Validar `output_dir`, formato y concurrencia en un único lugar.
- Aplicar el formato predeterminado en el diálogo de añadir.
- Actualizar `queue.output_dir` al guardar.
- Limitar `max_concurrent` al rango soportado por UI y scheduler.
- Crear la carpeta de salida con mensajes de error claros.
- Guardar JSON con UTF-8 y reemplazo atómico.
- Mantener el archivo anterior si el JSON está corrupto, registrando el error.
- Evitar que campos desconocidos rompan toda la carga de configuración.

Pruebas:

- Valores válidos, vacíos, negativos, excesivos e inválidos.
- Cambio de carpeta durante una sesión.
- Configuración corrupta o con campos adicionales.
- Fallo de permisos al crear o guardar la carpeta.

### Fase 6 — UI incremental y accesible

Objetivo: mejorar claridad y rendimiento percibido.

Cambios:

- Incluir `QUEUED` en la pestaña de cola.
- Mostrar estados distintos para pendiente, en cola, pausado, parcial y error.
- Mantener un modelo de vista y actualizar solo controles afectados.
- Evitar consultar y reconstruir toda la DB en cada progreso.
- Limitar eventos de progreso y agrupar actualizaciones con un dispatcher UI.
- Limpiar progreso al completar o eliminar un item.
- Mostrar progreso de expansión de playlist y permitir cancelarlo.
- Añadir confirmación antes de eliminar o cancelar en bloque.
- Hacer diálogos y filas responsivos para ventanas pequeñas.
- Evitar acumular SnackBars en `page.overlay`.
- Añadir estados vacíos específicos: cola vacía, sin completadas, error de
  expansión y herramienta externa no instalada.
- Revisar propagación de eventos para que pulsar una acción no expanda o cierre
  accidentalmente una playlist.

Pruebas:

- Renderizado de cada estado.
- Acciones de botones y checkboxes sin eventos duplicados.
- Cola grande con refrescos frecuentes.
- Ventana estrecha y cambio de tema.

### Fase 7 — Arquitectura y mantenibilidad

Objetivo: reducir acoplamiento y preparar futuras funcionalidades.

Estructura objetivo:

```text
app/
├── domain/
│   ├── models.py
│   └── state_machine.py
├── application/
│   ├── queue_service.py
│   ├── playlist_service.py
│   └── events.py
├── infrastructure/
│   ├── sqlite_repository.py
│   ├── yt_dlp_downloader.py
│   ├── settings_store.py
│   └── process_runner.py
├── ui/
│   ├── controllers/
│   └── components/
└── main.py
```

Cambios:

- La UI no debe importar directamente SQL ni construir comandos yt-dlp.
- Sustituir `**extra` en persistencia por métodos tipados o DTOs validados.
- Añadir type hints completos y docstrings a APIs públicas.
- Mantener funciones pequeñas y con una única responsabilidad.
- Separar textos, tema visual y configuración técnica.
- Añadir logging estructurado con rotación y niveles configurables.
- Documentar decisiones relevantes como ADRs breves.

### Fase 8 — Calidad, seguridad y distribución

Objetivo: hacer repetible la validación y el empaquetado.

Cambios:

- Configurar CI para tests, lint, type checking y build.
- Añadir `pre-commit` con ruff, formatter y mypy.
- Ejecutar `pip-audit` en CI.
- Fijar dependencias directas y generar lockfile reproducible.
- Validar entradas de usuario antes de pasarlas a subprocess.
- Evitar extracción insegura de archives descargados en `build.py`.
- Verificar hash o integridad de binarios ffmpeg cuando sea posible.
- Probar `onedir` y `onefile` en las plataformas soportadas.
- Revisar README, comandos Flet y documentación de build.

## Definición de terminado

Una fase se considera terminada cuando:

1. El código está implementado y tipado.
2. Las pruebas nuevas cubren el comportamiento y los casos de error.
3. La documentación correspondiente está actualizada.
4. `pytest`, `ruff` y `mypy` pasan en entorno limpio.
5. No quedan cambios sin explicar en el diff.
6. Si afecta a distribución, el artefacto de PyInstaller se valida con un smoke
   test.

## Riesgos y decisiones pendientes

- La concurrencia de descargas y el archive por playlist deben resolverse antes
  de aumentar el paralelismo.
- La pausa real depende de cómo finaliza yt-dlp y debe probarse con archivos
  parciales reales.
- Flet debe ejecutarse con las dependencias desktop/web correctas según el modo
  soportado.
- Hay cambios locales existentes en `app/core/queue.py`, `app/db.py`,
  `app/main.py`, `app/ui/layout.py` y `build.py`; deben revisarse antes de
  aplicar refactors que se solapen.

# Arquitectura

## Flujo de datos

```
UI (Flet) ──→ QueueManager ──→ Downloader (yt-dlp subprocess) ──→ ffmpeg
   ↑                │                                                │
   │                └── SQLite (persistencia)                        │
   └──── progress_callback ← stdout parser ← stdout pipe ───────────┘
```

1. El usuario agrega una URL → `QueueManager.add_playlist()` → hilo async para `extract_playlist_info()`.
2. `QueueManager._loop()` (hilo worker) toma el primer item `pending` y crea un `Downloader`.
3. `Downloader.run()` lanza `yt-dlp` como subproceso y parsea stdout línea por línea.
4. Cada línea de progreso → `ProgressCallback` → `QueueManager._on_progress()` → actualiza UI.
5. Al terminar → actualiza SQLite → notifica UI.

## Procesos

- **Main thread**: UI de Flet (event loop). Las actualizaciones desde otros hilos se hacen con `page.update()`.
- **Scheduler thread**: `QueueManager._loop()` — asigna slots y despierta ante
  cambios de cola; cada descarga se ejecuta mediante `ThreadPoolExecutor`.
- **Async thread**: `extract_playlist_info()` corre en un hilo separado para no bloquear ni la UI ni la cola.

## Estado de items

```
PENDING ──→ QUEUED ──→ DOWNLOADING ──→ COMPLETED
                         │              │
                         ├──→ PAUSED   └──→ PARTIAL
                         ├──→ CANCELLED
                         └──→ FAILED ──→ QUEUED (reintento manual)
PAUSED ──→ QUEUED
```

Al iniciar la app, los items en estado `DOWNLOADING` y `QUEUED` se resetan a
`PENDING`; los items `PAUSED` permanecen pausados.

## Persistencia

- **SQLite**: `~/.ytdwpl/queue.db` — WAL mode, `busy_timeout=5000`, conexión por hilo (`threading.local()`). El esquema usa `PRAGMA user_version`, índices por estado/playlist y una reclamación atómica `QUEUED → DOWNLOADING`.
- **Settings**: `~/.ytdwpl/settings.json` — JSON simple con `output_dir` y `format`.
- **Logs**: `~/.ytdwpl/app.log` — rotación limitada para errores de expansión,
  recarga y workers.
- **Download archive**: `{output_dir}/.ytdwpl-archive/{playlist_id}.archive.txt` —
  archivo de yt-dlp protegido por un lock por playlist para evitar escrituras
  simultáneas.

## Downloader detallado

### Argumentos de yt-dlp

| Argumento | Propósito |
|-----------|-----------|
| `--continue` | Reanudar descargas parciales |
| `--yes-playlist` | Tratar la URL como playlist |
| `--restrict-filenames` | Evitar caracteres problemáticos |
| `--no-overwrites` | No sobrescribir archivos existentes |
| `--newline` | Salida línea por línea (para parsear) |
| `--ignore-errors` | Continuar aunque falle un video |
| `--no-warnings` | Reducir ruido en stdout |
| `--output` | Template de salida personalizado |
| `--download-archive` | Archivo de seguimiento de descargas |
| `--ffmpeg-location` | Ruta a ffmpeg (solo si está en `bin/`) |
| `--extract-audio` / `--audio-format mp3` | Modo audio |
| `--format bestvideo+bestaudio` | Modo video MP4 |

### Parseo de progreso

El stdout de yt-dlp se parsea con regex:

- `Downloading (video|item) X of Y` → índice de video en la playlist
- `[download] X.X% of ~XX.XMiB at X.XMiB/s ETA XXs` → porcentaje, tamaño, velocidad, ETA
- `[download] Destination: path` → título del video actual
- `[download] Finished` → descarga completada
- `has already been downloaded` → saltear video existente

### Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Éxito completo |
| 2 | Éxito parcial (algunos videos fallaron con `--ignore-errors`) |
| ≠0,2 | Error real |

Se acepta 2 como éxito porque yt-dlp también retorna 2 para argumentos inválidos. Validar con una URL real.

### ffmpeg

- Se busca primero en `bin/` (junto al ejecutable empaquetado).
- Fallback a `shutil.which("ffmpeg")` (PATH del sistema).
- `ffprobe` se auto-detecta al estar colocado con ffmpeg.

## UI Components

```
layout.py
├── AppBar (título + settings icon)
├── ProgressCard (descarga activa)
├── Tabs
│   ├── Tab "Cola" → pending/failed/cancelled items
│   └── Tab "Completadas" → completed items
├── FAB (+) → AddDialog
└── SettingsDialog
```

Cada componente se refresca mediante `page.update()` desde cualquier hilo.

# ytdwpl — YouTube Playlist Downloader

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flet](https://img.shields.io/badge/Flet-0.86%2B-purple)](https://flet.dev)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-2024.12%2B-red)](https://github.com/yt-dlp/yt-dlp)

Descargador de playlists de YouTube con interfaz gráfica de escritorio. Cola de descargas, reanudación automática, persistencia SQLite y panel de progreso en tiempo real.

## Captura

![ytdwpl](docs/screenshot.png)

## Características

- **Cola de descargas** — agrega playlists y se descargan una tras otra.
- **Reanudación** — descargas interrumpidas se reanudan automáticamente (`.part` + `--download-archive`).
- **Persistencia** — la cola sobrevive al reinicio de la app (SQLite en `~/.ytdwpl/queue.db`).
- **Progreso en vivo** — barra de progreso, velocidad, ETA, video actual y panel de registro de yt-dlp.
- **Video o Audio** — descarga en MP4 (mejor calidad) o MP3 (extracción de audio).
- **Pausar / Reanudar / Cancelar** — control total sobre la descarga activa.
- **Configuración** — carpeta de salida y formato predeterminado configurables desde la UI.
- **Packaging** — script `build.py` que descarga ffmpeg estático y empaqueta con PyInstaller.

## Requisitos

- **Python 3.10+**
- **ffmpeg** — necesario para fusionar video+audio y extraer audio. Puedes:
  - Descargarlo automáticamente con `python build.py --ffmpeg`, o
  - Instalarlo en el PATH del sistema manualmente.

## Instalación

```bash
git clone https://github.com/BrunoJimenez73/ytdwpl.git
cd ytdwpl

# Entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Linux / macOS

# Instalar dependencias
pip install -e .
```

## Uso

```bash
# Desarrollo con hot-reload
flet run app/main.py

# O desde el entrypoint
python -m app.main
```

Abre el navegador en `http://127.0.0.1:64446` (Flet inicia en modo web por defecto).

Para cambiar el puerto:

```bash
flet run app/main.py --port 8080
```

## Packaging

```bash
# Solo descargar ffmpeg
python build.py --ffmpeg

# Empaquetar .exe (modo directorio)
python build.py --pack

# Empaquetar .exe individual
python build.py --onefile --pack
```

El ejecutable se genera en `dist/ytdwpl/`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Tecnologías

| Capa | Tecnología |
|------|------------|
| UI | [Flet](https://flet.dev) (Flutter sobre Python) |
| Descargas | [yt-dlp](https://github.com/yt-dlp/yt-dlp) (subprocess) |
| Base de datos | SQLite (WAL, hilos con conexión local) |
| Packaging | PyInstaller + ffmpeg estático |
| Formato | MP4 / MP3 vía ffmpeg |

## Estructura

```
app/
├── main.py              # Punto de entrada
├── db.py                # Capa de persistencia SQLite
├── core/
│   ├── models.py        # Dataclasses y enums
│   ├── downloader.py    # Wrapper de yt-dlp (subprocess)
│   ├── queue.py         # Gestor de cola en segundo plano
│   └── settings.py      # Configuración persistente
└── ui/
    ├── layout.py        # Layout principal y wiring
    ├── queue_table.py   # Tabla de items en cola
    ├── progress_card.py # Tarjeta de progreso activa
    ├── add_dialog.py    # Diálogo para agregar URL
    └── settings_dialog.py # Diálogo de configuración
```

## Licencia

MIT

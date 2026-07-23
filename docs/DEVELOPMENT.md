# Desarrollo

## Setup

```bash
git clone https://github.com/BrunoJimenez73/ytdwpl.git
cd ytdwpl
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Editable install + dev dependencies
pip install -e ".[dev]"

# Opcional: descargar ffmpeg
python build.py --ffmpeg
```

## Comandos

```bash
# Desarrollo (hot-reload)
flet run app/main.py

# Especificar puerto
flet run app/main.py --port 8080

# Tests
pytest tests/ -v
pytest tests/ -v --cov=app   # con cobertura
pytest tests/ -v -k "db"     # filtrar por test

# Lint
ruff check app/ tests/

# Formateo
ruff format app/ tests/

# Type check
mypy app/

# Packaging
python build.py --pack           # modo directorio
python build.py --onefile --pack # single .exe
```

## Convenciones

### Código

- **Python 3.10+** con `from __future__ import annotations`.
- Nombres en inglés para código, español para UI.
- Sin comentarios en código — el código debe ser auto-documentado.
- Docstrings solo en funciones públicas con lógica no trivial.
- Type hints completos.

### UI

- Los archivos en `app/ui/` reciben datos ya procesados; no hacen lógica de negocio.
- Las actualizaciones desde hilos secundarios requieren `page.update()`.
- No usar `FilePicker` (no funciona en web mode). Usar campos de texto para rutas.

### Base de datos

- Usar `threading.local()` para conexiones por hilo.
- Los nombres de columnas en SQL coinciden exactamente con los campos del dataclass.
- WAL mode + `busy_timeout=5000` para concurrencia.

### Gestión de errores

- Excepciones de yt-dlp (código de salida ≠ 0,2) → se capturan en `QueueManager._loop()` y se marcan como `FAILED`.
- `DownloadCancelled` se lanza internamente y se maneja en el loop.
- Errores de red en `extract_playlist_info()` se tragan silenciosamente (el worker reintenta al procesar el item).

## Agregar una UI component

1. Crear archivo en `app/ui/` con una función que retorne `ft.Control`.
2. Recibir callbacks como parámetros (nunca importar lógica de negocio).
3. Conectar en `app/ui/layout.py` dentro de `build_app()`.

## Agregar un formato de descarga

1. Agregar valor al enum `DownloadFormat` en `app/core/models.py`.
2. Agregar condición en `Downloader.run()` en `app/core/downloader.py`.
3. Agregar opción en `AddDialog` y `SettingsDialog`.

## Pruebas

### Estrategia

| Módulo | Enfoque |
|--------|---------|
| `models.py` | Unit tests sin dependencias |
| `settings.py` | Unit tests con archivos temporales |
| `db.py` | Tests con SQLite en memoria (`:memory:`) |
| `downloader.py` | Mock de `subprocess.Popen`, test de parseo |
| `queue.py` | Mock de `Downloader` y `db` |
| `ui/` | No se testea automáticamente (validación visual) |

### Fixtures importantes

- `tmp_path` — para archivos temporales (SQLite, settings).
- `mocker` — `pytest-mock` para mockear subprocess y yt-dlp.
- `sample_item` — `QueueItem` preconfigurado para tests.

### Mock de extract_playlist_info

```python
mocker.patch(
    "app.core.downloader.extract_playlist_info",
    return_value={"playlist_title": "Test", "video_count": 5},
)
```

### Mock de yt-dlp subprocess

```python
from unittest.mock import MagicMock, patch

mock_proc = MagicMock()
mock_proc.stdout = ["[download] Downloading video 1 of 5\n"]
mock_proc.returncode = 0
with patch("subprocess.Popen", return_value=mock_proc):
    downloader.run(item, output_dir, on_progress)
```

## CI (futuro)

```yaml
# .github/workflows/test.yml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - run: pip install -e ".[dev]"
  - run: pytest tests/ -v
  - run: ruff check app/
```

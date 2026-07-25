# AGENTS.md

YouTube Playlist Downloader — Flet desktop app with queue management and resume support.

## Stack
- **Desktop**: Flet (Python, Flutter-based UI)
- **Downloads**: yt-dlp (subprocess with JSON progress)
- **Persistence**: SQLite (queue survives restarts)
- **Build**: PyInstaller + bundled static ffmpeg in `bin/`

## Commands

```bash
# run dev (desktop, requires Flet desktop dependency)
flet run app/main.py

# run dev in browser
flet serve app/main.py

# fetch ffmpeg only
python build.py --ffmpeg

# package (fetches ffmpeg + builds .exe/.dmg/AppImage)
python build.py --pack

# single-file executable
python build.py --onefile --pack

# run with the configured output folder from the app settings
flet run app/main.py
```

## Architecture

```
app/
├── main.py              # Entrypoint: init DB → build UI → run event loop
├── db.py                # SQLite CRUD (thread-local connections, WAL mode)
├── core/
│   ├── models.py        # QueueItem dataclass, ItemStatus/DownloadFormat enums
│   ├── downloader.py    # yt-dlp subprocess wrapper, progress JSON parser
│   ├── queue.py         # Background worker thread, manages active/cancel/pause
│   └── settings.py      # AppSettings dataclass (output dir, format) persisted to JSON
└── ui/
    ├── layout.py        # Main layout: tabs, FAB, AppBar with settings, wires everything
    ├── queue_table.py   # DataTable for pending/completed items
    ├── progress_card.py # Active download card (progress bar, speed, ETA)
    ├── add_dialog.py    # AlertDialog to add playlist URL
└── settings_dialog.py  # AlertDialog for output dir + default format
```

## Implementation roadmap

The complete implementation plan is in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).
The actionable backlog is in [`FEATURES.md`](FEATURES.md).

Implement changes in this order:

1. Queue state consistency and graceful shutdown.
2. Downloader result classification, final file paths and timeouts.
3. Scheduler/concurrency and playlist/archive consistency.
4. Transactional persistence, migrations and settings validation.
5. Incremental UI refresh and responsive states.
6. Architecture separation, typing, CI and packaging.

Before starting a phase, inspect the current git diff. Existing local changes
must be preserved unless the user explicitly asks to discard them.

## Target architecture

New business logic should not be added directly to Flet callbacks or raw SQL.
Prefer the following boundaries:

- **Domain**: models and valid state transitions.
- **Application**: queue and playlist use cases, emitting typed events.
- **Infrastructure**: SQLite repository, yt-dlp process runner, settings store.
- **UI**: Flet controls and event wiring only.

Public Python APIs should use type hints, small functions and Google-style
docstrings. New behavior must include pytest coverage and error handling.

## Key details
- **Downloader runs yt-dlp as subprocess** (not Python API) — allows clean kill for cancel/pause
- **Resume**: yt-dlp `--continue` + `.part` files enable byte-level resume; the archive strategy must be concurrency-safe
- **Queue persistence**: SQLite at `~/.ytdwpl/queue.db` with schema versioning, indexes and atomic queued-item claims; stale `downloading` items reset to `pending` on startup
- **Progress**: yt-dlp stdout parsed with regex `[download]` lines; UI updates from background thread via `page.update()`
- **ffmpeg**: `downloader.py` checks `bin/` first (bundled), then falls back to `shutil.which("ffmpeg")`
- **Cross-platform**: Flet and yt-dlp work on Win/Mac/Linux; build.py auto-detects platform for ffmpeg download
- **Playlist expansion**: expansion uses an `EXPANDING` placeholder and replaces it with discovered items in one transaction; failures remain visible with the original error
- **Application logs**: rotating logs are written to `~/.ytdwpl/app.log`

## Conventions
- Background work must publish an event or schedule a UI refresh; do not mutate
  Flet controls directly from arbitrary worker code
- All state flows: UI → QueueManager → Downloader (subprocess) → progress callback → UI
- `Downloader.run()` is blocking (runs in worker thread); cancellation via `threading.Event`
- Column naming in SQL matches dataclass field names exactly

## Gotchas
- yt-dlp `--progress-template` JSON is unreliable on some playlists — regex parsing of `[download]` lines is more robust
- ffmpeg is NOT bundled in repo; use `build.py --ffmpeg` to download it
- First-run may be slow on large playlists due to `extract_playlist_info()` calling `--flat-playlist --dump-json`
- Flet's `page.update()` must be called after modifying controls from background threads
- **`--ffprobe-location` is NOT a valid yt-dlp option** — downloader uses only `--ffmpeg-location` (ffprobe must be colocated with ffmpeg)
- **Exit code 2 ambiguity**: yt-dlp returns 2 for both `--ignore-errors` partial failures AND invalid arguments — the downloader accepts 2 as success, so test downloads with a real URL to validate
- **Regex for playlist tracking**: yt-dlp outputs `Downloading item X of Y` (not `video`) when downloading playlists via `--yes-playlist`

## Quality gates

Before considering a change complete, run:

```bash
python -m pytest tests -q
ruff check app tests
mypy app
```

For downloader or packaging changes, also run a smoke test with a real test URL
and build the PyInstaller artifact in a clean environment. If a tool is not
available locally, report that limitation rather than marking the gate passed.

# AGENTS.md

YouTube Playlist Downloader — Flet desktop app with queue management and resume support.

## Stack
- **Desktop**: Flet (Python, Flutter-based UI)
- **Downloads**: yt-dlp (subprocess with JSON progress)
- **Persistence**: SQLite (queue survives restarts)
- **Build**: PyInstaller + bundled static ffmpeg in `bin/`

## Commands

```bash
# run dev (hot-reload)
flet run app/main.py

# fetch ffmpeg only
python build.py --ffmpeg

# package (fetches ffmpeg + builds .exe/.dmg/AppImage)
python build.py --pack

# single-file executable
python build.py --onefile --pack

# quick run after build
flet run app/main.py  "C:/path/to/downloads"
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

## Key details
- **Downloader runs yt-dlp as subprocess** (not Python API) — allows clean kill for cancel/pause
- **Resume**: yt-dlp `--continue` + `--download-archive` per playlist tracks completed videos; `.part` files enable byte-level resume
- **Queue persistence**: SQLite at `~/.ytdwpl/queue.db`; stale `downloading` items reset to `pending` on startup
- **Progress**: yt-dlp stdout parsed with regex `[download]` lines; UI updates from background thread via `page.update()`
- **ffmpeg**: `downloader.py` checks `bin/` first (bundled), then falls back to `shutil.which("ffmpeg")`
- **Cross-platform**: Flet and yt-dlp work on Win/Mac/Linux; build.py auto-detects platform for ffmpeg download

## Conventions
- UI updates from any thread call `page.update()` (thread-safe in Flet)
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

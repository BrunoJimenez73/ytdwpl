from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.core.models import DownloadFormat, QueueItem


@dataclass
class DownloadProgress:
    video_title: str = ""
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    downloaded_mb: float = 0.0
    total_mb: float = 0.0
    playlist_index: int = 0
    playlist_count: int = 0
    status: str = "starting"
    log_lines: list[str] = field(default_factory=list)


ProgressCallback = Callable[[DownloadProgress], None]


class DownloadCancelled(Exception):
    pass


def _resolve_ffmpeg() -> Optional[str]:
    priority = [
        Path(__file__).resolve().parent.parent.parent / "bin" / "ffmpeg.exe",
        Path(__file__).resolve().parent.parent.parent / "bin" / "ffmpeg",
    ]
    for p in priority:
        if p.is_file():
            return str(p)
    return shutil.which("ffmpeg")





def _sanitize_dirname(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")


def extract_playlist_info(url: str) -> dict:
    """Return playlist title and video count using a fast flat dump."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--ignore-errors",
        "--no-warnings",
        url,
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    title = ""
    count = 0
    for line in proc.stdout or []:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            count += 1
            if not title:
                title = data.get("playlist_title") or data.get("playlist", "") or ""
        except json.JSONDecodeError:
            continue
    proc.wait()
    return {"playlist_title": title or url.rsplit("/", 1)[-1], "video_count": count}


class Downloader:
    def __init__(self) -> None:
        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _make_archive_path(self, item: QueueItem, output_dir: Path) -> Path:
        archive_dir = output_dir / ".ytdwpl-archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir / f"{item.id}.archive.txt"

    def run(
        self,
        item: QueueItem,
        output_dir: Path,
        on_progress: ProgressCallback,
    ) -> None:
        self._cancel_event.clear()
        archive_path = self._make_archive_path(item, output_dir)

        ffmpeg = _resolve_ffmpeg()

        fmt = item.format
        outtmpl = str(output_dir / "%(playlist_title|Unknown)s" / "%(title)s.%(ext)s")

        args = [
            "yt-dlp",
            "--continue",
            "--yes-playlist",
            "--restrict-filenames",
            "--no-overwrites",
            "--newline",
            "--ignore-errors",
            "--no-warnings",
            "--output", outtmpl,
            "--download-archive", str(archive_path),
        ]

        if ffmpeg:
            args += ["--ffmpeg-location", os.path.dirname(ffmpeg)]

        if fmt == DownloadFormat.AUDIO:
            args += ["--extract-audio", "--audio-format", "mp3",
                     "--audio-quality", "0",
                     "--embed-thumbnail"]
        else:
            args += ["--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"]

        args.append(item.url)

        progress = DownloadProgress()

        self._process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        video_idx_re = re.compile(r'Downloading (?:video|item)\s+(\d+)\s+of\s+(\d+)')
        log_buffer: deque = deque(maxlen=100)
        log_counter = 0
        line_pattern = re.compile(
            r'\[download\]\s+(.+?)\s+of\s+[~]?(\S+)\s+'
            r'(?:at\s+(\S+))?\s*(?:ETA\s+(\S+))?'
        )

        try:
            for raw_line in self._process.stdout or []:
                if self._cancel_event.is_set():
                    self._process.terminate()
                    raise DownloadCancelled()

                line = raw_line.strip()
                log_buffer.append(line)
                log_counter += 1

                should_update = True

                if "[download] Destination:" in line:
                    title_part = line.split("Destination:")[-1].strip()
                    name = Path(title_part).stem
                    progress.video_title = name
                    progress.status = "downloading"

                elif idx_m := video_idx_re.search(line):
                    progress.playlist_index = int(idx_m.group(1))
                    progress.playlist_count = int(idx_m.group(2))

                elif m := line_pattern.search(line):
                    raw_percent_str = m.group(1).rstrip("%")
                    try:
                        progress.percent = float(raw_percent_str)
                    except ValueError:
                        progress.percent = 0.0
                    progress.total_mb = _parse_size(m.group(2))
                    if m.group(3):
                        progress.speed = m.group(3)
                    if m.group(4):
                        progress.eta = m.group(4)
                    progress.status = "downloading"

                elif "[download] Finished" in line:
                    progress.percent = 100.0
                    progress.status = "finishing"

                elif "[ExtractAudio]" in line and "Destination" in line:
                    dest = line.split("Destination:")[-1].strip()
                    progress.video_title = Path(dest).stem

                elif "has already been downloaded" in line:
                    path_part = line.split("[download]")[-1].strip()
                    name = Path(path_part.split("has already")[0].strip()).stem
                    progress.video_title = name
                    progress.status = "downloading"

                else:
                    should_update = False

                if should_update:
                    progress.log_lines = list(log_buffer)
                    on_progress(progress)

            self._process.wait()

        except DownloadCancelled:
            self._process.wait()
            raise
        except Exception as e:
            self._process.wait()
            raise RuntimeError(f"Download failed: {e}") from e

        if self._process.returncode not in (0, 2) and not self._cancel_event.is_set():
            raise RuntimeError(f"yt-dlp exited with code {self._process.returncode}")


def _parse_size(raw: str) -> float:
    raw = raw.strip()
    units = {"KiB": 1024, "MiB": 1024**2, "GiB": 1024**3,
             "KB": 1000, "MB": 1000**2, "GB": 1000**3}
    for unit, multiplier in units.items():
        if raw.endswith(unit):
            try:
                return float(raw[: -len(unit)].strip()) * multiplier / (1024**2)
            except ValueError:
                return 0.0
    try:
        return float(raw) / (1024**2)
    except ValueError:
        return 0.0

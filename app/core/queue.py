from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app import db
from app.core.downloader import (
    DownloadCancelled,
    DownloadProgress,
    Downloader,
    extract_playlist_info,
)
from app.core.models import DownloadFormat, ItemStatus, QueueItem


class QueueManager:
    def __init__(
        self,
        output_dir: Path,
        on_item_update: Callable[[QueueItem], None],
        on_progress: Callable[[str, DownloadProgress], None] = lambda i, p: None,
        max_concurrent: int = 4,
    ) -> None:
        self.output_dir = output_dir
        self.on_item_update = on_item_update
        self._on_progress_ext = on_progress
        self.max_concurrent = max_concurrent
        self._thread: Optional[threading.Thread] = None
        self._active: Dict[str, Downloader] = {}
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._running = True
        self._file_paths: Dict[str, str] = {}

    @property
    def active_ids(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def start(self) -> None:
        db.reset_stale_downloads()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._pause_event.set()
        with self._lock:
            for dl in self._active.values():
                dl.cancel()

    def pause(self) -> None:
        self._pause_event.clear()
        with self._lock:
            for dl in self._active.values():
                dl.cancel()

    def resume(self) -> None:
        self._pause_event.set()

    def add_playlist(self, url: str, fmt: DownloadFormat) -> None:
        playlist_id = QueueItem.new(url, fmt).id
        temp = QueueItem.new(
            url, fmt,
            playlist_title="Obteniendo informacion...",
            playlist_id=playlist_id,
        )
        db.add_item(temp)
        self.on_item_update(temp)
        db.delete_item(temp.id)

        def _expand() -> None:
            try:
                info = extract_playlist_info(url)
                title = info.get("playlist_title", url.rsplit("/", 1)[-1])
                videos = info.get("videos", [])
                total = len(videos)

                for v in videos:
                    item = QueueItem.new(
                        url=v["url"],
                        fmt=fmt,
                        video_title=v.get("title", ""),
                        playlist_title=title,
                        playlist_id=playlist_id,
                        total_videos=total,
                    )
                    db.add_item(item)
                    self.on_item_update(item)

            except Exception:
                item = QueueItem.new(
                    url=url, fmt=fmt,
                    playlist_title="Error al obtener playlist",
                    playlist_id=playlist_id,
                )
                db.add_item(item)
                self.on_item_update(item)

        threading.Thread(target=_expand, daemon=True).start()

    def toggle_selected(self, item_id: str) -> None:
        item = db.get_item(item_id)
        if item:
            new_val = not item.selected
            db.update_status(item_id, item.status, selected=int(new_val))
            self.on_item_update(db.get_item(item_id))

    def cancel_item(self, item_id: str) -> None:
        with self._lock:
            dl = self._active.pop(item_id, None)
            if dl:
                dl.cancel()
        item = db.get_item(item_id)
        if item and item.status in (ItemStatus.PENDING, ItemStatus.DOWNLOADING):
            db.update_status(item_id, ItemStatus.CANCELLED)
            self.on_item_update(db.get_item(item_id))

    def cancel_playlist(self, playlist_id: str) -> None:
        for item in db.get_playlist_items(playlist_id):
            self.cancel_item(item.id)

    def delete_item(self, item_id: str) -> None:
        self.cancel_item(item_id)
        db.delete_item(item_id)
        self.on_item_update(None)

    def delete_playlist(self, playlist_id: str) -> None:
        for item in db.get_playlist_items(playlist_id):
            self.cancel_item(item.id)
        db.delete_playlist(playlist_id)
        self.on_item_update(None)

    def _loop(self) -> None:
        while self._running:
            self._pause_event.wait()

            with self._lock:
                self._active = {
                    k: v for k, v in self._active.items()
                    if v.is_cancelled() is False
                }
                active_count = len(self._active)

            if active_count < self.max_concurrent:
                pending = [it for it in db.get_pending_items() if it.selected]
                to_start = pending[: self.max_concurrent - active_count]
                for item in to_start:
                    downloader = Downloader()
                    with self._lock:
                        self._active[item.id] = downloader
                    thread = threading.Thread(
                        target=self._download_one,
                        args=(item, downloader),
                        daemon=True,
                    )
                    thread.start()

            time.sleep(0.5)

    def _download_one(self, item: QueueItem, downloader: Downloader) -> None:
        try:
            db.update_status(item.id, ItemStatus.DOWNLOADING)
            self.on_item_update(db.get_item(item.id))

            downloader.run(
                item=item,
                output_dir=self.output_dir,
                on_progress=lambda p: self._on_progress(item.id, p),
            )

            fpath = self._file_paths.pop(item.id, "")
            db.update_status(item.id, ItemStatus.COMPLETED,
                             completed_at=datetime.now(timezone.utc).isoformat(),
                             file_path=fpath)

            pid = item.playlist_id
            if pid:
                completed = db.count_playlist_completed(pid)
                db.update_playlist_progress(pid, completed)

        except DownloadCancelled:
            db.update_status(item.id, ItemStatus.CANCELLED)

        except Exception as exc:
            db.update_status(item.id, ItemStatus.FAILED, error=str(exc))

        finally:
            with self._lock:
                self._active.pop(item.id, None)

        self.on_item_update(db.get_item(item.id))

    def _on_progress(self, item_id: str, progress: DownloadProgress) -> None:
        if progress.file_path:
            self._file_paths[item_id] = progress.file_path
        item = db.get_item(item_id)
        if item:
            self.on_item_update(item)
        self._on_progress_ext(item_id, progress)

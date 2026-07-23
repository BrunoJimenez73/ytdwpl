from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from app.core.downloader import (
    DownloadCancelled,
    DownloadProgress,
    Downloader,
    extract_playlist_info,
)
from app.core.models import DownloadFormat, ItemStatus, QueueItem
from app import db


class QueueManager:
    def __init__(
        self,
        output_dir: Path,
        on_item_update: Callable[[QueueItem], None],
        on_progress: Callable[[DownloadProgress], None] = lambda p: None,
    ) -> None:
        self.output_dir = output_dir
        self.on_item_update = on_item_update
        self._on_progress_ext = on_progress
        self._thread: Optional[threading.Thread] = None
        self._active_item_id: Optional[str] = None
        self._downloader = Downloader()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel_requested = False
        self._running = True

    @property
    def active_item_id(self) -> Optional[str]:
        return self._active_item_id

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
        self._downloader.cancel()

    def pause(self) -> None:
        self._pause_event.clear()
        self._downloader.cancel()

    def resume(self) -> None:
        self._pause_event.set()

    def add_item(self, url: str, fmt: DownloadFormat) -> QueueItem:
        item = QueueItem.new(url, fmt)
        db.add_item(item)
        self.on_item_update(item)

        def _fetch_info() -> None:
            try:
                info = extract_playlist_info(url)
                db_item = db.get_item(item.id)
                if db_item:
                    db.update_status(
                        item.id,
                        db_item.status,
                        playlist_title=info.get("playlist_title", ""),
                        total_videos=info.get("video_count", 0),
                    )
                    updated = db.get_item(item.id)
                    if updated:
                        self.on_item_update(updated)
            except Exception:
                pass

        threading.Thread(target=_fetch_info, daemon=True).start()
        return item

    def cancel_item(self, item_id: str) -> None:
        if self._active_item_id == item_id:
            self._cancel_requested = True
            self._downloader.cancel()
        else:
            item = db.get_item(item_id)
            if item and item.status in (ItemStatus.PENDING, ItemStatus.DOWNLOADING):
                db.update_status(item_id, ItemStatus.CANCELLED)
                self.on_item_update(db.get_item(item_id))

    def delete_item(self, item_id: str) -> None:
        self.cancel_item(item_id)
        db.delete_item(item_id)
        self.on_item_update(None)

    def _loop(self) -> None:
        while self._running:
            self._pause_event.wait()

            items = db.get_pending_items()
            if not items:
                threading.Event().wait(1)
                continue

            item = items[0]
            self._active_item_id = item.id

            if not item.playlist_title:
                try:
                    info = extract_playlist_info(item.url)
                    item.playlist_title = info.get("playlist_title", "")
                    item.total_videos = info.get("video_count", 0)
                    db.update_status(
                        item.id, ItemStatus.PENDING,
                        playlist_title=item.playlist_title,
                        total_videos=item.total_videos,
                    )
                except Exception:
                    item.playlist_title = item.url.rsplit("/", 1)[-1]

            try:
                db.update_status(item.id, ItemStatus.DOWNLOADING)
                self.on_item_update(db.get_item(item.id))

                self._downloader.run(
                    item=item,
                    output_dir=self.output_dir,
                    on_progress=lambda p: self._on_progress(item.id, p),
                )

                db.update_status(
                    item.id,
                    ItemStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    completed_videos=item.total_videos,
                )

            except DownloadCancelled:
                status = ItemStatus.CANCELLED if self._cancel_requested else ItemStatus.PENDING
                self._cancel_requested = False
                db.update_status(item.id, status)

            except Exception as exc:
                db.update_status(
                    item.id,
                    ItemStatus.FAILED,
                    error=str(exc),
                )

            self.on_item_update(db.get_item(item.id))
            self._active_item_id = None

    def _on_progress(self, item_id: str, progress: DownloadProgress) -> None:
        item = db.get_item(item_id)
        if item:
            item.completed_videos = progress.playlist_index or 0
            item.total_videos = max(item.total_videos, progress.playlist_count or 0)
            self.on_item_update(item)
        self._on_progress_ext(progress)

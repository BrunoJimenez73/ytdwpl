from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app import db
from app.core.constants import QUEUE_POLL_INTERVAL, S
from app.core.downloader import (
    DownloadCancelled,
    DownloadPartial,
    DownloadProgress,
    Downloader,
    extract_playlist_info,
)
from app.core.models import DownloadFormat, ItemStatus, QueueItem

LOGGER = logging.getLogger("ytdwpl.queue")


class QueueManager:
    def __init__(
        self,
        output_dir: Path,
        on_item_update: Callable[[Optional[QueueItem]], None],
        on_progress: Callable[[str, DownloadProgress], None] = lambda i, p: None,
        max_concurrent: int = 4,
    ) -> None:
        self.output_dir = output_dir
        self.on_item_update = on_item_update
        self._on_progress_ext = on_progress
        self.max_concurrent = max_concurrent
        self._thread: Optional[threading.Thread] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._active: Dict[str, Downloader] = {}
        self._futures: Dict[str, Future[None]] = {}
        self._expansion_cancel: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._wake_event = threading.Event()
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
        if self._thread and self._thread.is_alive():
            return
        db.reset_stale_downloads()
        self._running = True
        self._executor = ThreadPoolExecutor(
            max_workers=max(10, self.max_concurrent),
            thread_name_prefix="ytdwpl-download",
        )
        self._wake_event.set()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        if not self._running and not (self._thread and self._thread.is_alive()):
            return
        self._running = False
        self._pause_event.set()
        self._wake_event.set()
        with self._lock:
            active = list(self._active.values())
        for dl in active:
            dl.cancel()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        with self._lock:
            futures = list(self._futures.values())
            executor = self._executor
        if futures:
            wait(futures, timeout=timeout)
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            self._executor = None
            self._futures.clear()

    def pause(self) -> None:
        self._pause_event.clear()
        for item in db.get_items_by_status(ItemStatus.QUEUED):
            db.update_status(item.id, ItemStatus.PAUSED)
            self.on_item_update(db.get_item(item.id))
        self._wake_event.set()
        with self._lock:
            active = list(self._active.items())
        for item_id, dl in active:
            db.update_status(item_id, ItemStatus.PAUSED)
            dl.cancel()

    def resume(self) -> None:
        self._pause_event.set()
        for item in db.get_items_by_status(ItemStatus.PAUSED):
            db.update_status(item.id, ItemStatus.QUEUED)
            self.on_item_update(db.get_item(item.id))
        self._wake_event.set()

    def add_playlist(self, url: str, fmt: DownloadFormat) -> None:
        playlist_id = QueueItem.new(url, fmt).id
        temp = QueueItem.new(
            url, fmt,
            playlist_title=S.ADD_PLAYLIST_FETCHING,
            playlist_id=playlist_id,
        )
        db.add_item(temp)
        db.update_status(temp.id, ItemStatus.EXPANDING)
        self.on_item_update(db.get_item(temp.id))
        cancel_event = threading.Event()
        with self._lock:
            self._expansion_cancel[playlist_id] = cancel_event

        def _expand() -> None:
            try:
                info = extract_playlist_info(url)
                if cancel_event.is_set():
                    db.delete_item(temp.id)
                    self.on_item_update(None)
                    return
                title = info.get("playlist_title", url.rsplit("/", 1)[-1])
                videos = info.get("videos", [])
                total = len(videos)

                items = [
                    QueueItem.new(
                        url=v["url"],
                        fmt=fmt,
                        video_title=v.get("title", ""),
                        playlist_title=title,
                        playlist_id=playlist_id,
                        total_videos=total,
                        playlist_url=url,
                    )
                    for v in videos
                ]
                if cancel_event.is_set():
                    db.delete_item(temp.id)
                    self.on_item_update(None)
                    return
                db.replace_item_with_items(temp.id, items)
                for item in items:
                    self.on_item_update(item)

            except Exception as exc:
                if cancel_event.is_set():
                    db.delete_item(temp.id)
                    self.on_item_update(None)
                    return
                LOGGER.exception("Playlist expansion failed for %s", url)
                db.update_status(
                    temp.id,
                    ItemStatus.FAILED,
                    playlist_title=S.ADD_PLAYLIST_ERROR,
                    error=str(exc),
                )
                self.on_item_update(db.get_item(temp.id))
            finally:
                with self._lock:
                    self._expansion_cancel.pop(playlist_id, None)

        threading.Thread(target=_expand, daemon=True).start()

    def toggle_selected(self, item_id: str) -> None:
        item = db.get_item(item_id)
        if item:
            new_val = not item.selected
            db.update_status(item_id, item.status, selected=int(new_val))
            self.on_item_update(db.get_item(item_id))

    def cancel_item(self, item_id: str) -> None:
        item = db.get_item(item_id)
        if item and item.status == ItemStatus.EXPANDING:
            with self._lock:
                event = self._expansion_cancel.get(item.playlist_id)
            if event:
                event.set()
            self.on_item_update(None)
            return
        with self._lock:
            dl = self._active.get(item_id)
        if dl:
            dl.cancel()
        self._wake_event.set()
        item = db.get_item(item_id)
        if item and item.status in (
            ItemStatus.PENDING, ItemStatus.QUEUED, ItemStatus.DOWNLOADING, ItemStatus.PAUSED,
        ):
            db.update_status(item_id, ItemStatus.CANCELLED)
            self.on_item_update(db.get_item(item_id))

    def cancel_playlist(self, playlist_id: str) -> None:
        with self._lock:
            expansion = self._expansion_cancel.get(playlist_id)
        if expansion:
            expansion.set()
        for item in db.get_playlist_items(playlist_id):
            self.cancel_item(item.id)

    def delete_item(self, item_id: str) -> None:
        self.cancel_item(item_id)
        db.delete_item(item_id)
        self.on_item_update(None)

    def delete_playlist(self, playlist_id: str) -> None:
        with self._lock:
            expansion = self._expansion_cancel.get(playlist_id)
        if expansion:
            expansion.set()
        for item in db.get_playlist_items(playlist_id):
            self.cancel_item(item.id)
        db.delete_playlist(playlist_id)
        self.on_item_update(None)

    def delete_selected_playlist(self, playlist_id: str) -> None:
        for item in db.get_playlist_items(playlist_id):
            if item.selected:
                self.cancel_item(item.id)
        db.delete_playlist_selected(playlist_id)
        self.on_item_update(None)

    def start_selected(self, playlist_id: str) -> None:
        db.update_playlist_status_selected(
            playlist_id, from_status=ItemStatus.PENDING, to_status=ItemStatus.QUEUED,
        )
        self._wake_event.set()
        for item in db.get_playlist_items(playlist_id):
            self.on_item_update(item)

    def retry_selected(self, playlist_id: str) -> None:
        db.update_playlist_status_selected_multi(
            playlist_id,
            from_statuses=[ItemStatus.FAILED, ItemStatus.PARTIAL, ItemStatus.CANCELLED],
            to_status=ItemStatus.QUEUED,
        )
        self._wake_event.set()
        for item in db.get_playlist_items(playlist_id):
            self.on_item_update(item)

    def pause_playlist(self, playlist_id: str) -> None:
        for item in db.get_playlist_items(playlist_id):
            if item.status == ItemStatus.QUEUED:
                db.update_status(item.id, ItemStatus.PAUSED)
                self.on_item_update(item)
            elif item.status == ItemStatus.DOWNLOADING:
                db.update_status(item.id, ItemStatus.PAUSED)
                with self._lock:
                    downloader = self._active.get(item.id)
                if downloader:
                    downloader.cancel()
                self.on_item_update(db.get_item(item.id))

    def resume_playlist(self, playlist_id: str) -> None:
        for item in db.get_playlist_items(playlist_id):
            if item.status in (ItemStatus.PENDING, ItemStatus.PAUSED):
                db.update_status(item.id, ItemStatus.QUEUED)
                self.on_item_update(item)

    def toggle_select_all(self, playlist_id: str, selected: bool) -> None:
        db.update_playlist_select_all(playlist_id, selected)
        for item in db.get_playlist_items(playlist_id):
            self.on_item_update(item)

    def reload_playlist(self, playlist_id: str) -> None:
        def _reload() -> None:
            p_url = db.get_playlist_url(playlist_id)
            if not p_url:
                return
            try:
                info = extract_playlist_info(p_url)
                existing = db.get_playlist_items(playlist_id)
                title = info.get("playlist_title", "") or (
                    existing[0].playlist_title if existing else ""
                )
                videos = info.get("videos", [])
                db.sync_playlist_items(playlist_id, title, videos)
                for item in db.get_playlist_items(playlist_id):
                    self.on_item_update(item)
            except Exception:
                LOGGER.exception("Playlist reload failed for %s", playlist_id)

        threading.Thread(target=_reload, daemon=True).start()

    def _loop(self) -> None:
        while self._running:
            self._pause_event.wait()
            if not self._running:
                break

            with self._lock:
                active_count = len(self._active)
                executor = self._executor

            if executor and active_count < self.max_concurrent:
                queued = [it for it in db.get_items_by_status(ItemStatus.QUEUED) if it.selected]
                to_start = queued[: self.max_concurrent - active_count]
                for queued_item in to_start:
                    item = db.claim_item(queued_item.id)
                    if not item:
                        continue
                    downloader = Downloader()
                    with self._lock:
                        self._active[item.id] = downloader
                    self.on_item_update(item)
                    try:
                        future = executor.submit(self._download_one, item, downloader)
                    except RuntimeError:
                        with self._lock:
                            self._active.pop(item.id, None)
                        db.update_status(item.id, ItemStatus.QUEUED)
                        break
                    with self._lock:
                        self._futures[item.id] = future
                    future.add_done_callback(
                        lambda _, item_id=item.id: self._future_done(item_id)
                    )

            self._wake_event.wait(QUEUE_POLL_INTERVAL)
            self._wake_event.clear()

    def _download_one(self, item: QueueItem, downloader: Downloader) -> None:
        try:
            with Downloader.archive_lock(item, self.output_dir):
                if downloader.is_cancelled():
                    raise DownloadCancelled()
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
            current = db.get_item(item.id)
            if current and current.status != ItemStatus.PAUSED:
                db.update_status(item.id, ItemStatus.CANCELLED)

        except DownloadPartial as exc:
            db.update_status(item.id, ItemStatus.PARTIAL, error=str(exc))

        except Exception as exc:
            db.update_status(item.id, ItemStatus.FAILED, error=str(exc))

        finally:
            with self._lock:
                self._active.pop(item.id, None)
            self._wake_event.set()

        self.on_item_update(db.get_item(item.id))

    def _on_progress(self, item_id: str, progress: DownloadProgress) -> None:
        if progress.file_path:
            self._file_paths[item_id] = progress.file_path
        self._on_progress_ext(item_id, progress)

    def _future_done(self, item_id: str) -> None:
        with self._lock:
            self._futures.pop(item_id, None)

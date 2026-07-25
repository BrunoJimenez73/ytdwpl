from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.core.models import DownloadFormat, ItemStatus, QueueItem
from app.core.queue import QueueManager


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_file = tmp_path / "test_queue.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)
    monkeypatch.setattr(db, "_local", threading.local())
    db.init_db()


class TestQueueManager:
    @pytest.fixture
    def queue(self) -> QueueManager:
        q = QueueManager(
            output_dir=Path("/tmp/ytdwpl"),
            on_item_update=MagicMock(),
            on_progress=lambda i, p: None,
            max_concurrent=2,
        )
        q._running = False
        return q

    def test_max_concurrent_default(self):
        q = QueueManager(
            output_dir=Path("/tmp"),
            on_item_update=MagicMock(),
        )
        assert q.max_concurrent == 4

    def _make_queue(self, mocker) -> QueueManager:
        q = QueueManager(
            output_dir=Path("/tmp/ytdwpl"),
            on_item_update=MagicMock(),
            on_progress=lambda i, p: None,
            max_concurrent=2,
        )
        q._running = False
        return q

    def test_add_playlist_creates_items(self, monkeypatch):
        fake_info = {
            "playlist_title": "Test",
            "video_count": 3,
            "videos": [
                {"url": "https://youtube.com/watch?v=1", "title": "Video 1", "index": 1},
                {"url": "https://youtube.com/watch?v=2", "title": "Video 2", "index": 2},
                {"url": "https://youtube.com/watch?v=3", "title": "Video 3", "index": 3},
            ],
        }
        import app.core.queue
        monkeypatch.setattr(app.core.queue, "extract_playlist_info", lambda url: fake_info)

        queue = QueueManager(
            output_dir=Path("/tmp/ytdwpl"),
            on_item_update=MagicMock(),
            on_progress=lambda i, p: None,
            max_concurrent=2,
        )
        queue._running = False
        queue.add_playlist("https://youtube.com/playlist?list=ABC", DownloadFormat.VIDEO)
        import time
        time.sleep(0.5)
        all_items = db.get_all_items()
        assert len(all_items) == 3

    def test_add_playlist_preserves_format(self, monkeypatch):
        fake_info = {
            "playlist_title": "Audio Playlist",
            "video_count": 1,
            "videos": [{"url": "https://youtube.com/watch?v=1", "title": "Song", "index": 1}],
        }
        import app.core.queue
        monkeypatch.setattr(app.core.queue, "extract_playlist_info", lambda url: fake_info)

        queue = QueueManager(
            output_dir=Path("/tmp/ytdwpl"),
            on_item_update=MagicMock(),
            on_progress=lambda i, p: None,
            max_concurrent=2,
        )
        queue._running = False
        queue.add_playlist("https://youtube.com/playlist?list=XYZ", DownloadFormat.AUDIO)
        import time
        time.sleep(0.5)
        items = db.get_all_items()
        assert items[0].format == DownloadFormat.AUDIO

    def test_add_playlist_with_empty_result(self, monkeypatch):
        fake_info = {"playlist_title": "Empty", "video_count": 0, "videos": []}
        import app.core.queue
        monkeypatch.setattr(app.core.queue, "extract_playlist_info", lambda url: fake_info)

        queue = QueueManager(
            output_dir=Path("/tmp/ytdwpl"),
            on_item_update=MagicMock(),
            on_progress=lambda i, p: None,
            max_concurrent=2,
        )
        queue._running = False
        queue.add_playlist("https://youtube.com/playlist?list=EMPTY", DownloadFormat.VIDEO)
        import time
        time.sleep(0.5)
        items = db.get_all_items()
        assert len(items) == 0

    def test_add_playlist_preserves_expansion_error(self, monkeypatch):
        import app.core.queue
        monkeypatch.setattr(
            app.core.queue,
            "extract_playlist_info",
            lambda url: (_ for _ in ()).throw(RuntimeError("network failed")),
        )
        queue = QueueManager(
            output_dir=Path("/tmp/ytdwpl"),
            on_item_update=MagicMock(),
            on_progress=lambda i, p: None,
            max_concurrent=2,
        )
        queue._running = False
        queue.add_playlist("https://youtube.com/playlist?list=ERROR", DownloadFormat.VIDEO)
        import time
        time.sleep(0.5)
        items = db.get_all_items()
        assert len(items) == 1
        assert items[0].status == ItemStatus.FAILED
        assert "network failed" in items[0].error

    def test_cancel_pending_item(self, queue: QueueManager):
        item = QueueItem.new("https://example.com/v1", DownloadFormat.VIDEO)
        db.add_item(item)
        queue.cancel_item(item.id)
        loaded = db.get_item(item.id)
        assert loaded is not None
        assert loaded.status == ItemStatus.CANCELLED

    def test_delete_item_removes_from_db(self, queue: QueueManager):
        item = QueueItem.new("https://example.com/v1", DownloadFormat.VIDEO)
        db.add_item(item)
        queue.delete_item(item.id)
        assert db.get_item(item.id) is None

    def test_pause_and_resume(self, queue: QueueManager):
        assert queue.is_paused is False
        queue.pause()
        assert queue.is_paused is True
        queue.resume()
        assert queue.is_paused is False

    def test_pause_and_resume_queued_item(self, queue: QueueManager):
        item = QueueItem.new("https://example.com/v1", DownloadFormat.VIDEO)
        db.add_item(item)
        db.update_status(item.id, ItemStatus.QUEUED)

        queue.pause()
        assert db.get_item(item.id).status == ItemStatus.PAUSED

        queue.resume()
        assert db.get_item(item.id).status == ItemStatus.QUEUED

    def test_active_ids_starts_empty(self, queue: QueueManager):
        assert queue.active_ids == []

    def test_stop_cancels_all(self, queue: QueueManager):
        queue.stop()
        assert queue._running is False

    def test_start_is_idempotent(self, queue: QueueManager):
        queue.start()
        first_thread = queue._thread
        queue.start()
        assert queue._thread is first_thread
        queue.stop()

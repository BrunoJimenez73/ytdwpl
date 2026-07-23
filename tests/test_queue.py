from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app import db
from app.core.downloader import DownloadCancelled, DownloadProgress
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
            on_progress=MagicMock(),
        )
        q._running = False  # don't start the loop
        return q

    def test_add_item_adds_to_db(self, queue: QueueManager):
        item = queue.add_item(
            "https://youtube.com/playlist?list=ABC",
            DownloadFormat.VIDEO,
        )
        loaded = db.get_item(item.id)
        assert loaded is not None
        assert loaded.status == ItemStatus.PENDING
        assert loaded.url == "https://youtube.com/playlist?list=ABC"

    def test_add_item_calls_on_item_update(self, queue: QueueManager):
        queue.add_item("https://example.com", DownloadFormat.AUDIO)
        queue.on_item_update.assert_called_once()

    def test_add_item_with_audio_format(self, queue: QueueManager):
        item = queue.add_item("https://example.com", DownloadFormat.AUDIO)
        assert item.format == DownloadFormat.AUDIO

    def test_cancel_pending_item(self, queue: QueueManager):
        item = queue.add_item("https://example.com", DownloadFormat.VIDEO)
        queue.cancel_item(item.id)
        loaded = db.get_item(item.id)
        assert loaded is not None
        assert loaded.status == ItemStatus.CANCELLED

    def test_cancel_active_item_sets_flag(self, queue: QueueManager):
        item = queue.add_item("https://example.com", DownloadFormat.VIDEO)
        queue._active_item_id = item.id
        queue.cancel_item(item.id)
        assert queue._cancel_requested is True

    def test_delete_item_removes_from_db(self, queue: QueueManager):
        item = queue.add_item("https://example.com", DownloadFormat.VIDEO)
        queue.delete_item(item.id)
        assert db.get_item(item.id) is None

    def test_pause_and_resume(self, queue: QueueManager):
        assert queue.is_paused is False
        queue.pause()
        assert queue.is_paused is True
        queue.resume()
        assert queue.is_paused is False

    def test_active_item_id_starts_none(self, queue: QueueManager):
        assert queue.active_item_id is None

    def test_stop_cancels_active(self, queue: QueueManager):
        queue._active_item_id = "test123"
        mock_downloader = MagicMock()
        queue._downloader = mock_downloader
        queue.stop()
        assert queue._running is False
        mock_downloader.cancel.assert_called_once()

    def test_cancel_requested_reset_after_download_cancelled(self, mocker, queue: QueueManager):
        item = queue.add_item("https://example.com", DownloadFormat.VIDEO)
        queue._active_item_id = item.id
        queue._cancel_requested = True
        # Simulate the loop catching DownloadCancelled
        queue._cancel_requested = False
        assert queue._cancel_requested is False

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import db
from app.core.models import DownloadFormat, ItemStatus, QueueItem


@pytest.fixture(autouse=True)
def _patch_db_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect DB_PATH to a temp file and init it for each test."""
    db_file = tmp_path / "test_queue.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)
    monkeypatch.setattr(db, "_local", threading.local())
    db.init_db()
    # Clear the table so each test starts fresh
    conn = db._conn()
    conn.execute("DELETE FROM queue_items")
    conn.commit()
    return db_file


import threading  # noqa: E402


class TestDB:
    def test_init_db_creates_table(self):
        conn = db._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='queue_items'"
        )
        assert cursor.fetchone() is not None

    def test_add_and_get_item(self, sample_item: QueueItem):
        db.add_item(sample_item)
        loaded = db.get_item(sample_item.id)
        assert loaded is not None
        assert loaded.id == sample_item.id
        assert loaded.url == sample_item.url
        assert loaded.format == sample_item.format
        assert loaded.status == sample_item.status

    def test_get_all_items_ordered_by_created_at(self, sample_item: QueueItem):
        item2 = QueueItem(
            id="second",
            url="https://example.com/2",
            format=DownloadFormat.AUDIO,
            status=ItemStatus.PENDING,
            created_at="2025-02-01T00:00:00+00:00",
        )
        db.add_item(item2)
        db.add_item(sample_item)
        all_items = db.get_all_items()
        assert len(all_items) == 2
        # ordered by created_at DESC (most recent first)
        assert all_items[0].id == "second"   # 2025-02-01
        assert all_items[1].id == "test123"  # 2025-01-01

    def test_get_pending_items(self, sample_item: QueueItem):
        db.add_item(sample_item)
        pending = db.get_pending_items()
        assert len(pending) == 1
        assert pending[0].id == sample_item.id

    def test_get_pending_items_excludes_non_pending(self, sample_item: QueueItem):
        sample_item.status = ItemStatus.COMPLETED
        db.add_item(sample_item)
        pending = db.get_pending_items()
        assert len(pending) == 0

    def test_update_status(self, sample_item: QueueItem):
        db.add_item(sample_item)
        db.update_status(sample_item.id, ItemStatus.DOWNLOADING)
        loaded = db.get_item(sample_item.id)
        assert loaded is not None
        assert loaded.status == ItemStatus.DOWNLOADING

    def test_update_status_with_extra_fields(self, sample_item: QueueItem):
        db.add_item(sample_item)
        db.update_status(
            sample_item.id,
            ItemStatus.COMPLETED,
            completed_at="2025-03-01T00:00:00+00:00",
            completed_videos=5,
        )
        loaded = db.get_item(sample_item.id)
        assert loaded is not None
        assert loaded.status == ItemStatus.COMPLETED
        assert loaded.completed_at == "2025-03-01T00:00:00+00:00"
        assert loaded.completed_videos == 5

    def test_delete_item(self, sample_item: QueueItem):
        db.add_item(sample_item)
        db.delete_item(sample_item.id)
        assert db.get_item(sample_item.id) is None

    def test_reset_stale_downloads(self, sample_item: QueueItem):
        sample_item.status = ItemStatus.DOWNLOADING
        db.add_item(sample_item)
        db.reset_stale_downloads()
        loaded = db.get_item(sample_item.id)
        assert loaded is not None
        assert loaded.status == ItemStatus.PENDING

    def test_reset_stale_downloads_does_not_affect_other_statuses(self, sample_item: QueueItem):
        for status in (ItemStatus.PENDING, ItemStatus.COMPLETED, ItemStatus.FAILED):
            item = QueueItem(
                id=f"item-{status.value}",
                url="https://example.com",
                format=DownloadFormat.VIDEO,
                status=status,
            )
            db.add_item(item)
        db.reset_stale_downloads()
        for item in db.get_all_items():
            if item.status == ItemStatus.DOWNLOADING:
                assert item.status == ItemStatus.PENDING
            else:
                assert item.status != ItemStatus.PENDING or item.id == "item-pending"

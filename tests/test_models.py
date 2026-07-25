from __future__ import annotations

from app.core.models import DownloadFormat, ItemStatus, QueueItem


class TestDownloadFormat:
    def test_values(self):
        assert DownloadFormat.AUDIO.value == "audio"
        assert DownloadFormat.VIDEO.value == "video"

    def test_enum_members(self):
        assert len(DownloadFormat) == 2


class TestItemStatus:
    def test_values(self):
        assert ItemStatus.PENDING.value == "pending"
        assert ItemStatus.DOWNLOADING.value == "downloading"
        assert ItemStatus.PAUSED.value == "paused"
        assert ItemStatus.COMPLETED.value == "completed"
        assert ItemStatus.PARTIAL.value == "partial"
        assert ItemStatus.FAILED.value == "failed"
        assert ItemStatus.CANCELLED.value == "cancelled"


class TestQueueItem:
    def test_new_creates_pending_item(self):
        item = QueueItem.new(
            url="https://youtube.com/playlist?list=XYZ",
            fmt=DownloadFormat.VIDEO,
        )
        assert item.status == ItemStatus.PENDING
        assert item.url == "https://youtube.com/playlist?list=XYZ"
        assert item.format == DownloadFormat.VIDEO
        assert len(item.id) == 12
        assert item.created_at != ""
        assert item.playlist_title == ""

    def test_new_defaults(self):
        item = QueueItem.new("https://example.com", DownloadFormat.AUDIO)
        assert item.format == DownloadFormat.AUDIO
        assert item.completed_videos == 0
        assert item.total_videos == 0
        assert item.error == ""

    def test_repr(self, sample_item):
        s = repr(sample_item)
        assert "QueueItem" in s
        assert "test123" in s

    def test_equality_by_id(self, sample_item):
        same = QueueItem(
            id="test123",
            url="https://other.com",
            format=DownloadFormat.AUDIO,
            status=ItemStatus.COMPLETED,
        )
        assert sample_item.id == same.id

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DownloadFormat(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


class ItemStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    id: str
    url: str
    format: DownloadFormat
    status: ItemStatus
    playlist_title: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: str = ""
    archive_path: str = ""
    total_videos: int = 0
    completed_videos: int = 0

    @classmethod
    def new(cls, url: str, fmt: DownloadFormat) -> QueueItem:
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=uuid.uuid4().hex[:12],
            url=url,
            format=fmt,
            status=ItemStatus.PENDING,
            created_at=now,
        )

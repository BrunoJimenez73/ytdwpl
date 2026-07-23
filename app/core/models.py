from __future__ import annotations

import uuid
from dataclasses import dataclass
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
    video_title: str = ""
    playlist_id: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: str = ""
    file_path: str = ""
    archive_path: str = ""
    selected: bool = True
    total_videos: int = 0
    completed_videos: int = 0

    @classmethod
    def new(
        cls,
        url: str,
        fmt: DownloadFormat,
        *,
        video_title: str = "",
        playlist_title: str = "",
        playlist_id: str = "",
        selected: bool = True,
        total_videos: int = 0,
    ) -> QueueItem:
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=uuid.uuid4().hex[:12],
            url=url,
            format=fmt,
            status=ItemStatus.PENDING,
            video_title=video_title,
            playlist_title=playlist_title,
            playlist_id=playlist_id,
            created_at=now,
            selected=selected,
            total_videos=total_videos,
        )

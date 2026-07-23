from __future__ import annotations

from pathlib import Path

import pytest

from app.core.models import DownloadFormat, ItemStatus, QueueItem


@pytest.fixture
def sample_item() -> QueueItem:
    return QueueItem(
        id="test123",
        url="https://youtube.com/playlist?list=ABC",
        format=DownloadFormat.VIDEO,
        status=ItemStatus.PENDING,
        playlist_title="Test Playlist",
        created_at="2025-01-01T00:00:00+00:00",
        total_videos=5,
    )


@pytest.fixture
def tmp_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    return home

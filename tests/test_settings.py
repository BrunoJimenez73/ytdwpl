from __future__ import annotations

import json
from pathlib import Path

from app.core.models import DownloadFormat
from app.core.settings import AppSettings


class TestAppSettings:
    def test_defaults(self):
        s = AppSettings()
        assert s.output_dir == ""
        assert s.format == DownloadFormat.VIDEO.value
        assert s.max_concurrent == 4

    def test_load_returns_default_when_no_file(self, tmp_home: Path):
        s = AppSettings.load()
        assert s.output_dir == ""
        assert s.format == DownloadFormat.VIDEO.value
        assert s.max_concurrent == 4

    def test_save_and_load(self, tmp_home: Path):
        s = AppSettings(output_dir="C:/Downloads", format="audio", max_concurrent=3)
        s.save()
        loaded = AppSettings.load()
        assert loaded.output_dir == "C:/Downloads"
        assert loaded.format == "audio"
        assert loaded.max_concurrent == 3

    def test_save_creates_json_file(self, tmp_home: Path):
        s = AppSettings(output_dir="/tmp", format="video", max_concurrent=2)
        s.save()
        path = tmp_home / ".ytdwpl" / "settings.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["output_dir"] == "/tmp"
        assert data["format"] == "video"
        assert data["max_concurrent"] == 2

    def test_load_corrupted_json_returns_default(self, tmp_home: Path):
        path = tmp_home / ".ytdwpl" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text("{corrupted}")
        s = AppSettings.load()
        assert s.output_dir == ""

    def test_path_creates_directory(self, tmp_home: Path):
        p = AppSettings.path()
        assert p.parent.exists()

    def test_normalize_invalid_values(self):
        settings = AppSettings(format="unknown", max_concurrent=999)
        settings.normalize()
        assert settings.format == DownloadFormat.VIDEO.value
        assert settings.max_concurrent == 10

    def test_save_normalizes_values(self, tmp_home: Path):
        settings = AppSettings(format="unknown", max_concurrent=0)
        settings.save()
        loaded = AppSettings.load()
        assert loaded.format == DownloadFormat.VIDEO.value
        assert loaded.max_concurrent == 1

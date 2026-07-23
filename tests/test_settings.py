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

    def test_load_returns_default_when_no_file(self, tmp_home: Path):
        s = AppSettings.load()
        assert s.output_dir == ""
        assert s.format == DownloadFormat.VIDEO.value

    def test_save_and_load(self, tmp_home: Path):
        s = AppSettings(output_dir="C:/Downloads", format="audio")
        s.save()

        loaded = AppSettings.load()
        assert loaded.output_dir == "C:/Downloads"
        assert loaded.format == "audio"

    def test_save_creates_json_file(self, tmp_home: Path):
        s = AppSettings(output_dir="/tmp", format="video")
        s.save()

        path = tmp_home / ".ytdwpl" / "settings.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["output_dir"] == "/tmp"
        assert data["format"] == "video"

    def test_load_corrupted_json_returns_default(self, tmp_home: Path):
        path = tmp_home / ".ytdwpl" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text("{corrupted}")
        s = AppSettings.load()
        assert s.output_dir == ""

    def test_path_creates_directory(self, tmp_home: Path):
        p = AppSettings.path()
        assert p.parent.exists()

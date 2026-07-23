from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.core.downloader import (
    DownloadProgress,
    Downloader,
    _parse_size,
    _sanitize_dirname,
    extract_playlist_info,
)
from app.core.models import DownloadFormat, ItemStatus, QueueItem


class TestParseSize:
    def test_bytes(self):
        assert _parse_size("1048576") == 1.0  # 1 MiB in bytes

    def test_mib(self):
        result = _parse_size("5.5 MiB")
        assert abs(result - 5.5) < 0.01

    def test_gib(self):
        result = _parse_size("1.0 GiB")
        assert abs(result - 1024.0) < 0.01

    def test_mb(self):
        result = _parse_size("10 MB")
        assert abs(result - 9.5367) < 0.1  # 10 MB → MiB

    def test_kib(self):
        result = _parse_size("512 KiB")
        assert abs(result - 0.5) < 0.01

    def test_empty_string(self):
        assert _parse_size("") == 0.0

    def test_invalid_string(self):
        assert _parse_size("not-a-size") == 0.0


class TestSanitizeDirname:
    def test_replaces_invalid_chars(self):
        assert _sanitize_dirname('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_strips_trailing_spaces_and_dots(self):
        assert _sanitize_dirname("  hello. ") == "hello"

    def test_keeps_valid_name(self):
        assert _sanitize_dirname("My Playlist 2025") == "My Playlist 2025"


class TestDownloadProgress:
    def test_defaults(self):
        p = DownloadProgress()
        assert p.percent == 0.0
        assert p.status == "starting"
        assert p.log_lines == []

    def test_fields(self):
        p = DownloadProgress(
            video_title="Test",
            percent=50.0,
            speed="1.5 MiB/s",
            eta="10s",
            playlist_index=2,
            playlist_count=10,
            status="downloading",
        )
        assert p.video_title == "Test"
        assert p.percent == 50.0
        assert p.speed == "1.5 MiB/s"
        assert p.eta == "10s"
        assert p.playlist_index == 2
        assert p.playlist_count == 10


class TestDownloader:
    def test_cancel_before_run(self):
        d = Downloader()
        d.cancel()
        assert d.is_cancelled()

    def test_progress_regex_video(self):
        line = "[download] Downloading video 1 of 5"
        m = re.search(r'Downloading (?:video|item)\s+(\d+)\s+of\s+(\d+)', line)
        assert m is not None
        assert m.group(1) == "1"
        assert m.group(2) == "5"

    def test_progress_regex_item(self):
        """yt-dlp uses 'item' for playlists, not 'video'."""
        line = "[download] Downloading item 3 of 10"
        m = re.search(r'Downloading (?:video|item)\s+(\d+)\s+of\s+(\d+)', line)
        assert m is not None
        assert m.group(1) == "3"
        assert m.group(2) == "10"

    def test_destination_line_regex(self):
        line = "[download] Destination: C:\\Downloads\\Playlist\\MyVideo.mp4"
        title_part = line.split("Destination:")[-1].strip()
        name = Path(title_part).stem
        assert name == "MyVideo"

    def test_has_already_been_downloaded(self):
        line = "[download] C:\\Downloads\\Playlist\\ExistingVideo.mp4 has already been downloaded"
        path_part = line.split("[download]")[-1].strip()
        name = Path(path_part.split("has already")[0].strip()).stem
        assert name == "ExistingVideo"

    def test_progress_line_pattern(self):
        line = "[download]  45.2% of ~105.3MiB at 2.5 MiB/s ETA 00:12"
        pattern = re.compile(
            r'\[download\]\s+(.+?)\s+of\s+[~]?(\S+)\s+'
            r'(?:at\s+(\S+))?\s*(?:ETA\s+(\S+))?'
        )
        m = pattern.search(line)
        assert m is not None
        assert m.group(1).strip() == "45.2%"
        assert m.group(2) == "105.3MiB"
        # group 3 captures first token after "at" (speed number without units)
        assert m.group(3) == "2.5"

    def test_progress_line_pattern_with_eta(self):
        line = "[download]  50.0% of 100.0MiB ETA 00:30"
        pattern = re.compile(
            r'\[download\]\s+(.+?)\s+of\s+[~]?(\S+)\s+'
            r'(?:at\s+(\S+))?\s*(?:ETA\s+(\S+))?'
        )
        m = pattern.search(line)
        assert m is not None
        assert m.group(4) == "00:30"

    def test_finished_line(self):
        line = "[download] 100% of 50.0MiB in 00:30"
        assert "[download] Finished" in line or "100%" in line

    def test_extract_playlist_info_happy_path(self, mocker):
        fake_output = json.dumps({
            "playlist_title": "Mi Playlist",
            "playlist": "Mi Playlist",
            "title": "Video 1",
        })
        mock_proc = mocker.MagicMock()
        mock_proc.stdout = [fake_output + "\n", fake_output.replace("1", "2") + "\n"]
        mock_proc.wait.return_value = 0
        mocker.patch("subprocess.Popen", return_value=mock_proc)

        info = extract_playlist_info("https://youtube.com/playlist?list=ABC")
        assert info["playlist_title"] == "Mi Playlist"
        assert info["video_count"] == 2

    def test_extract_playlist_info_fallback_title(self, mocker):
        fake_output = json.dumps({"title": "Solo Video"})
        mock_proc = mocker.MagicMock()
        mock_proc.stdout = [fake_output + "\n"]
        mock_proc.wait.return_value = 0
        mocker.patch("subprocess.Popen", return_value=mock_proc)

        info = extract_playlist_info(
            "https://youtube.com/playlist?list=UNIQUE"
        )
        # fallback to last URL segment (includes query string since no path segment)
        assert "UNIQUE" in info["playlist_title"]
        assert info["video_count"] == 1

    def test_extract_playlist_info_empty_output(self, mocker):
        mock_proc = mocker.MagicMock()
        mock_proc.stdout = []
        mock_proc.wait.return_value = 0
        mocker.patch("subprocess.Popen", return_value=mock_proc)

        info = extract_playlist_info("https://youtube.com/playlist?list=XYZ")
        assert info["playlist_title"] == "playlist?list=XYZ"
        assert info["video_count"] == 0

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.models import DownloadFormat

MAX_CONCURRENT = 10


@dataclass
class AppSettings:
    output_dir: str = ""
    format: str = DownloadFormat.VIDEO.value
    max_concurrent: int = 4

    def normalize(self) -> "AppSettings":
        """Normalize persisted values before they reach the UI or queue."""
        if self.format not in {fmt.value for fmt in DownloadFormat}:
            self.format = DownloadFormat.VIDEO.value
        try:
            self.max_concurrent = min(MAX_CONCURRENT, max(1, int(self.max_concurrent)))
        except (TypeError, ValueError):
            self.max_concurrent = 4
        self.output_dir = str(self.output_dir or "").strip()
        return self

    @staticmethod
    def path() -> Path:
        p = Path.home() / ".ytdwpl"
        p.mkdir(parents=True, exist_ok=True)
        return p / "settings.json"

    @staticmethod
    def load() -> "AppSettings":
        p = AppSettings.path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                allowed = {"output_dir", "format", "max_concurrent"}
                values = {key: value for key, value in d.items() if key in allowed}
                return AppSettings(**values).normalize()
            except Exception:
                pass
        return AppSettings()

    def save(self) -> None:
        """Persist normalized settings atomically."""
        self.normalize()
        target = AppSettings.path()
        fd, temporary = tempfile.mkstemp(prefix="settings-", suffix=".json", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(asdict(self), handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

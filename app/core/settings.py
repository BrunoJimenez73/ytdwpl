import json
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.models import DownloadFormat


@dataclass
class AppSettings:
    output_dir: str = ""
    format: str = DownloadFormat.VIDEO.value
    max_concurrent: int = 4

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
                d = json.loads(p.read_text())
                return AppSettings(**d)
            except Exception:
                pass
        return AppSettings()

    def save(self):
        AppSettings.path().write_text(json.dumps(asdict(self), indent=2))

from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

from app import db
from app.ui.layout import build_app


def main(page: ft.Page) -> None:
    db.init_db()
    output_dir = _resolve_output_dir()
    build_app(page, output_dir)


def _resolve_output_dir() -> Path:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        return Path(args[0]).resolve()
    return Path.home() / "ytdwpl-downloads"


ft.app(target=main)

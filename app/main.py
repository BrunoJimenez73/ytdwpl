from __future__ import annotations

import atexit
import sys
from pathlib import Path

import flet as ft

from app import db
from app.core.logging_config import configure_logging
from app.core.queue import QueueManager
from app.core.settings import AppSettings
from app.ui.layout import build_app


_app_queue: QueueManager | None = None


def _cleanup() -> None:
    global _app_queue
    if _app_queue is not None:
        _app_queue.stop()
        _app_queue = None
    db.close_all_connections()


def main(page: ft.Page) -> None:
    global _app_queue
    configure_logging()
    atexit.register(_cleanup)
    db.init_db()
    settings = AppSettings.load()
    queue = build_app(page, Path(settings.output_dir))
    _app_queue = queue

    def _handle_close(e) -> None:
        _cleanup()

    page.on_close = _handle_close


ft.run(main=main, view=ft.AppView.WEB_BROWSER)

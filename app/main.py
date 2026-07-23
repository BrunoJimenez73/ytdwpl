from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

from app import db
from app.core.settings import AppSettings
from app.ui.layout import build_app


def main(page: ft.Page) -> None:
    db.init_db()
    settings = AppSettings.load()
    build_app(page, Path(settings.output_dir))


ft.run(main=main, view=ft.AppView.WEB_BROWSER)

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import flet as ft

from app.core.downloader import DownloadProgress
from app.core.models import DownloadFormat, ItemStatus, QueueItem
from app.core.queue import QueueManager
from app.core.settings import AppSettings
from app.ui.add_dialog import show_add_dialog
from app.ui.queue_table import build_queue_table
from app.ui.settings_dialog import show_settings_dialog

_THROTTLE = 0.3


def _open_file_desktop(file_path: str) -> None:
    p = Path(file_path)
    if not p.exists():
        alt = Path(file_path.replace("/", "\\"))
        if alt.exists():
            p = alt
        else:
            print(f"[open] file not found: {file_path}")
            return
    print(f"[open] opening: {p}")
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception as e:
        print(f"[open] error: {e}")


def build_app(page: ft.Page, output_dir: Path) -> None:
    page.title = "ytdwpl - YouTube Playlist Downloader"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    page.spacing = 12

    settings = AppSettings.load()
    output_dir = Path(settings.output_dir) if settings.output_dir else output_dir

    _progress_data: Dict[str, DownloadProgress] = {}
    _last_progress_ts = 0.0

    pending_table = ft.Container(expand=True)
    completed_table = ft.Container(expand=True)
    _pending_ref = ft.Ref[ft.ListView]()
    _completed_ref = ft.Ref[ft.ListView]()

    def _on_tab_change(e=None) -> None:
        _refresh()

    def _refresh() -> None:
        from app import db
        all_items = db.get_all_items()
        pending_items = [i for i in all_items if i.status in (
            ItemStatus.PENDING, ItemStatus.DOWNLOADING,
            ItemStatus.FAILED, ItemStatus.CANCELLED,
        )]
        completed_items = [i for i in all_items if i.status == ItemStatus.COMPLETED]

        _apply_table(_pending_ref, pending_table, pending_items, False)
        _apply_table(_completed_ref, completed_table, completed_items, True)
        page.update()

    def _apply_table(
        ref: ft.Ref[ft.ListView],
        container: ft.Container,
        items: list,
        is_completed: bool,
    ) -> None:
        new = build_queue_table(
            items=items,
            on_cancel=_cancel_item,
            on_delete=_delete_item,
            on_retry=_retry_item,
            on_toggle_selected=_toggle_selected,
            on_refresh=_refresh,
            on_cancel_playlist=_cancel_playlist,
            on_delete_selected=_delete_selected_playlist if is_completed else None,
            on_open_file=_open_file_desktop,
            active_progress=_progress_data,
            list_ref=None,
        )
        if isinstance(new, ft.ListView):
            if ref.current:
                ref.current.controls = new.controls
                ref.current.update()
            else:
                container.content = new
                ref.current = new
        else:
            container.content = new
            ref.current = None

    def _cancel_item(item_id: str) -> None:
        queue.cancel_item(item_id)
        _refresh()

    def _cancel_playlist(playlist_id: str) -> None:
        queue.cancel_playlist(playlist_id)
        _refresh()

    def _delete_item(item_id: str) -> None:
        queue.delete_item(item_id)
        _refresh()

    def _delete_selected_playlist(playlist_id: str) -> None:
        queue.delete_selected_playlist(playlist_id)
        _refresh()

    def _retry_item(item_id: str) -> None:
        from app import db
        item = db.get_item(item_id)
        if item:
            db.update_status(item_id, ItemStatus.PENDING)
            _refresh()

    def _toggle_selected(item_id: str) -> None:
        queue.toggle_selected(item_id)
        _refresh()

    def _add_item(url: str, fmt: DownloadFormat) -> None:
        queue.add_playlist(url, fmt)
        _refresh()

    def _on_settings_saved(new_settings: AppSettings) -> None:
        nonlocal settings
        settings = new_settings
        queue.max_concurrent = max(1, new_settings.max_concurrent)

    def _open_settings(e) -> None:
        show_settings_dialog(page, settings, _on_settings_saved)

    def _handle_progress(item_id: str, p: DownloadProgress) -> None:
        nonlocal _last_progress_ts
        _progress_data[item_id] = p
        now = time.time()
        if now - _last_progress_ts >= _THROTTLE:
            _last_progress_ts = now
            _refresh()

    def _handle_item_update(item: Optional[QueueItem]) -> None:
        _refresh()

    tabs = ft.Tabs(
        length=2,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Cola"),
                        ft.Tab(label="Completadas"),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        pending_table,
                        completed_table,
                    ],
                ),
            ],
        ),
        on_change=_on_tab_change,
    )

    queue = QueueManager(
        output_dir=Path(settings.output_dir) if settings.output_dir else Path.home(),
        on_item_update=_handle_item_update,
        on_progress=_handle_progress,
        max_concurrent=max(1, settings.max_concurrent),
    )

    settings_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        tooltip="Ajustes",
        on_click=_open_settings,
    )

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip="Agregar playlist",
        on_click=lambda e: show_add_dialog(page, _add_item),
        bgcolor=ft.Colors.PRIMARY,
        foreground_color=ft.Colors.ON_PRIMARY,
    )

    page.appbar = ft.AppBar(
        title=ft.Text("ytdwpl"),
        actions=[settings_btn],
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )

    page.add(tabs, fab)

    queue.start()
    _refresh()

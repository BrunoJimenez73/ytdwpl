from __future__ import annotations

from pathlib import Path
from typing import Optional

import flet as ft

from app.core.downloader import DownloadProgress
from app.core.models import DownloadFormat, ItemStatus, QueueItem
from app.core.queue import QueueManager
from app.core.settings import AppSettings
from app.ui.add_dialog import show_add_dialog
from app.ui.progress_card import build_progress_card
from app.ui.queue_table import build_queue_table
from app.ui.settings_dialog import show_settings_dialog


def build_app(page: ft.Page, output_dir: Path) -> None:
    page.title = "ytdwpl - YouTube Playlist Downloader"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    page.spacing = 16

    settings = AppSettings.load()
    output_dir = Path(settings.output_dir)

    active_progress = DownloadProgress()
    active_playlist_title = ""
    is_paused = False
    current_tab = 0

    pending_table = ft.Container(expand=True)
    completed_table = ft.Container(expand=True)
    progress_container = ft.Container(visible=False)

    def _on_tab_change(e=None) -> None:
        nonlocal current_tab
        current_tab = tabs.selected_index
        _refresh()

    def _refresh() -> None:
        from app import db
        all_items = db.get_all_items()
        pending_items = [i for i in all_items if i.status in (
            ItemStatus.PENDING, ItemStatus.DOWNLOADING,
            ItemStatus.FAILED, ItemStatus.CANCELLED,
        )]
        completed_items = [i for i in all_items if i.status == ItemStatus.COMPLETED]
        pending_table.content = build_queue_table(
            items=pending_items,
            on_cancel=_cancel_item,
            on_delete=_delete_item,
            on_retry=_retry_item,
        )
        completed_table.content = build_queue_table(
            items=completed_items,
            on_cancel=_cancel_item,
            on_delete=_delete_item,
            on_retry=_retry_item,
        )
        page.update()

    def _cancel_item(item_id: str) -> None:
        queue.cancel_item(item_id)
        _refresh()

    def _delete_item(item_id: str) -> None:
        queue.delete_item(item_id)
        _refresh()

    def _retry_item(item_id: str) -> None:
        from app import db
        item = db.get_item(item_id)
        if item:
            db.update_status(item_id, ItemStatus.PENDING)
            _refresh()

    def _add_item(url: str, fmt: DownloadFormat) -> None:
        queue.add_item(url, fmt)
        _refresh()

    def _on_pause(e) -> None:
        nonlocal is_paused
        if is_paused:
            queue.resume()
            is_paused = False
        else:
            queue.pause()
            is_paused = True
        _render_progress()

    def _on_cancel_active(e) -> None:
        if queue.active_item_id:
            queue.cancel_item(queue.active_item_id)
            progress_container.visible = False
            page.update()

    def _handle_progress(p: DownloadProgress) -> None:
        nonlocal active_progress
        active_progress = p
        _render_progress()

    def _handle_item_update(item: Optional[QueueItem]) -> None:
        nonlocal active_playlist_title
        if item and item.id == queue.active_item_id:
            active_playlist_title = item.playlist_title
        _refresh()

    def _render_progress() -> None:
        has_active = queue.active_item_id is not None
        progress_container.visible = has_active
        if has_active:
            progress_container.content = build_progress_card(
                progress=active_progress,
                playlist_title=active_playlist_title,
                is_paused=is_paused,
                on_pause=_on_pause,
                on_cancel=_on_cancel_active,
            )
        page.update()

    def _on_settings_saved(new_settings: AppSettings) -> None:
        nonlocal settings
        settings = new_settings

    def _open_settings(e) -> None:
        show_settings_dialog(page, settings, _on_settings_saved)

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
        output_dir=Path(settings.output_dir),
        on_item_update=_handle_item_update,
        on_progress=_handle_progress,
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

    page.add(
        progress_container,
        tabs,
        fab,
    )

    queue.start()
    _refresh()

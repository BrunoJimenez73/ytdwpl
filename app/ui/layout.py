from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

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
    page.spacing = 12

    settings = AppSettings.load()
    output_dir = Path(settings.output_dir) if settings.output_dir else output_dir

    current_tab = 0
    _progress_data: Dict[str, DownloadProgress] = {}

    pending_table = ft.Container(expand=True)
    completed_table = ft.Container(expand=True)
    active_cards_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    active_section = ft.Container(content=active_cards_col, visible=False)

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

        active_ids = queue.active_ids
        active_section.visible = len(active_ids) > 0
        cards = []
        for aid in active_ids:
            item = db.get_item(aid)
            if item:
                prog = _progress_data.get(aid, DownloadProgress())
                cards.append(build_progress_card(
                    item_id=aid,
                    progress=prog,
                    playlist_title=item.playlist_title,
                    on_cancel=_cancel_item,
                ))
        active_cards_col.controls = cards

        pending_table.content = build_queue_table(
            items=pending_items,
            on_cancel=_cancel_item,
            on_delete=_delete_item,
            on_retry=_retry_item,
            active_progress=_progress_data,
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
        queue.add_playlist(url, fmt)
        _refresh()

    def _on_settings_saved(new_settings: AppSettings) -> None:
        nonlocal settings
        settings = new_settings
        queue.max_concurrent = max(1, new_settings.max_concurrent)

    def _open_settings(e) -> None:
        show_settings_dialog(page, settings, _on_settings_saved)

    def _handle_progress(item_id: str, p: DownloadProgress) -> None:
        _progress_data[item_id] = p
        _render_active()

    def _handle_item_update(item: Optional[QueueItem]) -> None:
        _refresh()

    def _render_active() -> None:
        active_ids = queue.active_ids
        active_section.visible = len(active_ids) > 0
        cards = []
        for aid in active_ids:
            from app import db
            item = db.get_item(aid)
            if item:
                prog = _progress_data.get(aid, DownloadProgress())
                cards.append(build_progress_card(
                    item_id=aid,
                    progress=prog,
                    playlist_title=item.playlist_title,
                    on_cancel=_cancel_item,
                ))
        active_cards_col.controls = cards
        page.update()

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

    page.add(
        active_section,
        tabs,
        fab,
    )

    queue.start()
    _refresh()

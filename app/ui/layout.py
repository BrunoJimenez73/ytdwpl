from __future__ import annotations

from pathlib import Path
from typing import Optional

import flet as ft

from app.core.downloader import DownloadProgress
from app.core.models import DownloadFormat, ItemStatus, QueueItem
from app.core.queue import QueueManager
from app.ui.add_dialog import show_add_dialog
from app.ui.progress_card import build_progress_card
from app.ui.queue_table import build_queue_table


def build_app(page: ft.Page, output_dir: Path) -> None:
    page.title = "ytdwpl - YouTube Playlist Downloader"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    page.spacing = 16
    page.scroll = ft.ScrollMode.AUTO

    queue_data: list[QueueItem] = []
    active_progress = DownloadProgress()
    active_playlist_title = ""
    is_paused = False

    queue_table = ft.Container()
    progress_container = ft.Container(visible=False)
    empty_banner = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.PLAYLIST_PLAY, size=64, color=ft.Colors.GREY_400),
                ft.Text("Agrega una playlist para empezar",
                        size=18, color=ft.Colors.GREY_500),
                ft.Text("Usa el botón + en la esquina inferior derecha",
                        size=14, color=ft.Colors.GREY_400),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )

    tab_names = ["Cola", "Completadas"]
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[ft.Tab(text=n) for n in tab_names],
        on_change=lambda _: _refresh(),
    )

    def _refresh() -> None:
        nonlocal queue_data
        queue_data = _load_items_for_tab(tabs.selected_index)
        queue_table.content = build_queue_table(
            items=queue_data,
            on_cancel=_cancel_item,
            on_delete=_delete_item,
            on_retry=_retry_item,
        )
        page.update()

    def _load_items_for_tab(tab: int) -> list[QueueItem]:
        from app import db
        all_items = db.get_all_items()
        if tab == 0:
            return [i for i in all_items if i.status in (
                ItemStatus.PENDING, ItemStatus.DOWNLOADING,
                ItemStatus.FAILED, ItemStatus.CANCELLED,
            )]
        return [i for i in all_items if i.status == ItemStatus.COMPLETED]

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

    queue = QueueManager(
        output_dir=output_dir,
        on_item_update=_handle_item_update,
        on_progress=_handle_progress,
    )

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip="Agregar playlist",
        on_click=lambda e: show_add_dialog(page, _add_item),
        bgcolor=ft.Colors.PRIMARY,
        foreground_color=ft.Colors.ON_PRIMARY,
    )

    page.add(
        tabs,
        progress_container,
        empty_banner,
        queue_table,
        fab,
    )

    queue.start()
    _refresh()

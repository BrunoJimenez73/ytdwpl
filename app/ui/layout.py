from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Set

import flet as ft

from app.core.constants import PROGRESS_THROTTLE_SECONDS, S, AppTheme
from app.core.downloader import DownloadProgress
from app.core.models import DownloadFormat, ItemStatus, QueueItem
from app.core.queue import QueueManager
from app.core.settings import AppSettings
from app.ui.add_dialog import show_add_dialog
from app.ui.progress_card import build_progress_card
from app.ui.queue_table import TableConfig, build_queue_table
from app.ui.settings_dialog import show_settings_dialog


def _open_file_desktop(file_path: str, page: Optional[ft.Page] = None) -> None:
    p = Path(file_path)
    if not p.exists():
        alt = Path(file_path.replace("/", "\\"))
        if alt.exists():
            p = alt
        else:
            if page:
                _show_snack(page, f"{S.FILE_NOT_FOUND}: {file_path}")
            return
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception as e:
        if page:
            _show_snack(page, f"{S.OPEN_ERROR}: {e}")


def _show_snack(page: ft.Page, message: str) -> None:
    sb = ft.SnackBar(content=ft.Text(message), open=True)
    page.overlay.append(sb)
    page.update()


def build_app(page: ft.Page, output_dir: Path) -> None:
    page.title = S.APP_TITLE
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    page.spacing = 12

    settings = AppSettings.load()
    output_dir = Path(settings.output_dir) if settings.output_dir else output_dir

    _progress_data: Dict[str, DownloadProgress] = {}
    _progress_lock = threading.Lock()
    _last_progress_ts = 0.0
    _expanded_ids: Set[str] = set()

    pending_table = ft.Container(expand=True)
    completed_table = ft.Container(expand=True)
    _pending_ref = ft.Ref[ft.ListView]()
    _completed_ref = ft.Ref[ft.ListView]()
    active_download_card = ft.Container(visible=False)

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
        _update_active_card()
        page.update()

    def _apply_table(
        ref: ft.Ref[ft.ListView],
        container: ft.Container,
        items: list,
        is_completed: bool,
    ) -> None:
        config = TableConfig(
            items=items,
            on_cancel=_cancel_item,
            on_delete=_delete_item,
            on_retry=_retry_item,
            on_toggle_selected=_toggle_selected,
            on_refresh=_refresh,
            on_cancel_playlist=_cancel_playlist,
            on_delete_playlist=_delete_playlist,
            on_delete_selected=_delete_selected_playlist if is_completed else None,
            on_open_file=lambda p: _open_file_desktop(p, page),
            on_start_playlist=_start_playlist if not is_completed else None,
            on_pause_playlist=_pause_playlist if not is_completed else None,
            on_toggle_select_all=_toggle_select_all if not is_completed else None,
            on_reload_playlist=_reload_playlist if not is_completed else None,
            on_retry_selected=_retry_selected if not is_completed else None,
            active_progress=_progress_data,
            expanded_ids=_expanded_ids,
        )
        new = build_queue_table(config)
        container.content = new
        ref.current = new if isinstance(new, ft.ListView) else None

    def _update_active_card() -> None:
        from app import db
        downloading = db.get_downloading_items()
        if downloading:
            active = downloading[0]
            with _progress_lock:
                prog = _progress_data.get(active.id)
            active_download_card.content = build_progress_card(
                active.id, prog or DownloadProgress(),
                active.playlist_title, _cancel_item,
            )
            if not active_download_card.visible:
                active_download_card.visible = True
        elif active_download_card.visible:
            active_download_card.visible = False

    def _cancel_item(item_id: str) -> None:
        queue.cancel_item(item_id)
        _refresh()

    def _cancel_playlist(playlist_id: str) -> None:
        queue.cancel_playlist(playlist_id)
        _refresh()

    def _delete_playlist(playlist_id: str) -> None:
        queue.delete_playlist(playlist_id)
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
            db.update_status(item_id, ItemStatus.QUEUED, selected=1)
            _refresh()

    def _toggle_selected(item_id: str) -> None:
        queue.toggle_selected(item_id)
        _refresh()

    def _start_playlist(playlist_id: str) -> None:
        queue.start_selected(playlist_id)
        _refresh()

    def _pause_playlist(playlist_id: str) -> None:
        queue.pause_playlist(playlist_id)
        _refresh()

    def _toggle_select_all(playlist_id: str, selected: bool) -> None:
        queue.toggle_select_all(playlist_id, selected)
        _refresh()

    def _reload_playlist(playlist_id: str) -> None:
        queue.reload_playlist(playlist_id)
        _refresh()

    def _retry_selected(playlist_id: str) -> None:
        queue.retry_selected(playlist_id)
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
        with _progress_lock:
            _progress_data[item_id] = p
            now = time.time()
            if now - _last_progress_ts >= PROGRESS_THROTTLE_SECONDS:
                _last_progress_ts = now
                should_refresh = True
            else:
                should_refresh = False
        if should_refresh:
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
                        ft.Tab(label=S.TAB_QUEUE),
                        ft.Tab(label=S.TAB_COMPLETED),
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
        tooltip=S.TOOLTIP_SETTINGS,
        on_click=_open_settings,
    )

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip=S.TOOLTIP_ADD_PLAYLIST,
        on_click=lambda e: show_add_dialog(page, _add_item),
        bgcolor=AppTheme.PRIMARY,
        foreground_color=AppTheme.ON_PRIMARY,
    )

    page.appbar = ft.AppBar(
        title=ft.Text(S.APP_BAR_TITLE),
        actions=[settings_btn],
        bgcolor=AppTheme.SURFACE_CONTAINER_HIGHEST,
    )

    page.add(active_download_card, tabs, fab)

    queue.start()
    _refresh()

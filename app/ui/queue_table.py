from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import flet as ft

from app.core.downloader import DownloadProgress
from app.core.models import ItemStatus, QueueItem

_STATUS_LABELS = {
    ItemStatus.PENDING: ("Pendiente", ft.Colors.GREY),
    ItemStatus.DOWNLOADING: ("Descargando", ft.Colors.BLUE),
    ItemStatus.COMPLETED: ("Completada", ft.Colors.GREEN),
    ItemStatus.FAILED: ("Error", ft.Colors.RED),
    ItemStatus.CANCELLED: ("Cancelada", ft.Colors.ORANGE),
}

_expanded_playlist_ids: Set[str] = set()


def toggle_expanded(playlist_id: str) -> None:
    if playlist_id in _expanded_playlist_ids:
        _expanded_playlist_ids.discard(playlist_id)
    else:
        _expanded_playlist_ids.add(playlist_id)


def build_queue_table(
    items: List[QueueItem],
    on_cancel: Callable[[str], None],
    on_delete: Callable[[str], None],
    on_retry: Callable[[str], None],
    on_toggle_selected: Callable[[str], None],
    on_refresh: Callable[[], None],
    on_cancel_playlist: Optional[Callable[[str], None]] = None,
    on_delete_selected: Optional[Callable[[str], None]] = None,
    on_open_file: Optional[Callable[[str], None]] = None,
    active_progress: Optional[Dict[str, DownloadProgress]] = None,
    list_ref: Optional[ft.Ref[ft.ListView]] = None,
) -> ft.Control:
    active_progress = active_progress or {}

    if not items:
        c = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.INBOX, size=48, color=ft.Colors.GREY_400),
                ft.Text("No hay elementos en la lista",
                        color=ft.Colors.GREY_500, size=16),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(left=0, top=60, right=0, bottom=0),
            expand=True,
        )
        if list_ref:
            list_ref.current = None
        return c

    groups: Dict[str, List[QueueItem]] = {}
    standalone: List[QueueItem] = []
    for item in items:
        if item.playlist_id:
            groups.setdefault(item.playlist_id, []).append(item)
        else:
            standalone.append(item)

    for pid in groups:
        _expanded_playlist_ids.add(pid)

    rows: List[ft.Control] = []

    for pid, videos in groups.items():
        expanded = pid in _expanded_playlist_ids
        header = _build_playlist_header(
            pid, videos, expanded,
            on_toggle=lambda p=pid: (
                toggle_expanded(p),
                on_refresh(),
            ),
            on_delete_playlist=on_cancel_playlist,
            on_delete_selected=on_delete_selected,
        )
        rows.append(header)
        if expanded:
            for v in videos:
                prog = active_progress.get(v.id)
                rows.append(_build_video_row(
                    v, prog, on_cancel, on_delete,
                    on_retry, on_toggle_selected, on_open_file,
                ))

    for item in standalone:
        prog = active_progress.get(item.id)
        rows.append(_build_video_row(
            item, prog, on_cancel, on_delete,
            on_retry, on_toggle_selected, on_open_file,
        ))

    lv = ft.ListView(controls=rows, spacing=1, expand=True, padding=2)
    if list_ref:
        list_ref.current = lv
    return lv


def _build_playlist_header(
    playlist_id: str,
    videos: List[QueueItem],
    expanded: bool,
    on_toggle: Callable[[], None],
    on_delete_playlist: Optional[Callable[[str], None]],
    on_delete_selected: Optional[Callable[[str], None]],
) -> ft.Control:
    title = videos[0].playlist_title if videos and videos[0].playlist_title else "Playlist"
    total = len(videos)
    completed = sum(1 for v in videos if v.status == ItemStatus.COMPLETED)
    pending = sum(1 for v in videos if v.status == ItemStatus.PENDING)
    failed = sum(1 for v in videos if v.status == ItemStatus.FAILED)

    subtitle_parts = []
    if completed:
        subtitle_parts.append(f"{completed}\u2713")
    if pending:
        subtitle_parts.append(f"{pending} pend.")
    if failed:
        subtitle_parts.append(f"{failed} err.")
    subtitle = "  ".join(subtitle_parts) if subtitle_parts else f"{total} videos"

    icon = ft.Icons.EXPAND_MORE if expanded else ft.Icons.CHEVRON_RIGHT

    actions = ft.Row(spacing=0)
    if on_delete_selected:
        has_checked = any(v.selected for v in videos)
        if has_checked:
            actions.controls.append(ft.IconButton(
                ft.Icons.CHECKLIST,
                tooltip="Borrar marcados",
                icon_size=18,
                on_click=lambda e: on_delete_selected(playlist_id),
            ))
    if on_delete_playlist:
        actions.controls.append(ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            tooltip="Eliminar playlist",
            icon_size=18,
            on_click=lambda e: on_delete_playlist(playlist_id),
        ))

    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=20, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Column([
                ft.Text(title, weight=ft.FontWeight.W_600, size=14),
                ft.Text(subtitle, size=11, color=ft.Colors.GREY_600),
            ], spacing=1, tight=True, expand=True),
            actions,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        on_click=lambda e: on_toggle(),
        padding=ft.Padding(left=8, top=6, right=4, bottom=6),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=6,
    )


def _build_video_row(
    item: QueueItem,
    prog: Optional[DownloadProgress],
    on_cancel: Callable[[str], None],
    on_delete: Callable[[str], None],
    on_retry: Callable[[str], None],
    on_toggle_selected: Callable[[str], None],
    on_open_file: Optional[Callable[[str], None]],
) -> ft.Control:
    label, color = _STATUS_LABELS.get(item.status, (item.status.value, ft.Colors.GREY))
    is_finished = item.status in (ItemStatus.COMPLETED, ItemStatus.FAILED, ItemStatus.CANCELLED)
    is_downloading = item.status == ItemStatus.DOWNLOADING

    fmt_label = "MP4" if item.format.value == "video" else "MP3"
    video_name = item.video_title[:50] if item.video_title else item.url[:50]

    chk = ft.Checkbox(
        value=item.selected,
        on_change=lambda e, i=item.id: on_toggle_selected(i),
    )

    if is_downloading and prog:
        pct = prog.percent
        status_content = ft.Column([
            ft.ProgressBar(
                value=pct / 100.0,
                color=ft.Colors.BLUE,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                height=4,
                border_radius=2,
            ),
            ft.Row([
                ft.Text(f"{pct:.1f}%", size=11, color=ft.Colors.BLUE),
                ft.Text(prog.speed or "", size=10, color=ft.Colors.GREY_500),
                ft.Text(f"ETA {prog.eta}" if prog.eta else "", size=10, color=ft.Colors.GREY_500),
            ], spacing=4),
        ], spacing=1, tight=True)
    else:
        status_content = ft.Container(
            ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_500),
            padding=ft.Padding(left=4, top=1, right=4, bottom=1),
            border_radius=3,
        )

    progress_text = ""
    if item.status == ItemStatus.COMPLETED and item.file_path:
        fname = Path(item.file_path).name
        progress_text = f"\u2713 {fname}"
    elif item.status == ItemStatus.FAILED and item.error:
        progress_text = item.error[:35]
    elif item.total_videos > 0:
        progress_text = f"{item.completed_videos}/{item.total_videos}"
        if item.status == ItemStatus.COMPLETED:
            progress_text = f"\u2713 {progress_text}"
    elif item.status == ItemStatus.COMPLETED:
        progress_text = "\u2713 Completa"

    is_completed_file = item.status == ItemStatus.COMPLETED and bool(item.file_path)
    if is_completed_file and on_open_file:
        title_control = ft.TextButton(
            content=ft.Text(video_name, size=12, overflow=ft.TextOverflow.ELLIPSIS,
                            color=ft.Colors.PRIMARY),
            on_click=lambda e, p=item.file_path: on_open_file(p),
            style=ft.ButtonStyle(padding=0, bgcolor=ft.Colors.TRANSPARENT),
            tooltip="Abrir archivo",
        )
    else:
        title_control = ft.Text(video_name, size=12, overflow=ft.TextOverflow.ELLIPSIS)

    actions = []
    if item.status == ItemStatus.PENDING:
        actions.append(_action_btn(ft.Icons.CANCEL_OUTLINED, "Cancelar",
                                   lambda e, i=item.id: on_cancel(i)))
    if is_finished:
        actions.append(_action_btn(ft.Icons.DELETE_OUTLINE, "Eliminar",
                                   lambda e, i=item.id: on_delete(i)))
    if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
        actions.append(_action_btn(ft.Icons.REPLAY, "Reintentar",
                                   lambda e, i=item.id: on_retry(i)))

    return ft.Container(
        content=ft.Row([
            chk,
            ft.Column([
                title_control,
                ft.Row([
                    ft.Text(fmt_label, size=10, color=ft.Colors.GREY_500),
                    ft.Container(
                        ft.Text(progress_text, size=10, color=ft.Colors.GREY_600),
                        visible=bool(progress_text) and not is_downloading,
                    ),
                ], spacing=6),
            ], spacing=1, tight=True, expand=True),
            status_content,
            ft.Row(actions, spacing=1),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(left=24, top=3, right=4, bottom=3),
        bgcolor=ft.Colors.SURFACE,
        border_radius=4,
    )


def _action_btn(icon: ft.Icons, tip: str, on_click) -> ft.Control:
    return ft.IconButton(icon, tooltip=tip, icon_size=16, on_click=on_click)

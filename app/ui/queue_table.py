from __future__ import annotations

from typing import Callable, Dict, List, Optional

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


def build_queue_table(
    items: List[QueueItem],
    on_cancel: Callable[[str], None],
    on_delete: Callable[[str], None],
    on_retry: Callable[[str], None],
    on_cancel_playlist: Optional[Callable[[str], None]] = None,
    active_progress: Optional[Dict[str, DownloadProgress]] = None,
) -> ft.Control:
    active_progress = active_progress or {}

    if not items:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.INBOX, size=48, color=ft.Colors.GREY_400),
                ft.Text("No hay elementos en la lista",
                        color=ft.Colors.GREY_500, size=16),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(left=0, top=60, right=0, bottom=0),
            expand=True,
        )

    rows = []
    for item in items:
        prog = active_progress.get(item.id)
        rows.append(_build_row(
            item, prog, on_cancel, on_delete, on_retry, on_cancel_playlist,
        ))

    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Playlist", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Video", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Formato", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Estado", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Progreso", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Acciones", weight=ft.FontWeight.BOLD)),
        ],
        rows=rows,
        border=ft.Border(
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        ),
        border_radius=8,
        heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        column_spacing=16,
        horizontal_margin=8,
        data_row_min_height=40,
    )


def _build_row(
    item: QueueItem,
    prog: Optional[DownloadProgress],
    on_cancel: Callable[[str], None],
    on_delete: Callable[[str], None],
    on_retry: Callable[[str], None],
    on_cancel_playlist: Optional[Callable[[str], None]],
) -> ft.DataRow:
    label, color = _STATUS_LABELS.get(item.status, (item.status.value, ft.Colors.GREY))
    is_finished = item.status in (ItemStatus.COMPLETED, ItemStatus.FAILED, ItemStatus.CANCELLED)
    is_downloading = item.status == ItemStatus.DOWNLOADING

    fmt_label = "MP4" if item.format.value == "video" else "MP3"

    playlist_name = item.playlist_title[:30] if item.playlist_title else ""
    video_name = item.video_title[:40] if item.video_title else item.url[:40]
    if not item.video_title:
        video_name = f"Video #{item.id[:8]}"

    actions = []
    if item.status == ItemStatus.PENDING:
        actions.append(_action_btn(ft.Icons.CANCEL_OUTLINED, "Cancelar", lambda i=item.id: on_cancel(i)))
    if is_finished:
        actions.append(_action_btn(ft.Icons.DELETE_OUTLINE, "Eliminar", lambda i=item.id: on_delete(i)))
    if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
        actions.append(_action_btn(ft.Icons.REPLAY, "Reintentar", lambda i=item.id: on_retry(i)))

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
            ft.Text(f"{pct:.1f}%", size=11, color=ft.Colors.BLUE),
        ], spacing=1, tight=True)
    else:
        status_content = ft.Container(
            ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_500),
            padding=ft.Padding(left=4, top=1, right=4, bottom=1),
            border_radius=3,
        )

    progress_text = ""
    if item.status == ItemStatus.FAILED and item.error:
        progress_text = item.error[:30]
    elif item.total_videos > 0:
        progress_text = f"{item.completed_videos}/{item.total_videos}"
        if item.status == ItemStatus.COMPLETED:
            progress_text = f"\u2713 {progress_text}"
    elif item.status == ItemStatus.COMPLETED:
        progress_text = "\u2713 Completa"

    return ft.DataRow(
        cells=[
            ft.DataCell(ft.Text(playlist_name, size=12, overflow=ft.TextOverflow.ELLIPSIS)),
            ft.DataCell(ft.Text(video_name, size=12, overflow=ft.TextOverflow.ELLIPSIS)),
            ft.DataCell(ft.Text(fmt_label, size=12)),
            ft.DataCell(status_content),
            ft.DataCell(ft.Text(progress_text, size=12)),
            ft.DataCell(ft.Row(actions, spacing=1)),
        ]
    )


def _action_btn(icon: ft.Icons, tip: str, on_click) -> ft.Control:
    return ft.IconButton(icon, tooltip=tip, icon_size=16, on_click=on_click)

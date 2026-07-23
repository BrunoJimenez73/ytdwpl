from __future__ import annotations

from typing import Callable, List

import flet as ft

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
) -> ft.Control:
    headers = [
        ft.DataColumn(ft.Text("Playlist", weight=ft.FontWeight.BOLD)),
        ft.DataColumn(ft.Text("Formato", weight=ft.FontWeight.BOLD)),
        ft.DataColumn(ft.Text("Estado", weight=ft.FontWeight.BOLD)),
        ft.DataColumn(ft.Text("Progreso", weight=ft.FontWeight.BOLD)),
        ft.DataColumn(ft.Text("Acciones", weight=ft.FontWeight.BOLD)),
    ]

    rows = [_build_row(item, on_cancel, on_delete, on_retry) for item in items]

    if not rows:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.INBOX, size=48, color=ft.Colors.GREY_400),
                    ft.Text("No hay descargas en la cola",
                            color=ft.Colors.GREY_500, size=16),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            alignment=ft.alignment.center,
            padding=ft.Padding(left=0, top=60, right=0, bottom=0),
            expand=True,
        )

    return ft.DataTable(
        columns=headers,
        rows=rows,
        border=ft.Border(
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        ),
        border_radius=8,
        heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        column_spacing=24,
        horizontal_margin=12,
        data_row_min_height=48,
    )


def _build_row(
    item: QueueItem,
    on_cancel: Callable[[str], None],
    on_delete: Callable[[str], None],
    on_retry: Callable[[str], None],
) -> ft.DataRow:
    label, color = _STATUS_LABELS.get(item.status, (item.status.value, ft.Colors.GREY))
    is_finished = item.status in (ItemStatus.COMPLETED, ItemStatus.FAILED, ItemStatus.CANCELLED)

    actions = []
    if item.status == ItemStatus.PENDING:
        actions.append(
            ft.IconButton(
                ft.Icons.CANCEL_OUTLINED,
                tooltip="Cancelar",
                icon_size=18,
                on_click=lambda _, i=item.id: on_cancel(i),
            )
        )
    if is_finished:
        actions.append(
            ft.IconButton(
                ft.Icons.DELETE_OUTLINE,
                tooltip="Eliminar",
                icon_size=18,
                on_click=lambda _, i=item.id: on_delete(i),
            )
        )
    if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
        actions.append(
            ft.IconButton(
                ft.Icons.REPLAY,
                tooltip="Reintentar",
                icon_size=18,
                on_click=lambda _, i=item.id: on_retry(i),
            )
        )

    progress_text = ""
    if item.total_videos > 0:
        progress_text = f"{item.completed_videos}/{item.total_videos}"
        if item.status == ItemStatus.COMPLETED:
            progress_text = f"✓ {progress_text}"
    elif item.status == ItemStatus.COMPLETED:
        progress_text = "✓ Completa"

    fmt_label = "MP4" if item.format.value == "video" else "MP3"

    title = item.playlist_title[:50] if item.playlist_title else item.url[:50]

    return ft.DataRow(
        cells=[
            ft.DataCell(ft.Text(title, overflow=ft.TextOverflow.ELLIPSIS)),
            ft.DataCell(ft.Text(fmt_label)),
            ft.DataCell(
                ft.Container(
                    ft.Text(label, size=12, color=color, weight=ft.FontWeight.W_500),
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                    border_radius=4,
                )
            ),
            ft.DataCell(ft.Text(progress_text, size=13)),
            ft.DataCell(ft.Row(actions, spacing=2)),
        ]
    )

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from app.core.models import DownloadFormat


def show_add_dialog(
    page: ft.Page,
    on_submit: Callable[[str, DownloadFormat], None],
) -> None:
    url_field = ft.TextField(
        label="URL de la playlist",
        hint_text="https://youtube.com/playlist?list=...",
        width=500,
        autofocus=True,
    )
    format_dropdown = ft.Dropdown(
        label="Formato",
        options=[
            ft.dropdown.Option(DownloadFormat.VIDEO.value, "Video (MP4)"),
            ft.dropdown.Option(DownloadFormat.AUDIO.value, "Audio (MP3)"),
        ],
        value=DownloadFormat.VIDEO.value,
        width=200,
    )
    error_text = ft.Text(value="", color=ft.Colors.RED)

    def submit_click(e):
        url = url_field.value.strip() if url_field.value else ""
        if not url:
            error_text.value = "Ingresa una URL válida"
            page.update()
            return
        fmt = DownloadFormat(format_dropdown.value or DownloadFormat.VIDEO.value)
        page.pop_dialog()
        on_submit(url, fmt)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Agregar Playlist"),
        content=ft.Column(
            [
                url_field,
                format_dropdown,
                error_text,
            ],
            tight=True,
            spacing=12,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledButton("Agregar", on_click=submit_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.show_dialog(dialog)

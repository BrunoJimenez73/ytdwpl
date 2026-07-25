from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse

import flet as ft

from app.core.constants import S, AppTheme
from app.core.models import DownloadFormat


def show_add_dialog(
    page: ft.Page,
    on_submit: Callable[[str, DownloadFormat], None],
    default_format: DownloadFormat = DownloadFormat.VIDEO,
) -> None:
    url_field = ft.TextField(
        label=S.ADD_DIALOG_URL_LABEL,
        hint_text=S.ADD_DIALOG_URL_HINT,
        width=500,
        autofocus=True,
    )
    format_dropdown = ft.Dropdown(
        label=S.ADD_DIALOG_FORMAT_LABEL,
        options=[
            ft.dropdown.Option(DownloadFormat.VIDEO.value, S.ADD_DIALOG_VIDEO_OPTION),
            ft.dropdown.Option(DownloadFormat.AUDIO.value, S.ADD_DIALOG_AUDIO_OPTION),
        ],
        value=default_format.value,
        width=200,
    )
    error_text = ft.Text(value="", color=AppTheme.ERROR)

    def submit_click(e) -> None:
        url = url_field.value.strip() if url_field.value else ""
        if not url:
            error_text.value = S.ADD_DIALOG_ERROR_EMPTY_URL
            page.update()
            return
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            error_text.value = S.ADD_DIALOG_ERROR_INVALID_URL
            page.update()
            return
        fmt = DownloadFormat(format_dropdown.value or DownloadFormat.VIDEO.value)
        page.pop_dialog()
        on_submit(url, fmt)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(S.ADD_DIALOG_TITLE),
        content=ft.Column(
            [url_field, format_dropdown, error_text],
            tight=True,
            spacing=12,
        ),
        actions=[
            ft.TextButton(S.ADD_DIALOG_CANCEL, on_click=lambda e: page.pop_dialog()),
            ft.FilledButton(S.ADD_DIALOG_SUBMIT, on_click=submit_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.show_dialog(dialog)

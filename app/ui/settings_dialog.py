from __future__ import annotations

from typing import Callable

import flet as ft

from app.core.constants import S, AppTheme, DEFAULT_MAX_CONCURRENT, MAX_CONCURRENT_MIN
from app.core.models import DownloadFormat
from app.core.settings import AppSettings


def show_settings_dialog(
    page: ft.Page,
    settings: AppSettings,
    on_saved: Callable[[AppSettings], None],
) -> None:
    output_field = ft.TextField(
        label=S.SETTINGS_OUTPUT_LABEL,
        value=settings.output_dir,
        width=400,
    )
    format_dropdown = ft.Dropdown(
        label=S.SETTINGS_FORMAT_LABEL,
        value=settings.format,
        options=[
            ft.dropdown.Option(key=DownloadFormat.VIDEO.value, text="Video (mp4)"),
            ft.dropdown.Option(key=DownloadFormat.AUDIO.value, text="Audio (mp3)"),
        ],
        width=200,
    )
    concurrent_field = ft.TextField(
        label=S.SETTINGS_CONCURRENT_LABEL,
        value=str(settings.max_concurrent),
        width=100,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def close(e=None) -> None:
        page.pop_dialog()

    def save(e) -> None:
        settings.output_dir = output_field.value.strip()
        settings.format = format_dropdown.value
        try:
            settings.max_concurrent = max(MAX_CONCURRENT_MIN, int(concurrent_field.value.strip()))
        except (ValueError, AttributeError):
            settings.max_concurrent = DEFAULT_MAX_CONCURRENT
        settings.save()
        on_saved(settings)
        close(e)

    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(S.SETTINGS_TITLE),
        content=ft.Column([
            ft.Text(S.SETTINGS_OUTPUT_HINT),
            output_field,
            ft.Divider(),
            format_dropdown,
            ft.Divider(),
            ft.Row([
                ft.Text(S.SETTINGS_CONCURRENT_HINT),
                concurrent_field,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton(S.SETTINGS_CANCEL, on_click=close),
            ft.FilledButton(S.SETTINGS_SAVE, on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.show_dialog(d)

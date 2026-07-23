from __future__ import annotations

import flet as ft

from app.core.downloader import DownloadProgress


def build_progress_card(
    progress: DownloadProgress,
    playlist_title: str,
    is_paused: bool,
    on_pause: ft.ControlEventCallback,
    on_cancel: ft.ControlEventCallback,
) -> ft.Control:
    if is_paused:
        status_color = ft.Colors.ORANGE
        status_text = "Pausada"
        pause_icon = ft.Icons.PLAY_ARROW
        pause_label = "Reanudar"
    else:
        status_color = ft.Colors.BLUE
        status_text = "Descargando"
        pause_icon = ft.Icons.PAUSE
        pause_label = "Pausar"

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=status_color, size=24),
                        ft.Text(playlist_title[:60], weight=ft.FontWeight.W_600, size=16),
                        ft.Container(
                            ft.Text(status_text, size=12, color=status_color,
                                    weight=ft.FontWeight.W_500),
                            padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                            border=ft.Border(
                                ft.BorderSide(1, status_color),
                                ft.BorderSide(1, status_color),
                                ft.BorderSide(1, status_color),
                                ft.BorderSide(1, status_color),
                            ),
                            border_radius=12,
                        ),
                    ],
                    spacing=8,
                ),
                ft.ProgressBar(
                    value=progress.percent / 100.0 if progress.percent else None,
                    color=status_color,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    height=8,
                    border_radius=4,
                ),
                ft.Row(
                    [
                        ft.Text(f"{progress.percent:.1f}%", size=14,
                                weight=ft.FontWeight.W_500),
                        ft.Text(f"{progress.downloaded_mb:.1f} MB / {progress.total_mb:.1f} MB"
                                if progress.total_mb else "",
                                size=12, color=ft.Colors.GREY_600),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    progress.video_title or "Obteniendo información...",
                    size=13,
                    color=ft.Colors.GREY_700,
                    italic=not progress.video_title,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SPEED, size=14, color=ft.Colors.GREY_600),
                        ft.Text(progress.speed or "--", size=12,
                                color=ft.Colors.GREY_600),
                        ft.Text("·", color=ft.Colors.GREY_400),
                        ft.Icon(ft.Icons.TIMER_OUTLINED, size=14,
                                color=ft.Colors.GREY_600),
                        ft.Text(f"ETA {progress.eta}" if progress.eta else "ETA --",
                                size=12, color=ft.Colors.GREY_600),
                        ft.Text("·", color=ft.Colors.GREY_400),
                        ft.Text(
                            f"Video {progress.playlist_index} de {progress.playlist_count}"
                            if progress.playlist_count else "",
                            size=12, color=ft.Colors.GREY_600,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Row(
                    [
                        ft.FilledTonalButton(
                            pause_label,
                            icon=pause_icon,
                            on_click=on_pause,
                        ),
                        ft.FilledButton(
                            "Cancelar",
                            icon=ft.Icons.STOP,
                            on_click=on_cancel,
                            color=ft.Colors.ON_ERROR,
                            bgcolor=ft.Colors.ERROR,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=10,
        ),
        padding=ft.Padding(left=16, top=16, right=16, bottom=16),
        border=ft.Border(
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        ),
        border_radius=12,
        bgcolor=ft.Colors.SURFACE,
    )

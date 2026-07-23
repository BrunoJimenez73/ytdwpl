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

    pct = f"{progress.percent:.1f}%" if progress.percent else "0.0%"

    video_count = ""
    if progress.playlist_count:
        video_count = f"Video {progress.playlist_index} de {progress.playlist_count}"

    size_info = ""
    if progress.total_mb:
        size_info = f"{progress.downloaded_mb:.1f} MB / {progress.total_mb:.1f} MB"

    log_arrow = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16, color=ft.Colors.GREY_600)
    log_toggle_text = ft.Text("Mostrar registro", size=12, color=ft.Colors.GREY_600)
    log_visible = len(progress.log_lines) > 0

    log_text = ft.Text(
        "\n".join(progress.log_lines[-60:]),
        size=10,
        color=ft.Colors.GREY_400,
        font_family="monospace",
        selectable=True,
        no_wrap=False,
    )

    log_scroll = ft.Container(
        content=ft.Column(
            [log_text],
            scroll=ft.ScrollMode.AUTO,
            height=200,
        ),
        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.GREY_900),
        border_radius=6,
        padding=8,
    )

    log_container = ft.Container(content=log_scroll, visible=False)

    def toggle_log(e) -> None:
        new_visible = not log_container.visible
        log_container.visible = new_visible
        log_toggle_text.value = "Ocultar registro" if new_visible else "Mostrar registro"
        log_arrow.name = ft.Icons.KEYBOARD_ARROW_UP if new_visible else ft.Icons.KEYBOARD_ARROW_DOWN
        if e.control.page:
            e.control.page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=status_color, size=24),
                        ft.Text(playlist_title[:60], weight=ft.FontWeight.W_600, size=16, expand=True),
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
                        ft.Text(pct, size=14, weight=ft.FontWeight.W_500),
                        ft.Text(size_info, size=12, color=ft.Colors.GREY_600),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    progress.video_title or "Obteniendo informacion...",
                    size=13,
                    color=ft.Colors.GREY_700,
                    italic=not progress.video_title,
                ),
                ft.Container(
                    ft.Text(video_count, size=13, weight=ft.FontWeight.W_600,
                            color=ft.Colors.PRIMARY),
                    visible=bool(video_count),
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
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Row(
                                [log_arrow, log_toggle_text],
                                spacing=4,
                            ),
                            on_click=toggle_log,
                            visible=log_visible,
                        ),
                    ],
                    spacing=8,
                ),
                log_container,
            ],
            spacing=8,
            tight=True,
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

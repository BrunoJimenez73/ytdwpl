from __future__ import annotations

import flet as ft

from app.core.downloader import DownloadProgress


def build_progress_card(
    item_id: str,
    progress: DownloadProgress,
    playlist_title: str,
    on_cancel: ft.ControlEventCallback,
) -> ft.Control:
    pct = f"{progress.percent:.1f}%" if progress.percent else "0.0%"

    size_info = ""
    if progress.total_mb:
        size_info = f"{progress.downloaded_mb:.1f} MB / {progress.total_mb:.1f} MB"

    log_arrow = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=14, color=ft.Colors.GREY_500)
    log_toggle_text = ft.Text("Registro", size=11, color=ft.Colors.GREY_500)
    log_text = ft.Text(
        "\n".join(progress.log_lines[-60:]),
        size=10,
        color=ft.Colors.GREY_400,
        font_family="monospace",
        selectable=True,
    )
    log_scroll = ft.Container(
        content=ft.Column([log_text], scroll=ft.ScrollMode.AUTO, height=150),
        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.GREY_900),
        border_radius=4,
        padding=6,
    )
    log_container = ft.Container(content=log_scroll, visible=False)

    def toggle_log(e) -> None:
        new_visible = not log_container.visible
        log_container.visible = new_visible
        log_toggle_text.value = "Ocultar" if new_visible else "Registro"
        log_arrow.name = ft.Icons.KEYBOARD_ARROW_UP if new_visible else ft.Icons.KEYBOARD_ARROW_DOWN
        if e.control.page:
            e.control.page.update()

    return ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=ft.Colors.BLUE, size=18),
                    ft.Text(playlist_title[:40], size=13, weight=ft.FontWeight.W_600, expand=True),
                ], spacing=4),
                ft.Text(progress.video_title or "Iniciando...", size=12,
                        color=ft.Colors.GREY_700, italic=not progress.video_title),
            ], spacing=2, tight=True, expand=True),
            ft.Column([
                ft.ProgressBar(
                    value=progress.percent / 100.0 if progress.percent else None,
                    color=ft.Colors.BLUE,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    height=6,
                    border_radius=3,
                ),
                ft.Row([
                    ft.Text(pct, size=12, weight=ft.FontWeight.W_500),
                    ft.Text(size_info, size=11, color=ft.Colors.GREY_600),
                ], spacing=4),
                ft.Row([
                    ft.Icon(ft.Icons.SPEED, size=12, color=ft.Colors.GREY_500),
                    ft.Text(progress.speed or "--", size=11, color=ft.Colors.GREY_500),
                    ft.Text("·", size=11, color=ft.Colors.GREY_400),
                    ft.Text(f"ETA {progress.eta}" if progress.eta else "ETA --",
                            size=11, color=ft.Colors.GREY_500),
                ], spacing=2),
            ], spacing=2, tight=True, expand=True),
            ft.Column([
                ft.IconButton(
                    ft.Icons.STOP,
                    icon_size=18,
                    tooltip="Cancelar",
                    on_click=lambda _: on_cancel(item_id),
                ),
                ft.Container(
                    content=ft.Row([log_arrow, log_toggle_text], spacing=2),
                    on_click=toggle_log,
                ),
            ], spacing=2, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
        padding=ft.Padding(left=10, top=8, right=6, bottom=8),
        border=ft.Border(
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        ),
        border_radius=8,
        bgcolor=ft.Colors.SURFACE,
    )

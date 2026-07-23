import flet as ft

from app.core.models import DownloadFormat
from app.core.settings import AppSettings


def show_settings_dialog(page: ft.Page, settings: AppSettings, on_saved):
    output_field = ft.TextField(
        label="Carpeta de descargas",
        value=settings.output_dir,
        width=400,
    )
    format_dropdown = ft.Dropdown(
        label="Formato por defecto",
        value=settings.format,
        options=[
            ft.dropdown.Option(key=DownloadFormat.VIDEO.value, text="Video (mp4)"),
            ft.dropdown.Option(key=DownloadFormat.AUDIO.value, text="Audio (mp3)"),
        ],
        width=200,
    )
    concurrent_field = ft.TextField(
        label="Descargas simultaneas",
        value=str(settings.max_concurrent),
        width=100,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def close(e):
        d.open = False
        page.update()

    def save(e):
        settings.output_dir = output_field.value.strip()
        settings.format = format_dropdown.value
        try:
            settings.max_concurrent = max(1, int(concurrent_field.value.strip()))
        except (ValueError, AttributeError):
            settings.max_concurrent = 4
        settings.save()
        on_saved(settings)
        close(e)

    d = ft.AlertDialog(
        modal=True,
        title=ft.Text("Configuración"),
        content=ft.Column([
            ft.Text("Ruta de descarga (ruta completa):"),
            output_field,
            ft.Divider(),
            format_dropdown,
            ft.Divider(),
            ft.Row([
                ft.Text("Descargas simultaneas (1-10):"),
                concurrent_field,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Cancelar", on_click=close),
            ft.FilledButton("Guardar", on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(d)
    d.open = True
    page.update()

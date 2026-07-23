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

    def close(e):
        d.open = False
        page.update()

    def save(e):
        settings.output_dir = output_field.value.strip()
        settings.format = format_dropdown.value
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

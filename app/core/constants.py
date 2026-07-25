from __future__ import annotations

import flet as ft

from app.core.models import ItemStatus


class S:
    APP_TITLE = "ytdwpl - YouTube Playlist Downloader"
    APP_BAR_TITLE = "ytdwpl"

    TAB_QUEUE = "Cola"
    TAB_COMPLETED = "Completadas"
    SEARCH_HINT = "Buscar en la cola..."

    EMPTY_LIST_TITLE = "No hay elementos en la lista"
    PLAYLIST_FALLBACK_TITLE = "Playlist"
    CHECK_MARK = "\u2713"

    STATUS_PENDING = "Pendiente"
    STATUS_EXPANDING = "Obteniendo playlist"
    STATUS_QUEUED = "En cola"
    STATUS_DOWNLOADING = "Descargando"
    STATUS_PAUSED = "Pausada"
    STATUS_COMPLETED = "Completada"
    STATUS_PARTIAL = "Parcial"
    STATUS_FAILED = "Error"
    STATUS_CANCELLED = "Cancelada"

    PROGRESS_STARTING = "Iniciando..."
    PROGRESS_LOG_TOGGLE = "Registro"
    PROGRESS_LOG_HIDE = "Ocultar"
    PROGRESS_ETA = "ETA {}"
    PROGRESS_ETA_PLACEHOLDER = "ETA --"
    PROGRESS_COMPLETED_LABEL = "{}Completa"

    ADD_DIALOG_TITLE = "Agregar Playlist"
    ADD_DIALOG_URL_LABEL = "URL de la playlist"
    ADD_DIALOG_URL_HINT = "https://youtube.com/playlist?list=..."
    ADD_DIALOG_FORMAT_LABEL = "Formato"
    ADD_DIALOG_VIDEO_OPTION = "Video (MP4)"
    ADD_DIALOG_AUDIO_OPTION = "Audio (MP3)"
    ADD_DIALOG_ERROR_EMPTY_URL = "Ingresa una URL válida"
    ADD_DIALOG_ERROR_INVALID_URL = "La URL debe comenzar con http:// o https://"
    ADD_DIALOG_CANCEL = "Cancelar"
    ADD_DIALOG_SUBMIT = "Agregar"

    SETTINGS_TITLE = "Configuracion"
    SETTINGS_OUTPUT_LABEL = "Carpeta de descargas"
    SETTINGS_OUTPUT_HINT = "Ruta de descarga (ruta completa):"
    SETTINGS_FORMAT_LABEL = "Formato por defecto"
    SETTINGS_CONCURRENT_LABEL = "Descargas simultaneas"
    SETTINGS_CONCURRENT_HINT = "Descargas simultaneas (1-10):"
    SETTINGS_CANCEL = "Cancelar"
    SETTINGS_SAVE = "Guardar"
    SETTINGS_INVALID_OUTPUT = "No se pudo crear la carpeta de descargas"

    ADD_PLAYLIST_FETCHING = "Obteniendo informacion..."
    ADD_PLAYLIST_ERROR = "Error al obtener playlist"

    TOOLTIP_SETTINGS = "Ajustes"
    TOOLTIP_ADD_PLAYLIST = "Agregar playlist"
    TOOLTIP_CANCEL = "Cancelar"
    TOOLTIP_DELETE = "Eliminar"
    TOOLTIP_RETRY = "Reintentar"
    TOOLTIP_OPEN_FILE = "Abrir archivo"
    TOOLTIP_DELETE_PLAYLIST = "Eliminar playlist"
    TOOLTIP_DELETE_MARKED = "Borrar marcados"
    TOOLTIP_START = "Iniciar descarga"
    TOOLTIP_PAUSE = "Pausar"
    TOOLTIP_RESUME = "Reanudar"
    TOOLTIP_SELECT_ALL = "Seleccionar todo"
    TOOLTIP_DESELECT_ALL = "Deseleccionar todo"
    TOOLTIP_RELOAD = "Recargar playlist"
    TOOLTIP_RETRY_SELECTED = "Reintentar seleccionados"

    SUBTITLE_PENDING = "{} pend."
    SUBTITLE_QUEUED = "{} en cola"
    SUBTITLE_PAUSED = "{} paus."
    SUBTITLE_PARTIAL = "{} parc."
    SUBTITLE_FAILED = "{} err."
    OPEN_ERROR = "Error al abrir archivo"
    FILE_NOT_FOUND = "Archivo no encontrado"


class AppTheme:
    PRIMARY = ft.Colors.PRIMARY
    ON_PRIMARY = ft.Colors.ON_PRIMARY
    SURFACE = ft.Colors.SURFACE
    SURFACE_CONTAINER_HIGHEST = ft.Colors.SURFACE_CONTAINER_HIGHEST
    ON_SURFACE_VARIANT = ft.Colors.ON_SURFACE_VARIANT
    GREY_400 = ft.Colors.GREY_400
    GREY_500 = ft.Colors.GREY_500
    GREY_600 = ft.Colors.GREY_600
    GREY_700 = ft.Colors.GREY_700
    RED = ft.Colors.RED
    GREEN = ft.Colors.GREEN
    BLUE = ft.Colors.BLUE
    ORANGE = ft.Colors.ORANGE
    OUTLINE_VARIANT = ft.Colors.OUTLINE_VARIANT
    ERROR = ft.Colors.RED
    TRANSPARENT = ft.Colors.TRANSPARENT

    STATUS_PENDING = ft.Colors.GREY
    STATUS_DOWNLOADING = ft.Colors.BLUE
    STATUS_COMPLETED = ft.Colors.GREEN
    STATUS_FAILED = ft.Colors.RED
    STATUS_CANCELLED = ft.Colors.ORANGE


STATUS_LABELS = {
    ItemStatus.PENDING: (S.STATUS_PENDING, AppTheme.STATUS_PENDING),
    ItemStatus.EXPANDING: (S.STATUS_EXPANDING, AppTheme.STATUS_PENDING),
    ItemStatus.QUEUED: (S.STATUS_QUEUED, AppTheme.STATUS_PENDING),
    ItemStatus.DOWNLOADING: (S.STATUS_DOWNLOADING, AppTheme.STATUS_DOWNLOADING),
    ItemStatus.PAUSED: (S.STATUS_PAUSED, AppTheme.STATUS_CANCELLED),
    ItemStatus.COMPLETED: (S.STATUS_COMPLETED, AppTheme.STATUS_COMPLETED),
    ItemStatus.PARTIAL: (S.STATUS_PARTIAL, AppTheme.STATUS_FAILED),
    ItemStatus.FAILED: (S.STATUS_FAILED, AppTheme.STATUS_FAILED),
    ItemStatus.CANCELLED: (S.STATUS_CANCELLED, AppTheme.STATUS_CANCELLED),
}

PROGRESS_THROTTLE_SECONDS = 0.3
VIDEO_TITLE_MAX_CHARS = 50
URL_DISPLAY_MAX_CHARS = 50
PLAYLIST_TITLE_MAX_CHARS = 40
ERROR_MESSAGE_MAX_CHARS = 250
LOG_LINES_DISPLAY_COUNT = 60
LOG_BUFFER_MAXLEN = 100
DEFAULT_MAX_CONCURRENT = 4
MAX_CONCURRENT_MIN = 1
QUEUE_POLL_INTERVAL = 0.5

DB_DIR_NAME = ".ytdwpl"
DB_FILE_NAME = "queue.db"
SETTINGS_FILE_NAME = "settings.json"
ARCHIVE_DIR_NAME = ".ytdwpl-archive"

FORMAT_LABELS = {
    "video": "MP4",
    "audio": "MP3",
}

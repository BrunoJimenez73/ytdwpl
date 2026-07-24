from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import flet as ft

from app.core.constants import (
    S,
    STATUS_LABELS,
    AppTheme,
    ERROR_MESSAGE_MAX_CHARS,
    FORMAT_LABELS,
    VIDEO_TITLE_MAX_CHARS,
)
from app.core.downloader import DownloadProgress
from app.core.models import ItemStatus, QueueItem


@dataclass
class TableConfig:
    items: List[QueueItem]
    on_cancel: Callable[[str], None]
    on_delete: Callable[[str], None]
    on_retry: Callable[[str], None]
    on_toggle_selected: Callable[[str], None]
    on_refresh: Callable[[], None]
    on_cancel_playlist: Optional[Callable[[str], None]] = None
    on_delete_playlist: Optional[Callable[[str], None]] = None
    on_delete_selected: Optional[Callable[[str], None]] = None
    on_open_file: Optional[Callable[[str], None]] = None
    on_start_playlist: Optional[Callable[[str], None]] = None
    on_pause_playlist: Optional[Callable[[str], None]] = None
    on_toggle_select_all: Optional[Callable[[str, bool], None]] = None
    on_reload_playlist: Optional[Callable[[str], None]] = None
    on_retry_selected: Optional[Callable[[str], None]] = None
    active_progress: Optional[Dict[str, DownloadProgress]] = None
    expanded_ids: Optional[Set[str]] = None

    def __post_init__(self) -> None:
        self.active_progress = self.active_progress or {}
        if self.expanded_ids is None:
            self.expanded_ids = set()


def build_queue_table(config: TableConfig) -> ft.Control:
    items = config.items
    active_progress = config.active_progress or {}

    if not items:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.INBOX, size=48, color=ft.Colors.GREY_400),
                ft.Text(S.EMPTY_LIST_TITLE,
                        color=ft.Colors.GREY_500, size=16),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(left=0, top=60, right=0, bottom=0),
            expand=True,
        )

    groups: Dict[str, List[QueueItem]] = {}
    standalone: List[QueueItem] = []
    for item in items:
        if item.playlist_id:
            groups.setdefault(item.playlist_id, []).append(item)
        else:
            standalone.append(item)

    rows: List[ft.Control] = []

    for pid, videos in groups.items():
        expanded = pid in (config.expanded_ids or set())
        header = _build_playlist_header(
            playlist_id=pid,
            videos=videos,
            expanded=expanded,
            on_toggle=lambda p=pid: (
                _toggle_expanded(config.expanded_ids, p),
                config.on_refresh(),
            ),
            on_delete_playlist=config.on_delete_playlist,
            on_delete_selected=config.on_delete_selected,
            on_start_playlist=config.on_start_playlist,
            on_pause_playlist=config.on_pause_playlist,
            on_toggle_select_all=config.on_toggle_select_all,
            on_reload_playlist=config.on_reload_playlist,
            on_retry_selected=config.on_retry_selected,
        )
        rows.append(header)
        if expanded:
            for v in videos:
                prog = active_progress.get(v.id)
                rows.append(_build_video_row(
                    v, prog, config.on_cancel, config.on_delete,
                    config.on_retry, config.on_toggle_selected, config.on_open_file,
                ))

    for item in standalone:
        prog = active_progress.get(item.id)
        rows.append(_build_video_row(
            item, prog, config.on_cancel, config.on_delete,
            config.on_retry, config.on_toggle_selected, config.on_open_file,
        ))

    return ft.ListView(controls=rows, spacing=1, expand=True, padding=2)


def _toggle_expanded(expanded_ids: Optional[Set[str]], playlist_id: str) -> None:
    if expanded_ids is None:
        return
    if playlist_id in expanded_ids:
        expanded_ids.discard(playlist_id)
    else:
        expanded_ids.add(playlist_id)


def _build_playlist_header(
    playlist_id: str,
    videos: List[QueueItem],
    expanded: bool,
    on_toggle: Callable[[], None],
    on_delete_playlist: Optional[Callable[[str], None]],
    on_delete_selected: Optional[Callable[[str], None]],
    on_start_playlist: Optional[Callable[[str], None]] = None,
    on_pause_playlist: Optional[Callable[[str], None]] = None,
    on_toggle_select_all: Optional[Callable[[str, bool], None]] = None,
    on_reload_playlist: Optional[Callable[[str], None]] = None,
    on_retry_selected: Optional[Callable[[str], None]] = None,
) -> ft.Control:
    title = videos[0].playlist_title if videos and videos[0].playlist_title else S.PLAYLIST_FALLBACK_TITLE
    total = len(videos)
    completed = sum(1 for v in videos if v.status == ItemStatus.COMPLETED)
    pending = sum(1 for v in videos if v.status == ItemStatus.PENDING)
    failed = sum(1 for v in videos if v.status == ItemStatus.FAILED)

    subtitle_parts = []
    if completed:
        subtitle_parts.append(f"{completed}{S.CHECK_MARK}")
    if pending:
        subtitle_parts.append(S.SUBTITLE_PENDING.format(pending))
    if failed:
        subtitle_parts.append(S.SUBTITLE_FAILED.format(failed))
    subtitle = subtitle_parts if subtitle_parts else [f"{total} videos"]

    icon = ft.Icons.EXPAND_MORE if expanded else ft.Icons.CHEVRON_RIGHT

    has_queued_or_downloading = any(
        v.status in (ItemStatus.QUEUED, ItemStatus.DOWNLOADING)
        for v in videos
    )
    has_selected_pending = any(
        v.status == ItemStatus.PENDING and v.selected
        for v in videos
    )

    selected_count = sum(1 for v in videos if v.selected)
    all_selected = selected_count == total

    actions = ft.Row(spacing=0)

    if on_toggle_select_all:
        actions.controls.append(ft.Checkbox(
            value=all_selected,
            on_change=lambda e, p=playlist_id, v=not all_selected: on_toggle_select_all(p, v),
            tooltip=S.TOOLTIP_DESELECT_ALL if all_selected else S.TOOLTIP_SELECT_ALL,
        ))

    if on_reload_playlist:
        actions.controls.append(ft.IconButton(
            ft.Icons.REFRESH,
            tooltip=S.TOOLTIP_RELOAD,
            icon_size=18,
            on_click=lambda e, p=playlist_id: on_reload_playlist(p),
        ))

    if on_retry_selected:
        has_failed = any(v.status in (ItemStatus.FAILED, ItemStatus.CANCELLED) and v.selected for v in videos)
        if has_failed:
            actions.controls.append(ft.IconButton(
                ft.Icons.REPLAY,
                tooltip=S.TOOLTIP_RETRY_SELECTED,
                icon_size=18,
                on_click=lambda e, p=playlist_id: on_retry_selected(p),
            ))

    if has_queued_or_downloading and on_pause_playlist:
        actions.controls.append(ft.IconButton(
            ft.Icons.PAUSE,
            tooltip=S.TOOLTIP_PAUSE,
            icon_size=18,
            on_click=lambda e, p=playlist_id: on_pause_playlist(p),
        ))
    elif has_selected_pending and on_start_playlist:
        actions.controls.append(ft.IconButton(
            ft.Icons.PLAY_ARROW,
            tooltip=S.TOOLTIP_START,
            icon_size=18,
            on_click=lambda e, p=playlist_id: on_start_playlist(p),
        ))

    if on_delete_selected:
        has_checked = any(v.selected for v in videos)
        if has_checked:
            actions.controls.append(ft.IconButton(
                ft.Icons.CHECKLIST,
                tooltip=S.TOOLTIP_DELETE_MARKED,
                icon_size=18,
                on_click=lambda e, p=playlist_id: on_delete_selected(p),
            ))
    if on_delete_playlist:
        actions.controls.append(ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            tooltip=S.TOOLTIP_DELETE_PLAYLIST,
            icon_size=18,
            on_click=lambda e, p=playlist_id: on_delete_playlist(p),
        ))

    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=20, color=AppTheme.ON_SURFACE_VARIANT),
            ft.Column([
                ft.Text(title, weight=ft.FontWeight.W_600, size=14),
                ft.Text("  ".join(subtitle), size=11, color=AppTheme.GREY_600),
            ], spacing=1, tight=True, expand=True),
            actions,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        on_click=lambda e: on_toggle(),
        padding=ft.Padding(left=8, top=6, right=4, bottom=6),
        bgcolor=AppTheme.SURFACE_CONTAINER_HIGHEST,
        border_radius=6,
    )


def _build_video_row(
    item: QueueItem,
    prog: Optional[DownloadProgress],
    on_cancel: Callable[[str], None],
    on_delete: Callable[[str], None],
    on_retry: Callable[[str], None],
    on_toggle_selected: Callable[[str], None],
    on_open_file: Optional[Callable[[str], None]],
) -> ft.Control:
    label, color = STATUS_LABELS.get(item.status, (item.status.value, AppTheme.GREY_500))
    is_finished = item.status in (ItemStatus.COMPLETED, ItemStatus.FAILED, ItemStatus.CANCELLED)
    is_downloading = item.status == ItemStatus.DOWNLOADING

    fmt_label = FORMAT_LABELS.get(item.format.value, item.format.value.upper())
    video_name = item.video_title[:VIDEO_TITLE_MAX_CHARS] if item.video_title else item.url[:VIDEO_TITLE_MAX_CHARS]

    chk = ft.Checkbox(
        value=item.selected,
        on_change=lambda e, i=item.id: on_toggle_selected(i),
    )

    if is_downloading and prog:
        pct = prog.percent
        status_content = ft.Column([
            ft.ProgressBar(
                value=pct / 100.0,
                color=AppTheme.BLUE,
                bgcolor=AppTheme.SURFACE_CONTAINER_HIGHEST,
                height=4,
                border_radius=2,
            ),
            ft.Row([
                ft.Text(f"{pct:.1f}%", size=11, color=AppTheme.BLUE),
                ft.Text(prog.speed or "", size=10, color=AppTheme.GREY_500),
                ft.Text(f"ETA {prog.eta}" if prog.eta else "", size=10, color=AppTheme.GREY_500),
            ], spacing=4),
        ], spacing=1, tight=True)
    else:
        status_content = ft.Container(
            ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_500),
            padding=ft.Padding(left=4, top=1, right=4, bottom=1),
            border_radius=3,
        )

    progress_text = ""
    if item.status == ItemStatus.COMPLETED and item.file_path:
        fname = Path(item.file_path).name
        progress_text = f"{S.CHECK_MARK} {fname}"
    elif item.status == ItemStatus.FAILED and item.error:
        progress_text = item.error[:ERROR_MESSAGE_MAX_CHARS]
    elif item.total_videos > 0:
        progress_text = f"{item.completed_videos}/{item.total_videos}"
        if item.status == ItemStatus.COMPLETED:
            progress_text = f"{S.CHECK_MARK} {progress_text}"
    elif item.status == ItemStatus.COMPLETED:
        progress_text = f"{S.CHECK_MARK} {S.PROGRESS_COMPLETED_LABEL.format('')}"

    is_completed_file = item.status == ItemStatus.COMPLETED and bool(item.file_path)
    if is_completed_file and on_open_file:
        title_control = ft.TextButton(
            content=ft.Text(video_name, size=12, overflow=ft.TextOverflow.ELLIPSIS,
                            color=ft.Colors.PRIMARY),
            on_click=lambda e, p=item.file_path: on_open_file(p),
            style=ft.ButtonStyle(padding=0, bgcolor=AppTheme.TRANSPARENT),
            tooltip=S.TOOLTIP_OPEN_FILE,
        )
    else:
        title_control = ft.Text(video_name, size=12, overflow=ft.TextOverflow.ELLIPSIS)

    actions: List[ft.Control] = []
    if item.status == ItemStatus.PENDING:
        actions.append(_action_btn(ft.Icons.CANCEL_OUTLINED, S.TOOLTIP_CANCEL,
                                   lambda e, i=item.id: on_cancel(i)))
    if is_finished:
        actions.append(_action_btn(ft.Icons.DELETE_OUTLINE, S.TOOLTIP_DELETE,
                                   lambda e, i=item.id: on_delete(i)))
    if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
        actions.append(_action_btn(ft.Icons.REPLAY, S.TOOLTIP_RETRY,
                                   lambda e, i=item.id: on_retry(i)))

    return ft.Container(
        content=ft.Row([
            chk,
            ft.Column([
                title_control,
                ft.Row([
                    ft.Text(fmt_label, size=10, color=AppTheme.GREY_500),
                    ft.Container(
                        ft.Text(progress_text, size=10, color=AppTheme.GREY_600),
                        visible=bool(progress_text) and not is_downloading,
                    ),
                ], spacing=6),
            ], spacing=1, tight=True, expand=True),
            status_content,
            ft.Row(actions, spacing=1),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(left=24, top=3, right=4, bottom=3),
        bgcolor=AppTheme.SURFACE,
        border_radius=4,
    )


def _action_btn(icon: ft.Icons, tip: str, on_click) -> ft.Control:
    return ft.IconButton(icon, tooltip=tip, icon_size=16, on_click=on_click)

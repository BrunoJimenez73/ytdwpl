from __future__ import annotations

import atexit
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, List

from app.core.models import DownloadFormat, ItemStatus, QueueItem

DB_PATH = Path.home() / ".ytdwpl" / "queue.db"
SCHEMA_VERSION = 2


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _get_connection()
    return _local.conn


def _close_thread_connection() -> None:
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


def close_all_connections() -> None:
    _close_thread_connection()


def init_db() -> None:
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue_items (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            format TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            playlist_title TEXT DEFAULT '',
            video_title TEXT DEFAULT '',
            playlist_id TEXT DEFAULT '',
            selected INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT DEFAULT '',
            file_path TEXT DEFAULT '',
            archive_path TEXT DEFAULT '',
            total_videos INTEGER DEFAULT 0,
            completed_videos INTEGER DEFAULT 0
        )
    """)
    _migrate(conn)
    _create_indexes(conn)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(queue_items)").fetchall()}
    for col in ("video_title", "playlist_id", "file_path", "selected", "playlist_url"):
        if col not in existing:
            default = "1" if col == "selected" else "''"
            colltype = "INTEGER" if col == "selected" else "TEXT"
            conn.execute(f"ALTER TABLE queue_items ADD COLUMN {col} {colltype} DEFAULT {default}")


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_queue_items_status_created "
        "ON queue_items(status, created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_queue_items_playlist "
        "ON queue_items(playlist_id, created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_queue_items_selected_status "
        "ON queue_items(selected, status, created_at)"
    )


def reset_stale_downloads() -> None:
    conn = _conn()
    conn.execute(
        "UPDATE queue_items SET status = ? WHERE status IN (?, ?)",
        (ItemStatus.PENDING.value, ItemStatus.DOWNLOADING.value, ItemStatus.QUEUED.value),
    )
    conn.execute(
        "UPDATE queue_items SET status = ?, error = ? WHERE status = ?",
        (
            ItemStatus.FAILED.value,
            "La expansión de la playlist se interrumpió al cerrar la aplicación.",
            ItemStatus.EXPANDING.value,
        ),
    )
    conn.commit()


def add_item(item: QueueItem) -> None:
    add_items([item])


def add_items(items: Iterable[QueueItem]) -> None:
    """Insert queue items in one transaction."""
    items = list(items)
    if not items:
        return
    conn = _conn()
    conn.executemany(
        """INSERT INTO queue_items
           (id, url, format, status, playlist_title, video_title, playlist_id,
            selected, created_at, file_path, archive_path, total_videos, playlist_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                item.id, item.url, item.format.value, item.status.value,
                item.playlist_title, item.video_title, item.playlist_id,
                int(item.selected), item.created_at, item.file_path, item.archive_path,
                item.total_videos, item.playlist_url,
            )
            for item in items
        ],
    )
    conn.commit()


def replace_item_with_items(placeholder_id: str, items: Iterable[QueueItem]) -> None:
    """Replace an expansion placeholder and its children atomically."""
    items = list(items)
    conn = _conn()
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM queue_items WHERE id = ?", (placeholder_id,))
        conn.executemany(
            """INSERT INTO queue_items
               (id, url, format, status, playlist_title, video_title, playlist_id,
                selected, created_at, file_path, archive_path, total_videos, playlist_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    item.id, item.url, item.format.value, item.status.value,
                    item.playlist_title, item.video_title, item.playlist_id,
                    int(item.selected), item.created_at, item.file_path, item.archive_path,
                    item.total_videos, item.playlist_url,
                )
                for item in items
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_all_items() -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def get_items_by_status(status: ItemStatus) -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items WHERE status = ? ORDER BY created_at ASC",
        (status.value,),
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def get_pending_items() -> List[QueueItem]:
    return get_items_by_status(ItemStatus.PENDING)


def get_downloading_items() -> List[QueueItem]:
    return get_items_by_status(ItemStatus.DOWNLOADING)


def get_playlist_items(playlist_id: str) -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items WHERE playlist_id = ? ORDER BY created_at ASC",
        (playlist_id,),
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def _validate_columns(extra: dict) -> None:
    allowed = {
        "playlist_title", "video_title", "playlist_id", "selected",
        "completed_at", "error", "file_path", "archive_path",
        "total_videos", "completed_videos", "playlist_url"
    }
    for k in extra:
        if k not in allowed:
            raise ValueError(f"Invalid column name: {k}")


def update_status(item_id: str, status: ItemStatus, **extra) -> None:
    _validate_columns(extra)
    conn = _conn()
    fields = ["status = ?"]
    values = [status.value]
    for k, v in extra.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(item_id)
    conn.execute(
        f"UPDATE queue_items SET {', '.join(fields)} WHERE id = ?", values
    )
    conn.commit()


def claim_item(item_id: str) -> QueueItem | None:
    """Atomically claim a selected queued item for downloading."""
    conn = _conn()
    cursor = conn.execute(
        """UPDATE queue_items SET status = ?
           WHERE id = ? AND status = ? AND selected = 1""",
        (ItemStatus.DOWNLOADING.value, item_id, ItemStatus.QUEUED.value),
    )
    conn.commit()
    if cursor.rowcount != 1:
        return None
    return get_item(item_id)


def update_playlist_status(playlist_id: str, status: ItemStatus, **extra) -> None:
    _validate_columns(extra)
    conn = _conn()
    fields = ["status = ?"]
    values = [status.value]
    for k, v in extra.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(playlist_id)
    conn.execute(
        f"UPDATE queue_items SET {', '.join(fields)} WHERE playlist_id = ?", values
    )
    conn.commit()


def update_playlist_status_selected(playlist_id: str, from_status: ItemStatus, to_status: ItemStatus) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE queue_items SET status = ? WHERE playlist_id = ? AND selected = 1 AND status = ?",
        (to_status.value, playlist_id, from_status.value),
    )
    conn.commit()


def update_playlist_status_selected_multi(playlist_id: str, from_statuses: list, to_status: ItemStatus) -> None:
    conn = _conn()
    placeholders = ",".join("?" for _ in from_statuses)
    conn.execute(
        f"UPDATE queue_items SET status = ?, selected = 1 WHERE playlist_id = ? AND selected = 1 AND status IN ({placeholders})",
        (to_status.value, playlist_id, *[s.value for s in from_statuses]),
    )
    conn.commit()


def get_item(item_id: str) -> QueueItem | None:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM queue_items WHERE id = ?", (item_id,)
    ).fetchone()
    return _row_to_item(row) if row else None


def delete_item(item_id: str) -> None:
    conn = _conn()
    conn.execute("DELETE FROM queue_items WHERE id = ?", (item_id,))
    conn.commit()


def delete_playlist(playlist_id: str) -> None:
    conn = _conn()
    conn.execute("DELETE FROM queue_items WHERE playlist_id = ?", (playlist_id,))
    conn.commit()


def delete_playlist_selected(playlist_id: str) -> None:
    conn = _conn()
    conn.execute(
        "DELETE FROM queue_items WHERE playlist_id = ? AND selected = 1",
        (playlist_id,),
    )
    conn.commit()


def update_playlist_progress(playlist_id: str, completed_videos: int) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE queue_items SET completed_videos = ? WHERE playlist_id = ?",
        (completed_videos, playlist_id),
    )
    conn.commit()


def update_playlist_select_all(playlist_id: str, selected: bool) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE queue_items SET selected = ? WHERE playlist_id = ?",
        (int(selected), playlist_id),
    )
    conn.commit()


def get_playlist_url(playlist_id: str) -> str:
    conn = _conn()
    row = conn.execute(
        "SELECT playlist_url FROM queue_items WHERE playlist_id = ? AND playlist_url != '' LIMIT 1",
        (playlist_id,),
    ).fetchone()
    return row["playlist_url"] if row else ""


def update_playlist_item_videos(playlist_id: str, videos: list) -> None:
    conn = _conn()
    existing = conn.execute(
        "SELECT id, url FROM queue_items WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchall()
    url_map = {row["url"]: row["id"] for row in existing}
    for v in videos:
        vid_url = v.get("url") or v.get("webpage_url") or ""
        matched_id = url_map.get(vid_url)
        if matched_id:
            new_title = v.get("title", "")
            conn.execute(
                "UPDATE queue_items SET video_title = ? WHERE id = ?",
                (new_title, matched_id),
            )
    conn.commit()


def sync_playlist_items(playlist_id: str, playlist_title: str, videos: list[dict]) -> None:
    """Synchronize discovered playlist entries while preserving item state."""
    conn = _conn()
    existing = conn.execute(
        "SELECT * FROM queue_items WHERE playlist_id = ? ORDER BY created_at ASC",
        (playlist_id,),
    ).fetchall()
    if not existing:
        return

    first = existing[0]
    fmt = DownloadFormat(first["format"])
    playlist_url = first["playlist_url"] or ""
    total = len(videos)
    known_urls = {row["url"] for row in existing}
    new_items: list[QueueItem] = []

    try:
        conn.execute("BEGIN")
        conn.execute(
            "UPDATE queue_items SET playlist_title = ?, total_videos = ? WHERE playlist_id = ?",
            (playlist_title, total, playlist_id),
        )
        for video in videos:
            video_url = video.get("url") or video.get("webpage_url") or ""
            if not video_url:
                continue
            title = video.get("title") or ""
            if video_url in known_urls:
                conn.execute(
                    "UPDATE queue_items SET video_title = ? WHERE playlist_id = ? AND url = ?",
                    (title, playlist_id, video_url),
                )
                continue
            new_items.append(
                QueueItem.new(
                    url=video_url,
                    fmt=fmt,
                    video_title=title,
                    playlist_title=playlist_title,
                    playlist_id=playlist_id,
                    total_videos=total,
                    playlist_url=playlist_url,
                )
            )
        if new_items:
            conn.executemany(
                """INSERT INTO queue_items
                   (id, url, format, status, playlist_title, video_title, playlist_id,
                    selected, created_at, file_path, archive_path, total_videos, playlist_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        item.id, item.url, item.format.value, item.status.value,
                        item.playlist_title, item.video_title, item.playlist_id,
                        int(item.selected), item.created_at, item.file_path, item.archive_path,
                        item.total_videos, item.playlist_url,
                    )
                    for item in new_items
                ],
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def count_playlist_completed(playlist_id: str) -> int:
    conn = _conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM queue_items WHERE playlist_id = ? AND status = ?",
        (playlist_id, ItemStatus.COMPLETED.value),
    ).fetchone()
    return row["cnt"] if row else 0


def _row_to_item(row: sqlite3.Row) -> QueueItem:
    return QueueItem(
        id=row["id"],
        url=row["url"],
        format=DownloadFormat(row["format"]),
        status=ItemStatus(row["status"]),
        playlist_title=row["playlist_title"] or "",
        video_title=row["video_title"] or "",
        playlist_id=row["playlist_id"] or "",
        created_at=row["created_at"],
        completed_at=row["completed_at"] or "",
        error=row["error"] or "",
        file_path=row["file_path"] or "",
        archive_path=row["archive_path"] or "",
        selected=bool(row["selected"]) if "selected" in row.keys() else True,
        total_videos=row["total_videos"] or 0,
        completed_videos=row["completed_videos"] or 0,
        playlist_url=row["playlist_url"] or "",
    )


atexit.register(close_all_connections)

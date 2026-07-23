from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List

from app.core.models import DownloadFormat, ItemStatus, QueueItem

DB_PATH = Path.home() / ".ytdwpl" / "queue.db"


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
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT DEFAULT '',
            archive_path TEXT DEFAULT '',
            total_videos INTEGER DEFAULT 0,
            completed_videos INTEGER DEFAULT 0
        )
    """)
    _migrate(conn)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(queue_items)").fetchall()}
    if "video_title" not in existing:
        conn.execute("ALTER TABLE queue_items ADD COLUMN video_title TEXT DEFAULT ''")
    if "playlist_id" not in existing:
        conn.execute("ALTER TABLE queue_items ADD COLUMN playlist_id TEXT DEFAULT ''")


def reset_stale_downloads() -> None:
    conn = _conn()
    conn.execute(
        "UPDATE queue_items SET status = ? WHERE status = ?",
        (ItemStatus.PENDING.value, ItemStatus.DOWNLOADING.value),
    )
    conn.commit()


def add_item(item: QueueItem) -> None:
    conn = _conn()
    conn.execute(
        """INSERT INTO queue_items
           (id, url, format, status, playlist_title, video_title, playlist_id,
            created_at, archive_path, total_videos)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item.id, item.url, item.format.value, item.status.value,
         item.playlist_title, item.video_title, item.playlist_id,
         item.created_at, item.archive_path, item.total_videos),
    )
    conn.commit()


def get_all_items() -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def get_pending_items() -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items WHERE status = ? ORDER BY created_at ASC",
        (ItemStatus.PENDING.value,),
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def get_downloading_items() -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items WHERE status = ? ORDER BY created_at ASC",
        (ItemStatus.DOWNLOADING.value,),
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def get_playlist_items(playlist_id: str) -> List[QueueItem]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM queue_items WHERE playlist_id = ? ORDER BY created_at ASC",
        (playlist_id,),
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def update_status(item_id: str, status: ItemStatus, **extra) -> None:
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


def update_playlist_status(playlist_id: str, status: ItemStatus, **extra) -> None:
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
        archive_path=row["archive_path"] or "",
        total_videos=row["total_videos"] or 0,
        completed_videos=row["completed_videos"] or 0,
    )

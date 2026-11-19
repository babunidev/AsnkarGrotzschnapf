"""Persistent Reel eligibility and job ledger."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from anskar.reels.errors import ReelError

BATCH_SIZE = 7
JOB_STATES = ("pending", "rendering", "publishing", "published", "failed")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reel_artworks (
    artwork_id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    reel_job_id TEXT
);

CREATE TABLE IF NOT EXISTS reel_jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'rendering', 'publishing', 'published', 'failed'
    )),
    artwork_ids TEXT NOT NULL,
    video_path TEXT,
    video_sha256 TEXT,
    caption TEXT,
    caption_sha256 TEXT,
    staging_key TEXT,
    container_id TEXT,
    media_id TEXT,
    permalink TEXT,
    error_kind TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS reel_artworks_waiting
    ON reel_artworks (completed_at)
    WHERE reel_job_id IS NULL;
"""


def reels_database_path() -> Path:
    override = os.environ.get("ANSKAR_REELS_DB")
    if override:
        return Path(override).expanduser()
    from anskar.config import PROJECT_ROOT

    return PROJECT_ROOT / "data" / "reels.sqlite"


def reels_output_dir() -> Path:
    override = os.environ.get("ANSKAR_REELS_DIR")
    if override:
        return Path(override).expanduser()
    from anskar.config import PROJECT_ROOT

    return PROJECT_ROOT / "data" / "reels"


def music_dir() -> Path:
    override = os.environ.get("ANSKAR_REELS_MUSIC")
    if override:
        return Path(override).expanduser()
    from anskar.config import PROJECT_ROOT

    return PROJECT_ROOT / "data" / "reels-music"


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    file = path or reels_database_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(file)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_eligible(
    connection: sqlite3.Connection,
    *,
    artwork_id: str,
    pack_id: str,
    completed_at: str | None = None,
) -> bool:
    """Insert eligibility. Returns True when newly recorded."""
    if not artwork_id or not pack_id:
        raise ReelError("Reel eligibility needs artwork_id and pack_id.", kind="error")
    existing = connection.execute(
        "SELECT artwork_id FROM reel_artworks WHERE artwork_id = ? OR pack_id = ?",
        (artwork_id, pack_id),
    ).fetchone()
    if existing is not None:
        return False
    connection.execute(
        """
        INSERT INTO reel_artworks (artwork_id, pack_id, completed_at, reel_job_id)
        VALUES (?, ?, ?, NULL)
        """,
        (artwork_id, pack_id, completed_at or _now()),
    )
    return True


def waiting_count(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS n FROM reel_artworks WHERE reel_job_id IS NULL"
    ).fetchone()
    return int(row["n"] if row else 0)


def claim_next_batch(connection: sqlite3.Connection, *, size: int = BATCH_SIZE) -> str | None:
    """Claim the oldest unbatched artworks into a new pending job. Returns job id or None."""
    if size != BATCH_SIZE:
        raise ReelError("A Reel must contain exactly seven artworks.", kind="error")
    if not connection.in_transaction:
        connection.execute("BEGIN IMMEDIATE")
    rows = list(
        connection.execute(
            """
            SELECT artwork_id, pack_id, completed_at
            FROM reel_artworks
            WHERE reel_job_id IS NULL
              AND pack_id NOT IN (
                  SELECT pack_id FROM reel_artworks WHERE reel_job_id IS NOT NULL
              )
            GROUP BY pack_id
            ORDER BY completed_at ASC, artwork_id ASC
            LIMIT ?
            """,
            (size,),
        )
    )
    if len(rows) < size:
        return None
    job_id = f"reel-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    artwork_ids = [str(row["artwork_id"]) for row in rows]
    now = _now()
    connection.execute(
        """
        INSERT INTO reel_jobs (
            id, status, artwork_ids, created_at, updated_at
        ) VALUES (?, 'pending', ?, ?, ?)
        """,
        (job_id, json.dumps(artwork_ids), now, now),
    )
    for artwork_id in artwork_ids:
        connection.execute(
            "UPDATE reel_artworks SET reel_job_id = ? WHERE artwork_id = ?",
            (job_id, artwork_id),
        )
    return job_id


def get_job(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM reel_jobs WHERE id = ?", (job_id,)).fetchone()


def list_jobs(connection: sqlite3.Connection, *, limit: int = 20) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            "SELECT * FROM reel_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    )


def update_job(connection: sqlite3.Connection, job_id: str, **fields: object) -> None:
    allowed = {
        "status",
        "video_path",
        "video_sha256",
        "caption",
        "caption_sha256",
        "staging_key",
        "container_id",
        "media_id",
        "permalink",
        "error_kind",
        "error_message",
        "artwork_ids",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ReelError(f"Unknown reel job field: {sorted(unknown)[0]}", kind="error")
    if "status" in fields and fields["status"] not in JOB_STATES:
        raise ReelError("The reel job status is not valid.", kind="error")
    if not fields:
        return
    assignments = ", ".join(f"{name} = ?" for name in fields)
    connection.execute(
        f"UPDATE reel_jobs SET {assignments}, updated_at = ? WHERE id = ?",
        (*fields.values(), _now(), job_id),
    )


def public_job(row: sqlite3.Row) -> dict[str, object]:
    artwork_ids = []
    raw = row["artwork_ids"]
    if isinstance(raw, str) and raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, list):
                artwork_ids = [str(item) for item in loaded]
        except json.JSONDecodeError:
            artwork_ids = []
    return {
        "id": row["id"],
        "status": row["status"],
        "artwork_ids": artwork_ids,
        "video_path": row["video_path"],
        "caption": row["caption"],
        "container_id": row["container_id"],
        "media_id": row["media_id"],
        "permalink": row["permalink"],
        "error_kind": row["error_kind"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def jobs_needing_work(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT * FROM reel_jobs
            WHERE status IN ('pending', 'rendering', 'publishing', 'failed')
            ORDER BY created_at ASC
            """
        )
    )


def pack_ids_for_job(connection: sqlite3.Connection, job_id: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT pack_id FROM reel_artworks
        WHERE reel_job_id = ?
        ORDER BY completed_at ASC
        """,
        (job_id,),
    ).fetchall()
    return [str(row["pack_id"]) for row in rows]

"""Orchestrate Reel eligibility, render, and Instagram VIDEO publish."""

from __future__ import annotations

import json
import fcntl
import time
from collections.abc import Callable
from pathlib import Path

from anskar.daily.notify import notify_stage
from anskar.instagram.credentials import load_credentials
from anskar.instagram.errors import InstagramError
from anskar.instagram.graph import GraphClient
from anskar.instagram.r2 import VIDEO_PRESIGN_SECONDS, R2StagingAdapter, stage_video
from anskar.printmaker import packs_dir
from anskar.reels.caption import build_reel_caption, caption_matches
from anskar.reels.errors import ReelError
from anskar.reels.ledger import (
    BATCH_SIZE,
    claim_next_batch,
    connect,
    get_job,
    jobs_needing_work,
    list_jobs,
    pack_ids_for_job,
    public_job,
    record_eligible,
    reels_database_path,
    reels_output_dir,
    update_job,
    waiting_count,
)
from anskar.reels.render import render_reel

VIDEO_POLL_INTERVAL = 60.0
VIDEO_POLL_MAX_SECONDS = 300.0


def record_reel_eligible(
    *,
    artwork_id: str,
    pack_id: str,
    database: Path | None = None,
    completed_at: str | None = None,
) -> bool:
    with connect(database) as connection:
        return record_eligible(
            connection,
            artwork_id=artwork_id,
            pack_id=pack_id,
            completed_at=completed_at,
        )


def _is_production_pack(pack_id: str) -> bool:
    """Lab/experiment packs never count toward Reels; production packs do."""
    return str(pack_id).startswith("production-")


def recover_missed_eligibility(
    *,
    database: Path | None = None,
    daily_db: Path | None = None,
    packs: Path | None = None,
) -> int:
    """Recover only ledger-proven daily publications; never infer from manifests.

    Rehearsals and orphaned historical packs cannot establish daily eligibility.
    """
    from anskar.daily.ledger import connect as daily_connect
    from anskar.daily.ledger import database_path as daily_database_path
    from anskar.daily.ledger import list_runs

    inserted = 0
    root = packs or packs_dir()
    with daily_connect(daily_db or daily_database_path()) as daily:
        rows = list_runs(daily, limit=500)
    with connect(database) as connection:
        for row in rows:
            keys = row.keys()
            if bool(row["dry_run"]) or row["run_kind"] != "daily":
                continue
            if row["status"] not in {"completed", "instagram_published"}:
                continue
            if not row["instagram_media_id"] and row["instagram_status"] != "published":
                continue
            pack_id = row["pack_id"]
            if not pack_id or not _is_production_pack(str(pack_id)):
                continue
            artwork_id, completed_at = _artwork_meta_from_pack(
                root, str(pack_id), row=row, keys=keys
            )
            if record_eligible(
                connection,
                artwork_id=artwork_id,
                pack_id=str(pack_id),
                completed_at=completed_at,
            ):
                inserted += 1

    return inserted


def _artwork_meta_from_pack(
    root: Path,
    pack_id: str,
    *,
    row=None,
    keys=(),
) -> tuple[str, str | None]:
    artwork_id = pack_id
    completed_at = None
    if row is not None:
        if "completed_at" in keys and row["completed_at"]:
            completed_at = str(row["completed_at"])
        elif "updated_at" in keys and row["updated_at"]:
            completed_at = str(row["updated_at"])
    manifest_path = root / pack_id / "manifest.json"
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("artwork_id"):
                artwork_id = str(payload["artwork_id"])
        except (OSError, json.JSONDecodeError):
            pass
    return artwork_id, completed_at


def maybe_run_reel_pipeline(
    *,
    database: Path | None = None,
    packs: Path | None = None,
    dry_run: bool = False,
    publish: bool = True,
) -> dict[str, object]:
    """Claim a batch of seven when ready and process pending jobs."""
    report: dict[str, object] = {
        "waiting": 0,
        "claimed": None,
        "processed": [],
        "errors": [],
    }
    root = packs or packs_dir()
    with connect(database) as connection:
        report["waiting"] = waiting_count(connection)
        if report["waiting"] >= BATCH_SIZE:
            job_id = claim_next_batch(connection, size=BATCH_SIZE)
            report["claimed"] = job_id
        work = [public_job(row) for row in jobs_needing_work(connection)]

    for job in work:
        job_id = str(job["id"])
        try:
            result = process_reel_job(
                job_id,
                database=database,
                packs=root,
                dry_run=dry_run,
                publish=publish,
            )
            report["processed"].append(result)  # type: ignore[union-attr]
        except (ReelError, InstagramError) as exc:
            report["errors"].append(f"{job_id}: {exc}")  # type: ignore[union-attr]
            if getattr(exc, "kind", None) == "busy":
                continue
            with connect(database) as connection:
                update_job(
                    connection,
                    job_id,
                    status="failed",
                    error_kind=getattr(exc, "kind", "error"),
                    error_message=str(exc),
                )
            notify_stage("failed", f"Reel {job_id}: {exc}")
    return report


def process_reel_job(job_id: str, **kwargs) -> dict[str, object]:
    """Serialize publish/reconcile across daily, maintenance and manual callers."""
    database = kwargs.get("database") or reels_database_path()
    lock_path = Path(str(database) + ".publish.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReelError("Another Reel publisher is active.", kind="busy") from exc
        try:
            return _process_reel_job(job_id, **kwargs)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _process_reel_job(
    job_id: str,
    *,
    database: Path | None = None,
    packs: Path | None = None,
    dry_run: bool = False,
    publish: bool = True,
    graph: GraphClient | None = None,
    adapter: R2StagingAdapter | None = None,
    sleep: Callable[[float], object] = time.sleep,
) -> dict[str, object]:
    root = packs or packs_dir()
    with connect(database) as connection:
        row = get_job(connection, job_id)
        if row is None:
            raise ReelError(f"Reel job not found: {job_id}", kind="error")
        job = public_job(row)
        pack_ids = pack_ids_for_job(connection, job_id)

    if job.get("media_id") or job.get("status") == "published":
        return {"id": job_id, "status": "published", "media_id": job.get("media_id"), "skipped": "already_published"}

    if len(pack_ids) != BATCH_SIZE or len(set(pack_ids)) != BATCH_SIZE:
        raise ReelError("A Reel requires seven distinct, exclusively claimed packs.", kind="media")

    # Alternate ledgers must not borrow real credentials/staging. Tests inject both.
    from anskar.config import PROJECT_ROOT
    actual_db = (database or reels_database_path()).resolve()
    if publish and not dry_run and actual_db != (PROJECT_ROOT / "data/reels.sqlite").resolve():
        if graph is None or adapter is None:
            raise ReelError("Non-production Reel ledger requires explicit publishing adapters.", kind="credentials")

    folders = [_pack_folder(root, pack_id) for pack_id in pack_ids]
    out_dir = reels_output_dir() / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = Path(str(job["video_path"])) if job.get("video_path") else out_dir / "reel.mp4"

    if not video_path.is_file():
        with connect(database) as connection:
            update_job(connection, job_id, status="rendering", error_kind=None, error_message=None)
        rendered = render_reel(folders, output=video_path, job_id=job_id)
        with connect(database) as connection:
            update_job(
                connection,
                job_id,
                status="pending",
                video_path=str(video_path),
                video_sha256=str(rendered["sha256"]),
            )
        (out_dir / "manifest.json").write_text(
            json.dumps({"job_id": job_id, "pack_ids": pack_ids, **rendered}, indent=2) + "\n",
            encoding="utf-8",
        )

    caption = job.get("caption")
    caption_sha = job.get("caption_sha256")
    if not caption:
        caption, caption_sha = build_reel_caption(folders, job_id=job_id)
        with connect(database) as connection:
            update_job(connection, job_id, caption=caption, caption_sha256=caption_sha)

    if dry_run or not publish:
        with connect(database) as connection:
            update_job(connection, job_id, status="pending")
        return {
            "id": job_id,
            "status": "dry_run" if dry_run else "rendered",
            "video_path": str(video_path),
            "caption": caption,
            "pack_ids": pack_ids,
        }

    return _publish_job(
        job_id,
        video_path=video_path,
        caption=str(caption),
        database=database,
        graph=graph,
        adapter=adapter,
        sleep=sleep,
    )


def _publish_job(
    job_id: str,
    *,
    video_path: Path,
    caption: str,
    database: Path | None,
    graph: GraphClient | None,
    adapter: R2StagingAdapter | None,
    sleep,
) -> dict[str, object]:
    with connect(database) as connection:
        row = get_job(connection, job_id)
        assert row is not None
        job = public_job(row)

    from anskar.instagram.api_gate import InstagramApiGate

    gate = InstagramApiGate()
    try:
        gate.assert_clear()
    except InstagramError as exc:
        raise ReelError(str(exc), kind=exc.kind) from exc

    client = graph or GraphClient(load_credentials().access_token)
    creds = load_credentials()
    user_id = creds.user_id
    if not user_id:
        profile = client.profile()
        user_id = str(profile.get("user_id") or profile.get("id") or "")
    if not user_id:
        raise ReelError("Instagram user id is missing.", kind="credentials")

    # Safeguard 2: reconcile before creating another container.
    bound = _reconcile_existing(client, user_id=user_id, job=job, caption=caption, database=database, job_id=job_id)
    if bound is not None:
        return bound

    with connect(database) as connection:
        update_job(connection, job_id, status="publishing", error_kind=None, error_message=None)

    staging = adapter or R2StagingAdapter(expires_in=VIDEO_PRESIGN_SECONDS)
    staged = stage_video(video_path, job_id=job_id, adapter=staging, expires_in=VIDEO_PRESIGN_SECONDS)
    with connect(database) as connection:
        update_job(connection, job_id, staging_key=staged.key)

    try:
        container_id = client.create_video(user_id, video_url=staged.url, caption=caption)
    except InstagramError as exc:
        gate.note_error(exc)
        with connect(database) as connection:
            update_job(
                connection,
                job_id,
                status="failed",
                error_kind=getattr(exc, "kind", "api") or "api",
                error_message=str(exc),
            )
        raise

    with connect(database) as connection:
        update_job(connection, job_id, container_id=container_id)

    _wait_video_ready(client, container_id, sleep=sleep)
    media_id = client.publish(user_id, container_id)
    permalink = None
    try:
        media = client.media(media_id)
        if isinstance(media.get("permalink"), str):
            permalink = media["permalink"]
    except InstagramError:
        permalink = None

    with connect(database) as connection:
        update_job(
            connection,
            job_id,
            status="published",
            media_id=media_id,
            permalink=permalink,
            error_kind=None,
            error_message=None,
        )
    # Delete staging only after successful publish.
    try:
        staging.delete(staged.key)
    except Exception:  # noqa: BLE001
        pass
    notify_stage("instagram", f"Reel published {job_id}")
    return {
        "id": job_id,
        "status": "published",
        "media_id": media_id,
        "permalink": permalink,
        "container_id": container_id,
    }


def _reconcile_existing(
    client: GraphClient,
    *,
    user_id: str,
    job: dict[str, object],
    caption: str,
    database: Path | None,
    job_id: str,
) -> dict[str, object] | None:
    if job.get("media_id"):
        return {"id": job_id, "status": "published", "media_id": job["media_id"], "reconciled": True}

    container_id = job.get("container_id")
    if isinstance(container_id, str) and container_id:
        try:
            status = client.container_status(container_id)
        except InstagramError as exc:
            if exc.kind in {"rate_limit", "access_blocked"}:
                raise
            status = {}
        code = str(status.get("status_code") or "").upper()
        if code in {"PUBLISHED"}:
            # Best-effort: treat as published without a media id until fetch.
            with connect(database) as connection:
                update_job(connection, job_id, status="published")
            return {"id": job_id, "status": "published", "reconciled": "container_published"}
        if code == "FINISHED":
            media_id = client.publish(user_id, container_id)
            permalink = None
            try:
                media = client.media(media_id)
                if isinstance(media.get("permalink"), str):
                    permalink = media["permalink"]
            except InstagramError:
                pass
            with connect(database) as connection:
                update_job(
                    connection,
                    job_id,
                    status="published",
                    media_id=media_id,
                    permalink=permalink,
                )
            return {"id": job_id, "status": "published", "media_id": media_id, "reconciled": "finished"}
        if code in {"ERROR", "EXPIRED"}:
            with connect(database) as connection:
                update_job(connection, job_id, container_id=None)
            return None
        # Ambiguous: do not create another container.
        with connect(database) as connection:
            update_job(
                connection,
                job_id,
                status="failed",
                error_kind="ambiguous",
                error_message=f"Container {container_id} status={code or 'unknown'}; not recreating.",
            )
        raise ReelError(
            f"Reel container {container_id} is ambiguous ({code or 'unknown'}); "
            "maintain will retry without creating a duplicate.",
            kind="busy",
        )

    # Caption match against recent media.
    try:
        recent = client.recent_media(user_id)
    except InstagramError:
        recent = []
    for item in recent:
        if caption_matches(item.get("caption"), caption):
            media_id = str(item.get("id") or "")
            if not media_id:
                continue
            permalink = item.get("permalink") if isinstance(item.get("permalink"), str) else None
            with connect(database) as connection:
                update_job(
                    connection,
                    job_id,
                    status="published",
                    media_id=media_id,
                    permalink=permalink,
                )
            return {
                "id": job_id,
                "status": "published",
                "media_id": media_id,
                "permalink": permalink,
                "reconciled": "caption",
            }
    return None


def _wait_video_ready(client: GraphClient, container_id: str, *, sleep) -> None:
    deadline = time.monotonic() + VIDEO_POLL_MAX_SECONDS
    while time.monotonic() < deadline:
        status = client.container_status(container_id)
        code = str(status.get("status_code") or "").upper()
        if code in {"FINISHED", "PUBLISHED"}:
            return
        if code in {"ERROR", "EXPIRED"}:
            raise ReelError(f"Video container failed: {code}", kind="api")
        sleep(VIDEO_POLL_INTERVAL)
    raise ReelError("Timed out waiting for Instagram video container.", kind="timeout")


def maintain_reels(
    *,
    database: Path | None = None,
    packs: Path | None = None,
    daily_db: Path | None = None,
    publish: bool = True,
) -> dict[str, object]:
    recovered = recover_missed_eligibility(database=database, daily_db=daily_db, packs=packs)
    pipeline = maybe_run_reel_pipeline(database=database, packs=packs, publish=publish)
    with connect(database) as connection:
        waiting = waiting_count(connection)
        jobs = [public_job(row) for row in list_jobs(connection, limit=10)]
    return {
        "recovered_eligibility": recovered,
        "waiting": waiting,
        "claimed": pipeline.get("claimed"),
        "processed": pipeline.get("processed"),
        "errors": pipeline.get("errors"),
        "recent_jobs": jobs,
        "database": str(database or reels_database_path()),
    }


def reels_status(*, database: Path | None = None) -> dict[str, object]:
    with connect(database) as connection:
        return {
            "waiting": waiting_count(connection),
            "batch_size": BATCH_SIZE,
            "jobs": [public_job(row) for row in list_jobs(connection, limit=20)],
            "database": str(database or reels_database_path()),
        }


def _pack_folder(root: Path, pack_id: str) -> Path:
    folder = root / pack_id
    if not folder.is_dir():
        raise ReelError(f"Publish pack not found: {pack_id}", kind="media")
    return folder

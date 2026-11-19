"""Offline tests for autonomous Instagram Reels (v1.1)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from anskar.instagram.r2 import (
    VIDEO_PRESIGN_SECONDS,
    R2Credentials,
    R2StagingAdapter,
    StagedObject,
    stage_video,
)
from anskar.reels.caption import build_reel_caption, caption_matches
from anskar.reels.errors import ReelError
from anskar.reels.ffmpeg_tools import VideoProbe, validate_reel_output
from anskar.reels.ledger import (
    BATCH_SIZE,
    claim_next_batch,
    connect,
    get_job,
    record_eligible,
    update_job,
    waiting_count,
)
from anskar.reels.render import pick_music_file, render_reel
from anskar.reels.service import (
    maintain_reels,
    process_reel_job,
    recover_missed_eligibility,
    record_reel_eligible,
)


class ReelLedgerTests(unittest.TestCase):
    def test_next_batch_waits_for_seven_new_packs(self):
        with connect(self.db) as connection:
            for i in range(7):
                record_eligible(connection, artwork_id=f"old-{i}", pack_id=f"old-pack-{i}")
            first = claim_next_batch(connection)
            update_job(connection, first, status="published", media_id="original")
            for i in range(7):
                self.assertFalse(record_eligible(connection, artwork_id=f"alias-{i}", pack_id=f"old-pack-{i}"))
            for i in range(5):
                record_eligible(connection, artwork_id=f"new-{i}", pack_id=f"new-pack-{i}")
            self.assertIsNone(claim_next_batch(connection))
            for i in range(5, 7):
                record_eligible(connection, artwork_id=f"new-{i}", pack_id=f"new-pack-{i}")
            second = claim_next_batch(connection)
            self.assertEqual(set(json.loads(get_job(connection, second)["artwork_ids"])), {f"new-{i}" for i in range(7)})
            self.assertIsNone(claim_next_batch(connection))

    def test_wrong_batch_size_refused(self):
        with connect(self.db) as connection:
            with self.assertRaises(ReelError):
                claim_next_batch(connection, size=5)

    def setUp(self):
        self.env = patch.dict(os.environ)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = self.root / "reels.sqlite"
        os.environ["ANSKAR_REELS_DB"] = str(self.db)
        os.environ["ANSKAR_NOTIFY"] = "0"

    def tearDown(self):
        self.temporary.cleanup()

    def test_claim_seven_without_double_claim(self):
        with connect(self.db) as connection:
            for index in range(8):
                record_eligible(
                    connection,
                    artwork_id=f"art-{index}",
                    pack_id=f"pack-{index}",
                    completed_at=f"2026-01-0{index + 1}T12:00:00+00:00"
                    if index < 9
                    else "2026-01-10T12:00:00+00:00",
                )
            first = claim_next_batch(connection, size=BATCH_SIZE)
            second = claim_next_batch(connection, size=BATCH_SIZE)
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertEqual(waiting_count(connection), 1)
            job = get_job(connection, first)
            self.assertEqual(job["status"], "pending")
            ids = json.loads(job["artwork_ids"])
            self.assertEqual(len(ids), 7)
            self.assertEqual(ids[0], "art-0")

    def test_eligibility_recovery_counts_production_ignores_lab(self):
        packs = self.root / "packs"
        packs.mkdir()
        daily_db = self.root / "daily.sqlite"
        from anskar.daily.ledger import connect as daily_connect
        from anskar.daily.ledger import begin_run, update_run

        with daily_connect(daily_db) as daily:
            live = begin_run(daily, dry_run=False, run_kind="daily")
            update_run(
                daily,
                live,
                status="completed",
                pack_id="production-poem-1-seed-1-aaaaaaaa",
                instagram_status="published",
                instagram_media_id="ig-live",
            )
            # Rehearsals never count, even with a production-prefixed pack.
            rehearsal = begin_run(daily, dry_run=False, run_kind="test")
            update_run(
                daily,
                rehearsal,
                status="completed",
                pack_id="production-poem-2-seed-2-bbbbbbbb",
                instagram_status="published",
                instagram_media_id="ig-rehearsal",
            )
            # Lab pack published somehow — never counts.
            lab = begin_run(daily, dry_run=False, run_kind="test")
            update_run(
                daily,
                lab,
                status="completed",
                pack_id="lab-pack-1",
                instagram_status="published",
                instagram_media_id="ig-lab",
            )
        for pack_id, art in (
            ("production-poem-1-seed-1-aaaaaaaa", "prod-art-1"),
            ("production-poem-2-seed-2-bbbbbbbb", "prod-art-2"),
            ("lab-pack-1", "lab-art-1"),
        ):
            (packs / pack_id).mkdir()
            (packs / pack_id / "manifest.json").write_text(
                json.dumps({"artwork_id": art, "instagram_published": True}),
                encoding="utf-8",
            )
        inserted = recover_missed_eligibility(
            database=self.db, daily_db=daily_db, packs=packs
        )
        self.assertEqual(inserted, 1)
        with connect(self.db) as connection:
            self.assertEqual(waiting_count(connection), 1)
            packs_seen = {
                row["pack_id"]
                for row in connection.execute("SELECT pack_id FROM reel_artworks")
            }
            self.assertEqual(
                packs_seen,
                {
                    "production-poem-1-seed-1-aaaaaaaa",
                },
            )

class ReelRenderTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        os.environ["ANSKAR_NOTIFY"] = "0"
        os.environ["ANSKAR_REELS_MUSIC"] = str(self.root / "music")
        (self.root / "music").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_pick_music_file_is_random_and_allows_reuse(self):
        import random

        library = self.root / "music"
        tracks = [library / name for name in ("a.ogg", "b.ogg", "c.ogg")]
        for path in tracks:
            path.write_bytes(b"x")
        chosen = {
            pick_music_file(library, rng=random.Random(seed))
            for seed in range(40)
        }
        self.assertTrue(chosen.issubset(set(tracks)))
        self.assertGreaterEqual(len(chosen), 2)
        fixed = pick_music_file(library, rng=random.Random(7))
        self.assertEqual(fixed, pick_music_file(library, rng=random.Random(7)))

    def test_render_uses_silent_aac_and_faststart_when_music_empty(self):
        packs = []
        for index in range(7):
            folder = self.root / f"pack-{index}"
            (folder / "print").mkdir(parents=True)
            image = folder / "print" / "artwork.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([index]) * 64)
            packs.append(folder)
        captured: list[list[str]] = []

        def fake_ffmpeg(argv, *, timeout=600.0):
            captured.append(list(argv))
            # Write tiny destination files so later steps see paths.
            dest = Path(argv[-1])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"0" * 1200)

        fake_probe = VideoProbe(
            width=1080,
            height=1920,
            duration=22.0,
            fps=30.0,
            has_audio=True,
            video_codec="h264",
            audio_codec="aac",
        )
        output = self.root / "out" / "reel.mp4"
        with patch("anskar.reels.render.run_ffmpeg", side_effect=fake_ffmpeg):
            with patch("anskar.reels.render.validate_reel_output", return_value=fake_probe):
                with patch("anskar.reels.ffmpeg_tools.probe_video", return_value=fake_probe):
                    result = render_reel(packs, output=output, job_id="reel-test", music=None)
        self.assertTrue(result["silent_audio"])
        joined = " ".join(" ".join(args) for args in captured)
        self.assertIn("libx264", joined)
        self.assertIn("yuv420p", joined)
        self.assertIn("+faststart", joined)
        self.assertIn("anullsrc", joined)
        self.assertIn("48000", joined)
        self.assertIn("aac", joined)
        self.assertIn("128k", joined)

    def test_ffprobe_rejects_wrong_dimensions(self):
        path = self.root / "bad.mp4"
        path.write_bytes(b"0" * 2000)
        bad = VideoProbe(
            width=1920,
            height=1080,
            duration=20.0,
            fps=30.0,
            has_audio=True,
            video_codec="h264",
            audio_codec="aac",
        )
        with patch("anskar.reels.ffmpeg_tools.probe_video", return_value=bad):
            with self.assertRaises(ReelError) as ctx:
                validate_reel_output(path)
        self.assertIn("1080x1920", str(ctx.exception))


class ReelCaptionTests(unittest.TestCase):
    def test_fallback_includes_brand_hashtag(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folders = []
            for index in range(7):
                folder = root / f"p{index}"
                folder.mkdir()
                (folder / "manifest.json").write_text(
                    json.dumps({"rights": {"title": f"Work {index}", "author": "Blake"}}),
                    encoding="utf-8",
                )
                folders.append(folder)
            caption, digest = build_reel_caption(folders, job_id="reel-seed-1", use_ollama=False)
            self.assertIn("#AnskarGrotzschnapf", caption)
            self.assertEqual(len(digest), 64)
            self.assertTrue(caption_matches(caption, caption))
            self.assertFalse(caption_matches("totally different", caption))


class ReelPublishTests(unittest.TestCase):
    def test_temporary_ledger_cannot_use_live_credentials(self):
        with patch("anskar.reels.service.load_credentials", side_effect=AssertionError("real credentials accessed")):
            with self.assertRaisesRegex(ReelError, "explicit publishing adapters"):
                process_reel_job(self.job_id, database=self.db, packs=self.packs)

    def test_published_without_media_id_is_not_republished(self):
        with connect(self.db) as connection:
            update_job(connection, self.job_id, status="published", media_id=None)
        with patch("anskar.reels.service.load_credentials", side_effect=AssertionError("credentials accessed")):
            result = process_reel_job(self.job_id, database=self.db, packs=self.packs)
        self.assertEqual(result["skipped"], "already_published")

    def setUp(self):
        self.env = patch.dict(os.environ)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = self.root / "reels.sqlite"
        self.packs = self.root / "packs"
        self.packs.mkdir()
        self.reels_dir = self.root / "reels"
        self.reels_dir.mkdir()
        os.environ["ANSKAR_REELS_DB"] = str(self.db)
        os.environ["ANSKAR_REELS_DIR"] = str(self.reels_dir)
        os.environ["ANSKAR_NOTIFY"] = "0"
        self.pack_ids = []
        for index in range(7):
            pack_id = f"pack-{index}"
            self.pack_ids.append(pack_id)
            folder = self.packs / pack_id
            (folder / "print").mkdir(parents=True)
            (folder / "print" / "artwork.png").write_bytes(b"\x89PNG" + bytes([index]) * 32)
            (folder / "manifest.json").write_text(
                json.dumps({"rights": {"title": f"Title {index}", "author": "Author"}}),
                encoding="utf-8",
            )
            record_reel_eligible(artwork_id=f"art-{index}", pack_id=pack_id, database=self.db)
        with connect(self.db) as connection:
            self.job_id = claim_next_batch(connection)
        assert self.job_id is not None
        # Pre-write a fake rendered video so process skips ffmpeg.
        video = self.reels_dir / self.job_id / "reel.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"0" * 2000)
        with connect(self.db) as connection:
            update_job(
                connection,
                self.job_id,
                video_path=str(video),
                video_sha256="abc",
                caption="Seven works.\n\n#AnskarGrotzschnapf",
                caption_sha256="cap",
            )

    def tearDown(self):
        self.temporary.cleanup()

    def test_media_id_short_circuits(self):
        with connect(self.db) as connection:
            update_job(connection, self.job_id, media_id="already-live", status="published")
        result = process_reel_job(
            self.job_id,
            database=self.db,
            packs=self.packs,
            publish=True,
            graph=object(),  # unused
            adapter=object(),
        )
        self.assertEqual(result["media_id"], "already-live")
        self.assertEqual(result.get("skipped"), "already_published")

    def test_finished_container_publishes_without_recreate(self):
        with connect(self.db) as connection:
            update_job(connection, self.job_id, container_id="ctr-1", status="publishing")

        calls: list[str] = []

        class FakeGraph:
            def create_video(self, *a, **k):
                calls.append("create")
                raise AssertionError("must not recreate")

            def container_status(self, container_id):
                return {"id": container_id, "status_code": "FINISHED"}

            def publish(self, user_id, creation_id):
                calls.append("publish")
                return "media-99"

            def media(self, media_id):
                return {"id": media_id, "permalink": "https://www.instagram.com/reel/x/"}

            def recent_media(self, user_id):
                return []

            def profile(self):
                return {"user_id": "1789", "username": "anskargrotzschnapf"}

        with patch("anskar.reels.service.load_credentials") as load:
            load.return_value.access_token = "token"
            load.return_value.user_id = "1789"
            result = process_reel_job(
                self.job_id,
                database=self.db,
                packs=self.packs,
                publish=True,
                graph=FakeGraph(),
                adapter=_FakeVideoStaging(),
            )
        self.assertEqual(result["media_id"], "media-99")
        self.assertEqual(result.get("reconciled"), "finished")
        self.assertNotIn("create", calls)
        self.assertIn("publish", calls)

    def test_caption_reconcile_binds_without_create(self):
        caption = "Seven works.\n\n#AnskarGrotzschnapf"
        with connect(self.db) as connection:
            update_job(connection, self.job_id, caption=caption, container_id=None)

        class FakeGraph:
            def create_video(self, *a, **k):
                raise AssertionError("must not create")

            def recent_media(self, user_id):
                return [{"id": "remote-1", "caption": caption, "permalink": "https://ig/p/1"}]

            def profile(self):
                return {"user_id": "1789"}

        with patch("anskar.reels.service.load_credentials") as load:
            load.return_value.access_token = "token"
            load.return_value.user_id = "1789"
            result = process_reel_job(
                self.job_id,
                database=self.db,
                packs=self.packs,
                publish=True,
                graph=FakeGraph(),
                adapter=_FakeVideoStaging(),
            )
        self.assertEqual(result["media_id"], "remote-1")
        self.assertEqual(result.get("reconciled"), "caption")

    def test_r2_video_ttl_at_least_24h(self):
        self.assertGreaterEqual(VIDEO_PRESIGN_SECONDS, 86400)
        path = self.root / "clip.mp4"
        path.write_bytes(b"0" * 1500)
        staging = _FakeVideoStaging()
        staged = stage_video(path, job_id="job-ttl", adapter=staging, expires_in=VIDEO_PRESIGN_SECONDS)
        self.assertEqual(staging.last_expires_in, VIDEO_PRESIGN_SECONDS)
        self.assertTrue(staged.url.startswith("https://"))
        self.assertIn("instagram/reels/", staged.key)


class ReelMaintainWiringTests(unittest.TestCase):
    def test_maintain_recovers_and_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            db = root / "reels.sqlite"
            packs = root / "packs"
            packs.mkdir()
            daily_db = root / "daily.sqlite"
            from anskar.daily.ledger import connect as daily_connect
            from anskar.daily.ledger import begin_run, update_run

            pack_id = "production-poem-9-seed-9-cccccccc"
            with daily_connect(daily_db) as daily:
                run_id = begin_run(daily, dry_run=False, run_kind="daily")
                update_run(
                    daily,
                    run_id,
                    status="completed",
                    pack_id=pack_id,
                    instagram_status="published",
                    instagram_media_id="ig-1",
                )
            (packs / pack_id).mkdir()
            (packs / pack_id / "manifest.json").write_text(
                json.dumps({"artwork_id": "art-recover"}),
                encoding="utf-8",
            )
            report = maintain_reels(
                database=db, packs=packs, daily_db=daily_db, publish=False
            )
            self.assertEqual(report["recovered_eligibility"], 1)
            self.assertEqual(report["waiting"], 1)


class _FakeVideoStaging(R2StagingAdapter):
    def __init__(self) -> None:
        self.credentials = R2Credentials(
            access_key_id="test",
            secret_access_key="test-secret",
            endpoint_url="https://example.r2.cloudflarestorage.com",
        )
        self.bucket = "anskar-grotzschnapf"
        self.expires_in = VIDEO_PRESIGN_SECONDS
        self._client = object()
        self.objects: dict[str, bytes] = {}
        self.last_expires_in: int | None = None

    def upload(
        self,
        path: Path,
        key: str | None = None,
        *,
        content_type: str = "video/mp4",
        expires_in: int | None = None,
    ) -> StagedObject:
        object_key = key or self.object_key(path.stem, suffix=".mp4", prefix="instagram/reels/")
        self.objects[object_key] = path.read_bytes()
        self.last_expires_in = self.expires_in if expires_in is None else int(expires_in)
        url = f"https://example.r2.cloudflarestorage.com/{object_key}?X-Amz-Signature=test"
        return StagedObject(key=object_key, url=url)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


if __name__ == "__main__":
    unittest.main()

# Task 022 — Autonomous Instagram Reels (v1.1)

Status: done (implemented 2026-10-22).

## Goal

After every seven completed daily Instagram artworks, assemble a local 9:16 H.264/AAC MP4 and publish it as an Instagram video (marketing: Reel) via Instagram Login. Reels stay up when featured Etsy listings expire.

## Locked decisions

| Topic | Choice |
|-------|--------|
| Music | Local library in `data/reels-music/`; Meta Audio API is Facebook Login only |
| API | `media_type=VIDEO` on `graph.instagram.com` (not `REELS` + Audio API) |
| Trigger | After daily IG success → eligibility; maintain recovers misses and drains jobs |
| Lifecycle | Keep Reels on day-42 Etsy expiry; do not delete Instagram media |
| Batch | Exactly seven production artworks; test/rehearsal packs never count |

## Lessons from Azeroth Moments

Reuse: libx264, yuv420p, `+faststart`, AAC 128k stereo, even 1080×1920, private R2 + presigned GET, create → poll → publish, ~60s poll / ~300s max, reconcile before recreate.

Anskar deviations: silent AAC @ 48 kHz when music is missing; R2 video TTL ≥24h; one continuous compilation (no landscape carousels); Anskar artistic captions / hashtags.

## Layout

- `src/anskar/reels/` — ledger, ffmpeg/ffprobe, render, caption, orchestrator
- `data/reels.sqlite` — eligibility + jobs
- `data/reels/<job_id>/reel.mp4` — rendered artifacts
- `anskar reels status|render|publish|maintain`
- `etsy maintain` also drains Reels (same timer)

## Safeguards

1. Maintain recovers missed eligibility from daily / IG records after crash.
2. Reconcile existing `media_id` / `container_id` / caption match before creating another container.
3. Silent AAC when the music library is empty.
4. ffprobe gate (dims, codecs, duration, fps, size) before upload.
5. Video staging TTL ≥24h; delete object only after successful publish.

## Out of scope

Facebook Login / Meta Audio API / deleting Reels on Etsy expiry / landscape carousels / cloud video APIs / historical bulk backfill.

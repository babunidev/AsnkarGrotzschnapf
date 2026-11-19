# Changelog

Development history for Anskar Grotzschnapf. Detailed design notes stay in [`docs/tasks/`](docs/tasks/). This file is the short public log.

## 2026-11-19 — human–AI collaboration record

- Rewrote `docs/AI_COLLABORATION.md` to the shared text used in all of Babuni's repositories: how Babuni works with AI, who did what (the tools and recorded models named in this project's records) and where the details are. The earlier, longer version stays in the Git history. Claude Code (Claude Opus 5.5).

## 2026-11-19 — documentation moved into `docs/`

- Moved `CONCEPT.md`, `ROADMAP.md` and `ASSET_RIGHTS.md` into `docs/`. The root keeps only `README.md`, `AGENTS.md`, `LICENSE` and `CHANGELOG.md`; links to the moved files and the documentation rules in `AGENTS.md` were updated. No code changed. Claude Code (Claude Opus 5.5).

## 2026-11-14 — Lower Etsy base price

- New Etsy listings start at 120 SEK instead of 230 SEK (`120 + 20R + 10S`, Swedish VAT-inclusive). Listings that are already active keep their price.
- Etsy was reconnected after its refresh token was revoked; the prints queued from 2 to 14 November were published at the new price.

## 2026-10-29 — Development and troubleshooting history

- Expanded [the development journal](docs/DEVLOG.md) with the progression from the eight-poem archive and Prompt Lab through print sizing, duplicate-artwork recovery, exact source preservation, Etsy authorization, wake rehearsals and daily retry safeguards.
- Added explicitly identified later local evidence for Reels and the 24 October 300-poem expansion; these notes do not imply that all local code changes are in GitHub.
- Recorded the read-only investigation of the successful 29 October noon run: wake, automatic Ollama startup, and saved Instagram/Etsy publication results. No new artwork or social/storefront publication was triggered.
- Kept historical test results and uncertain dates distinct from fresh verification. Omitted personal network identifiers and account circumstances.
- Confirmed the portfolio already selects this journal; its saved content snapshot must be refreshed and built before the website displays the addition.

## [1.1.0] — 2026-10-22

Autonomous Instagram compilation Reels:

- After every seven successful daily Instagram publishes, claim a batch, render a local 1080×1920 H.264/AAC MP4 (FFmpeg: yuv420p, faststart, music or silent AAC @ 48 kHz), and publish with Instagram Login `media_type=VIDEO`.
- SQLite reel ledger with eligibility recovery on maintain; reconcile remote containers before recreating; R2 video staging TTL ≥24h.
- `anskar reels status|render|publish|maintain`; `etsy maintain` also drains Reels. Failures notify; the daily run still completes. Reels stay when Etsy listings expire.
- Optional instrumental library in `data/reels-music/` (binaries gitignored).

## [1.0.0] — 2026-10-21

First operational “set and forget” daily artist:

- Noon systemd timer selects one cleared poem, generates 1600×1600 artwork locally, packs a print, publishes to Instagram, and lists a quantity-1 SEK digital download on Etsy when the shop is `ready`.
- System wake timer (`WakeSystem=true`) can start the noon run from sleep; user and system noon timers must not both be enabled.
- `anskar-etsy-maintain.timer` syncs sales, applies the day-30 20% discount, and removes unsold listings after 42 days.
- Review hardening (task 021): auto-resume incomplete runs, one live Instagram post per Swedish day, durable Etsy retry queue, soft Instagram media failures, safer OAuth/packs/manifests, cleaner buyer listing copy.
- Etsy gallery uses preview images and detail crops; the paid download stays the full-resolution print PNG.
- Desktop notifications for daily stages (`ANSKAR_NOTIFY=0` to silence).

Earlier milestones (archive import, prompt lab, Instagram Login, Etsy OAuth, wake rehearsal) are recorded as tasks 010–020 under `docs/tasks/`.

## 2026-10-28 — Documentation audit #36

- Added design and content/provenance guides and consolidated the artistic intention, daily pipeline and archival failure lessons into the supporting project documentation.
- Preserved the original numbered task archive, all creative source material, publication scripts and existing operational release notes.
- Identified the difference between `pyproject.toml` package version 0.1.0 and the documented operational 1.0.0 milestone for later review. No art, service publication or runtime test performed in this pass.

## 2026-11-13 — License and rights

- Established MIT for software with separate poetry, art and model rights and updated repository documentation to explain the permission boundary.
- Preserved third-party authorship and external assets' separate terms. No application behavior or runtime verification is claimed.

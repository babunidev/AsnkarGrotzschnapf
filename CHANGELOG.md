# Changelog

Development history for Anskar Grotzschnapf. Detailed design notes stay in [`docs/tasks/`](docs/tasks/). This file is the short public log.

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

## 2026-10-29 — Development and troubleshooting history

- Expanded [the development journal](docs/DEVLOG.md) with the progression from the eight-poem archive and Prompt Lab through print sizing, duplicate-artwork recovery, exact source preservation, Etsy authorization, wake rehearsals and daily retry safeguards.
- Added explicitly identified later local evidence for Reels and the 24 October 300-poem expansion; these notes do not imply that all local code changes are in GitHub.
- Recorded the read-only investigation of the successful 29 October noon run: wake, automatic Ollama startup, and saved Instagram/Etsy publication results. No new artwork or social/storefront publication was triggered.
- Kept historical test results and uncertain dates distinct from fresh verification. Omitted personal network identifiers and account circumstances.
- Confirmed the portfolio already selects this journal; its saved content snapshot must be refreshed and built before the website displays the addition.

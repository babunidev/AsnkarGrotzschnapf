# Anskar Grotzschnapf — roadmap and verification

**Author:** Babuni.dev

## Source-documented milestone

[CHANGELOG](CHANGELOG.md) records a 1.0.0 daily loop dated 2026-10-21: noon timer, locally generated 1600 × 1600 art, print pack, Instagram publishing, conditional quantity-one Etsy download listing, and Etsy maintenance (day-30 discount, day-42 removal). Task 021 describes resume, retry and duplicate-post hardening.

## Outstanding verification

This documentation audit did not run the systemd timer, generate an image, publish to Instagram/Etsy, or inspect active credentials. Status from earlier development records should not be mistaken for verification of the present installation.

Proposed checks: end-to-end run logs, scheduled wake behavior, safe retry/idempotency, eligibility/poetry attribution, final print quality, and Etsy listing/purchase flow. These are checks, not approved new features.

## Audit #36 — evidence and release checks (2026-10-28)

- [x] Add visual/publication design and poetry/content-provenance guides.
- [x] Preserve task 015's whitespace/source-match failure and task 021's retry, one-day and publishing safety decisions in the development history.
- [ ] Reconcile `pyproject.toml` version 0.1.0 with the changelog's operational 1.0.0 milestone without silently changing either.
- [ ] Run current tests and record command, environment, commit and result; the historical 118 passing tests from task 015 are not a fresh suite result.
- [ ] Check active noon timer selection, wake operation, idempotency and recovery on the local computer.
- [ ] Verify current poetry eligibility, source/translator credits, print previews and final print fidelity before publication.
- [ ] Test Instagram and Etsy publishing, queued retries, maintenance rules and sales state using safe controlled scenarios.

These are verification tasks, not automatically approved changes to project behavior.

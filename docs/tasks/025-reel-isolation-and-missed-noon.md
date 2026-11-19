# Task 025 — Duplicate Reel and missed noon investigation

Date: 2026-10-30. Request: explain today's missing image and yesterday's repeated Reel; enforce seven new images per Reel.

## Findings

- System shutdown: 29 October 21:19:59 Stockholm time. Next boot: 30 October 12:15:25. Installed noon timer has `Persistent=false`; no daily service invocation or daily ledger row today at investigation time. No scheduler change or catch-up publication was requested or performed.
- Production Reel ledger had one published job from 24 October and five waiting packs from 25–29 October. Maintenance on 29 October at 12:17 and 18:16 and on 30 October at 12:18 reported five waiting, zero recovered, zero processed.
- Read-only Instagram API returned an additional Reel at 29 October 12:57:45 UTC (13:57:45 local), coinciding with this chat's unrestricted documentation test rerun. Its caption described the original batch. The production ledger did not record it.
- Root cause: `maintain_etsy` automatically invoked real Reel maintenance even when given a fake Etsy client. Daily tests leaked temporary Reel ledger/output environment settings. Recovery used default real packs and daily records, treating historical images as new in an empty test ledger, then reached real Instagram/R2 credentials. This explains the duplicate and absent production job. The earlier no-publication claim was incorrect.

## Changes

- `maintain_etsy` defaults to no cross-service Reel invocation. CLI explicitly opts in; offline mode never invokes Reels.
- Simulated daily databases cannot enqueue or publish production Reels. Alternate Reel databases require explicit publishing adapters before rendering or credential access.
- Test environment changes are restored. Recovery accepts only daily ledger evidence, excludes rehearsals and no longer enrolls orphan manifests.
- Enrollment deduplicates by pack as well as artwork ID. Claims require exactly seven unused distinct packs under a write transaction. A process lock serializes publishers. Published status is terminal even without a media ID.
- Added regression tests for five-versus-seven, disjoint second batches, aliases, alternate ledgers, simulated daily runs, published jobs and Etsy side effects.
- Added `scripts/run_tests_offline.py`: blocks external Python socket connections, permits localhost tests, reports unexpected external attempts. It is not a subprocess sandbox.

## Verification and data handling

`ANSKAR_NOTIFY=0 .venv/bin/python scripts/run_tests_offline.py`: **259 tests passed in 3.690 seconds**, no blocked external connection attempts. Local socket permission was granted for server tests.

During verification, restoring formerly leaked environment variables exposed a schedule test inserting synthetic pack `production-poem-2-seed-7-a` into the production Reel ledger. Added the simulated-daily guard, backed up the ledger to `data/backups/reels-before-test-row-cleanup-20261030.sqlite`, removed only that new unclaimed synthetic row, and reran the complete suite. Final production counts stayed **five waiting packs, one published job**. Real artwork and historical batch memberships were preserved. No live publishing command or deletion of remote posts was performed in this investigation.

The local development journal contains the incident correction. Detailed public disclosure was rejected by automatic approval review; a minimal factual correction without operational details or post links was successfully published to GitHub in commit `998bc9ad60c5cffd7298e3fdcff657679029d645`. Source fixes remain local, available to the existing services on their next invocation. No model, driver, timer or credentials were changed.

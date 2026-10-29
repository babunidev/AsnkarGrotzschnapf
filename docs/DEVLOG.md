# Anskar Grotzschnapf — development journal

**Author:** Babuni.dev

## Retrospective source review — 2026-10-26

The project began with the artistic experiment of a fictional machine artist creating on a schedule rather than a one-off image generator. Its repository now records the practical journey needed to make that fiction operational: assembling and clearing a poetry archive, interpreting text without replacing the original poem, selecting image-generation styles, preparing printable files, and integrating publication services.

The [numbered task archive](tasks/) is the primary record of these experiments. One particularly instructive incident appears in [Task 015](tasks/015-source-attribution.md): an automated step stripped leading whitespace from Walt Whitman's archived poem and caused an exact source lookup to fail. The subsequent design favored poem ID and exact source-text validation, preserving an already generated image while reconstructing an unpublished pack. That task reports 118 tests passing for its fix.

The [2026-10-21 changelog](../CHANGELOG.md) records the first operational version, including scheduling, publication, and resume safeguards. This retrospective summary does not imply that the present audit ran those systems. Babuni.dev defined the artistic direction; AI tools contributed implementation, generative steps and this documentation synthesis. The poets remain credited for their own writing.

## 2026-10-28 — Audit #36: keeping the literary source visible in a machine artist

Babuni.dev's project imagines Anskar as a fictional artist whose daily creative practice continues without repeated human prompting. The machine selects a cleared poem, interprets it visually, produces local art, prepares a print, and can post or list the work. The original poets are not displaced by this fiction: their words and their attributions must survive every technical transformation.

The task archive shows why provenance became a technical requirement. Task 015 describes a Whitman poem whose leading indentation was accidentally removed during source matching, interrupting print preparation after the artwork already existed. The correction preserved exact text and the original image, preferring poem ID and verifiable source identity. Task 021 then tackled a different kind of continuity: resuming interrupted noon runs, avoiding duplicate daily posts, retrying failed Etsy listings and protecting manifests and the full-resolution download. These are concrete corrections, not a retrospective story of flawless automation.

**Babuni.dev direction:** A daily fictional artist with careful poetry rights and a local-first workflow. **AI contribution:** Implementation and imagery where evidenced, plus this documentation synthesis. **Creative iteration:** Safeguards emerged from documented failures and operator decisions, not from automatic permission to publish. **Verification in this audit:** Existing repo, package metadata and task records examined; no model execution, image generation, systemd job, Instagram post or Etsy listing performed. The 118 tests in task 015 are historical reports only.

## 2026-10-29 — How the daily artist became reliable

This retrospective brings together the numbered task records, the local working installation, and a read-only investigation of the 29 October run. It is a history of recorded attempts and corrections, not a complete transcript of every conversation. Early milestones below are ordered by task sequence where their exact dates are not established. Historical test counts belong to their original tasks.

### From eight poems to a visual language

The first milestone was a local SQLite archive containing eight complete poems, with source and rights evidence and one pending selection at a time ([task 001](tasks/001-poetry-archive.md)). Generation and publishing were deliberately separate stages. This made it possible to experiment without silently consuming a poem or publishing a test.

The Prompt Lab introduced direct text-to-image experiments, house styles, and then a local Ollama interpreter. The interpreter produced one visual prompt while keeping the full poem separately. Text too long for the context window was refused instead of shortened ([task 006](tasks/006-prompt-interpreter.md)). The artistic controls then separated surface style from construction: Gentle, Surreal Abstract and Experimental could be compared on the same poem. Task 007 records three interpretations of “THE LAMB” and retained earlier attempts. The aim was a visual metaphor, not simply illustrating the poem line by line.

This evolved rather than arriving fully formed. [Task 007](tasks/007-abstraction-and-printmaker.md) still described generating a larger print sample from a small approved experiment; [task 009](tasks/009-print-size.md) established the later rule that the approved image itself is the download. Print preparation must not replace it with a new sample or pretend that a DPI label adds detail. A 1024-pixel square could support a six-inch print at about 171 PPI, but not an eight-inch print at the project's minimum quality. The production default became 1600 × 1600 for an eight-inch print at 200 PPI. Earlier samples stayed intact.

### A successful image could still stop the pipeline

The first live daily attempt for “THE TIGER” hit a duplicate-artwork error. An earlier dry run had already created a valid image and pack, while leaving the poem pending. The live run attempted generation again and correctly refused to overwrite the image—but had no recovery path.

[Task 014](tasks/014-duplicate-artwork-recovery.md) added a decision before generation: reuse compatible production work, preserve incompatible older work, and avoid selecting poems that already had successful artwork. Its verification resumed the existing pack without generating again and reported 115 tests passing. The lesson was that “already generated” is useful progress to recover, not automatically an unrecoverable failure.

A second failure involved “O Captain! My Captain!” by Walt Whitman. The printmaker stripped leading whitespace before comparing the source with the archive. The poem began with indentation, so matching failed even though the saved source and poem identity were correct. [Task 015, source attribution](tasks/015-source-attribution.md), removed that destructive trimming, preferred poem ID plus exact source verification, and rebuilt the unpublished pack from the existing image. It reported 118 tests passing. No replacement artwork was necessary.

### Moving from manual stages to one daily run

[Task 015, simplifying the artist](tasks/015-simplify-daily-artist.md), removed repeated approvals from daily mode while keeping manual commands separate. The archive's documented eligibility decision became the daily pipeline's input; the visual prompt never became a substitute for the poem. Instagram success determined when the poem was marked used, while Etsy could remain queued during seller verification.

That record also preserves an unresolved Instagram container failure at the time of the task. The correction was to continue with the existing container rather than create another while the first was already finished. Its 125-test result and simulated day were not evidence of a successful live retry. Keeping this distinction matters: a working simulation and a real publication are different milestones.

### Connecting Etsy required exact details

Etsy rejected the numeric loopback callback URL but accepted the registered localhost hostname. [Task 017a](tasks/017a-etsy-oauth-callback.md) aligned authorization, callback validation and token exchange with that exact URL, while keeping the listener bound locally and making the certificate match.

OAuth authorization and seller verification remained separate. Later safeguards made Etsy failures independent of Instagram completion: a failed listing could enter a durable retry queue without making another daily post. The public gallery used previews and detail crops, while the full-resolution PNG remained the paid download. These distinctions prevented a successful login, an uploaded preview, or a queued pack from being mistaken for a completed sale or listing.

### Waking the computer was only the beginning

The wake rehearsals exposed failures outside image generation. A globally “degraded” system status could come from an unrelated failed service. [Task 019a](tasks/019a-wake-readiness.md) replaced that broad check with checks of the actual dependencies and bounded retries after resume. The installation also needed to start Ollama itself: where no service unit existed, it could launch the local server and wait for readiness.

A 21 October rehearsal then woke the computer but never started the production worker. The nested launch exited in roughly 22 milliseconds, its error was captured but not propagated, and the rehearsal stayed “scheduled” even though the surrounding service reported success.

[Task 020](tasks/020-end-to-end-sleep-wake-publish-sleep.md) corrected the inhibitor/privilege-launch ordering, made worker output visible in the journal, propagated exit codes, and recorded explicit rehearsal stages. It allowed a three-hour work budget. The task marked the implementation ready for a live rehearsal; it did not claim that development itself completed a live sleep–wake–publish–sleep cycle.

The noon schedule and the rehearsal retained different behavior: the daily run protects generation from sleep but does not force the computer back to sleep. Only the explicitly requested rehearsal may do that, subject to session activity.

### Hardening partial success

[Task 021](tasks/021-review-hardening.md), dated 21 October, addressed what happens between stages: resume incomplete runs, count a successful daily Instagram post against the Swedish calendar day even if bookkeeping is unfinished, retry eligible Etsy failures without bulk-publishing old packs, and keep rehearsal packs queue-only on resume.

The same review covered misleading sales states, duplicate draft risk, callback handling and damaged manifests. It also recorded a bounded response to repeated Instagram media failures while leaving the poem eligible for future use. These are recorded review findings and implemented safeguards; they should not all be read as incidents observed in production.

### 22–24 October: Reels and a larger poetry archive

The local task 022 and changelog record the addition of compilation Reels after seven successful production Instagram posts. The implementation renders video locally, keeps its own ledger, excludes rehearsals, and lets a Reel failure leave the daily artwork complete.

There is a useful historical mismatch: task 022 originally specified `media_type=VIDEO`, but the local implementation inspected on 29 October uses `REELS`; its code notes that the old type was deprecated. The exact correction date is not established here, and this history does not assert that a Reel was published. These later local changes are not all present in the older GitHub source snapshot.

The local 24 October collection report records **300 complete poems by 11 authors added to the original eight**: 300 imported, none rejected; a second import added none and identified 300 duplicates. The report says original poems and use history were preserved, full texts were checked against retained sources, and the real caption composer accepted all 300. It records 250 tests passing after rerunning with local socket access.

The research also had dead ends. Several providers returned access errors; an accessible API repository contained test fixtures rather than a suitable source collection; a large third-party dataset did not establish per-poem rights and completeness; other material required permission or a different supported rights basis. The imported batch used Standard Ebooks and Project Gutenberg source material with recorded author-death evidence. Long poems were excluded whole, not shortened. These are historical import results, not a new legal assessment or a fresh import in this documentation pass.

### 29 October: did it really publish without internet?

The operator noticed that the daily artwork had appeared despite earlier connection trouble. Comparing the daily service journal, network connection history and SQLite run record resolved the apparent contradiction.

All times below are Swedish local time:

| Time | Recorded event |
|---|---|
| Around 04:02–04:04 | Several connection attempts failed before another wireless connection succeeded. |
| 09:54 | The computer connected to its usual Wi-Fi, then went to sleep. |
| 12:00:49 | The computer woke and the daily service started. |
| 12:00:53 | The usual Wi-Fi reconnected and became the default route. |
| 12:01:19–12:01:21 | The pipeline started Ollama automatically and confirmed it was ready. |
| 12:04:50 | The ledger recorded the run complete, with both Instagram and Etsy marked published. |
| 12:05:06 | The service exited successfully. |

The work was based on Wilfred Owen's “The Send-Off”: [Instagram post](https://www.instagram.com/p/DfE21yviD8C/) and [Etsy listing](https://www.etsy.com/listing/4605536569). These links come from the saved run record; no new publication was triggered by the investigation.

Local interpretation and image generation can operate without internet, but successful uploads require connectivity. The logs show a working publication path at noon, with no recorded switch to the earlier alternative Wi-Fi during the run. They cannot establish why the upstream connection had failed earlier or when the provider restored it. Wireless names, device addresses and personal account circumstances are omitted from this public history.

### Evidence, authorship and remaining gaps

Babuni.dev supplied the concept, artistic direction and operating constraints; AI tools assisted with implementation and this source-based reconstruction. The original poets retain their literary authorship.

This addition combines tasks 001–021 already represented in the repository with later local task/collection records, current source inspection and the 29 October operational logs. It does not claim access to every earlier chat or recover every failed experiment. The local checkout contains changes beyond its last committed source version; a documentation update does not publish those code changes. Today's successful daily run does not by itself verify every retry path, Reel, sale, discount or expiry operation.

The portfolio website already includes `docs/DEVLOG.md` among this project's eight configured source documents. It reads a saved repository snapshot: updating GitHub makes this history available for its next content sync and build, rather than immediately changing the deployed website.

# Anskar Grotzschnapf — architecture

**Author:** Babuni.dev

The Python package lives in `src/anskar/`, with archive eligibility/selection, artwork interpretation/generation, publishing, and scheduling workflows. `pyproject.toml` declares the CLI entry point. `data/` holds archived and generated production records, including publish-pack manifests; `docs/tasks/` contains task-by-task design and remediation evidence.

The published README documents two mutually exclusive noon scheduling approaches: a system timer capable of waking the PC, and a user timer for an already-awake machine. Etsy maintenance is separate. Platform credentials live outside Git.

**Failure evidence:** [Task 015, Source Attribution](tasks/015-source-attribution.md) describes a poem-source lookup bug caused by stripping leading indentation. The fix preserved original text, preferred stable poem identity, and permitted resume without regenerating an existing image. That task records 118 passing tests for its scope, not a newly run suite today.

This is a repository audit; no local process was executed.

## Daily process and evidence boundary — 2026-10-28

The source describes a Python 3.14 local-first CLI in `src/anskar/`, with an SQLite archive, local Ollama interpretation, `sd-cli` image generation, print-pack preparation, Instagram publishing, conditional Etsy listings and separate Etsy maintenance. For the noon run, README documents **mutually exclusive** system wake and user timers; both should not be enabled together. The shop-maintenance timer separately syncs sales and applies day-30 discount/day-42 expiry rules.

Task 021 records a design to resume incomplete daily runs, avoid two live Instagram posts in the same Swedish day, queue transient Etsy failures and guard against duplicate listings or corrupt manifests. Task 015 records a source identity bug caused by trimming leading poem whitespace; matching now prefers a stable poem ID with exact source-text verification. These are historical implementation reports, not proof of the present installation's behavior.

**Version note:** `pyproject.toml` declares 0.1.0 while CHANGELOG and README describe operational 1.0.0. Investigate packaging/version policy before updating release guidance. No system timers, credentials, API accounts or live local process were queried in this review.

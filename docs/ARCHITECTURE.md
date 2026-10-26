# Anskar Grotzschnapf — architecture

**Author:** Babuni.dev

The Python package lives in `src/anskar/`, with archive eligibility/selection, artwork interpretation/generation, publishing, and scheduling workflows. `pyproject.toml` declares the CLI entry point. `data/` holds archived and generated production records, including publish-pack manifests; `docs/tasks/` contains task-by-task design and remediation evidence.

The published README documents two mutually exclusive noon scheduling approaches: a system timer capable of waking the PC, and a user timer for an already-awake machine. Etsy maintenance is separate. Platform credentials live outside Git.

**Failure evidence:** [Task 015, Source Attribution](tasks/015-source-attribution.md) describes a poem-source lookup bug caused by stripping leading indentation. The fix preserved original text, preferred stable poem identity, and permitted resume without regenerating an existing image. That task records 118 passing tests for its scope, not a newly run suite today.

This is a repository audit; no local process was executed.

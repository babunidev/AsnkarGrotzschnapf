# Task 023 — Add a varied working poetry collection

User request, 24 October 2026: take poems from the researched sources, provide a few hundred, and add them to the collection.

## Scope

Prepare and import 300 complete poems with documented Swedish commercial-use evidence. Preserve existing poems, use history and pending selection. Do not generate images or publish posts as part of this task. Do not treat a request to use a permission-only source as permission from its copyright holder.

## Deliverables

- `data/collections/varied-public-domain-2026-10-24.json`: 300 complete English poems from 11 authors, with author-death citations, rights notes and per-poem source provenance.
- `data/sources/poetry-expansion-2026-10-24/`: retained source XHTML, Gutenberg text, edition metadata and author RDF records; ignored by Git under the existing policy.
- `scripts/build_poetry_expansion_20261024.py`: offline, deterministic reconstruction from those snapshots. No database writes or generation.
- `docs/poetry-collection-2026-10-24.md`: human-readable catalogue, source coverage and validation outcome.
- `tests/test_expansion_collection.py`: actual import/idempotency/text-preservation and full-poem caption checks.

## Source decisions

Poem Index and Past Poetry are discovery indexes; direct downloads returned HTTP 403. Use their upstream Standard Ebooks editions rather than their derivative website text. Standard Ebooks metadata records underlying editions and dedicates its own editorial contributions under CC0. Author death evidence comes from retained Gutenberg RDF, assessed against the date-derived Swedish cutoff. The second text provider is Gutenberg directly (Sara Teasdale).

PoetryDB's API returned HTTP 403. Its accessible repository contains test fixtures, not an authoritative production data export; those were not imported. Litteraturbanken direct access also returned HTTP 403; unverified OCR from a facsimile is not substituted for exact poems. The large Hugging Face collection's label does not establish per-poem rights or completeness, so it is not used as the source of this cleared batch.

Peter Saint-Andre's dedication remains a promising route, but the current permanent policy, schema and importer require expired-term evidence; do not fabricate a death year. Jackson and Poetry in Translation require commercial permission that has not been obtained. These sources remain recorded in the research note, not silently marked cleared. No requests were sent. This task does not add licensed-work schema support or change permanent rules.

## Text handling

Select only structurally complete poem articles, never truncate a long poem. Exclude nested parts, identified fragments, translations, foreign-language markup, footnoted poems and complex structures requiring separate review. Each XHTML span becomes a verse line and each verse paragraph a stanza; preserve wording and punctuation, rendering iN indentation as four spaces per level. Dates/place footers are retained separately as source metadata. Gutenberg plain text is copied as an exact verse substring with LF newlines. Titles are whitespace-normalized separately from poem bodies.

Select a reproducible mix throughout each collection, balanced across authors with shorter qualifying corpora exhausted first. Reject repeated author/title pairs and normalized duplicate verse, including the original starter collection. Limit complete bodies to 1,400 characters and verify them with the real Instagram caption composer.

## Acceptance commands

```sh
python3 scripts/build_poetry_expansion_20261024.py
ANSKAR_NOTIFY=0 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
ANSKAR_NOTIFY=0 PYTHONPATH=src .venv/bin/python -m anskar import data/collections/varied-public-domain-2026-10-24.json
```

Back up SQLite before the live import. Verify old rows/use history remain identical, all 300 new poems are unused and eligible, and re-import creates no duplicates. Record exact results in the catalogue. No manual `select` against the live archive is necessary.

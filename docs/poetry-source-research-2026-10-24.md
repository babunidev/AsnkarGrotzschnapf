# Poetry supply research — 24 October 2026

Research only: no poems imported, rights flags changed, or external publications made.

## Local collection search

The production database `data/archive.sqlite` has eight poems, all marked documented/yes, and all eight have confirmed use history. There are zero unused cleared poems.

`docs/tasks/001-poetry-archive.md` explicitly specifies an initial eight-poem collection. The original Cursor plan at `/home/babuni/.cursor/plans/poetry_archive_foundation_51ba508a.plan.md` agrees. The collection file is `data/collections/gutenberg-public-domain.json`.

No larger poetry collection was located. Searches covered poetry-related filenames in the home directory (including hidden locations in follow-up searches), project files, Documents, Downloads, Desktop, `/home/babuni/data`, accessible temporary files, and the mounted `/run/media/babuni/64 GB` drive. ZIP member names in Downloads and the mounted drive were checked. Larger common text/dataset files in the main document/project/drive locations were inventoried. Relevant project plans were searched for references to PoetryDB, Poem Index, or 5,000 poems. Some system-private temporary directories were inaccessible. This is a bounded negative result, not proof that the collection never existed or is absent from every backup, cloud account, or differently named file.

## Sources worth pursuing

| Source | Evidence found | Recommended handling |
|---|---|---|
| [Poem Index](https://poemindex.org/) | Reports 5,508 poems, with author dates and counts. Includes Mary Weston Fordham, Frances Ellen Watkins Harper, James McIntyre, Voltairine de Cleyre and many others. | Strong discovery index. Check source editions and author/translator rights individually; the collection includes authors who died after the project's Swedish cutoff. No evidence connects this website to the missing local collection. |
| [Past Poetry archive](https://pastpoetry.com/archive/) | Reports 4,323 source texts derived from Standard Ebooks; explicitly notes territorial variation. | Discovery source for less familiar poets; follow source editions and document Swedish eligibility. |
| [Project Gutenberg](https://www.gutenberg.org/policy/permission.html) | Its permissions page explains commercial reuse of public-domain material and its US-only copyright basis. | Best fit for the existing importer: original-language collections, sourced author dates, full individual poems, and recorded editions. Inspect each ebook's rights and any separate contributions. |
| [PoetryDB](https://github.com/thundercomb/poetrydb) | Structured poetry API; repository describes the curated data as CC BY 4.0 and underlying poems as public domain. | Convenient ingestion format. Retain database attribution and independently check underlying poem rights in Sweden. The database licence cannot clear rights the curator does not own. |
| [Litteraturbanken: Frithiof Strömmerstedt, Dikter](https://litteraturbanken.se/export/faksimil/lb1626632.pdf) | This particular edition says it is free of known copyright restrictions and requests attribution to Göteborgs universitetsbibliotek and Litteraturbanken. | Concrete lesser-known Swedish candidate. Verify author dates, edition and exact poem boundaries before import. Do not generalize this notice to all Litteraturbanken content. |
| [DanFosing/public-domain-poetry](https://huggingface.co/datasets/DanFosing/public-domain-poetry) | Dataset reports 38,499 English poems, sourced from public-domain-poetry.com, with a CC0 label. | Large discovery pool, not ready-made legal clearance. Visible fields do not provide the full provenance and rights evidence required by this project. |

## Contemporary and permission-based routes

- **Peter Saint-Andre:** [Ancient Fire](https://stpeter.im/writings/fire/) contains original poems and translations. His [homepage](https://stpeter.im/) and [public-domain statement](https://stpeter.im/writings/essays/publicdomain.html) expressly dedicate his personal works to the public domain. Original poems such as *Cobalt*, *Urban Haiku*, and *Drought* are concrete contemporary candidates. Preserve the author's declaration as evidence; assess the legal effect and any underlying translation rights separately. Do not invent a death year to pass the existing importer.
- **Jackson / Janet Ruth Jackson:** the [licensing page](https://writerjackson.com/licensing/) uses CC BY-NC-ND by default but explicitly invites requests for commercial use and derivative works, including generative AI output. This is a particularly relevant permission lead, not permission already obtained.
- **Poetry in Translation / A. S. Kline:** the [publisher's homepage](https://www.poetryintranslation.com/) allows noncommercial reuse and invites enquiries about commercial applications. Original poetry and translations could broaden the archive if written permission covers the intended use and all necessary underlying rights.
- **Swedish authors and estates:** [ALIS's current notice](https://www.alis.org/) says licensing ceased at the end of 2025. Seek individual permission from the rights holder; Författarförbundet or Författarfonden may help locate them. Do not use outdated advice to apply to ALIS for a new licence.

Any permission request should describe local full-text storage and AI processing, creation and sale of art prints, publication of complete poems with artwork on Instagram, any text used in Reels, territory, duration, attribution, fees and continued use of existing publications. No requests have been sent.

## Rules versus implementation

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) permits commercial sharing and adaptation with its conditions. NC licences do not supply commercial permission; ND licences do not supply permission to share adaptations. ShareAlike needs its own compliance assessment. Confirm the licence applies to the poem itself and comes from someone entitled to grant it; a website footer or dataset label alone may not establish that.

The current `src/anskar/archive/eligibility.py` only admits the expired-term route with sourced death-year evidence. Supporting author permissions, open licences or dedications requires an explicit additional rights basis in project policy, storage and validation. Rights status should remain `documented`, not `verified`.

Recommendation: first build a varied batch from original-language older collections, with author-level evidence reused and each poem's provenance retained. Add contemporary licensed poems through a separate documented route. For variety, consider choosing an eligible author first, then an unused poem, rather than letting a single prolific author dominate a random draw from all poems. This is a proposed future change, not implemented here.

## Verification

Read-only database queries and source-code inspection established the local counts and importer limitation. Online sources were inspected on 24 October 2026. This research did not perform poem-by-poem clearance. No application code changed; tests and publishing commands were not run. Imported count: zero.

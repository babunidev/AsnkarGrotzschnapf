# Poetry collection — 24 October 2026

Added **300 complete English poems by 11 authors**. The live archive now holds **308 poems**, with **300 unused eligible poems**. Existing poems, selection history and artwork records were preserved.

## Authors

| Author | Added |
|---|---:|
| Edward Thomas | 33 |
| Frances Ellen Watkins Harper | 35 |
| James McIntyre | 35 |
| James Weldon Johnson | 35 |
| Matthew Arnold | 34 |
| Oscar Wilde | 8 |
| Robert Louis Stevenson | 35 |
| Sara Teasdale | 32 |
| Voltairine de Cleyre | 7 |
| W. B. Yeats | 34 |
| Wilfred Owen | 12 |

## Files

- Importable collection: `data/collections/varied-public-domain-2026-10-24.json`.
- Full reading copy: `data/collections/varied-public-domain-2026-10-24.md`.
- Retained source evidence: `data/sources/poetry-expansion-2026-10-24/`.
- Backup: `data/backups/archive-before-poetry-expansion-20261024T123224.sqlite`.

## Sources and limits

Texts come from Standard Ebooks (268 poems) and Project Gutenberg (32 poems). Poem Index and Past Poetry helped identify the upstream collections. This is not a claim that every researched provider supplied poems: PoetryDB and Litteraturbanken downloads were blocked; the large third-party dataset lacked sufficient per-poem evidence; contemporary dedicated/licensed material needs a separate supported rights basis; Jackson and Poetry in Translation still need commercial permission. See task 023 and the research note. No permission-only poem was marked cleared.

Each imported entry cites a sourced author death year and records the expired Swedish economic term as its rights basis. Status is `documented`, never `verified`. Titles and verse were checked for duplicates. Long poems were excluded as whole works, not shortened.

## Validation

- Complete suite: **250 tests passed**. The initial sandbox run could not open localhost sockets in three pre-existing tests; rerunning with local socket access passed.
- All 300 verse bodies compared against retained source text and stanza/line structure.
- All 300 fit the actual Instagram caption composer with the full poem and shop link.
- Live import: **300 imported, 0 rejected**.
- Re-import: **0 imported, 300 duplicates, 0 rejected**.
- Original eight poems and existing history/artwork records compared unchanged with the backup.
- No generation, publication, or manual poem selection was performed.

The 300 newly eligible poems are available to the existing daily pipeline. No decision is needed to use this batch; the excluded permission-based sources remain future work.

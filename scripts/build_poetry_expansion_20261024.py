"""Rebuild this dated collection offline from the retained source snapshots.

No network calls and no database writes. XHTML verse lines become text lines;
paragraphs become stanzas and the edition's iN indentation becomes 4*N spaces.
The entire verse of each selected article is retained. Editorial notes, dates,
and subtitles are recorded separately rather than silently included as verse.
"""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/sources/poetry-expansion-2026-10-24"
OUTPUT = ROOT / "data/collections/varied-public-domain-2026-10-24.json"
H = "{http://www.w3.org/1999/xhtml}"
EP = "{http://www.idpf.org/2007/ops}type"
DC = "{http://purl.org/dc/elements/1.1/}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
NS = {"d": "http://purl.org/dc/terms/", "p": "http://www.gutenberg.org/2009/pgterms/"}
ON = date(2026, 10, 24)
AUTHORS = [
    ("james-mcintyre", "James McIntyre", 36068, "McIntyre, James", "mcintyre"),
    ("frances-ellen-watkins-harper", "Frances Ellen Watkins Harper", 69249, "Harper, Frances Ellen Watkins", None),
    ("edward-thomas", "Edward Thomas", 22423, "Thomas, Edward", None),
    ("james-weldon-johnson", "James Weldon Johnson", 17884, "Johnson, James Weldon", None),
    ("voltairine-de-cleyre", "Voltairine de Cleyre", 43098, "De Cleyre, Voltairine", None),
    ("robert-louis-stevenson", "Robert Louis Stevenson", 441, "Stevenson, Robert Louis", None),
    ("oscar-wilde", "Oscar Wilde", 1057, "Wilde, Oscar", None),
    ("wilfred-owen", "Wilfred Owen", 1034, "Owen, Wilfred", None),
    ("matthew-arnold", "Matthew Arnold", 27739, "Arnold, Matthew", None),
    ("w-b-yeats", "W. B. Yeats", 49608, "Yeats, W. B. (William Butler)", None),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text).casefold() if c.isalnum())


def record(title, author, pg_id, pg_name, body, url, provenance):
    rdf = ET.parse(SOURCES / f"pg{pg_id}.rdf")
    agents = [a for a in rdf.findall(".//d:creator/p:agent", NS)
              if a.findtext("p:name", namespaces=NS) == pg_name]
    assert len(agents) == 1, (author, pg_id)
    death = int(agents[0].findtext("p:deathdate", namespaces=NS))
    assert death <= ON.year - 71
    citation = f"https://www.gutenberg.org/cache/epub/{pg_id}/pg{pg_id}.rdf"
    return dict(title=title, author=author, author_death_year=death,
                author_death_year_source=citation, origin=None, origin_source=None,
                original_language="en", text_language="en", translator=None,
                translator_death_year=None, translator_death_year_source=None,
                body=body, source_url=url,
                license_name="Swedish economic rights expired (SFS 1960:729 section 43)",
                license_info=(f"Assessed {ON}: {citation} records {pg_name}, died {death}. "
                              f"Under section 43 the economic term has ended (cutoff {ON.year - 71}). "
                              "Original English poem; no translator. US public-domain status alone "
                              "is not the Swedish rights basis. Only the complete poem's verse is "
                              "included, not ebook introductions, illustrations or editorial notes. "
                              + provenance["rights_note"]),
                rights_verification_status="documented", source_provenance=provenance)


def se_candidates(slug, author, pg_id, pg_name, alias):
    path = SOURCES / (f"{alias}.xhtml" if alias else f"{slug}-text-poetry.xhtml")
    opf = SOURCES / (f"{alias}.opf" if alias else f"{slug}-content.opf")
    meta = ET.parse(opf)
    assert meta.findtext(f".//{DC}creator") == author
    rights = meta.findtext(f".//{DC}rights")
    assert "CC0" in rights
    tree = ET.parse(path)
    parents = {child: parent for parent in tree.iter() for child in parent}
    results = []
    for article in tree.iter(H + "article"):
        if "z3998:poem" not in article.get(EP, ""):
            continue
        if any(e.tag in (H + "article", H + "section", H + "a", H + "blockquote")
               or e.get(XML_LANG) for e in article.iter() if e is not article):
            continue
        ancestor = parents.get(article)
        nested = False
        while ancestor is not None:
            if "z3998:poem" in ancestor.get(EP, "") or ancestor.get(XML_LANG, "en").split("-")[0] != "en":
                nested = True
            ancestor = parents.get(ancestor)
        if nested:
            continue
        titles = [e for e in article.iter() if "title" in e.get(EP, "").split()]
        if len(titles) != 1:
            continue
        title = " ".join("".join(titles[0].itertext()).split())
        if re.search(r"fragment|translation|translated|from (?:the )?(?:horace|martial|heine|spanish|french|german)|^continued$", title, re.I):
            continue
        # This separately printed version is also excerpted from Dark Women;
        # leave it out of a collection requiring complete, independent poems.
        if slug == "robert-louis-stevenson" and article.get("id") == "to-you-let-snow-and-roses":
            continue
        if any(c.tag not in {H + x for x in ("h2", "h3", "h4", "header", "hgroup", "p", "footer")}
               for c in article):
            continue
        # Headings with prose bridges/dedications need individual handling.
        if any(e.tag == H + "p" for c in article if c.tag in (H + "header", H + "hgroup")
               for e in c.iter()):
            continue
        stanzas = []
        valid = True
        for p in article.findall(H + "p"):
            if (p.text or "").strip() or not p.findall(H + "span"):
                valid = False
                break
            lines = []
            for child in p:
                if (child.tail or "").strip() or child.tag not in (H + "span", H + "br"):
                    valid = False
                    break
                if child.tag == H + "br":
                    continue
                # Accept only simple typographic inline markup inside verse lines.
                if any(e.tag not in {H + t for t in ("span", "i", "em", "b", "strong", "abbr")}
                       for e in child.iter()):
                    valid = False
                    break
                indent = 0
                for cls in child.get("class", "").split():
                    if not re.fullmatch(r"i\d+", cls):
                        valid = False
                        break
                    indent = int(cls[1:])
                verse = "".join(child.itertext())
                if "\n" in verse or "\t" in verse:
                    valid = False
                    break
                lines.append(" " * (4 * indent) + verse)
            stanzas.append("\n".join(lines))
        body = "\n\n".join(stanzas)
        if not valid or not 80 <= len(body) <= 1400 or len(body.splitlines()) < 4:
            continue
        identifier = article.get("id")
        footer = ["".join(p.itertext()) for f in article.findall(H + "footer") for p in f.findall(H + "p")]
        provenance = dict(provider="Standard Ebooks", source_file=str(path.relative_to(ROOT)),
                          source_sha256=sha(path), article_id=identifier,
                          metadata_file=str(opf.relative_to(ROOT)), metadata_sha256=sha(opf),
                          original_edition_sources=[e.text for e in meta.iter(DC + "source")],
                          footer_metadata=footer, retrieved_on=str(ON),
                          rights_note="Standard Ebooks dedicates its editorial contributions under CC0 1.0, as recorded in the retained content.opf. "
                          "XHTML verse spans and stanza boundaries are transcribed without changing wording or punctuation; iN indentation is rendered as 4*N spaces.")
        url = f"https://standardebooks.org/ebooks/{slug}/poetry/text/poetry.xhtml#{identifier}"
        results.append(record(title, author, pg_id, pg_name, body, url, provenance))
    return results


def teasdale_candidates():
    path = SOURCES / "pg400.txt"
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r"\n{4,}", text)
    results = []
    # These boundaries bracket the two lyric sections, excluding the play,
    # biography, front matter and long dramatic monologues.
    assert chunks[13] == "Love Songs"
    assert chunks[58] == "Sonnets and Lyrics"
    assert chunks[86] == "On the Tower"
    for index in list(range(14, 58)) + list(range(59, 86)):
        chunk = chunks[index]
        if "\n\n\n" not in chunk:
            continue
        heading, body = chunk.split("\n\n\n", 1)
        if "\n" in heading or not 80 <= len(body) <= 1400:
            continue
        title = heading.strip()
        provenance = dict(provider="Project Gutenberg", source_file=str(path.relative_to(ROOT)),
                          source_sha256=sha(path), chunk_index=index, retrieved_on=str(ON),
                          rights_note="Exact complete verse substring from Gutenberg ebook 400 (1911 edition), preserving indentation, punctuation and stanza breaks. CRLF transport newlines become LF; no poem text is shortened or rewritten.")
        results.append(record(title, "Sara Teasdale", 400, "Teasdale, Sara", body,
                              "https://www.gutenberg.org/cache/epub/400/pg400.txt", provenance))
    return results


def build():
    pools = [se_candidates(*a) for a in AUTHORS] + [teasdale_candidates()]
    # Reproducible mixed selection throughout each edition, not its first poems.
    for pool in pools:
        pool.sort(key=lambda p: hashlib.sha256((p["author"] + "\n" + p["title"]).encode()).hexdigest())
    initial = json.loads((ROOT / "data/collections/gutenberg-public-domain.json").read_text())["poems"]
    seen_titles = {(key(p["author"]), key(p["title"])) for p in initial}
    seen_bodies = {key(p["body"]) for p in initial}
    selected = []
    while len(selected) < 300 and any(pools):
        for pool in pools:
            if not pool or len(selected) >= 300:
                continue
            p = pool.pop(0)
            identity = (key(p["author"]), key(p["title"]))
            if identity in seen_titles or key(p["body"]) in seen_bodies:
                continue
            selected.append(p)
            seen_titles.add(identity)
            seen_bodies.add(key(p["body"]))
    assert len(selected) == 300, len(selected)
    return dict(collection_id="varied-public-domain-2026-10-24", assessed_on=str(ON),
                notes="300 complete original-English poems from 11 authors, balanced across authors. Discovery via Poem Index and Past Poetry; texts taken from their upstream Standard Ebooks editions and Project Gutenberg. This collection does not claim clearance of other catalog entries or permission-only sources.",
                poems=selected)


if __name__ == "__main__":
    document = build()
    content = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != content:
        raise SystemExit("Refusing to overwrite a different existing collection.")
    if not OUTPUT.exists():
        OUTPUT.write_text(content, encoding="utf-8")
    print(json.dumps(Counter(p["author"] for p in document["poems"]), indent=2))
    print(f"Total: {len(document['poems'])}; saved {OUTPUT}")

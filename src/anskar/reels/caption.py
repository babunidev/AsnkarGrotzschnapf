"""Caption generation for compilation Reels."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from anskar.reels.errors import ReelError

HASHTAG_FALLBACKS = (
    "#DigitalArt",
    "#ContemporaryArt",
    "#AbstractArt",
    "#OneOfOneArt",
    "#AnskarGrotzschnapf",
)


def load_pack_meta(pack_folder: Path) -> dict[str, object]:
    manifest_path = pack_folder / "manifest.json"
    if not manifest_path.is_file():
        return {"pack_id": pack_folder.name}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pack_id": pack_folder.name}
    if not isinstance(payload, dict):
        return {"pack_id": pack_folder.name}
    rights = payload.get("rights") if isinstance(payload.get("rights"), dict) else {}
    return {
        "pack_id": pack_folder.name,
        "title": rights.get("title") or payload.get("title"),
        "author": rights.get("author") or payload.get("author"),
        "abstraction": payload.get("abstraction"),
        "style_preset": payload.get("style_preset"),
    }


def build_reel_caption(
    pack_folders: list[Path],
    *,
    job_id: str,
    use_ollama: bool = True,
) -> tuple[str, str]:
    """Return (caption, caption_sha256). Prefer Ollama; fall back to a seeded template."""
    metas = [load_pack_meta(folder) for folder in pack_folders]
    titles = [str(m.get("title") or "Untitled") for m in metas]
    authors = sorted({str(m.get("author")) for m in metas if m.get("author")})
    caption = None
    if use_ollama:
        try:
            caption = _ollama_caption(titles=titles, authors=authors)
        except Exception:  # noqa: BLE001
            caption = None
    if not caption:
        caption = _fallback_caption(job_id=job_id, titles=titles, authors=authors)
    caption = caption.strip()
    if "#AnskarGrotzschnapf" not in caption:
        caption = caption.rstrip() + "\n\n" + " ".join(HASHTAG_FALLBACKS)
    digest = hashlib.sha256(caption.encode("utf-8")).hexdigest()
    return caption, digest


def _ollama_caption(*, titles: list[str], authors: list[str]) -> str:
    import os
    import urllib.error
    import urllib.request

    from anskar.interpret import MODEL as OLLAMA_MODEL

    host = os.environ.get("ANSKAR_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    prompt = (
        "Write a short Instagram caption for a compilation Reel of seven one-of-one "
        "digital artworks. Tone: artistic, thoughtful, not salesy. Mention that each "
        "work is a single digital original. Suggest discovering the collection via the "
        "link in the profile. End with up to five hashtags including #AnskarGrotzschnapf. "
        "Do not invent poem text. Works:\n"
        + "\n".join(f"- {title}" for title in titles)
        + ("\nAuthors: " + ", ".join(authors) if authors else "")
    )
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": "You write concise Instagram captions. Plain text only."},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise ReelError(f"Ollama caption failed: {exc}", kind="error") from exc
    message = body.get("message") if isinstance(body, dict) else None
    text = ""
    if isinstance(message, dict):
        text = str(message.get("content") or "")
    cleaned = text.strip()
    if not cleaned:
        raise ReelError("Empty caption from Ollama.", kind="error")
    return cleaned[:2100]


def _fallback_caption(*, job_id: str, titles: list[str], authors: list[str]) -> str:
    seed = int(hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:8], 16)
    openings = (
        "Seven works. Seven fleeting moments.",
        "A quiet sequence of form and light.",
        "Seven singular images, gathered once.",
        "Texture, colour, and pause — seven pieces.",
    )
    middles = (
        "An exploration of form, texture, and imagination.",
        "Each frame stands alone; together they form a brief gallery.",
        "Drawn from poetry into paint, then into this short film.",
    )
    closing = (
        "Each artwork exists as a single digital original, offered once and never reproduced.\n\n"
        "Discover the collection through the link in the profile.\n\n"
        "Anskar Grotzschnapf"
    )
    opening = openings[seed % len(openings)]
    middle = middles[(seed // 3) % len(middles)]
    # Lightly reference titles without dumping all seven.
    sample = ", ".join(titles[:2])
    if len(titles) > 2:
        sample += ", and others"
    author_line = f"\nIncluding works after {authors[0]}." if authors else ""
    body = f"{opening}\n\n{middle}\n\nAmong them: {sample}.{author_line}\n\n{closing}"
    tags = list(HASHTAG_FALLBACKS)
    # Rotate first tag slightly for variety.
    rotate = seed % 3
    tags = tags[rotate:] + tags[:rotate]
    return body + "\n\n" + " ".join(tags)


def caption_matches(remote_caption: object, expected: str) -> bool:
    if not isinstance(remote_caption, str) or not expected:
        return False
    left = _normalize(remote_caption)
    right = _normalize(expected)
    if left == right:
        return True
    # Allow trailing hashtag drift if body matches.
    return left.startswith(right[:120]) or right.startswith(left[:120])


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()

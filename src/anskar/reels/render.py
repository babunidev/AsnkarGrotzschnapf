"""Compile seven artworks into a 9:16 Reel MP4."""

from __future__ import annotations

import hashlib
import random
import shutil
import subprocess
from pathlib import Path

from anskar.reels.errors import ReelError
from anskar.reels.ffmpeg_tools import run_ffmpeg, validate_reel_output
from anskar.reels.ledger import music_dir

TARGET_W = 1080
TARGET_H = 1920
FPS = 30
SEGMENT_SECONDS = 3.0
END_CARD_SECONDS = 2.0
XFADE_SECONDS = 0.4


def resolve_artwork_image(pack_folder: Path) -> Path:
    # Prefer JPEG: some print PNGs carry a misplaced pHYs chunk that makes
    # FFmpeg hang when decoding a looped still.
    for relative in (
        "print/artwork.jpg",
        "etsy/print.jpg",
        "etsy/preview.jpg",
        "print/artwork.png",
        "original/artwork.png",
        "etsy/print.png",
        "etsy/preview.png",
    ):
        candidate = pack_folder / relative
        if candidate.is_file():
            return candidate
    raise ReelError(f"No artwork image found in pack {pack_folder.name}.", kind="media")


def pick_music_file(
    library: Path | None = None,
    *,
    rng: random.Random | None = None,
) -> Path | None:
    """Pick one track at random from the library. Reuse across Reels is fine."""
    root = library if library is not None else music_dir()
    if not root.is_dir():
        return None
    candidates: list[Path] = []
    for pattern in ("*.mp3", "*.ogg", "*.wav", "*.m4a", "*.aac", "*.flac"):
        candidates.extend(root.glob(pattern))
    if not candidates:
        return None
    return (rng or random.SystemRandom()).choice(candidates)


def render_reel(
    pack_folders: list[Path],
    *,
    output: Path,
    job_id: str,
    music: Path | None | object = ...,
) -> dict[str, object]:
    """
    Build 1080x1920 H.264/AAC MP4 with crop, subtle zoom, crossfades, end card.
    Always includes AAC @ 48 kHz (silent if no music).
    """
    if len(pack_folders) != 7:
        raise ReelError("A Reel needs exactly seven pack folders.", kind="error")
    images = [resolve_artwork_image(folder) for folder in pack_folders]
    work = output.parent / f".work-{job_id}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        segments: list[Path] = []
        for index, image in enumerate(images):
            segment = work / f"seg-{index:02d}.mp4"
            _encode_still_segment(image, segment, seed=index)
            segments.append(segment)
        end_card = work / "endcard.png"
        _write_end_card(end_card)
        end_seg = work / "seg-end.mp4"
        _encode_still_segment(end_card, end_seg, seed=99, duration=END_CARD_SECONDS, zoom=False)
        segments.append(end_seg)

        video_only = work / "video.mp4"
        _xfade_concat(segments, video_only)

        music_path: Path | None
        if music is ...:
            music_path = pick_music_file()
        elif music is None:
            music_path = None
        else:
            music_path = Path(music)  # type: ignore[arg-type]

        output.parent.mkdir(parents=True, exist_ok=True)
        _mux_audio(video_only, output, music_path=music_path)
        probe = validate_reel_output(output)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        return {
            "path": str(output),
            "sha256": digest,
            "duration": probe.duration,
            "width": probe.width,
            "height": probe.height,
            "music": str(music_path) if music_path else None,
            "silent_audio": music_path is None,
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _sanitize_still_for_ffmpeg(image: Path, work_dir: Path) -> Path:
    """Rewrite PNG stills to JPEG so looped decode cannot hang on bad metadata."""
    if image.suffix.lower() in {".jpg", ".jpeg"}:
        return image
    cleaned = work_dir / f"{image.stem}-clean.jpg"
    if cleaned.is_file() and cleaned.stat().st_mtime >= image.stat().st_mtime:
        return cleaned
    run_ffmpeg(
        [
            "-i",
            str(image),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(cleaned),
        ],
        timeout=60.0,
    )
    return cleaned


def _encode_still_segment(
    image: Path,
    dest: Path,
    *,
    seed: int,
    duration: float = SEGMENT_SECONDS,
    zoom: bool = True,
) -> None:
    # Subtle Ken Burns: slight zoom over the segment.
    frames = max(int(duration * FPS), 1)
    source = _sanitize_still_for_ffmpeg(image, dest.parent)
    if zoom:
        z_end = 1.04 + (seed % 3) * 0.01
        zoompan = (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W}:{TARGET_H},"
            f"zoompan=z='min(zoom+0.0004\\,{z_end:.3f})':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d={frames}:s={TARGET_W}x{TARGET_H}:fps={FPS}"
        )
    else:
        zoompan = (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W}:{TARGET_H},fps={FPS}"
        )
    run_ffmpeg(
        [
            "-loop",
            "1",
            "-i",
            str(source),
            "-t",
            f"{duration:.2f}",
            "-vf",
            zoompan,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-an",
            "-r",
            str(FPS),
            str(dest),
        ]
    )


def _xfade_concat(segments: list[Path], dest: Path) -> None:
    if len(segments) == 1:
        shutil.copy2(segments[0], dest)
        return
    # Build filter graph of sequential xfades.
    inputs: list[str] = []
    for path in segments:
        inputs.extend(["-i", str(path)])
    n = len(segments)
    filters: list[str] = []
    # Approximate offset: each segment SEGMENT_SECONDS minus xfade (end card may differ).
    current = "0:v"
    offset = SEGMENT_SECONDS - XFADE_SECONDS
    for index in range(1, n):
        out = f"v{index}"
        # Last input may be end card with different duration; offset still accumulates.
        filters.append(
            f"[{current}][{index}:v]xfade=transition=fade:duration={XFADE_SECONDS}:offset={offset:.2f}[{out}]"
        )
        current = out
        if index < n - 1:
            offset += SEGMENT_SECONDS - XFADE_SECONDS
        else:
            offset += END_CARD_SECONDS - XFADE_SECONDS
    filter_complex = ";".join(filters)
    run_ffmpeg(
        [
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{current}]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(dest),
        ],
        timeout=900.0,
    )


def _mux_audio(video: Path, dest: Path, *, music_path: Path | None) -> None:
    # Probe duration of video for silent/music length.
    from anskar.reels.ffmpeg_tools import probe_video

    duration = max(probe_video(video).duration, 1.0)
    if music_path is not None and music_path.is_file():
        run_ffmpeg(
            [
                "-i",
                str(video),
                "-stream_loop",
                "-1",
                "-i",
                str(music_path),
                "-t",
                f"{duration:.2f}",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-af",
                "afade=t=in:st=0:d=1,afade=t=out:st={:.2f}:d=1.5".format(max(duration - 1.5, 0.5)),
                "-shortest",
                "-movflags",
                "+faststart",
                str(dest),
            ]
        )
        return
    # Silent AAC 48 kHz (safeguard 3).
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            f"{duration:.2f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )


def _write_end_card(path: Path) -> None:
    """Dark understated end card via ImageMagick when available, else ffmpeg lavfi."""
    magick = shutil.which("magick") or shutil.which("convert")
    if magick:
        cmd = [
            magick,
            "-size",
            f"{TARGET_W}x{TARGET_H}",
            "xc:#1a1612",
            "-fill",
            "#e8dcc8",
            "-gravity",
            "center",
            "-font",
            "DejaVu-Serif",
            "-pointsize",
            "56",
            "-annotate",
            "+0-40",
            "Anskar Grotzschnapf",
            "-fill",
            "#c4a574",
            "-pointsize",
            "32",
            "-annotate",
            "+0+40",
            "Original Digital Art",
            str(path),
        ]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
            if completed.returncode == 0 and path.is_file():
                return
        except (OSError, subprocess.TimeoutExpired):
            pass
    # Fallback: solid dark frame (branding still present via caption).
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x1a1612:s={TARGET_W}x{TARGET_H}:d=0.1",
            "-frames:v",
            "1",
            str(path),
        ]
    )

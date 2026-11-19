"""FFmpeg / ffprobe helpers for Reel compilation (Azeroth-shaped)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from anskar.reels.errors import ReelError


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise ReelError(
            "ffmpeg/ffprobe not found. Install FFmpeg before rendering Reels.",
            kind="media",
        )


@dataclass(frozen=True)
class VideoProbe:
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool
    video_codec: str
    audio_codec: str


def probe_video(path: Path) -> VideoProbe:
    require_ffmpeg()
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise ReelError(f"ffprobe failed for {path.name}: {exc}", kind="media") from exc
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams") or []
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not vstream:
        raise ReelError(f"No video stream in {path.name}", kind="media")
    width = int(vstream.get("width") or 0)
    height = int(vstream.get("height") or 0)
    if width < 16 or height < 16:
        raise ReelError(f"Video too small: {width}x{height}", kind="media")
    duration = float(data.get("format", {}).get("duration") or vstream.get("duration") or 0)
    fps = _parse_fps(vstream.get("avg_frame_rate") or vstream.get("r_frame_rate") or "30/1")
    return VideoProbe(
        width=width,
        height=height,
        duration=duration,
        fps=fps,
        has_audio=astream is not None,
        video_codec=str(vstream.get("codec_name") or ""),
        audio_codec=str((astream or {}).get("codec_name") or ""),
    )


def run_ffmpeg(argv: list[str], *, timeout: float = 600.0) -> None:
    require_ffmpeg()
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *argv]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReelError(f"ffmpeg failed to start: {exc}", kind="media") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[:500]
        raise ReelError(f"ffmpeg failed: {detail or completed.returncode}", kind="media")


def validate_reel_output(path: Path) -> VideoProbe:
    """ffprobe gate before upload (safeguard 4)."""
    if not path.is_file() or path.stat().st_size < 1000:
        raise ReelError("The rendered Reel file is missing or too small.", kind="media")
    probe = probe_video(path)
    if probe.width != 1080 or probe.height != 1920:
        raise ReelError(
            f"Reel must be 1080x1920, got {probe.width}x{probe.height}.",
            kind="media",
        )
    if probe.video_codec not in {"h264", "avc1"}:
        raise ReelError(f"Reel video codec must be h264, got {probe.video_codec}.", kind="media")
    if not probe.has_audio or probe.audio_codec not in {"aac", "mp4a"}:
        raise ReelError(
            f"Reel must include AAC audio, got has_audio={probe.has_audio} codec={probe.audio_codec}.",
            kind="media",
        )
    if probe.duration < 15 or probe.duration > 45:
        raise ReelError(
            f"Reel duration {probe.duration:.1f}s is outside the expected 15–45s band.",
            kind="media",
        )
    if abs(probe.fps - 30.0) > 2.0:
        raise ReelError(f"Reel fps should be ~30, got {probe.fps:.2f}.", kind="media")
    return probe


def _parse_fps(raw: str) -> float:
    text = str(raw or "30/1")
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            denominator = float(den) or 1.0
            return float(num) / denominator
        except ValueError:
            return 30.0
    try:
        return float(text)
    except ValueError:
        return 30.0

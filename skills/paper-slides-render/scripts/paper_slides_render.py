#!/usr/bin/env python3
"""paper_slides_render.py — canonical helper for the /paper-slides-render SKILL.

Bridges /paper-slides (emits slides/main.pdf + slides/TALK_SCRIPT.md) and
/paper-video (packages a venue-ready MP4). Synthesizes per-slide narration
via edge-tts, rasterizes the PDF via pdftoppm, composes per-slide ffmpeg
segments, concatenates into a single 1080p30 H.264 MP4, and optionally
burns word-aligned subtitles via whisper.

Subcommands
-----------
  preflight   Check edge-tts / pdftoppm / ffmpeg / ffprobe (+ optional whisper)
              and writable output dir.
  parse       Parse TALK_SCRIPT.md into a slide manifest (read-only).
  narrate     Run TTS-only per slide (preview audio without composing video).
  render      Full pipeline: parse + rasterize + TTS + compose + concat.
  verify      Verify a finished narrated MP4 against codec / faststart /
              audio-track / duration-drift gates.

Exit codes
----------
  0   success (or verify with ok=true)
  1   helper-level error (missing dependency, malformed script, bad PDF)
  2   verify gate failed
  3   ffmpeg / TTS / whisper render failed
  4   render halted after TTS: projected duration over --max-seconds (no compose)

Policy A (skill-local gate) per
skills/shared-references/integration-contract.md §2.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_VOICE = "en-US-AvaNeural"
DEFAULT_RESOLUTION = "1920x1080"
DEFAULT_FPS = 30
DEFAULT_DURATION_TOLERANCE = 0.15  # 15% of planned
# Still slides are cut to exactly narration + this tail. A fixed -t (instead of
# ffmpeg's -shortest, which overshoots a looped image by ~2.5s) makes segment
# length deterministic and equal to what the post-TTS duration projection expects.
STILL_TAIL_SECONDS = 0.0

ALLOWED_VIDEO_CODECS = {"h264", "hevc", "av1"}
ALLOWED_AUDIO_CODECS = {"aac", "ac3", "opus"}
REQUIRED_PIXEL_FORMAT = "yuv420p"

SLIDE_HEADER_RE = re.compile(
    # Trailing text after the time bracket (e.g. "(~40 words)", "· 5× [VIDEO: …]")
    # is tolerated and ignored — /paper-slides emits such annotations, so the
    # reader must not choke on them. `[^\n]*$` keeps the match ON the header line
    # (using \s* here would let it swallow the blank line + the quote that follows).
    # Dash class covers hyphen / en-dash / em-dash.
    r"^##\s+Slide\s+(?P<num>\d+)\s*:\s+(?P<title>.+?)\s+\[(?P<start>[\d:]+)\s*[-–—]\s*(?P<end>[\d:]+)\][^\n]*$",
    re.MULTILINE,
)

QUOTE_RE = re.compile(r'"([^"]+)"|“([^”]+)”', re.DOTALL)
TRANSITION_RE = re.compile(r"^\s*→\s*\*?Transition\*?\s*:.*$", re.MULTILINE)
STAGE_RE = re.compile(r"^\s*\*\[[^\]]+\]\*\s*$", re.MULTILINE)
HRULE_RE = re.compile(r"^---\s*$", re.MULTILINE)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
VIDEO_MARKER_RE = re.compile(
    r"^\s*\[VIDEO:\s*(?P<path>[^\]@]+?)"
    r"(?:\s*@\s*(?P<start>[\d:.]+)\s*-\s*(?P<end>[\d:.]+))?"
    r"(?:\s+ON\s+(?P<anchor>[^\]]+?))?"
    r"\s*\]\s*$",
    re.MULTILINE,
)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(payload: dict[str, Any], path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _print_and_dump(payload: dict[str, Any], args: argparse.Namespace, *, stream=None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if stream is None:
        print(text)
    else:
        print(text, file=stream)
    _dump(payload, Path(args.json_out) if args.json_out else None)


def _parse_timestamp(s: str) -> float:
    parts = s.strip().split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError as e:
        raise ValueError(f"invalid timestamp {s!r}: {e}")
    if not nums:
        raise ValueError(f"empty timestamp {s!r}")
    # Last token = seconds; earlier tokens are minutes, hours.
    total = 0.0
    for i, val in enumerate(reversed(nums)):
        total += val * (60 ** i)
    return total


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_edge_tts() -> dict[str, Any]:
    module_present = importlib.util.find_spec("edge_tts") is not None
    cli_path = shutil.which("edge-tts")
    return {
        "python_module": module_present,
        "cli_path": cli_path,
        "available": module_present or bool(cli_path),
    }


def _check_whisper() -> dict[str, Any]:
    module_present = importlib.util.find_spec("whisper") is not None
    cli_path = shutil.which("whisper")
    kind: str | None
    if module_present:
        kind = "python"
    elif cli_path:
        kind = "cli"
    else:
        kind = None
    return {
        "python_module": module_present,
        "cli_path": cli_path,
        "available": module_present or bool(cli_path),
        "kind": kind,
    }


# ── Slide model + parse ──────────────────────────────────────────────────────

@dataclass
class VideoClipRef:
    declared_path: str
    path: str
    trim_start_seconds: float | None = None
    trim_end_seconds: float | None = None
    source_duration_seconds: float | None = None
    effective_duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    exists: bool = False
    # In-place anchor: when set, this clip overlays the still it names at the
    # still's location on the rendered slide (found via template matching),
    # instead of replacing the whole frame. Enables multiple clips per slide.
    anchor_declared: str | None = None
    anchor_path: str | None = None
    anchor_exists: bool = False

    @property
    def is_inplace(self) -> bool:
        return self.anchor_path is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "declared_path": self.declared_path,
            "path": self.path,
            "trim_start_seconds": round(self.trim_start_seconds, 3) if self.trim_start_seconds is not None else None,
            "trim_end_seconds": round(self.trim_end_seconds, 3) if self.trim_end_seconds is not None else None,
            "source_duration_seconds": round(self.source_duration_seconds, 3) if self.source_duration_seconds is not None else None,
            "effective_duration_seconds": round(self.effective_duration_seconds, 3) if self.effective_duration_seconds is not None else None,
            "width": self.width,
            "height": self.height,
            "exists": self.exists,
            "anchor_declared": self.anchor_declared,
            "anchor_path": self.anchor_path,
            "anchor_exists": self.anchor_exists,
        }


@dataclass
class SlideEntry:
    slide_number: int
    title: str
    planned_start_seconds: float
    planned_end_seconds: float
    speakable_text: str
    raw_body: str
    fallback_mode: bool = False
    warnings: list[str] = field(default_factory=list)
    # video_clip holds the single full-frame clip (legacy mode); video_clips
    # holds every clip for the slide. video_mode ∈ {"none","fullframe","inplace"}.
    video_clip: VideoClipRef | None = None
    video_clips: list[VideoClipRef] = field(default_factory=list)
    video_mode: str = "none"
    extra_video_markers: list[str] = field(default_factory=list)

    @property
    def planned_seconds(self) -> float:
        return max(0.0, self.planned_end_seconds - self.planned_start_seconds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_number": self.slide_number,
            "title": self.title,
            "planned_start_seconds": round(self.planned_start_seconds, 3),
            "planned_end_seconds": round(self.planned_end_seconds, 3),
            "planned_seconds": round(self.planned_seconds, 3),
            "speakable_text": self.speakable_text,
            "speakable_preview": (self.speakable_text[:60] + "...") if len(self.speakable_text) > 60 else self.speakable_text,
            "fallback_mode": self.fallback_mode,
            "warnings": list(self.warnings),
            "video_mode": self.video_mode,
            "video_clip": self.video_clip.to_dict() if self.video_clip else None,
            "video_clips": [c.to_dict() for c in self.video_clips],
            "extra_video_markers": list(self.extra_video_markers),
        }


def _strip_markdown(text: str) -> str:
    text = MD_LINK_RE.sub(r"\1", text)
    text = MD_BOLD_RE.sub(r"\1", text)
    text = MD_ITALIC_RE.sub(r"\1", text)
    return text


def _resolve_under(script_dir: Path, declared: str) -> Path:
    return (script_dir / declared).resolve() if not Path(declared).is_absolute() else Path(declared).resolve()


def _build_clip_ref(match: re.Match, script_dir: Path, errors: list[str]) -> VideoClipRef:
    """Turn one VIDEO_MARKER_RE match into a VideoClipRef (trim + anchor parsed)."""
    declared = match.group("path").strip()
    start_str = match.group("start")
    end_str = match.group("end")
    anchor_str = match.group("anchor")

    trim_start: float | None = None
    trim_end: float | None = None
    if start_str is not None and end_str is not None:
        try:
            trim_start = _parse_timestamp(start_str)
            trim_end = _parse_timestamp(end_str)
        except ValueError as e:
            errors.append(f"invalid VIDEO trim range: {e}")
            trim_start, trim_end = None, None
        if trim_start is not None and trim_end is not None:
            if trim_start < 0 or trim_end <= trim_start:
                errors.append(
                    f"invalid VIDEO trim range [{start_str}-{end_str}]: must satisfy 0 ≤ start < end"
                )
                trim_start, trim_end = None, None

    resolved = _resolve_under(script_dir, declared)
    anchor_declared = anchor_path = None
    anchor_exists = False
    if anchor_str is not None:
        anchor_declared = anchor_str.strip()
        anchor_resolved = _resolve_under(script_dir, anchor_declared)
        anchor_path = str(anchor_resolved)
        anchor_exists = anchor_resolved.is_file()

    return VideoClipRef(
        declared_path=declared,
        path=str(resolved),
        trim_start_seconds=trim_start,
        trim_end_seconds=trim_end,
        exists=resolved.is_file(),
        anchor_declared=anchor_declared,
        anchor_path=anchor_path,
        anchor_exists=anchor_exists,
    )


def _extract_video_markers(
    raw_body: str,
    script_dir: Path,
) -> tuple[list[VideoClipRef], str, list[str], list[str]]:
    """Pull VIDEO markers out of a slide body.

    Returns (clips, mode, extra_marker_lines, marker_errors) where mode is one of
    "none" / "fullframe" / "inplace". The caller strips marker lines from the body
    before quoted-speech extraction.

    Mode resolution:
      - any marker carries `ON <still>`  -> "inplace": every anchored clip is kept
        (it overlays its still at the still's location); bare markers are ignored
        as extras.
      - otherwise, first bare marker wins -> "fullframe" (legacy whole-frame swap);
        later markers are ignored as extras.
    """
    matches = list(VIDEO_MARKER_RE.finditer(raw_body))
    if not matches:
        return [], "none", [], []

    errors: list[str] = []
    refs = [_build_clip_ref(m, script_dir, errors) for m in matches]
    anchored = [r for r in refs if r.is_inplace]
    bare = [r for r in refs if not r.is_inplace]

    if anchored:
        extras = [r.declared_path for r in bare]
        return anchored, "inplace", extras, errors

    extras = [r.declared_path for r in bare[1:]]
    return bare[:1], "fullframe", extras, errors


def _strip_video_markers(raw_body: str) -> str:
    return VIDEO_MARKER_RE.sub("", raw_body)


def _extract_speakable(raw_body: str) -> tuple[str, bool]:
    """Return (speakable_text, fallback_mode)."""
    body = _strip_video_markers(raw_body)
    body = TRANSITION_RE.sub("", body)
    body = STAGE_RE.sub("", body)
    quotes: list[str] = []
    for match in QUOTE_RE.finditer(body):
        # group(1) = straight quote, group(2) = curly quote
        captured = match.group(1) if match.group(1) is not None else match.group(2)
        if captured:
            captured = captured.strip()
            if captured:
                quotes.append(captured)
    if quotes:
        joined = " ".join(quotes)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined, False
    # Fallback: strip markdown and use whole body
    stripped = _strip_markdown(body)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped, True


def parse_talk_script(script_path: Path) -> tuple[list[SlideEntry], list[dict[str, Any]]]:
    """Parse the TALK_SCRIPT.md into slides + an errors list.

    Returns (slides, parse_errors). When parse_errors is non-empty the caller
    should treat the parse as failed (exit 1).
    """
    if not script_path.is_file():
        return [], [{"slide_number": None, "line": None, "message": f"talk script not found: {script_path}"}]
    text = script_path.read_text(encoding="utf-8")
    script_dir = script_path.parent
    matches = list(SLIDE_HEADER_RE.finditer(text))
    if not matches:
        return [], [{"slide_number": None, "line": None, "message": "no slide headers found; expected '## Slide N: Title [MM:SS - MM:SS]'"}]

    slides: list[SlideEntry] = []
    errors: list[dict[str, Any]] = []

    for i, match in enumerate(matches):
        slide_num_str = match.group("num")
        title = match.group("title").strip()
        start_str = match.group("start")
        end_str = match.group("end")
        header_line = text[: match.start()].count("\n") + 1

        try:
            slide_num = int(slide_num_str)
        except ValueError:
            errors.append({"slide_number": slide_num_str, "line": header_line, "message": f"invalid slide number {slide_num_str!r}"})
            continue

        try:
            start_s = _parse_timestamp(start_str)
            end_s = _parse_timestamp(end_str)
        except ValueError as e:
            errors.append({"slide_number": slide_num, "line": header_line, "message": str(e)})
            continue

        if end_s <= start_s:
            errors.append({"slide_number": slide_num, "line": header_line, "message": f"end {end_str!r} <= start {start_str!r}"})
            continue

        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        # Truncate body at horizontal rule, if present
        hrule_match = HRULE_RE.search(body)
        if hrule_match:
            body = body[: hrule_match.start()]
        raw_body = body.strip("\n")

        video_clips, video_mode, extras, marker_errors = _extract_video_markers(raw_body, script_dir)
        for me in marker_errors:
            errors.append({"slide_number": slide_num, "line": header_line, "message": me})
        # Legacy single-clip handle: only meaningful in full-frame mode.
        video_clip = video_clips[0] if video_mode == "fullframe" and video_clips else None

        speakable, fallback = _extract_speakable(raw_body)
        warnings: list[str] = []
        if fallback:
            warnings.append("no quoted speech found; using full body as fallback")
        if extras:
            kept = "anchored markers" if video_mode == "inplace" else "first marker wins"
            warnings.append(f"{len(extras)} extra VIDEO marker(s) ignored; {kept}")
        for ref in video_clips:
            if not ref.exists:
                warnings.append(f"VIDEO clip not found at parse time: {ref.path}")
            if ref.is_inplace and not ref.anchor_exists:
                warnings.append(f"VIDEO anchor still not found at parse time: {ref.anchor_path}")
        if not speakable:
            errors.append({"slide_number": slide_num, "line": header_line, "message": "speakable text is empty after extraction"})
            continue

        slides.append(SlideEntry(
            slide_number=slide_num,
            title=title,
            planned_start_seconds=start_s,
            planned_end_seconds=end_s,
            speakable_text=speakable,
            raw_body=raw_body,
            fallback_mode=fallback,
            warnings=warnings,
            video_clip=video_clip,
            video_clips=video_clips,
            video_mode=video_mode,
            extra_video_markers=extras,
        ))

    # Monotonic slide-number check
    if slides:
        for prev, curr in zip(slides, slides[1:]):
            if curr.slide_number <= prev.slide_number:
                errors.append({
                    "slide_number": curr.slide_number,
                    "line": None,
                    "message": f"slide numbers not monotonically increasing (got {curr.slide_number} after {prev.slide_number})",
                })

    if not slides and not errors:
        errors.append({"slide_number": None, "line": None, "message": "no parseable slides found"})
    elif slides and not any(s.speakable_text for s in slides):
        errors.append({"slide_number": None, "line": None, "message": "all slides have empty speakable text"})

    return slides, errors


def _gaps_between_slides(slides: list[SlideEntry]) -> list[dict[str, float]]:
    gaps: list[dict[str, float]] = []
    for prev, curr in zip(slides, slides[1:]):
        gap = curr.planned_start_seconds - prev.planned_end_seconds
        if abs(gap) > 0.05:
            gaps.append({
                "after_slide": float(prev.slide_number),
                "before_slide": float(curr.slide_number),
                "gap_seconds": round(gap, 3),
            })
    return gaps


# ── ffprobe ────────────────────────────────────────────────────────────────────

def _ffprobe_streams(video: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt:format=duration,size,format_name,start_time",
        "-of", "json", str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"ffprobe failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def _has_faststart(video: Path) -> bool:
    try:
        with video.open("rb") as f:
            head = f.read(262144)
    except OSError:
        return False
    moov = head.find(b"moov")
    mdat = head.find(b"mdat")
    if moov == -1:
        return False
    if mdat == -1:
        return True
    return moov < mdat


def _ffprobe_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return 0.0
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def _probe_clip(clip_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Probe a video clip for duration/dimensions/audio-track presence.

    Returns ({duration, width, height, video_codec, has_audio_track}, error).
    """
    if not clip_path.is_file():
        return None, f"clip not found: {clip_path}"
    try:
        info = _ffprobe_streams(clip_path)
    except SystemExit as e:
        return None, str(e)
    fmt = info.get("format", {}) or {}
    try:
        duration = float(fmt.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    streams = info.get("streams", []) or []
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if vstream is None:
        return None, f"no video stream in clip: {clip_path}"
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "duration": duration,
        "width": int(vstream.get("width") or 0),
        "height": int(vstream.get("height") or 0),
        "video_codec": vstream.get("codec_name") or "",
        "has_audio_track": astream is not None,
    }, None


# ── Preflight ─────────────────────────────────────────────────────────────────

def cmd_preflight(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    out_dir = _render_root(workspace)

    edge_tts_info = _check_edge_tts()
    pdftoppm = shutil.which("pdftoppm")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    whisper_info = _check_whisper() if args.with_subtitles else {"python_module": False, "cli_path": None, "available": False, "kind": None}

    can_write = False
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        probe = out_dir / ".paper_slides_render_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        can_write = True
    except OSError:
        can_write = False

    warnings: list[str] = []
    whisper_required_missing = bool(args.with_subtitles) and not whisper_info["available"]

    # Optional clip probing when --talk-script is provided
    clips_info: list[dict[str, Any]] = []
    clip_errors: list[str] = []
    if args.talk_script:
        script_path = Path(args.talk_script).resolve()
        slides, parse_errors = parse_talk_script(script_path)
        if parse_errors:
            for pe in parse_errors:
                clip_errors.append(
                    f"talk script parse error (slide {pe.get('slide_number')}): {pe.get('message')}"
                )
        for slide in slides:
            for ref in slide.video_clips:
                clip_path = Path(ref.path)
                probe_info, probe_err = (None, None) if not ffprobe else _probe_clip(clip_path)
                entry: dict[str, Any] = {
                    "slide_number": slide.slide_number,
                    "mode": "inplace" if ref.is_inplace else slide.video_mode,
                    "declared_path": ref.declared_path,
                    "path": ref.path,
                    "exists": clip_path.is_file(),
                    "anchor_declared": ref.anchor_declared,
                    "anchor_path": ref.anchor_path,
                    "anchor_exists": ref.anchor_exists,
                    "trim_start_seconds": ref.trim_start_seconds,
                    "trim_end_seconds": ref.trim_end_seconds,
                    "source_duration_seconds": None,
                    "effective_duration_seconds": None,
                    "width": None,
                    "height": None,
                    "video_codec": None,
                    "has_audio_track": None,
                    "probe_error": probe_err,
                }
                if probe_info:
                    entry.update({
                        "source_duration_seconds": round(probe_info["duration"], 3),
                        "width": probe_info["width"],
                        "height": probe_info["height"],
                        "video_codec": probe_info["video_codec"],
                        "has_audio_track": probe_info["has_audio_track"],
                    })
                    # Trim bounds validation
                    if ref.trim_start_seconds is not None and ref.trim_end_seconds is not None:
                        if ref.trim_end_seconds > probe_info["duration"] + 0.01:
                            clip_errors.append(
                                f"slide {slide.slide_number}: VIDEO trim_end ({ref.trim_end_seconds:.2f}s) > source_duration ({probe_info['duration']:.2f}s) for {ref.declared_path}"
                            )
                            entry["effective_duration_seconds"] = None
                        else:
                            entry["effective_duration_seconds"] = round(ref.trim_end_seconds - ref.trim_start_seconds, 3)
                    else:
                        entry["effective_duration_seconds"] = round(probe_info["duration"], 3)
                elif probe_err:
                    clip_errors.append(f"slide {slide.slide_number}: clip probe failed: {probe_err}")
                elif not clip_path.is_file():
                    clip_errors.append(f"slide {slide.slide_number}: clip not found: {ref.path}")
                # In-place anchor must exist, else we can't locate the overlay box.
                if ref.is_inplace and not ref.anchor_exists:
                    clip_errors.append(f"slide {slide.slide_number}: VIDEO anchor still not found: {ref.anchor_path}")
                clips_info.append(entry)

    required_ok = bool(edge_tts_info["available"]) and bool(pdftoppm) and bool(ffmpeg) and bool(ffprobe) and can_write
    ok = required_ok and not clip_errors and not whisper_required_missing

    payload: dict[str, Any] = {
        "ok": ok,
        "workspace": str(workspace),
        "edge_tts": edge_tts_info,
        "pdftoppm": pdftoppm,
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "whisper": whisper_info,
        "outputDir": str(out_dir),
        "outputDirWritable": can_write,
        "withSubtitles": bool(args.with_subtitles),
        "talkScript": str(Path(args.talk_script).resolve()) if args.talk_script else None,
        "clips": clips_info,
        "warnings": warnings,
        "checkedAt": _now(),
    }

    errors: list[str] = []
    if not edge_tts_info["available"]:
        errors.append("edge-tts not found (pip install edge-tts)")
    if not pdftoppm:
        errors.append("pdftoppm not on PATH (apt-get install poppler-utils / brew install poppler)")
    if not ffmpeg:
        errors.append("ffmpeg not on PATH (apt-get install ffmpeg / brew install ffmpeg)")
    if not ffprobe:
        errors.append("ffprobe not on PATH (usually shipped with ffmpeg)")
    if not can_write:
        errors.append(f"output directory not writable: {out_dir}")
    if whisper_required_missing:
        errors.append(
            "--with-subtitles was requested but whisper is not available "
            "(pip install openai-whisper, or drop --with-subtitles)"
        )
    errors.extend(clip_errors)
    if errors:
        payload["error"] = "; ".join(errors)

    _print_and_dump(payload, args)
    return 0 if ok else 1


# ── Parse ─────────────────────────────────────────────────────────────────────

def _pdf_page_count(pdf: Path) -> tuple[int, str | None]:
    """Return (page_count, error_message). Page count is 0 on error."""
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        proc = subprocess.run([pdfinfo, str(pdf)], capture_output=True, text=True)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if line.startswith("Pages:"):
                    try:
                        return int(line.split(":", 1)[1].strip()), None
                    except ValueError:
                        pass
        return 0, f"pdfinfo failed: {proc.stderr.strip()}"
    # Fall back: count pdftoppm's -l with a huge number — but cheaper to use
    # subprocess on pdftoppm -h-? Skip the fallback; if pdfinfo missing, return
    # 0 with a warning so caller can decide.
    return 0, "pdfinfo not on PATH; cannot count PDF pages"


def cmd_parse(args: argparse.Namespace) -> int:
    script_path = Path(args.talk_script).resolve()
    pdf_path = Path(args.slides_pdf).resolve() if args.slides_pdf else None

    slides, errors = parse_talk_script(script_path)

    pdf_pages = 0
    pdf_warning: str | None = None
    if pdf_path is not None:
        if not pdf_path.is_file():
            pdf_warning = f"slides PDF not found: {pdf_path}"
        else:
            pdf_pages, err = _pdf_page_count(pdf_path)
            if err:
                pdf_warning = err

    gaps = _gaps_between_slides(slides) if slides else []

    ok = not errors

    payload: dict[str, Any] = {
        "ok": ok,
        "talk_script": str(script_path),
        "slides_pdf": str(pdf_path) if pdf_path else None,
        "slide_count": len(slides),
        "pdf_page_count": pdf_pages,
        "pdf_warning": pdf_warning,
        "slides": [s.to_dict() for s in slides],
        "gaps_seconds": gaps,
        "parse_errors": errors,
        "fallback_mode_slides": [s.slide_number for s in slides if s.fallback_mode],
        "totals": {
            "planned_seconds": round(sum(s.planned_seconds for s in slides), 3),
        },
        "checkedAt": _now(),
    }

    _print_and_dump(payload, args, stream=None if ok else sys.stderr)
    return 0 if ok else 1


# ── Narrate (TTS) ─────────────────────────────────────────────────────────────

def _render_root(workspace: Path) -> Path:
    """Resolve the render output root, tolerating `workspace` being EITHER the
    paper dir (which contains a slides/ subdir) OR the slides dir itself.

    Without this, invoking with the slides dir as workspace produced a doubled
    `slides/slides/render` path. We detect the slides dir by the presence of
    main.pdf / TALK_SCRIPT.md, or a basename of "slides".
    """
    # Discriminate on TALK_SCRIPT.md, NOT main.pdf: the paper dir also contains a
    # main.pdf (the paper itself), so only the talk script reliably marks where the
    # slides live. Check the paper-dir shape (slides/TALK_SCRIPT.md) first.
    sub = workspace / "slides"
    if sub.is_dir() and ((sub / "TALK_SCRIPT.md").is_file() or (sub / "main.pdf").is_file()):
        return sub / "render"            # workspace is the paper dir
    if (workspace / "TALK_SCRIPT.md").is_file() or workspace.name == "slides":
        return workspace / "render"      # workspace is the slides dir itself
    if sub.is_dir():
        return sub / "render"            # has a slides/ subdir but no clear marker
    return workspace / "slides" / "render"  # legacy default


def _audio_paths(workspace: Path, slide_number: int) -> tuple[Path, Path]:
    audio_dir = _render_root(workspace) / "audio"
    wav = audio_dir / f"slide_{slide_number:02d}.wav"
    meta = audio_dir / f"slide_{slide_number:02d}.meta.json"
    return wav, meta


def _content_hash(voice: str, text: str, rate: str | None = None) -> str:
    data: dict[str, Any] = {"voice": voice, "text": text}
    if rate:  # only perturb the hash when a rate is actually set (keeps old caches valid)
        data["rate"] = rate
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return "sha256:" + _sha256_bytes(payload.encode("utf-8"))


def _read_meta(meta_path: Path) -> dict[str, Any] | None:
    if not meta_path.is_file():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_meta(meta_path: Path, payload: dict[str, Any]) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = meta_path.with_suffix(meta_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(meta_path)


def _edge_tts_synthesize(text: str, voice: str, out_wav: Path, retries: int = 1, rate: str | None = None) -> tuple[bool, str | None]:
    """Synthesize via edge-tts CLI to out_wav (atomic). Returns (ok, error).

    `rate` is an optional edge-tts speed delta like "+10%" / "-5%" — the natural
    remedy when a deck overruns its time budget without rewriting the prose.
    """
    cli = shutil.which("edge-tts")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out_wav.with_suffix(out_wav.suffix + ".tmp")
    last_err: str | None = None
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            if cli:
                cmd = [cli, "--voice", voice, "--text", text, "--write-media", str(tmp_out)]
                if rate:
                    cmd += ["--rate", rate]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode == 0 and tmp_out.is_file() and tmp_out.stat().st_size > 0:
                    tmp_out.replace(out_wav)
                    return True, None
                last_err = (proc.stderr or proc.stdout or "edge-tts failed").strip()
            else:
                # Module fallback: run a tiny embedded script via python3 -c.
                py = (
                    "import asyncio, sys, edge_tts;"
                    "txt=sys.argv[1]; v=sys.argv[2]; p=sys.argv[3]; r=sys.argv[4];"
                    "async def m():\n"
                    "    c=edge_tts.Communicate(txt, v, rate=r) if r else edge_tts.Communicate(txt, v);\n"
                    "    await c.save(p)\n"
                    "asyncio.run(m())"
                )
                cmd = [sys.executable, "-c", py, text, voice, str(tmp_out), rate or ""]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode == 0 and tmp_out.is_file() and tmp_out.stat().st_size > 0:
                    tmp_out.replace(out_wav)
                    return True, None
                last_err = (proc.stderr or proc.stdout or "edge-tts module failed").strip()
        except subprocess.TimeoutExpired:
            last_err = "edge-tts timed out after 120s"
        except OSError as e:
            last_err = f"edge-tts subprocess error: {e}"
        if attempt < attempts - 1:
            time.sleep(2.0)
    if tmp_out.exists():
        try:
            tmp_out.unlink()
        except OSError:
            pass
    return False, last_err


def _narrate_slides(
    slides: list[SlideEntry],
    voice: str,
    workspace: Path,
    rate: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Synthesize per-slide audio with content-hash caching.

    Returns (per_slide_results, per_slide_errors).
    """
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for slide in slides:
        wav, meta = _audio_paths(workspace, slide.slide_number)
        chash = _content_hash(voice, slide.speakable_text, rate)
        cached_meta = _read_meta(meta)
        cached = (
            wav.is_file()
            and wav.stat().st_size > 0
            and cached_meta is not None
            and cached_meta.get("content_hash") == chash
            and cached_meta.get("voice") == voice
        )
        if not cached:
            ok, err = _edge_tts_synthesize(slide.speakable_text, voice, wav, rate=rate)
            if not ok:
                errors.append({
                    "slide_number": slide.slide_number,
                    "tts_error": err or "unknown",
                })
                results.append({
                    "slide_number": slide.slide_number,
                    "audio_path": str(wav),
                    "duration_seconds": 0.0,
                    "cached": False,
                    "voice": voice,
                    "content_hash": chash,
                    "ok": False,
                })
                continue
            _write_meta(meta, {
                "voice": voice,
                "rate": rate,
                "content_hash": chash,
                "generated_at": _now(),
                "speakable_chars": len(slide.speakable_text),
            })
        duration = _ffprobe_duration(wav)
        results.append({
            "slide_number": slide.slide_number,
            "audio_path": str(wav),
            "duration_seconds": round(duration, 3),
            "cached": cached,
            "voice": voice,
            "content_hash": chash,
            "ok": True,
        })
    return results, errors


def cmd_narrate(args: argparse.Namespace) -> int:
    script_path = Path(args.talk_script).resolve()
    workspace = Path(args.workspace).resolve()
    voice = args.voice or DEFAULT_VOICE

    slides, parse_errors = parse_talk_script(script_path)
    if parse_errors:
        payload = {
            "ok": False,
            "talk_script": str(script_path),
            "parse_errors": parse_errors,
            "checkedAt": _now(),
        }
        _print_and_dump(payload, args, stream=sys.stderr)
        return 1

    results, errors = _narrate_slides(slides, voice, workspace)

    ok = not errors
    payload = {
        "ok": ok,
        "talk_script": str(script_path),
        "voice": voice,
        "workspace": str(workspace),
        "slides": results,
        "tts_errors": errors,
        "checkedAt": _now(),
    }
    _print_and_dump(payload, args, stream=None if ok else sys.stderr)
    return 0 if ok else 1


# ── Render: rasterize + whisper + compose + concat ───────────────────────────

def _rasterize_pdf(pdf: Path, slide_count: int, workspace: Path) -> tuple[list[Path], str | None]:
    png_dir = _render_root(workspace) / "png"
    png_dir.mkdir(parents=True, exist_ok=True)
    pdf_mtime = pdf.stat().st_mtime
    paths: list[Path] = []
    for n in range(1, slide_count + 1):
        out = png_dir / f"slide_{n:02d}.png"
        cached = out.is_file() and out.stat().st_mtime >= pdf_mtime
        if not cached:
            # pdftoppm writes <prefix>-<N>.png by default; we use -singlefile
            # so the output goes directly to <prefix>.png.
            prefix = png_dir / f"slide_{n:02d}"
            cmd = [
                "pdftoppm", "-r", "144", "-png", "-singlefile",
                "-f", str(n), "-l", str(n), str(pdf), str(prefix),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return [], f"pdftoppm failed on page {n}: {proc.stderr.strip()[-800:]}"
            if not out.is_file():
                # Some pdftoppm versions append -1 even with -singlefile when -f/-l is set.
                alt = png_dir / f"slide_{n:02d}-1.png"
                if alt.is_file():
                    alt.replace(out)
            if not out.is_file():
                return [], f"pdftoppm produced no PNG for page {n}"
        paths.append(out)
    return paths, None


def _whisper_align(
    audio_wav: Path,
    output_dir: Path,
    model_name: str = "base.en",
) -> tuple[Path | None, str | None]:
    """Run whisper, return (per-slide srt path, error)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cli = shutil.which("whisper")
    if cli:
        cmd = [
            cli, str(audio_wav),
            "--model", model_name,
            "--word_timestamps", "True",
            "--output_format", "srt",
            "--output_dir", str(output_dir),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            return None, (proc.stderr or proc.stdout or "whisper failed").strip()[-800:]
        srt = output_dir / (audio_wav.stem + ".srt")
        if srt.is_file():
            return srt, None
        return None, f"whisper produced no SRT for {audio_wav.name}"
    # Module fallback
    if importlib.util.find_spec("whisper") is None:
        return None, "whisper not available"
    py = (
        "import sys, json, whisper;"
        "p=sys.argv[1]; o=sys.argv[2]; m=sys.argv[3];"
        "model=whisper.load_model(m);"
        "r=model.transcribe(p, word_timestamps=True);"
        "import os; out=os.path.join(o, os.path.splitext(os.path.basename(p))[0]+'.srt');"
        "import datetime;"
        "def fmt(t):\n"
        "    ms=int((t-int(t))*1000); s=int(t)%60; m=(int(t)//60)%60; h=int(t)//3600;\n"
        "    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'\n"
        "lines=[]\n"
        "for i,seg in enumerate(r.get('segments') or [], start=1):\n"
        "    lines.append(str(i))\n"
        "    lines.append(fmt(seg['start'])+' --> '+fmt(seg['end']))\n"
        "    lines.append(seg['text'].strip())\n"
        "    lines.append('')\n"
        "open(out,'w',encoding='utf-8').write('\\n'.join(lines))"
    )
    cmd = [sys.executable, "-c", py, str(audio_wav), str(output_dir), model_name]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or "whisper module failed").strip()[-800:]
    srt = output_dir / (audio_wav.stem + ".srt")
    if srt.is_file():
        return srt, None
    return None, f"whisper module produced no SRT for {audio_wav.name}"


def _srt_offset(srt_path: Path, offset_seconds: float) -> str:
    """Read an SRT file and shift every cue by offset_seconds. Return the body."""
    text = srt_path.read_text(encoding="utf-8")
    def shift(match: re.Match) -> str:
        def to_secs(s: str) -> float:
            hh, mm, rest = s.split(":")
            ss, ms = rest.split(",")
            return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0
        def to_str(t: float) -> str:
            ms = int(round((t - int(t)) * 1000))
            s = int(t) % 60
            m = (int(t) // 60) % 60
            h = int(t) // 3600
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        a, b = match.group(1), match.group(2)
        return f"{to_str(to_secs(a) + offset_seconds)} --> {to_str(to_secs(b) + offset_seconds)}"
    return re.sub(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", shift, text)


def _merge_srts(per_slide: list[tuple[Path, float]], merged: Path) -> str | None:
    """Merge per-slide (srt_path, offset) into a single SRT at merged. Returns error."""
    chunks: list[str] = []
    counter = 1
    for srt_path, offset in per_slide:
        body = _srt_offset(srt_path, offset)
        # Renumber cue indices to be globally unique
        out_lines: list[str] = []
        block: list[str] = []
        for line in body.splitlines():
            if line.strip() == "":
                if block:
                    if block[0].strip().isdigit():
                        block[0] = str(counter)
                        counter += 1
                    out_lines.extend(block)
                    out_lines.append("")
                    block = []
                else:
                    out_lines.append("")
            else:
                block.append(line)
        if block:
            if block[0].strip().isdigit():
                block[0] = str(counter)
                counter += 1
            out_lines.extend(block)
            out_lines.append("")
        chunks.append("\n".join(out_lines))
    merged.parent.mkdir(parents=True, exist_ok=True)
    tmp = merged.with_suffix(merged.suffix + ".tmp")
    tmp.write_text("\n".join(chunks), encoding="utf-8")
    tmp.replace(merged)
    return None


def _locate_anchor_box(
    slide_bgr,
    anchor_bgr,
    min_score: float = 0.45,
) -> tuple[tuple[int, int, int, int] | None, float | None]:
    """Find where `anchor_bgr` (a still that appears on the slide) sits on the
    rendered slide, via multi-scale normalized cross-correlation.

    The still is placed on the slide at a size decided by LaTeX (\\includegraphics
    [height=...]); we don't know that size, so we sweep template heights from 6%
    to 30% of the slide height and keep the best-correlating placement.

    Returns ((x, y, w, h), score) in slide-pixel space, or (None, best_score) if
    nothing clears `min_score`.
    """
    import cv2  # lazy: only needed for in-place mode

    sh, sw = slide_bgr.shape[:2]
    ah, aw = anchor_bgr.shape[:2]
    if ah < 2 or aw < 2:
        return None, None
    slide_gray = cv2.cvtColor(slide_bgr, cv2.COLOR_BGR2GRAY)
    anchor_gray = cv2.cvtColor(anchor_bgr, cv2.COLOR_BGR2GRAY)

    best: tuple[float, int, int, int, int] | None = None
    # Sweep target heights in pixels; step keeps this ~60 matchTemplate calls.
    for frac in range(60, 301, 4):
        th = int(round(sh * frac / 1000.0))
        if th < 16:
            continue
        scale = th / ah
        tw = int(round(aw * scale))
        if tw < 16 or tw >= sw or th >= sh:
            continue
        tmpl = cv2.resize(anchor_gray, (tw, th), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(slide_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv2.minMaxLoc(res)
        if best is None or maxv > best[0]:
            best = (float(maxv), int(maxloc[0]), int(maxloc[1]), tw, th)

    if best is None:
        return None, None
    if best[0] < min_score:
        return None, best[0]
    return (best[1], best[2], best[3], best[4]), best[0]


def _ffmpeg_compose_inplace_slide(
    slide_png: Path,
    clips: list[VideoClipRef],
    wav: Path,
    out_mp4: Path,
    width: int,
    height: int,
    fps: int,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Compose a slide segment that overlays each anchored clip onto the still it
    names, at that still's location on the rendered slide. The rasterized slide is
    the background, so the slide's own title/captions/layout are preserved and only
    the named thumbnails come alive.

    Policy mirrors the full-frame composer: clip audio muted; narration is the only
    audio; each clip loops to fill; total = max(narration, longest clip effective).

    Returns (ok, info, error).
    """
    try:
        import cv2  # lazy: only needed for in-place mode
    except ImportError:
        return False, None, "in-place VIDEO overlay needs opencv-python (pip install opencv-python-headless)"

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    slide_img = cv2.imread(str(slide_png))
    if slide_img is None:
        return False, None, f"could not read slide raster {slide_png}"
    bg = cv2.resize(slide_img, (width, height), interpolation=cv2.INTER_AREA)

    placements: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for clip in clips:
        probe_info, probe_err = _probe_clip(Path(clip.path))
        if probe_info is None:
            return False, None, probe_err or f"clip probe failed: {clip.path}"
        if clip.trim_start_seconds is not None and clip.trim_end_seconds is not None:
            if clip.trim_end_seconds > probe_info["duration"] + 0.01:
                return False, None, (
                    f"VIDEO trim_end ({clip.trim_end_seconds:.2f}s) > source_duration "
                    f"({probe_info['duration']:.2f}s) for {clip.declared_path}"
                )
            effective = max(0.001, clip.trim_end_seconds - clip.trim_start_seconds)
        else:
            effective = max(0.001, float(probe_info["duration"]))

        anchor_img = cv2.imread(clip.anchor_path) if clip.anchor_path else None
        if anchor_img is None:
            unmatched.append({"clip": Path(clip.path).name, "anchor": clip.anchor_declared, "reason": "anchor unreadable", "score": None})
            continue
        box, score = _locate_anchor_box(bg, anchor_img)
        if box is None:
            unmatched.append({"clip": Path(clip.path).name, "anchor": clip.anchor_declared, "reason": "no confident match", "score": round(score, 3) if score else None})
            continue
        placements.append({"clip": clip, "box": box, "effective": effective, "score": score})

    narration_dur = _ffprobe_duration(wav)
    if narration_dur <= 0.0:
        return False, None, f"failed to probe narration duration for {wav}"
    total = max(narration_dur, max((p["effective"] for p in placements), default=0.0))

    # Background still scaled to exact output size; fed to ffmpeg as a looped image.
    bg_path = out_mp4.parent / f"{out_mp4.stem}_bg.png"
    if not cv2.imwrite(str(bg_path), bg):
        return False, None, f"could not write background raster {bg_path}"

    cmd: list[str] = ["ffmpeg", "-y", "-loop", "1", "-t", f"{total:.3f}", "-i", str(bg_path)]
    for p in placements:
        clip = p["clip"]
        cmd += ["-stream_loop", "-1"]
        if clip.trim_start_seconds is not None and clip.trim_end_seconds is not None:
            cmd += ["-ss", f"{clip.trim_start_seconds:.3f}", "-to", f"{clip.trim_end_seconds:.3f}"]
        cmd += ["-i", str(clip.path)]
    cmd += ["-i", str(wav)]
    wav_idx = 1 + len(placements)

    parts = [f"[0:v]scale={width}:{height},setsar=1,fps={fps},format=yuv420p[bg0]"]
    cur = "bg0"
    for i, p in enumerate(placements, start=1):
        x, y, w, h = p["box"]
        nxt = f"t{i}"
        parts.append(f"[{i}:v]scale={w}:{h},setsar=1[c{i}]")
        parts.append(f"[{cur}][c{i}]overlay={x}:{y}[{nxt}]")
        cur = nxt
    parts.append(f"[{wav_idx}:a]apad=whole_dur={total:.3f}[a]")
    filt = ";".join(parts)

    cmd += [
        "-filter_complex", filt,
        "-map", f"[{cur}]", "-map", "[a]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(out_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, None, (proc.stderr or proc.stdout or "ffmpeg in-place compose failed").strip()[-1500:]

    info = {
        "mode": "inplace",
        "narration_seconds": round(narration_dur, 3),
        "total_seconds": round(total, 3),
        "overlays": [
            {
                "clip": Path(p["clip"].path).name,
                "anchor": p["clip"].anchor_declared,
                "box": list(p["box"]),
                "match_score": round(p["score"], 3) if p["score"] is not None else None,
                "effective_seconds": round(p["effective"], 3),
            }
            for p in placements
        ],
        "unmatched": unmatched,
    }
    return True, info, None


def _ffmpeg_compose_slide(
    png: Path,
    wav: Path,
    out_mp4: Path,
    width: int,
    height: int,
    fps: int,
) -> tuple[bool, str | None]:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic duration: hold the still for exactly narration + tail. Using a
    # fixed -t (rather than -shortest, which overshoots a looped image by ~2.5s)
    # keeps the segment length predictable and equal to the duration projection.
    seg_dur = max(0.1, _ffprobe_duration(wav) + STILL_TAIL_SECONDS)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(png),
        "-i", str(wav),
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-vf", vf,
        "-t", f"{seg_dur:.3f}",
        str(out_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "ffmpeg failed").strip()[-1200:]
    return True, None


def _ffmpeg_compose_video_slide(
    clip: VideoClipRef,
    wav: Path,
    out_mp4: Path,
    width: int,
    height: int,
    fps: int,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Compose one slide segment from a video clip + narration WAV.

    Policy (user-confirmed):
      - clip source audio is fully muted; narration is the only audio
      - narration > clip: loop the clip, no upper cap
      - clip > narration: pad narration with silence to clip duration

    Returns (ok, info_dict_or_none, error_or_none). info_dict carries the
    measured durations for drift accounting.
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    clip_path = Path(clip.path)
    probe_info, probe_err = _probe_clip(clip_path)
    if probe_info is None:
        return False, None, probe_err or "clip probe failed"

    if clip.trim_start_seconds is not None and clip.trim_end_seconds is not None:
        if clip.trim_end_seconds > probe_info["duration"] + 0.01:
            return False, None, (
                f"VIDEO trim_end ({clip.trim_end_seconds:.2f}s) > source_duration "
                f"({probe_info['duration']:.2f}s) for {clip.declared_path}"
            )
        effective = max(0.001, clip.trim_end_seconds - clip.trim_start_seconds)
    else:
        effective = max(0.001, float(probe_info["duration"]))

    narration_dur = _ffprobe_duration(wav)
    if narration_dur <= 0.0:
        return False, None, f"failed to probe narration duration for {wav}"
    total = max(narration_dur, effective)

    vf = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"fps={fps},format=yuv420p[v];"
        f"[1:a]apad=whole_dur={total:.3f}[a]"
    )
    cmd: list[str] = ["ffmpeg", "-y", "-stream_loop", "-1"]
    if clip.trim_start_seconds is not None and clip.trim_end_seconds is not None:
        cmd += ["-ss", f"{clip.trim_start_seconds:.3f}", "-to", f"{clip.trim_end_seconds:.3f}"]
    cmd += [
        "-i", str(clip_path),
        "-i", str(wav),
        "-filter_complex", vf,
        "-map", "[v]", "-map", "[a]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(out_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, None, (proc.stderr or proc.stdout or "ffmpeg failed").strip()[-1200:]
    info = {
        "narration_seconds": round(narration_dur, 3),
        "clip_effective_seconds": round(effective, 3),
        "clip_source_seconds": round(float(probe_info["duration"]), 3),
        "clip_source_width": probe_info["width"],
        "clip_source_height": probe_info["height"],
        "total_seconds": round(total, 3),
        "loop_factor": round(total / effective, 3) if effective > 0 else None,
    }
    return True, info, None


def _ffmpeg_concat(segments: list[Path], output: Path) -> tuple[bool, str | None]:
    output.parent.mkdir(parents=True, exist_ok=True)
    concat_list = output.parent / "concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p}'" for p in segments) + "\n",
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "ffmpeg concat failed").strip()[-1200:]
    return True, None


def _ffmpeg_burn_subtitles(input_mp4: Path, srt: Path, output: Path, font: str = "DejaVuSans") -> tuple[bool, str | None]:
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = f"subtitles={srt}:force_style='FontName={font},FontSize=20'"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_mp4),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "ffmpeg subtitle burn failed").strip()[-1200:]
    return True, None


def _project_durations(
    slides_by_num: dict[int, SlideEntry],
    narrate_results: list[dict[str, Any]],
    workspace: Path,
) -> tuple[float, list[dict[str, Any]]]:
    """Estimate the final video length from synthesized narration + clip lengths,
    WITHOUT composing. A slide's length is max(narration, longest video clip on it),
    mirroring the compose policy. Returns (total_seconds, per_slide).
    """
    per_slide: list[dict[str, Any]] = []
    total = 0.0
    for rec in narrate_results:
        n = rec["slide_number"]
        slide = slides_by_num.get(n)
        wav, _ = _audio_paths(workspace, n)
        narration = _ffprobe_duration(wav)
        clip_max = 0.0
        clips = slide.video_clips if slide else []
        for c in clips:
            probe_info, _ = _probe_clip(Path(c.path))
            if not probe_info:
                continue
            if c.trim_start_seconds is not None and c.trim_end_seconds is not None:
                cd = max(0.001, c.trim_end_seconds - c.trim_start_seconds)
            else:
                cd = max(0.001, float(probe_info["duration"]))
            clip_max = max(clip_max, cd)
        # Mirror compose: video slides → max(narration, clip); still slides →
        # narration + the fixed tail used by _ffmpeg_compose_slide.
        effective = max(narration, clip_max) if clips else narration + STILL_TAIL_SECONDS
        total += effective
        per_slide.append({
            "slide_number": n,
            "narration_seconds": round(narration, 3),
            "clip_max_seconds": round(clip_max, 3) if clips else None,
            "effective_seconds": round(effective, 3),
        })
    return total, per_slide


def cmd_render(args: argparse.Namespace) -> int:
    pdf_path = Path(args.slides_pdf).resolve()
    script_path = Path(args.talk_script).resolve()
    output = Path(args.output).resolve()
    workspace = Path(args.workspace).resolve()
    voice = args.voice or DEFAULT_VOICE
    rate = getattr(args, "rate", None) or None
    max_seconds = getattr(args, "max_seconds", None)
    allow_over_cap = bool(getattr(args, "allow_over_cap", False))
    width, height = (int(x) for x in args.resolution.lower().split("x"))
    fps = int(args.fps)
    with_subtitles = bool(args.with_subtitles)

    warnings: list[str] = []

    # Phase 1: parse
    slides, parse_errors = parse_talk_script(script_path)
    if parse_errors:
        payload = {
            "ok": False,
            "error": "talk script parse failed",
            "parse_errors": parse_errors,
            "checkedAt": _now(),
        }
        _print_and_dump(payload, args, stream=sys.stderr)
        return 1

    # Phase 2: PDF sanity check
    if not pdf_path.is_file():
        payload = {"ok": False, "error": f"slides PDF not found: {pdf_path}", "checkedAt": _now()}
        _print_and_dump(payload, args, stream=sys.stderr)
        return 1
    pdf_pages, pdf_err = _pdf_page_count(pdf_path)
    page_gap_warning: str | None = None
    if pdf_err and pdf_pages == 0:
        # If pdfinfo is missing, fall back to using slide count as truth.
        page_gap_warning = f"could not determine PDF page count ({pdf_err}); proceeding with {len(slides)} slides"
        warnings.append(page_gap_warning)
        effective_pages = len(slides)
    else:
        effective_pages = pdf_pages
        gap = abs(pdf_pages - len(slides))
        if gap >= 2:
            payload = {
                "ok": False,
                "error": f"PDF page count ({pdf_pages}) and slide count ({len(slides)}) differ by {gap} (>1); cannot reconcile",
                "checkedAt": _now(),
            }
            _print_and_dump(payload, args, stream=sys.stderr)
            return 1
        if gap == 1:
            warnings.append(f"PDF has {pdf_pages} pages but script lists {len(slides)} slides (gap of 1 tolerated)")

    # Phase 3: rasterize
    pages_to_render = min(effective_pages, len(slides)) if effective_pages else len(slides)
    pngs, raster_err = _rasterize_pdf(pdf_path, pages_to_render, workspace)
    if raster_err:
        payload = {"ok": False, "error": raster_err, "checkedAt": _now()}
        _print_and_dump(payload, args, stream=sys.stderr)
        return 1

    # Phase 4: TTS
    narrate_results, narrate_errors = _narrate_slides(slides[:pages_to_render], voice, workspace, rate=rate)
    if narrate_errors:
        payload = {
            "ok": False,
            "error": "TTS failed for one or more slides",
            "tts_errors": narrate_errors,
            "checkedAt": _now(),
        }
        _print_and_dump(payload, args, stream=sys.stderr)
        return 1

    # Phase 4.5: duration-cap gate. Audio is now synthesized, so we can project
    # the final length cheaply (before the expensive whisper + compose phases). If
    # it overruns --max-seconds, halt here and let the orchestrator decide (trim,
    # re-render with --rate, or re-run with --allow-over-cap) instead of burning a
    # full compose on a deck that won't pass the venue cap.
    if max_seconds is not None:
        slides_by_num_pre = {s.slide_number: s for s in slides}
        projected_total, projected_per = _project_durations(slides_by_num_pre, narrate_results, workspace)
        if projected_total > float(max_seconds) and not allow_over_cap:
            payload = {
                "ok": False,
                "error": "projected duration exceeds --max-seconds (halted after TTS, before compose)",
                "over_cap": True,
                "projected_seconds": round(projected_total, 3),
                "cap_seconds": float(max_seconds),
                "over_by_seconds": round(projected_total - float(max_seconds), 3),
                "rate": rate,
                "per_slide": projected_per,
                "hint": "trim narration on the longest slides, re-render with --rate (e.g. +10%), or pass --allow-over-cap to proceed anyway",
                "checkedAt": _now(),
            }
            _print_and_dump(payload, args, stream=sys.stderr)
            return 4

    # Phase 5: subtitle plan (placeholder only; whisper runs after concat in Phase 8)
    subtitles_info: dict[str, Any] = {
        "requested": with_subtitles,
        "available": False,
        "skipped": False,
        "skipReason": None,
        "path": None,
        "preBurnPath": None,
    }
    merged_srt: Path | None = None

    # Phase 6: per-slide compose
    segments_dir = _render_root(workspace) / "segments"
    segments: list[Path] = []
    per_slide_drift: list[dict[str, Any]] = []
    slides_by_num = {s.slide_number: s for s in slides}
    for slide_record, png in zip(narrate_results, pngs):
        slide_num = slide_record["slide_number"]
        slide = slides_by_num.get(slide_num)
        wav, _ = _audio_paths(workspace, slide_num)
        seg = segments_dir / f"slide_{slide_num:02d}.mp4"
        compose_info: dict[str, Any] | None = None
        if slide is not None and slide.video_mode == "inplace" and slide.video_clips:
            ok, compose_info, err = _ffmpeg_compose_inplace_slide(
                png, slide.video_clips, wav, seg, width, height, fps,
            )
            compose_mode = "inplace"
        elif slide is not None and slide.video_clip is not None:
            ok, compose_info, err = _ffmpeg_compose_video_slide(
                slide.video_clip, wav, seg, width, height, fps,
            )
            compose_mode = "video"
        else:
            ok, err = _ffmpeg_compose_slide(png, wav, seg, width, height, fps)
            compose_mode = "still"
        if not ok:
            payload = {
                "ok": False,
                "error": f"ffmpeg compose failed for slide {slide_num}: {err}",
                "compose_mode": compose_mode,
                "checkedAt": _now(),
            }
            _print_and_dump(payload, args, stream=sys.stderr)
            return 3
        actual = _ffprobe_duration(seg)
        planned = next((s.planned_seconds for s in slides if s.slide_number == slide_num), 0.0)
        drift_entry: dict[str, Any] = {
            "slide_number": slide_num,
            "title": next((s.title for s in slides if s.slide_number == slide_num), ""),
            "planned_seconds": round(planned, 3),
            "actual_seconds": round(actual, 3),
            "drift_seconds": round(actual - planned, 3),
            "audio_cached": slide_record.get("cached", False),
            "content_hash": slide_record.get("content_hash"),
            "compose_mode": compose_mode,
        }
        if compose_info:
            drift_entry["narration_seconds"] = compose_info.get("narration_seconds")
            if compose_mode == "inplace":
                drift_entry["total_seconds"] = compose_info.get("total_seconds")
                drift_entry["overlays"] = compose_info.get("overlays")
                drift_entry["unmatched_overlays"] = compose_info.get("unmatched")
            else:
                drift_entry["clip_effective_seconds"] = compose_info.get("clip_effective_seconds")
                drift_entry["clip_source_seconds"] = compose_info.get("clip_source_seconds")
                drift_entry["loop_factor"] = compose_info.get("loop_factor")
                if slide is not None and slide.video_clip is not None:
                    drift_entry["clip_path"] = slide.video_clip.path
        per_slide_drift.append(drift_entry)
        segments.append(seg)

    if not segments:
        payload = {"ok": False, "error": "no segments produced", "checkedAt": _now()}
        _print_and_dump(payload, args, stream=sys.stderr)
        return 3

    # Phase 7: concat → no-subs MP4 is the milestone deliverable
    # Always concat directly to `output`. If --with-subtitles is set, Phase 8
    # will produce a burned-in copy and atomically replace `output`; if any
    # whisper step fails, `output` stays as the no-subs version (which is
    # already a valid render). This way the user never waits on subtitles
    # before the main deliverable lands on disk.
    ok, err = _ffmpeg_concat(segments, output)
    if not ok:
        payload = {"ok": False, "error": err, "checkedAt": _now()}
        _print_and_dump(payload, args, stream=sys.stderr)
        return 3
    subtitles_info["preBurnPath"] = str(output)

    # Phase 8: optional whisper alignment + subtitle burn-in (post-concat)
    # Subtitles are non-blocking: every failure mode here is soft-fail. The
    # no-subs MP4 written by Phase 7 stays as the final output on any error.
    if with_subtitles:
        whisper_info = _check_whisper()
        if not whisper_info["available"]:
            # In normal flow this is caught by preflight (hard error), so this
            # branch only fires if the user bypassed preflight. Soft-fail to
            # match the helper's "never block on subtitles" contract.
            subtitles_info["skipped"] = True
            subtitles_info["skipReason"] = "whisper-missing"
            warnings.append("whisper not available; --with-subtitles requested but skipped (preflight should have caught this)")
        else:
            subtitles_info["available"] = True
            srt_dir = _render_root(workspace) / "srt"
            cumulative_offset = 0.0
            per_slide_srt: list[tuple[Path, float]] = []
            for slide_record in narrate_results:
                slide_num = slide_record["slide_number"]
                wav, _ = _audio_paths(workspace, slide_num)
                srt_path, err = _whisper_align(wav, srt_dir)
                if err:
                    subtitles_info["skipped"] = True
                    subtitles_info["skipReason"] = "whisper-failed"
                    warnings.append(f"whisper failed for slide {slide_num}: {err}; keeping no-subs MP4")
                    per_slide_srt = []
                    break
                per_slide_srt.append((srt_path, cumulative_offset))
                cumulative_offset += slide_record.get("duration_seconds") or 0.0
            if per_slide_srt:
                merged_srt = _render_root(workspace) / "subtitles.srt"
                merge_err = _merge_srts(per_slide_srt, merged_srt)
                if merge_err:
                    subtitles_info["skipped"] = True
                    subtitles_info["skipReason"] = "alignment-merge-failed"
                    warnings.append(f"SRT merge failed: {merge_err}; keeping no-subs MP4")
                    merged_srt = None
                else:
                    subtitles_info["path"] = str(merged_srt)

        # Burn-in pass: write to a temp neighbour of output, then atomically
        # replace output on success. Failure leaves output untouched.
        if merged_srt is not None:
            burned = output.with_suffix(".subs.mp4")
            ok_burn, burn_err = _ffmpeg_burn_subtitles(output, merged_srt, burned)
            if not ok_burn:
                subtitles_info["skipped"] = True
                subtitles_info["skipReason"] = "ffmpeg-subtitle-burn-failed"
                warnings.append(f"subtitle burn failed: {burn_err}; keeping no-subs MP4")
                if burned.exists():
                    try:
                        burned.unlink()
                    except OSError:
                        pass
            else:
                # Atomically swap the burned-in copy into place.
                burned.replace(output)

    # Final stats
    final_size_mb = output.stat().st_size / (1024 * 1024) if output.is_file() else 0.0
    total_planned = sum(d["planned_seconds"] for d in per_slide_drift)
    total_actual = sum(d["actual_seconds"] for d in per_slide_drift)

    payload = {
        "ok": True,
        "output": str(output),
        "slides_pdf": str(pdf_path),
        "talk_script": str(script_path),
        "voice": voice,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "withSubtitles": with_subtitles,
        "subtitles": subtitles_info,
        "slides": per_slide_drift,
        "totals": {
            "planned_seconds": round(total_planned, 3),
            "actual_seconds": round(total_actual, 3),
            "drift_seconds": round(total_actual - total_planned, 3),
            "size_mb": round(final_size_mb, 2),
        },
        "warnings": warnings,
        "checkedAt": _now(),
    }
    _print_and_dump(payload, args)
    return 0


# ── Verify ────────────────────────────────────────────────────────────────────

def cmd_verify(args: argparse.Namespace) -> int:
    video = Path(args.video).resolve()
    tolerance = float(args.duration_tolerance)

    payload: dict[str, Any] = {
        "ok": False,
        "video": str(video),
        "limits": {"duration_tolerance": tolerance},
        "checkedAt": _now(),
    }

    if not video.is_file() or video.stat().st_size == 0:
        payload["violations"] = [{"check": "exists", "hint": f"video missing or empty: {video}"}]
        _print_and_dump(payload, args, stream=sys.stderr)
        return 2

    info = _ffprobe_streams(video)
    fmt = info.get("format", {}) or {}
    duration = float(fmt.get("duration") or 0.0)
    streams = info.get("streams", []) or []
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    vcodec = (vstream or {}).get("codec_name", "") or ""
    acodec = (astream or {}).get("codec_name", "") or ""
    pixfmt = (vstream or {}).get("pix_fmt", "") or ""
    width = int((vstream or {}).get("width") or 0)
    height = int((vstream or {}).get("height") or 0)
    fps = 0.0
    rfr = (vstream or {}).get("r_frame_rate") or "0/1"
    if "/" in rfr:
        num, den = rfr.split("/", 1)
        try:
            fps = float(num) / float(den) if float(den) else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    faststart = _has_faststart(video)
    size_mb = video.stat().st_size / (1024 * 1024)

    planned_duration = 0.0
    planned_info: dict[str, Any] = {"duration_seconds": None, "tolerance_seconds": None}
    if args.talk_script:
        script_path = Path(args.talk_script).resolve()
        slides, parse_errors = parse_talk_script(script_path)
        if parse_errors:
            payload["violations"] = [{
                "check": "talk_script",
                "hint": f"could not parse talk script for duration check: {parse_errors[0].get('message')}",
            }]
            _print_and_dump(payload, args, stream=sys.stderr)
            return 2
        planned_duration = sum(s.planned_seconds for s in slides)
        planned_info = {
            "duration_seconds": round(planned_duration, 3),
            "tolerance_seconds": round(planned_duration * tolerance, 3),
        }

    violations: list[dict[str, str]] = []
    if vcodec not in ALLOWED_VIDEO_CODECS:
        violations.append({"check": "video_codec", "hint": f"video codec {vcodec!r} not in {sorted(ALLOWED_VIDEO_CODECS)}; re-encode with -c:v libx264"})
    if not astream:
        violations.append({"check": "audio_codec", "hint": "no audio stream found; narration is required for /paper-slides-render output"})
    elif acodec not in ALLOWED_AUDIO_CODECS:
        violations.append({"check": "audio_codec", "hint": f"audio codec {acodec!r} not in {sorted(ALLOWED_AUDIO_CODECS)}; re-encode with -c:a aac"})
    if pixfmt and pixfmt != REQUIRED_PIXEL_FORMAT:
        violations.append({"check": "pixel_format", "hint": f"pixel format {pixfmt!r} != yuv420p"})
    if not faststart:
        violations.append({"check": "faststart", "hint": "moov atom not at file head; re-encode with -movflags +faststart"})
    if fps > 60.0:
        violations.append({"check": "fps", "hint": f"fps {fps:.1f} > 60; downsample with -r 30"})
    if width > 3840 or height > 2160:
        violations.append({"check": "resolution", "hint": f"{width}x{height} exceeds 3840x2160"})

    if planned_duration > 0:
        drift_abs = abs(duration - planned_duration)
        tol_seconds = planned_duration * tolerance
        if drift_abs > tol_seconds:
            sign = "+" if duration > planned_duration else "-"
            violations.append({
                "check": "duration_match",
                "hint": (
                    f"actual {duration:.1f}s vs planned {planned_duration:.1f}s "
                    f"(drift {sign}{drift_abs:.1f}s exceeds ±{tol_seconds:.1f}s tolerance)"
                ),
            })

    payload.update({
        "ok": not violations,
        "actual": {
            "size_mb": round(size_mb, 2),
            "duration_seconds": round(duration, 2),
            "video_codec": vcodec,
            "audio_codec": acodec or "none",
            "pixel_format": pixfmt,
            "faststart": faststart,
            "fps": round(fps, 2),
            "width": width,
            "height": height,
        },
        "planned": planned_info,
        "violations": violations,
    })
    _print_and_dump(payload, args, stream=None if not violations else sys.stderr)
    return 0 if not violations else 2


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="paper_slides_render.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="Check edge-tts / pdftoppm / ffmpeg / ffprobe and writable output dir")
    pre.add_argument("--workspace", default=".", help="Project workspace root (default: cwd)")
    pre.add_argument("--with-subtitles", action="store_true", help="Also probe whisper availability")
    pre.add_argument("--talk-script", default=None, help="Optional TALK_SCRIPT.md path; when given, probe any [VIDEO: ...] clip references")
    pre.add_argument("--json-out", help="Path to write JSON result")
    pre.set_defaults(func=cmd_preflight)

    par = sub.add_parser("parse", help="Parse TALK_SCRIPT.md into a slide manifest (read-only)")
    par.add_argument("--talk-script", required=True, help="Path to TALK_SCRIPT.md")
    par.add_argument("--slides-pdf", default=None, help="Optional path to slides PDF for page-count cross-check")
    par.add_argument("--json-out", help="Path to write JSON result")
    par.set_defaults(func=cmd_parse)

    nar = sub.add_parser("narrate", help="Synthesize per-slide audio via edge-tts (TTS-only preview)")
    nar.add_argument("--talk-script", required=True, help="Path to TALK_SCRIPT.md")
    nar.add_argument("--voice", default=DEFAULT_VOICE, help=f"Edge TTS voice (default: {DEFAULT_VOICE})")
    nar.add_argument("--workspace", default=".", help="Project workspace root (default: cwd)")
    nar.add_argument("--json-out", help="Path to write JSON result")
    nar.set_defaults(func=cmd_narrate)

    ren = sub.add_parser("render", help="Render the narrated MP4")
    ren.add_argument("--slides-pdf", required=True, help="Path to slides/main.pdf")
    ren.add_argument("--talk-script", required=True, help="Path to TALK_SCRIPT.md")
    ren.add_argument("--output", required=True, help="Output MP4 path")
    ren.add_argument("--voice", default=DEFAULT_VOICE, help=f"Edge TTS voice (default: {DEFAULT_VOICE})")
    ren.add_argument("--resolution", default=DEFAULT_RESOLUTION, help=f"WxH (default: {DEFAULT_RESOLUTION})")
    ren.add_argument("--fps", type=int, default=DEFAULT_FPS, help=f"Output fps (default: {DEFAULT_FPS})")
    ren.add_argument("--workspace", default=".", help="Project workspace root (default: cwd)")
    ren.add_argument("--with-subtitles", action="store_true", help="Burn whisper-aligned subtitles (degrades to no-subs if whisper missing)")
    ren.add_argument("--rate", default=None, help="edge-tts speed delta, e.g. +10%% or -5%% (remedy for over-cap decks; invalidates audio cache)")
    ren.add_argument("--max-seconds", type=float, default=None, help="Halt after TTS (exit 4) if projected total exceeds this cap, before composing")
    ren.add_argument("--allow-over-cap", action="store_true", help="Proceed even if projected total exceeds --max-seconds")
    ren.add_argument("--json-out", help="Path to write JSON result")
    ren.set_defaults(func=cmd_render)

    ver = sub.add_parser("verify", help="Verify the narrated MP4 against gates")
    ver.add_argument("--video", required=True, help="Path to the rendered MP4")
    ver.add_argument("--talk-script", default=None, help="Optional path to TALK_SCRIPT.md for duration drift check")
    ver.add_argument("--duration-tolerance", type=float, default=DEFAULT_DURATION_TOLERANCE,
                     help=f"Drift tolerance as a fraction of planned duration (default: {DEFAULT_DURATION_TOLERANCE})")
    ver.add_argument("--json-out", help="Path to write JSON result")
    ver.set_defaults(func=cmd_verify)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())

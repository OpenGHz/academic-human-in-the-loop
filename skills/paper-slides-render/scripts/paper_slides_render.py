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

ALLOWED_VIDEO_CODECS = {"h264", "hevc", "av1"}
ALLOWED_AUDIO_CODECS = {"aac", "ac3", "opus"}
REQUIRED_PIXEL_FORMAT = "yuv420p"

SLIDE_HEADER_RE = re.compile(
    r"^##\s+Slide\s+(?P<num>\d+)\s*:\s+(?P<title>.+?)\s+\[(?P<start>[\d:]+)\s*[-–]\s*(?P<end>[\d:]+)\]\s*$",
    re.MULTILINE,
)

QUOTE_RE = re.compile(r'"([^"]+)"|“([^”]+)”', re.DOTALL)
TRANSITION_RE = re.compile(r"^\s*→\s*\*?Transition\*?\s*:.*$", re.MULTILINE)
STAGE_RE = re.compile(r"^\s*\*\[[^\]]+\]\*\s*$", re.MULTILINE)
HRULE_RE = re.compile(r"^---\s*$", re.MULTILINE)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


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
class SlideEntry:
    slide_number: int
    title: str
    planned_start_seconds: float
    planned_end_seconds: float
    speakable_text: str
    raw_body: str
    fallback_mode: bool = False
    warnings: list[str] = field(default_factory=list)

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
        }


def _strip_markdown(text: str) -> str:
    text = MD_LINK_RE.sub(r"\1", text)
    text = MD_BOLD_RE.sub(r"\1", text)
    text = MD_ITALIC_RE.sub(r"\1", text)
    return text


def _extract_speakable(raw_body: str) -> tuple[str, bool]:
    """Return (speakable_text, fallback_mode)."""
    body = TRANSITION_RE.sub("", raw_body)
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

        speakable, fallback = _extract_speakable(raw_body)
        warnings: list[str] = []
        if fallback:
            warnings.append("no quoted speech found; using full body as fallback")
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


# ── Preflight ─────────────────────────────────────────────────────────────────

def cmd_preflight(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    out_dir = workspace / "slides" / "render"

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
    if args.with_subtitles and not whisper_info["available"]:
        warnings.append("whisper not available; subtitles will be skipped when render runs with --with-subtitles")

    required_ok = bool(edge_tts_info["available"]) and bool(pdftoppm) and bool(ffmpeg) and bool(ffprobe) and can_write
    ok = required_ok

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

def _audio_paths(workspace: Path, slide_number: int) -> tuple[Path, Path]:
    audio_dir = workspace / "slides" / "render" / "audio"
    wav = audio_dir / f"slide_{slide_number:02d}.wav"
    meta = audio_dir / f"slide_{slide_number:02d}.meta.json"
    return wav, meta


def _content_hash(voice: str, text: str) -> str:
    payload = json.dumps({"voice": voice, "text": text}, ensure_ascii=False, sort_keys=True)
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


def _edge_tts_synthesize(text: str, voice: str, out_wav: Path, retries: int = 1) -> tuple[bool, str | None]:
    """Synthesize via edge-tts CLI to out_wav (atomic). Returns (ok, error)."""
    cli = shutil.which("edge-tts")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out_wav.with_suffix(out_wav.suffix + ".tmp")
    last_err: str | None = None
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            if cli:
                cmd = [cli, "--voice", voice, "--text", text, "--write-media", str(tmp_out)]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode == 0 and tmp_out.is_file() and tmp_out.stat().st_size > 0:
                    tmp_out.replace(out_wav)
                    return True, None
                last_err = (proc.stderr or proc.stdout or "edge-tts failed").strip()
            else:
                # Module fallback: run a tiny embedded script via python3 -c.
                py = (
                    "import asyncio, sys, edge_tts;"
                    "txt=sys.argv[1]; v=sys.argv[2]; p=sys.argv[3];"
                    "async def m():\n"
                    "    c=edge_tts.Communicate(txt, v);\n"
                    "    await c.save(p)\n"
                    "asyncio.run(m())"
                )
                cmd = [sys.executable, "-c", py, text, voice, str(tmp_out)]
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Synthesize per-slide audio with content-hash caching.

    Returns (per_slide_results, per_slide_errors).
    """
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for slide in slides:
        wav, meta = _audio_paths(workspace, slide.slide_number)
        chash = _content_hash(voice, slide.speakable_text)
        cached_meta = _read_meta(meta)
        cached = (
            wav.is_file()
            and wav.stat().st_size > 0
            and cached_meta is not None
            and cached_meta.get("content_hash") == chash
            and cached_meta.get("voice") == voice
        )
        if not cached:
            ok, err = _edge_tts_synthesize(slide.speakable_text, voice, wav)
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
    png_dir = workspace / "slides" / "render" / "png"
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


def _ffmpeg_compose_slide(
    png: Path,
    wav: Path,
    out_mp4: Path,
    width: int,
    height: int,
    fps: int,
) -> tuple[bool, str | None]:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
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
        "-shortest",
        str(out_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "ffmpeg failed").strip()[-1200:]
    return True, None


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


def cmd_render(args: argparse.Namespace) -> int:
    pdf_path = Path(args.slides_pdf).resolve()
    script_path = Path(args.talk_script).resolve()
    output = Path(args.output).resolve()
    workspace = Path(args.workspace).resolve()
    voice = args.voice or DEFAULT_VOICE
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
    narrate_results, narrate_errors = _narrate_slides(slides[:pages_to_render], voice, workspace)
    if narrate_errors:
        payload = {
            "ok": False,
            "error": "TTS failed for one or more slides",
            "tts_errors": narrate_errors,
            "checkedAt": _now(),
        }
        _print_and_dump(payload, args, stream=sys.stderr)
        return 1

    # Phase 5: optional whisper alignment
    subtitles_info: dict[str, Any] = {
        "requested": with_subtitles,
        "available": False,
        "skipped": False,
        "skipReason": None,
        "path": None,
    }
    merged_srt: Path | None = None
    if with_subtitles:
        whisper_info = _check_whisper()
        if not whisper_info["available"]:
            subtitles_info["skipped"] = True
            subtitles_info["skipReason"] = "whisper-missing"
            warnings.append("whisper not available; --with-subtitles requested but skipped")
        else:
            subtitles_info["available"] = True
            srt_dir = workspace / "slides" / "render" / "srt"
            cumulative_offset = 0.0
            per_slide_srt: list[tuple[Path, float]] = []
            for slide_record in narrate_results:
                slide_num = slide_record["slide_number"]
                wav, _ = _audio_paths(workspace, slide_num)
                srt_path, err = _whisper_align(wav, srt_dir)
                if err:
                    subtitles_info["skipped"] = True
                    subtitles_info["skipReason"] = "whisper-failed"
                    warnings.append(f"whisper failed for slide {slide_num}: {err}")
                    per_slide_srt = []
                    break
                per_slide_srt.append((srt_path, cumulative_offset))
                cumulative_offset += slide_record.get("duration_seconds") or 0.0
            if per_slide_srt:
                merged_srt = workspace / "slides" / "render" / "subtitles.srt"
                merge_err = _merge_srts(per_slide_srt, merged_srt)
                if merge_err:
                    subtitles_info["skipped"] = True
                    subtitles_info["skipReason"] = "alignment-merge-failed"
                    warnings.append(f"SRT merge failed: {merge_err}")
                    merged_srt = None
                else:
                    subtitles_info["path"] = str(merged_srt)

    # Phase 6: per-slide compose
    segments_dir = workspace / "slides" / "render" / "segments"
    segments: list[Path] = []
    per_slide_drift: list[dict[str, Any]] = []
    for slide_record, png in zip(narrate_results, pngs):
        slide_num = slide_record["slide_number"]
        wav, _ = _audio_paths(workspace, slide_num)
        seg = segments_dir / f"slide_{slide_num:02d}.mp4"
        ok, err = _ffmpeg_compose_slide(png, wav, seg, width, height, fps)
        if not ok:
            payload = {
                "ok": False,
                "error": f"ffmpeg compose failed for slide {slide_num}: {err}",
                "checkedAt": _now(),
            }
            _print_and_dump(payload, args, stream=sys.stderr)
            return 3
        actual = _ffprobe_duration(seg)
        planned = next((s.planned_seconds for s in slides if s.slide_number == slide_num), 0.0)
        per_slide_drift.append({
            "slide_number": slide_num,
            "title": next((s.title for s in slides if s.slide_number == slide_num), ""),
            "planned_seconds": round(planned, 3),
            "actual_seconds": round(actual, 3),
            "drift_seconds": round(actual - planned, 3),
            "audio_cached": slide_record.get("cached", False),
            "content_hash": slide_record.get("content_hash"),
        })
        segments.append(seg)

    if not segments:
        payload = {"ok": False, "error": "no segments produced", "checkedAt": _now()}
        _print_and_dump(payload, args, stream=sys.stderr)
        return 3

    # Phase 7: concat
    concat_target = output
    if merged_srt is not None:
        # We will burn subtitles afterwards; concat to a temp file first.
        concat_target = output.with_suffix(".pre-subs.mp4")
    ok, err = _ffmpeg_concat(segments, concat_target)
    if not ok:
        payload = {"ok": False, "error": err, "checkedAt": _now()}
        _print_and_dump(payload, args, stream=sys.stderr)
        return 3

    # Phase 8: optional subtitle burn
    if merged_srt is not None:
        ok, err = _ffmpeg_burn_subtitles(concat_target, merged_srt, output)
        if not ok:
            subtitles_info["skipped"] = True
            subtitles_info["skipReason"] = "ffmpeg-subtitle-burn-failed"
            warnings.append(f"subtitle burn failed: {err}; output uses pre-burn concat")
            concat_target.replace(output)
        else:
            try:
                concat_target.unlink()
            except OSError:
                pass

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

#!/usr/bin/env python3
"""paper_video.py — canonical helper for the /paper-video SKILL.

Self-contained gate that enforces submission-video constraints (size,
duration, codec, faststart) for venues like CoRL / ICRA / RSS / NeurIPS-supp.

Subcommands
-----------
  preflight   Check ffmpeg / ffprobe availability and writable output dir.
  assemble    Assemble a manifest of clips + title cards into a single MP4.
  verify      Verify a finished MP4 against the venue's hard limits.
  package     Zip a supplementary bundle and enforce the size ceiling.

Exit codes
----------
  0   success (or verify with ok=true)
  1   helper-level error (missing dependency, malformed manifest, etc.)
  2   verify gate failed (size / duration / codec / faststart violation)
  3   assemble ffmpeg failed (stderr surfaced in JSON output)

All subcommands accept --json-out PATH to mirror their result as JSON.
This is Policy A (skill-local gate) per
skills/shared-references/integration-contract.md §2.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Venue + mode profiles ─────────────────────────────────────────────────────

VENUE_PROFILES: dict[str, dict[str, int]] = {
    "CORL":     {"max_mb": 250, "max_seconds": 180},
    "ICRA":     {"max_mb": 100, "max_seconds": 180},
    "RSS":      {"max_mb": 100, "max_seconds": 300},
    "IROS":     {"max_mb": 100, "max_seconds": 180},
    "NEURIPS":  {"max_mb": 100, "max_seconds": 600},
    "ICLR":     {"max_mb": 100, "max_seconds": 600},
    "ICML":     {"max_mb": 100, "max_seconds": 600},
    "CVPR":     {"max_mb": 100, "max_seconds": 600},
    "GENERIC":  {"max_mb": 250, "max_seconds": 300},
}

# Mode profiles override venue when mode != submission. The submission mode
# is the only one that defers to the venue's hard limit. Showcase and teaser
# target shorter, web-friendly cuts regardless of submission venue.
MODE_PROFILES: dict[str, dict[str, Any]] = {
    "submission": {"max_mb": None, "max_seconds": None, "anon_scan": True},
    "showcase":   {"max_mb": 100,  "max_seconds": 90,   "anon_scan": False},
    "teaser":     {"max_mb": 50,   "max_seconds": 45,   "anon_scan": False},
}

# Anonymity blocklist applied when mode == submission. These patterns mark
# strings that almost always identify the authors / institution and would
# get flagged at desk-reject. Caller can add more via --anon-blocklist.
ANON_BLOCKLIST_PATTERNS: list[tuple[str, str]] = [
    (r"https?://\S+",                                   "URL"),
    (r"\bwww\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",          "www-URL"),
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "email"),
    (r"(?<!\w)@[A-Za-z][A-Za-z0-9_]{2,}\b",             "social-handle"),
    (r"\bgithub\.com\b",                                "github-url"),
    (r"\b[a-zA-Z0-9-]+\.(?:edu|ac\.uk|ac\.jp|ac\.cn|edu\.cn)\b", "institutional-domain"),
    (r"\barxiv\.org/abs/\d{4}\.\d{4,5}\b",              "arxiv-id"),
]

ALLOWED_VIDEO_CODECS = {"h264", "hevc", "av1"}
ALLOWED_AUDIO_CODECS = {"aac", "ac3", "opus", "none", ""}
REQUIRED_PIXEL_FORMAT = "yuv420p"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(payload: dict[str, Any], path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _resolve_mode(mode: str | None) -> tuple[str, dict[str, Any]]:
    key = (mode or "submission").lower()
    if key not in MODE_PROFILES:
        raise SystemExit(f"unknown --mode {mode!r}; expected one of {sorted(MODE_PROFILES)}")
    return key, MODE_PROFILES[key]


def _resolve_venue(venue: str | None) -> tuple[str, dict[str, int]]:
    key = (venue or "CORL").upper()
    if key not in VENUE_PROFILES:
        # Fall back to GENERIC rather than erroring out; report the resolved key.
        return key, VENUE_PROFILES["GENERIC"]
    return key, VENUE_PROFILES[key]


def _effective_limits(
    mode_key: str,
    venue_profile: dict[str, int],
    cli_max_mb: float | None,
    cli_max_seconds: float | None,
) -> tuple[float, float]:
    """Resolve effective MAX_MB / MAX_SECONDS in this precedence:
       CLI override > mode profile (when non-null) > venue profile."""
    mode_profile = MODE_PROFILES[mode_key]
    max_mb = float(
        cli_max_mb
        if cli_max_mb is not None
        else (mode_profile["max_mb"] if mode_profile["max_mb"] is not None else venue_profile["max_mb"])
    )
    max_seconds = float(
        cli_max_seconds
        if cli_max_seconds is not None
        else (mode_profile["max_seconds"] if mode_profile["max_seconds"] is not None else venue_profile["max_seconds"])
    )
    return max_mb, max_seconds


# ── Preflight ─────────────────────────────────────────────────────────────────

def cmd_preflight(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    venue, venue_profile = _resolve_venue(args.venue)
    mode_key, _ = _resolve_mode(args.mode)
    effective_mb, effective_seconds = _effective_limits(mode_key, venue_profile, None, None)
    out_dir = workspace / "submission" / "video"

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    can_write = False
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        probe = out_dir / ".paper_video_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        can_write = True
    except OSError:
        can_write = False

    ok = bool(ffmpeg) and bool(ffprobe) and can_write
    payload: dict[str, Any] = {
        "ok": ok,
        "workspace": str(workspace),
        "venue": venue,
        "mode": mode_key,
        "limits": {"max_mb": effective_mb, "max_seconds": effective_seconds},
        "venueLimits": venue_profile,
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "outputDir": str(out_dir),
        "outputDirWritable": can_write,
        "checkedAt": _now(),
    }
    if not ffmpeg:
        payload["error"] = "ffmpeg not found on PATH; install via apt-get install ffmpeg / brew install ffmpeg"
    elif not ffprobe:
        payload["error"] = "ffprobe not found on PATH (usually shipped with ffmpeg)"
    elif not can_write:
        payload["error"] = f"output directory not writable: {out_dir}"

    _dump(payload, Path(args.json_out) if args.json_out else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


# ── Manifest model ────────────────────────────────────────────────────────────

@dataclass
class Shot:
    kind: str
    source: str | None = None
    start: float | None = None
    end: float | None = None
    duration: float | None = None
    text: str | None = None
    caption: str | None = None
    speed: float = 1.0

    def planned_duration(self) -> float:
        if self.kind == "title_card":
            return float(self.duration or 3.0)
        if self.kind == "clip":
            raw = float((self.end or 0.0) - (self.start or 0.0))
            spd = max(0.25, float(self.speed or 1.0))
            return max(0.0, raw / spd)
        return float(self.duration or 0.0)


def _load_manifest(path: Path) -> tuple[dict[str, Any], list[Shot]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    shots: list[Shot] = []
    for i, raw in enumerate(data.get("shots") or []):
        try:
            shots.append(Shot(**raw))
        except TypeError as e:
            raise SystemExit(f"manifest shot #{i} malformed: {e}")
    if not shots:
        raise SystemExit("manifest has no shots")
    return data, shots


# ── ffprobe wrapper ───────────────────────────────────────────────────────────

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
    """Detect a moov-at-front MP4 by reading the first ~256KiB and looking for
    'moov' before 'mdat'. This is the same heuristic mp4 web players use."""
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
        # No mdat in the first 256KiB but moov is present -> faststart
        return True
    return moov < mdat


def _scan_manifest_for_anon_violations(
    manifest_path: Path,
    extra_patterns: list[str] | None = None,
) -> list[dict[str, str]]:
    """Scan a manifest JSON for strings that would break double-blind review.

    Walks the manifest body as text (not JSON-aware on purpose, so it catches
    matches inside any nested string field — captions, narration, titles,
    file paths, comments, etc.). Returns a list of violation entries shaped
    like the rest of verify's output: {check, hint}.
    """
    if not manifest_path.is_file():
        return [{"check": "no_identifying_strings", "hint": f"manifest not found for anon scan: {manifest_path}"}]
    try:
        text = manifest_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [{"check": "no_identifying_strings", "hint": f"could not read manifest: {e}"}]

    patterns: list[tuple[str, str]] = list(ANON_BLOCKLIST_PATTERNS)
    for extra in extra_patterns or []:
        patterns.append((extra, "user-supplied"))

    violations: list[dict[str, str]] = []
    for pattern, label in patterns:
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            violations.append({
                "check": "no_identifying_strings",
                "hint": f"invalid blocklist pattern {pattern!r} ({label}): {e}",
            })
            continue
        for match in compiled.finditer(text):
            snippet = match.group(0)
            if len(snippet) > 80:
                snippet = snippet[:77] + "..."
            violations.append({
                "check": "no_identifying_strings",
                "hint": f"manifest contains {label!r} match {snippet!r}; remove or paraphrase before submission",
            })
    return violations


# ── Verify ────────────────────────────────────────────────────────────────────

def cmd_verify(args: argparse.Namespace) -> int:
    video = Path(args.video).resolve()
    venue, venue_profile = _resolve_venue(args.venue)
    mode_key, mode_profile = _resolve_mode(args.mode)
    max_mb, max_seconds = _effective_limits(
        mode_key,
        venue_profile,
        args.max_mb,
        args.max_seconds,
    )

    if not video.is_file():
        payload = {
            "ok": False,
            "video": str(video),
            "venue": venue,
            "mode": mode_key,
            "violations": [{"check": "exists", "hint": f"video file not found: {video}"}],
            "checkedAt": _now(),
        }
        _dump(payload, Path(args.json_out) if args.json_out else None)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2

    size_bytes = video.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    info = _ffprobe_streams(video)
    fmt = info.get("format", {}) or {}
    duration = float(fmt.get("duration") or 0.0)

    vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    astream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)

    vcodec = (vstream or {}).get("codec_name", "") or ""
    acodec = (astream or {}).get("codec_name", "") or "none"
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

    violations: list[dict[str, str]] = []
    if size_mb > max_mb:
        violations.append({
            "check": "size",
            "hint": f"size {size_mb:.1f} MB > {max_mb:.0f} MB; re-encode at lower bitrate (try -b:v {int(max_mb*8000/duration*0.9) if duration > 0 else 5000}k)",
        })
    if duration > max_seconds:
        violations.append({
            "check": "duration",
            "hint": f"duration {duration:.1f}s > {max_seconds:.0f}s; trim manifest shots or raise speed for filler clips",
        })
    if vcodec not in ALLOWED_VIDEO_CODECS:
        violations.append({"check": "video_codec", "hint": f"video codec {vcodec!r} not in {sorted(ALLOWED_VIDEO_CODECS)}; re-encode with -c:v libx264"})
    if acodec not in ALLOWED_AUDIO_CODECS:
        violations.append({"check": "audio_codec", "hint": f"audio codec {acodec!r} not in {sorted(ALLOWED_AUDIO_CODECS)}; re-encode with -c:a aac"})
    if pixfmt and pixfmt != REQUIRED_PIXEL_FORMAT:
        violations.append({"check": "pixel_format", "hint": f"pixel format {pixfmt!r} != yuv420p; re-encode with -pix_fmt yuv420p"})
    if not faststart:
        violations.append({"check": "faststart", "hint": "moov atom is not at file head; re-encode with -movflags +faststart"})
    if fps > 60.0:
        violations.append({"check": "fps", "hint": f"fps {fps:.1f} > 60; downsample with -r 30"})
    if width > 3840 or height > 2160:
        violations.append({"check": "resolution", "hint": f"{width}x{height} exceeds 3840x2160; downscale with -vf scale=1920:1080"})

    anon_scan_ran = False
    anon_violations: list[dict[str, str]] = []
    if mode_profile["anon_scan"] and args.manifest:
        anon_scan_ran = True
        anon_violations = _scan_manifest_for_anon_violations(
            Path(args.manifest).resolve(),
            extra_patterns=args.anon_blocklist or None,
        )
        violations.extend(anon_violations)
    elif mode_profile["anon_scan"] and not args.manifest:
        violations.append({
            "check": "no_identifying_strings",
            "hint": "submission mode requires --manifest to run the anonymity scan; pass the manifest used for assemble",
        })

    ok = not violations
    payload = {
        "ok": ok,
        "video": str(video),
        "venue": venue,
        "mode": mode_key,
        "limits": {"max_mb": max_mb, "max_seconds": max_seconds},
        "anon_scan": {
            "enabled": bool(mode_profile["anon_scan"]),
            "ran": anon_scan_ran,
            "manifest": str(Path(args.manifest).resolve()) if args.manifest else None,
            "extra_patterns": list(args.anon_blocklist or []),
            "violations": anon_violations,
        },
        "actual": {
            "size_mb": round(size_mb, 2),
            "duration_seconds": round(duration, 2),
            "video_codec": vcodec,
            "audio_codec": acodec,
            "pixel_format": pixfmt,
            "faststart": faststart,
            "fps": round(fps, 2),
            "width": width,
            "height": height,
        },
        "violations": violations,
        "checkedAt": _now(),
    }
    _dump(payload, Path(args.json_out) if args.json_out else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 2


# ── Assemble ──────────────────────────────────────────────────────────────────

def _ffmpeg_escape_drawtext(text: str) -> str:
    # ffmpeg drawtext requires escaping for colons, single quotes, and backslashes.
    text = text.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
    return text


def _build_title_filter(text: str, duration: float, width: int, height: int, fps: int) -> tuple[str, str]:
    """Return (input_args, filter_string) for a single title-card clip.

    We synthesize a solid white background via color= filter then drawtext on top.
    The output label is unique per shot index — caller is responsible for that.
    """
    color = f"color=c=white:s={width}x{height}:r={fps}:d={duration:.3f}"
    text_esc = _ffmpeg_escape_drawtext(text)
    # Use the bundled DejaVu font if present, else let ffmpeg choose a default.
    fontfile_arg = ""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for c in candidates:
        if Path(c).is_file():
            fontfile_arg = f"fontfile={c}:"
            break
    draw = (
        f"drawtext={fontfile_arg}text='{text_esc}':"
        f"fontcolor=black:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2"
    )
    return color, draw


def cmd_assemble(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.is_file():
        print(json.dumps({"ok": False, "error": f"manifest not found: {manifest_path}"}), file=sys.stderr)
        return 1
    data, shots = _load_manifest(manifest_path)

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    venue, venue_profile = _resolve_venue(args.venue)
    mode_key, _ = _resolve_mode(args.mode)
    # mode-aware default target_mb: if caller did not pass --target-mb,
    # derive it from the effective limit (90% of the cap, capped to 230 MB
    # to leave headroom for muxing overhead).
    effective_mb, effective_seconds = _effective_limits(mode_key, venue_profile, None, None)
    if args.target_mb is not None:
        target_mb = float(args.target_mb)
    else:
        target_mb = float(min(230.0, effective_mb * 0.92))

    w, h = (int(x) for x in args.target_resolution.lower().split("x"))
    fps = int(args.target_fps)

    planned_total = sum(s.planned_duration() for s in shots)
    if planned_total <= 0:
        return _emit_assemble_error(args, "planned duration is zero — manifest needs at least one shot with positive duration")

    target_bitrate_kbps = max(500, int((target_mb * 8 * 1024) / planned_total * 0.92))

    # Render each shot to a temp MP4 with identical params, then concat.
    with tempfile.TemporaryDirectory(prefix="paper_video_") as tmp:
        tmp_dir = Path(tmp)
        clip_paths: list[Path] = []

        for i, shot in enumerate(shots):
            clip_path = tmp_dir / f"shot_{i:03d}.mp4"
            if shot.kind == "title_card":
                input_arg, draw_filter = _build_title_filter(
                    shot.text or "", shot.duration or 3.0, w, h, fps
                )
                ffcmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", input_arg,
                    "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
                    "-shortest",
                    "-vf", draw_filter,
                    "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k",
                    "-r", str(fps),
                    str(clip_path),
                ]
            elif shot.kind == "clip":
                source = (manifest_path.parent / (shot.source or "")).resolve() if shot.source and not Path(shot.source).is_absolute() else Path(shot.source or "")
                if not source.is_file():
                    return _emit_assemble_error(args, f"shot #{i} source not found: {source}")
                start = float(shot.start or 0.0)
                end = float(shot.end or 0.0)
                if end <= start:
                    return _emit_assemble_error(args, f"shot #{i} has non-positive duration ({start}..{end})")
                speed = max(0.25, float(shot.speed or 1.0))
                # video setpts compresses time; audio atempo handles speed but only 0.5..2.0 per pass.
                atempo_chain = _atempo_chain(speed)
                vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setpts=PTS/{speed:.6f}"
                if shot.caption:
                    cap = _ffmpeg_escape_drawtext(shot.caption)
                    vf += (
                        f",drawtext=text='{cap}':fontcolor=white:fontsize=36:"
                        f"box=1:boxcolor=black@0.55:boxborderw=12:"
                        f"x=(w-text_w)/2:y=h-text_h-60"
                    )
                ffcmd = [
                    "ffmpeg", "-y",
                    "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-i", str(source),
                    "-vf", vf,
                    "-af", atempo_chain,
                    "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k",
                    "-r", str(fps),
                    "-ar", "48000", "-ac", "2",
                    str(clip_path),
                ]
            else:
                return _emit_assemble_error(args, f"shot #{i} has unknown kind: {shot.kind!r}")

            proc = subprocess.run(ffcmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return _emit_assemble_error(args, f"ffmpeg failed on shot #{i}: {proc.stderr.strip()[-1200:]}")
            clip_paths.append(clip_path)

        # Concat demuxer expects a text file listing each clip
        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p}'" for p in clip_paths) + "\n",
            encoding="utf-8",
        )

        # Two-pass-ish: try CRF concat first; if oversized, fall back to target bitrate.
        ffcmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output),
        ]
        proc = subprocess.run(ffcmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return _emit_assemble_error(args, f"concat copy failed: {proc.stderr.strip()[-1200:]}")

        # If oversize, re-encode with target bitrate
        if output.stat().st_size > target_mb * 1024 * 1024:
            re_encoded = output.with_suffix(".reencoded.mp4")
            ffcmd = [
                "ffmpeg", "-y",
                "-i", str(output),
                "-c:v", "libx264", "-preset", "slow",
                "-b:v", f"{target_bitrate_kbps}k",
                "-maxrate", f"{int(target_bitrate_kbps*1.1)}k",
                "-bufsize", f"{int(target_bitrate_kbps*2)}k",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                str(re_encoded),
            ]
            proc = subprocess.run(ffcmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return _emit_assemble_error(args, f"re-encode failed: {proc.stderr.strip()[-1200:]}")
            re_encoded.replace(output)

    payload = {
        "ok": True,
        "manifest": str(manifest_path),
        "output": str(output),
        "venue": venue,
        "mode": mode_key,
        "limits": {"max_mb": effective_mb, "max_seconds": effective_seconds},
        "target_mb": round(target_mb, 2),
        "size_mb": round(output.stat().st_size / (1024 * 1024), 2),
        "planned_duration_seconds": round(planned_total, 2),
        "target_bitrate_kbps": target_bitrate_kbps,
        "checkedAt": _now(),
    }
    _dump(payload, Path(args.json_out) if args.json_out else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _emit_assemble_error(args: argparse.Namespace, msg: str) -> int:
    payload = {"ok": False, "error": msg, "checkedAt": _now()}
    _dump(payload, Path(args.json_out) if args.json_out else None)
    print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
    return 3


def _atempo_chain(speed: float) -> str:
    """ffmpeg atempo supports 0.5..2.0; chain filters for outside range."""
    if abs(speed - 1.0) < 1e-6:
        return "anull"
    remaining = float(speed)
    parts: list[str] = []
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining *= 2.0
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


# ── Package ───────────────────────────────────────────────────────────────────

STORED_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".png", ".jpg", ".jpeg", ".pdf", ".zip", ".gz", ".bz2"}


def cmd_package(args: argparse.Namespace) -> int:
    items = [Path(p).resolve() for p in args.include]
    for it in items:
        if not it.exists():
            print(json.dumps({"ok": False, "error": f"include path not found: {it}"}), file=sys.stderr)
            return 1

    mode_key, _ = _resolve_mode(args.mode)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = int(args.max_mb * 1024 * 1024)

    tmp_out = output.with_suffix(output.suffix + ".tmp")
    file_list: list[tuple[Path, str]] = []
    for item in items:
        if item.is_file():
            file_list.append((item, item.name))
        elif item.is_dir():
            for f in sorted(item.rglob("*")):
                if f.is_file():
                    file_list.append((f, str(Path(item.name) / f.relative_to(item))))

    with zipfile.ZipFile(tmp_out, mode="w", allowZip64=True) as zf:
        for src, arcname in file_list:
            compress = zipfile.ZIP_STORED if src.suffix.lower() in STORED_EXTS else zipfile.ZIP_DEFLATED
            zf.write(src, arcname=arcname, compress_type=compress)

    size_bytes = tmp_out.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes > max_bytes:
        tmp_out.unlink(missing_ok=True)
        payload = {
            "ok": False,
            "output": str(output),
            "mode": mode_key,
            "size_mb": round(size_mb, 2),
            "limit_mb": args.max_mb,
            "violations": [{"check": "package_size", "hint": f"bundle {size_mb:.1f} MB exceeds limit {args.max_mb} MB; drop large items or pre-compress"}],
            "checkedAt": _now(),
        }
        _dump(payload, Path(args.json_out) if args.json_out else None)
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 2

    tmp_out.replace(output)
    payload = {
        "ok": True,
        "output": str(output),
        "mode": mode_key,
        "size_mb": round(size_mb, 2),
        "limit_mb": args.max_mb,
        "files": len(file_list),
        "checkedAt": _now(),
    }
    _dump(payload, Path(args.json_out) if args.json_out else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="paper_video.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    mode_choices = sorted(MODE_PROFILES.keys())

    pre = sub.add_parser("preflight", help="Check ffmpeg/ffprobe + writable output dir")
    pre.add_argument("--workspace", default=".", help="Project workspace root (default: cwd)")
    pre.add_argument("--venue", default="CORL", help="Venue profile name (default: CORL)")
    pre.add_argument("--mode", choices=mode_choices, default="submission",
                     help="Video mode (default: submission). Submission obeys venue limits; "
                          "showcase / teaser override with shorter, web-friendly defaults.")
    pre.add_argument("--json-out", help="Path to write JSON result")
    pre.set_defaults(func=cmd_preflight)

    asm = sub.add_parser("assemble", help="Assemble shots into a single MP4")
    asm.add_argument("--manifest", required=True, help="Manifest JSON path")
    asm.add_argument("--output", required=True, help="Output MP4 path")
    asm.add_argument("--venue", default="CORL", help="Venue profile name (default: CORL)")
    asm.add_argument("--mode", choices=mode_choices, default="submission",
                     help="Video mode (default: submission). Drives the default --target-mb when omitted.")
    asm.add_argument("--target-mb", type=float, default=None,
                     help="Target output size in MB. If omitted, derived from the resolved mode/venue limits.")
    asm.add_argument("--target-resolution", default="1920x1080", help="WxH (default: 1920x1080)")
    asm.add_argument("--target-fps", type=int, default=30, help="Output fps (default: 30)")
    asm.add_argument("--json-out", help="Path to write JSON result")
    asm.set_defaults(func=cmd_assemble)

    ver = sub.add_parser("verify", help="Verify finished MP4 against venue gates")
    ver.add_argument("--video", required=True, help="Path to the finished MP4")
    ver.add_argument("--venue", default="CORL", help="Venue profile name (default: CORL)")
    ver.add_argument("--mode", choices=mode_choices, default="submission",
                     help="Video mode (default: submission). Selects effective MAX_MB / MAX_SECONDS and "
                          "enables the anonymity scan when manifest is supplied.")
    ver.add_argument("--manifest", default=None,
                     help="Optional manifest path. Required for the anonymity scan in submission mode.")
    ver.add_argument("--anon-blocklist", action="append", default=[],
                     help="Extra regex pattern to add to the submission-mode anonymity scan (repeatable).")
    ver.add_argument("--max-mb", type=float, help="Override the resolved MAX_MB")
    ver.add_argument("--max-seconds", type=float, help="Override the resolved MAX_SECONDS")
    ver.add_argument("--json-out", help="Path to write JSON result")
    ver.set_defaults(func=cmd_verify)

    pkg = sub.add_parser("package", help="Zip a supplementary bundle and enforce size ceiling")
    pkg.add_argument("--include", action="append", required=True, help="Path to include (repeatable)")
    pkg.add_argument("--output", required=True, help="Output zip path")
    pkg.add_argument("--mode", choices=mode_choices, default="submission",
                     help="Video mode (default: submission). Reported in the output JSON for traceability.")
    pkg.add_argument("--max-mb", type=float, default=250.0, help="Size ceiling MB (default: 250)")
    pkg.add_argument("--json-out", help="Path to write JSON result")
    pkg.set_defaults(func=cmd_package)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())

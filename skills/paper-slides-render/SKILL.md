---
name: paper-slides-render
description: "Render a narrated presentation MP4 from a compiled slide deck plus its talk script. Synthesizes per-slide audio via edge-tts, rasterizes slides via pdftoppm, composes per-slide ffmpeg segments, concatenates into 1080p30 H.264, and optionally burns word-aligned subtitles via whisper. Bridges /paper-slides (emits PDF + TALK_SCRIPT.md) and /paper-video (gates a venue-ready MP4). Use when user says \"把幻灯片做成视频\", \"生成讲解视频\", \"render slides to video\", \"narrate the slides\", \"slide narration video\", or \"PPT 讲解视频\". NOT for recorded demos (use /paper-video) or for producing the slides themselves (use /paper-slides)."
argument-hint: "[slides-dir-or-pdf] [— voice: en-US-AvaNeural] [— with-subtitles] [— resolution: 1920x1080] [— fps: 30] [— workspace: .]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob
---

# Paper Slides Render: Slides → Narrated MP4

Turn a compiled slide deck plus its talk script into a watchable narrated MP4: **$ARGUMENTS**

Claude is the **orchestrator**; a self-contained Python helper does the work: TTS (`edge-tts`), rasterization (`pdftoppm`), per-slide ffmpeg compose, concat, optional whisper-aligned subtitle burn-in. The output drops at `slides/render/presentation.mp4` and is ready to feed into `/paper-video` for venue gating.

## Why this skill exists

`/paper-slides` produces `slides/main.pdf` plus `slides/TALK_SCRIPT.md`. `/paper-video` packages and venue-gates a finished MP4. Nothing in between turned the slides + script into the actual video the user can watch — which is exactly the gap the [Paper2Video](https://github.com/showlab/Paper2Video) project addresses for AI papers. This bridge fills that gap with a single helper script, no GPU required.

## Constants

- **DEFAULT_VOICE = `en-US-AvaNeural`** — Edge TTS neural voice. Override with `— voice: <name>`. Common alternatives: `en-US-GuyNeural`, `en-GB-RyanNeural`, `zh-CN-XiaoxiaoNeural`. Full list: `edge-tts --list-voices`.
- **DEFAULT_RESOLUTION = `1920x1080`** — 1080p; downscale if PDF is larger.
- **DEFAULT_FPS = `30`** — 30 fps.
- **TARGET_CODEC = `libx264 + aac (faststart)`** — Same codec target as `/paper-video` for compatibility.
- **DURATION_TOLERANCE = `0.15`** — `verify` allows up to ±15 % drift between actual and planned duration. TTS variance makes a fixed-seconds tolerance too loose for short talks and too tight for long ones; fractional tolerance is the right knob.
- **WITH_SUBTITLES = off (default)** — Pass `— with-subtitles` to burn word-aligned subtitles via `whisper base.en`. If whisper is missing the render degrades to no-subs (`subtitles.skipped=true`) and never blocks.
- **OUTPUT_DIR = `slides/render/`** — All artifacts land here.
- **RENDER_HELPER** — canonical name `paper_slides_render.py`, resolved per
  [`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2
  (Policy A — skill-local gate). Canonical location is
  `skills/paper-slides-render/scripts/paper_slides_render.py`; this skill is
  self-contained (Arch C, no shim in `tools/`). Resolve via:

  ```bash
  RENDER_HELPER=""
  if [ -n "${CLAUDE_SKILL_DIR:-}" ] && [ -f "$CLAUDE_SKILL_DIR/scripts/paper_slides_render.py" ]; then
    RENDER_HELPER="$CLAUDE_SKILL_DIR/scripts/paper_slides_render.py"
  fi
  if [ -z "$RENDER_HELPER" ]; then
    cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
    if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
      ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
    fi
    RENDER_HELPER=".aris/tools/paper_slides_render.py"
    [ -f "$RENDER_HELPER" ] || RENDER_HELPER="tools/paper_slides_render.py"
    [ -f "$RENDER_HELPER" ] || { [ -n "${ARIS_REPO:-}" ] && RENDER_HELPER="$ARIS_REPO/skills/paper-slides-render/scripts/paper_slides_render.py"; }
    [ -f "$RENDER_HELPER" ] || RENDER_HELPER=""
  fi
  [ -z "$RENDER_HELPER" ] && {
    echo "ERROR: paper_slides_render.py not resolved (layer 0: \$CLAUDE_SKILL_DIR/scripts/; layers 1-3: .aris/tools/, tools/, \$ARIS_REPO/skills/paper-slides-render/scripts/)." >&2
    echo "       /paper-slides-render cannot proceed. Fix: rerun bash tools/install_aris.sh." >&2
    exit 1
  }
  ```

  All invocations below use `python3 "$RENDER_HELPER" <subcommand>`.

## Scope

| Use case | Fit |
|---|---|
| Turn `/paper-slides` output into a narrated MP4 | ✅ designed for this |
| Conference-talk preview / dry-run video | ✅ |
| Lab-meeting walkthrough video | ✅ |
| Submission demo video from raw clips | ❌ use `/paper-video` |
| Generate the slides themselves | ❌ use `/paper-slides` |
| Cinematic project-page hero video | ❌ use `/paper-video — mode: showcase` |
| Recorded talking-head presentation | ❌ this skill is TTS-only; no avatar render |

## Inputs

Required:

- `slides/main.pdf` — compiled slide deck (one PDF page per slide).
- `slides/TALK_SCRIPT.md` — talk script with the exact header format below.

If `$ARGUMENTS` is a path to a slides directory or a PDF, the skill infers `TALK_SCRIPT.md` next to it (sibling file or parent directory).

### TALK_SCRIPT.md format

Each slide is introduced by an H2 header that names its number, title, and planned time range. The body holds quoted speech the narrator should say. The format matches what `/paper-slides` emits — Phase 8 of that skill is the upstream producer.

```
## Slide 1: Title and Headline [0:00 - 0:15]

"Hi everyone. I'm presenting our work on <topic>. The headline result is <X>."

→ *Transition*: "Let's start with the problem."

---

## Slide 2: Problem Statement [0:15 - 0:45]

"The problem we tackle is <Y>. Existing methods struggle because <Z>."
```

Parsing rules (enforced by the helper):

- Headers must match `## Slide N: <title> [MM:SS - MM:SS]` (hyphen, en-dash `–`, or em-dash `—` accepted). Trailing annotations after the bracket — e.g. `[0:00 - 0:15]  (~40 words)` or `· 5× [VIDEO: …]` — are tolerated and ignored, so `/paper-slides` output parses without hand-editing.
- The body is everything between the header and the next `## Slide` header, or a horizontal-rule `---` line, whichever comes first.
- **Only quoted text becomes narration**. Straight quotes (`"..."`) and curly quotes (`"..."`) are both detected.
- `→ *Transition*: ...` markers are stripped.
- Italicized stage directions (`*[Wait for chair...]*` lines) are stripped.
- If no quotes are found, the helper falls back to the full body with markdown stripped, and flags the slide in `fallback_mode_slides`.
- A slide body may carry `[VIDEO: ...]` marker(s). A bare `[VIDEO: path]` swaps the whole rasterized PNG for the clip (full-frame; one per slide). Anchored markers `[VIDEO: clip ON still.png]` overlay each clip onto the still it names, in place — **multiple per slide** — preserving the slide's own title/captions. See [Embedding experiment videos](#embedding-experiment-videos) for syntax + duration semantics.

## Workflow: MUST EXECUTE ALL STEPS

### Phase 0: Inputs + Preflight

Render this checklist explicitly:

```text
📋 paper-slides-render checklist:
   [ ] 1. Resolve $RENDER_HELPER via §2 resolver (above)
   [ ] 2. Confirm slides/main.pdf + slides/TALK_SCRIPT.md exist
   [ ] 3. mkdir -p slides/render/
   [ ] 4. python3 "$RENDER_HELPER" preflight --workspace <cwd> [--with-subtitles] --json-out slides/render/preflight.json
   [ ] 5. Confirm preflight JSON says ok=true (edge-tts + pdftoppm + ffmpeg + ffprobe + writable output dir)
   [ ] 6. Phase 1 parse to preview the slide model (STOP for user confirmation)
   [ ] 7. Phase 2 render via "$RENDER_HELPER" render ...
   [ ] 8. Phase 3 verify via "$RENDER_HELPER" verify --video <mp4> --talk-script <md>
```

1. Confirm inputs exist:

   ```bash
   [ -f slides/main.pdf ] || { echo "ERROR: slides/main.pdf missing"; exit 1; }
   [ -f slides/TALK_SCRIPT.md ] || { echo "ERROR: slides/TALK_SCRIPT.md missing"; exit 1; }
   mkdir -p slides/render
   ```

2. Run preflight:

   ```bash
   python3 "$RENDER_HELPER" preflight \
     --workspace . \
     --talk-script slides/TALK_SCRIPT.md \
     ${WITH_SUBTITLES:+--with-subtitles} \
     --json-out slides/render/preflight.json
   ```

   The `--talk-script` flag is optional but recommended — it lets preflight probe any `[VIDEO: ...]` clip references and fail fast on missing files or out-of-bounds trim ranges, before any TTS or ffmpeg work starts. See [Embedding experiment videos](#embedding-experiment-videos) below.

3. If `ok=false`, stop and surface the helper's error verbatim. The most common cause is `edge-tts` not installed: `pip install edge-tts`. For `pdftoppm`: `apt-get install poppler-utils` (Linux) or `brew install poppler` (macOS). For missing/invalid video clips, fix the referenced file or the trim range in `TALK_SCRIPT.md`.

4. Write the initial `slides/render/RENDER_STATE.json` with `phase: 0`:

   ```json
   {
     "phase": 0,
     "status": "in_progress",
     "voice": "en-US-AvaNeural",
     "with_subtitles": false,
     "resolution": "1920x1080",
     "fps": 30,
     "timestamp": "<now>"
   }
   ```

### Phase 1: Parse & Preview (STOP for confirmation)

```bash
python3 "$RENDER_HELPER" parse \
  --talk-script slides/TALK_SCRIPT.md \
  --slides-pdf slides/main.pdf \
  --json-out slides/render/parse.json
```

Then present a per-slide table to the user (slide number, title, planned duration, first 60 chars of speakable text, and **video clip** if a `[VIDEO: ...]` marker is present — show path + effective duration). If `parse.json.fallback_mode_slides` is non-empty, ⚠️ flag those slides — the helper used a markdown-stripped body instead of quoted speech, which usually means the talk script needs quotes. If any slide carries a `video_clip` whose `exists` is `false`, ⛔ stop and ask the user to fix the path.

**⛔ STOP HERE**. Confirm with the user:

- Slide count matches what `slides/main.pdf` actually contains.
- No fallback-mode slides (or the user accepts the fallback).
- Voice + subtitle flags are correct.
- Video-clip-backed slides (if any) point at the intended clips and trim ranges.

On "go", advance state to `phase: 1`.

### Phase 2: Render

```bash
python3 "$RENDER_HELPER" render \
  --slides-pdf slides/main.pdf \
  --talk-script slides/TALK_SCRIPT.md \
  --output slides/render/presentation.mp4 \
  --voice "${VOICE:-en-US-AvaNeural}" \
  --resolution "${RESOLUTION:-1920x1080}" \
  --fps "${FPS:-30}" \
  --workspace . \
  ${VENUE_CAP:+--max-seconds $VENUE_CAP} \
  ${RATE:+--rate "$RATE"} \
  ${WITH_SUBTITLES:+--with-subtitles} \
  --json-out slides/render/render.json
```

`--workspace` may be the paper dir (which contains `slides/`) **or** the slides dir itself — the helper auto-detects and never doubles the path.

Pass `--max-seconds <cap>` whenever the talk has a venue ceiling (e.g. 180 for CoRL / NeurIPS-supp). The helper synthesizes all narration first, then **projects the final length before the expensive compose**, so an over-budget deck is caught early (see exit 4 below) rather than after a full render. `--rate +10%` (edge-tts speed delta) is the no-rewrite remedy when it overruns.

This is long-running. Per slide it: looks up cached audio (content-hash on voice + text + rate) and PNG (mtime on PDF) → falls back to `edge-tts` and `pdftoppm` only on cache miss → projects total vs `--max-seconds` and halts if over (exit 4) → optionally calls `whisper` for word-level alignment → composes a per-slide MP4 segment (still slides held for exactly narration length; deterministic, no `-shortest` overshoot) → concatenates everything with `-movflags +faststart` → if `--with-subtitles` and whisper produced SRTs, re-encodes once with a subtitle burn-in pass.

On non-zero exit:

- Exit 1 — parse / TTS / pdftoppm failed. Read `render.json.tts_errors` or `error` field, fix, rerun. Do NOT auto-retry; most failures are user-actionable (network drop, malformed script).
- **Exit 4 — projected duration over `--max-seconds`** (halted after TTS, before any compose). The JSON carries `projected_seconds`, `cap_seconds`, `over_by_seconds`, and a `per_slide` breakdown. **STOP and ask the user** how to proceed: trim narration on the longest slides, re-render with `--rate +N%`, or re-run with `--allow-over-cap` to accept the overflow. Do not silently proceed.
- Exit 3 — ffmpeg or whisper failed. Stderr is captured verbatim in the JSON. Read it before rerunning.

Whisper-missing with `--with-subtitles` is **not** a failure: `render.json.subtitles.skipped=true` with `skipReason="whisper-missing"`, and the MP4 is produced without subtitles.

Advance state to `phase: 2`.

### Phase 3: Verify

```bash
python3 "$RENDER_HELPER" verify \
  --video slides/render/presentation.mp4 \
  --talk-script slides/TALK_SCRIPT.md \
  --duration-tolerance 0.15 \
  --json-out slides/render/verify.json
```

Gates (all hard fails → exit 2):

- `exists` — file present and non-zero size.
- `video_codec` ∈ {`h264`, `hevc`, `av1`}.
- `audio_codec` ∈ {`aac`, `ac3`, `opus`} **and** an audio stream must exist (narration is required for this skill).
- `pixel_format == yuv420p`.
- `faststart` — moov atom at file head.
- `duration_match` — `|actual − planned_from_script| ≤ tolerance × planned`.
- `fps ≤ 60`, `width × height ≤ 3840×2160`.

Verify must produce `ok=true`. If `ok=false`, surface violations and stop.

Then report to the user:

- Path: `slides/render/presentation.mp4`
- Total duration vs. planned + per-slide drift table (from `render.json.slides[].drift_seconds`).
- Size in MB.
- If the user wants venue gating (CoRL / NeurIPS-supp / etc.), recommend `/paper-video — mode: showcase` or `— mode: teaser` next. Submission-mode is unlikely to be the right fit (a 10-min narrated talk overflows the 180 s CoRL cap; for that case render a teaser cut).

Advance state to `phase: 3, status: "completed"`.

## State Files

`slides/render/RENDER_STATE.json` tracks progress across the four phases (mirrors `SLIDES_STATE.json` from `/paper-slides`):

```json
{
  "phase": 2,
  "status": "in_progress",
  "voice": "en-US-AvaNeural",
  "with_subtitles": true,
  "resolution": "1920x1080",
  "fps": 30,
  "slide_count": 12,
  "talk_script_sha256": "...",
  "slides_pdf_sha256": "...",
  "timestamp": "2026-05-21T15:00:00Z"
}
```

Resume rule: if state exists with `status: "in_progress"`, `timestamp` is within the last 24 h, and the SHAs of `TALK_SCRIPT.md` + `main.pdf` still match → resume from `phase + 1`. Otherwise → fresh start, backing up the old `slides/render/` to `slides/render-backup-<ts>/` before clobbering.

## Output Layout

After a successful run:

```
slides/render/
├── RENDER_STATE.json
├── preflight.json
├── parse.json
├── narrate.json            # only if narrate was invoked standalone
├── render.json
├── verify.json
├── audio/
│   ├── slide_01.wav
│   ├── slide_01.meta.json  # {voice, content_hash, generated_at}
│   └── ...
├── png/
│   └── slide_01.png
├── segments/
│   └── slide_01.mp4        # per-slide ffmpeg output, kept for re-runs
├── srt/                    # only if --with-subtitles
│   └── slide_01.srt
├── subtitles.srt           # merged with cumulative timestamp offsets
└── presentation.mp4        # ⭐ deliverable
```

## Failure Policy

This skill follows **Policy A (skill-local gate)** per `shared-references/integration-contract.md` §2. Helper subcommand exit codes:

| Subcommand | Non-`ok` consequence | Exit |
|---|---|---|
| `preflight` | Halt before render; surface missing dep | 1 |
| `parse` | Halt; user fixes TALK_SCRIPT.md | 1 |
| `narrate` | Continue per-slide; final `ok=false` if any slide failed | 1 if any failed |
| `render` | Halt at failing step. Subtitles-missing degrades, does NOT fail. | 1 (TTS / pdftoppm / parse), 3 (ffmpeg / whisper) |
| `render --max-seconds N` | Projected total over cap → halt after TTS, before compose; **orchestrator STOPs and asks user** | 4 |
| `verify` | Report all violations | 2 |

Soft-fail slot: `subtitles.skipReason ∈ {"whisper-missing", "whisper-failed", "alignment-merge-failed", "ffmpeg-subtitle-burn-failed"}`. Subtitle failure is the only soft-fail in the entire skill.

## Idempotency Contract

- Re-running `render` with unchanged inputs **reuses** cached audio (per-slide content-hash on voice+text+rate) and PNGs (per-slide PDF mtime). Skipped work is logged with `audio_cached: true` or `png_cached: true`. Changing `--rate` invalidates only the audio cache.
- `edge-tts` calls a server-side voice; identical input text may produce slightly different waveform bytes across runs. Bit-identical MP4 is **not** guaranteed — `verify.json.ok=true` is the acceptance criterion.
- `render` writes the output MP4 atomically (`.tmp` then `replace`).
- `preflight`, `parse`, `narrate`, `verify` never mutate the source `slides/main.pdf` or `slides/TALK_SCRIPT.md`.

## When to skip this skill

- The user wants the slides themselves, not a video — use `/paper-slides` (with `/slides-polish` for per-page review).
- The user has raw experiment recordings and wants a submission video — use `/paper-video`.
- The user wants a 15-min conference oral recording of themselves presenting — this skill is TTS-only; record manually.

## Recommended follow-ups

- `/paper-video` to gate the output against a venue's submission limits (mode = `showcase` for camera-ready, `teaser` for social, or `submission` if the talk fits).
- Manual subtitle proofreading on `slides/render/subtitles.srt` if the talk uses domain-specific jargon whisper may mis-transcribe.

## Defaults Summary

| Setting | Default | Override |
|---|---|---|
| Voice | `en-US-AvaNeural` | `— voice: <edge-tts voice name>` |
| Resolution | `1920x1080` | `— resolution: WxH` |
| FPS | `30` | `— fps: N` |
| Subtitles | off | `— with-subtitles` |
| Narration rate | normal | `— rate: +10%` / `-5%` (edge-tts speed; remedy for over-cap decks) |
| Duration cap | none | `— max-seconds: N` (halt after TTS if projected total over cap; exit 4) |
| Duration tolerance | 15 % | `--duration-tolerance 0.10` (on the helper directly) |

Edge TTS voice list: `edge-tts --list-voices` (200+ voices across 50+ locales).

## Embedding experiment videos

Robotics, manipulation, and animation work usually needs a moving demonstration on at least one slide — the static PDF page can't communicate "the arm grasps the unseen object in two seconds". This skill lets the talk script swap any slide's still PNG for a video clip at compose time, without touching the beamer source.

### Syntax

Add a `[VIDEO: path]` marker on its own line inside a slide body. Paths are resolved relative to `TALK_SCRIPT.md`'s directory; absolute paths are also allowed. A bare marker is **full-frame**: one per slide, extras ignored with a warning.

```markdown
## Slide 3: Grasping Demo [0:30 - 0:42]

[VIDEO: figures/grasp.mp4]

"Our policy executes the grasp on the unseen object in under two seconds."
```

Optional clip trim (start–end inside the source clip; seconds or `MM:SS`):

```markdown
[VIDEO: figures/grasp.mp4 @ 2.5-7.0]
[VIDEO: figures/grasp.mp4 @ 0:02-0:07]
```

### In-place overlays (`ON <still>`) — multiple clips per slide

When a slide already lays out several still thumbnails (e.g. a task gallery), anchor each clip to the still it should replace with `ON <still.png>`. **Multiple anchored markers per slide are allowed** — this is the only way to animate more than one region of a slide.

```markdown
## Slide 5: Five-task gallery [1:27 - 2:00]

[VIDEO: figures/safe_rollout.mp4 ON figures/still_safe.png]
[VIDEO: figures/lamp_rollout.mp4 ON figures/still_lamp.png]
[VIDEO: figures/door_rollout.mp4 @ 0-1.5 ON figures/still_door.png]

"EMT-QA spans five tasks..."
```

How it works: the helper rasterizes the slide, locates each named still on the page by **template matching** (cv2 normalized cross-correlation, multi-scale — so it recovers the LaTeX-decided box without manual coordinates), and overlays the clip there, looping/trimmed and muted. The slide's own title, captions, and layout are preserved because the rasterized page is the background; only the thumbnails come alive. Requires `opencv-python`; if absent the helper errors only for slides that use `ON` (bare full-frame markers are unaffected). `parse`/`preflight` report each clip's `anchor_path` + `anchor_exists`, and `render.json` logs per-overlay `box` + `match_score` and any `unmatched_overlays`.

> Anchored overlays are still **one composite per slide** under the hood — exactly the "pre-stitch, reference once" pattern, but automated. Unlike a hand-built grid, the slide's real captions and structure survive.

### Duration policy

For a video-backed slide the helper computes `total = max(narration_dur, clip_effective_dur)` and:

| Case | Behavior |
|---|---|
| `narration > clip` | Loop the clip until narration finishes. **No upper cap on loop count** — a 60 s narration over a 1 s clip plays 60 loops. Use trim to make the loop unit longer if that's a problem. |
| `clip > narration` | Narration plays once at the start; remainder is silent until the clip finishes. |
| `narration == clip` | Plays once. |

Always: **the clip's source audio is muted** (motor whirr, ambient sound, etc. are discarded). Narration is the only audio track in the output. If you want clip audio mixed in, render the clip into the beamer PDF via `\movie` instead — this skill won't do dubbing.

### Aesthetic notes

- Video slides are letterboxed/pillarboxed against a **black** background to match `/paper-video`'s clip pipeline. Still-PNG slides use white. Mixing both in one deck is fine but the pad color visibly differs at clip boundaries.
- The PDF still shows whatever figure beamer rendered — VIDEO markers are a render-time substitution, not a beamer change. Reviewers who only have the PDF (no MP4) still see the static figure.

### Where `[VIDEO: ...]` markers do NOT take effect

`[VIDEO: ...]` is a **render-time substitution for this skill's MP4 output only**. It is not a slide-embedding mechanism. In particular:

- **`slides/main.pdf`** — beamer renders whatever the LaTeX source declared (typically `\includegraphics{...}` for a still). VIDEO markers are inside `TALK_SCRIPT.md`, not in the LaTeX, so the PDF is unchanged. If you want a playable clip inside the PDF, use beamer `\movie` / `media9` — but those depend on a video-capable PDF reader (Adobe Reader yes; Preview / zathura / most browsers no), which is why this skill bypasses them.
- **`slides/presentation.pptx`** — the PPTX produced by `/paper-slides` Phase 7 uses `python-pptx`, which can write images, shapes, and text but **cannot embed video shapes**. So the same slide that displays a clip in `presentation.mp4` will display the still figure (or be empty) in `presentation.pptx`. If you need a playable clip inside the PPTX for live presentation, add the video manually in PowerPoint / Keynote after Phase 7 — that path is out of scope for this skill.

In short: VIDEO markers are honored **only** in the MP4 produced by `python3 "$RENDER_HELPER" render`. They are silently inert in the PDF and PPTX outputs of `/paper-slides`.

### Preflight (recommended)

Pass `--talk-script` to preflight so missing files / out-of-bounds trim ranges fail before any TTS or ffmpeg work starts:

```bash
python3 "$RENDER_HELPER" preflight \
  --workspace . \
  --talk-script slides/TALK_SCRIPT.md \
  --json-out slides/render/preflight.json
```

`preflight.json.clips[]` lists every referenced clip with `exists`, `source_duration_seconds`, `width`, `height`, and `effective_duration_seconds` (after trim). Non-zero exit on any missing clip or trim range exceeding the source duration.

### When NOT to embed video here

- **Whole project-page video / supplementary submission video** → use `/paper-video` directly. It's tuned for assembling raw clips with shot lists and venue gates.
- **Multi-clip composition on one slide** (side-by-side rollouts, picture-in-picture) → pre-stitch into one MP4 via `/paper-video` or external tools, then reference it via a single VIDEO marker.
- **Animated slide transitions** → out of scope; this skill renders each slide as a discrete segment and concatenates with cuts.

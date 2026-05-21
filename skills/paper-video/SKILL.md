---
name: paper-video
description: "Produce a paper-submission demonstration video (CoRL / ICRA / RSS / NeurIPS-supp / project-page) under hard size + duration gates. Default target: H.264 MP4, ≤180 s, ≤250 MB (CoRL ceiling). Claude plans narration + shot list, ffmpeg assembles raw clips, helper enforces gates, optional zip-package emits the full supplementary bundle. Use when user says \"做 supplementary video\", \"做投稿 demo 视频\", \"CoRL video\", \"demo video\", \"supp 视频\", or wants the recorded experiments turned into a submission-ready clip."
argument-hint: "[paper-dir-or-raw-clips] [— mode: submission|showcase|teaser] [— venue: CORL|ICRA|RSS|NEURIPS|GENERIC] [— max-mb: N] [— max-seconds: N] [— with-subtitles] [— with-narration]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex, mcp__codex__codex-reply
---

# Paper Video: Submission-Ready Demonstration Video

Build a paper-submission demonstration video from: **$ARGUMENTS**

Claude is the **planner / narrator / reviewer**; ffmpeg is the **renderer**; a
self-contained Python helper is the **gate** that enforces venue-specific
size + duration limits. The deliverable is a single `submission/video/<name>.mp4`
plus an optional `supplementary.zip` bundle, both verified against the venue's
hard ceilings before being marked `submission-ready`.

## Why this skill exists

CoRL, ICRA, RSS, NeurIPS-supp and most robotics venues require a short
demonstration video as part of the supplementary package. These submissions
fail silently when the upload silently truncates or the reviewer's player
refuses the codec. This skill exists to make every produced video pass the
venue's *literal* upload limits before claiming success — never just "looks
about right".

## Constants

- **DEFAULT_MODE = `submission`** — Three modes governing tone, anonymity, length, and CTA. See **Mode Profiles** below. Override with `— mode:`.
- **DEFAULT_VENUE = `CORL`** — Determines `MAX_MB` / `MAX_SECONDS` for `submission` mode (other modes default by mode, not venue). Override with `— venue:`.
- **MAX_MB = 250** — Hard size ceiling. CoRL strict. ICRA/RSS typically ≤100 MB. `showcase` / `teaser` modes target a smaller size (web-friendly).
- **MAX_SECONDS** — Soft duration ceiling. `submission` → venue cap (CoRL: 180 s "suggested"). `showcase` → 90 s. `teaser` → 45 s. Verified; over-cap is a soft fail.
- **TARGET_CODEC = `libx264 + aac (faststart)`** — Most-compatible across reviewer players.
- **TARGET_RESOLUTION = `1920x1080`** — 1080p; we downscale 4K input, never upscale.
- **TARGET_FPS = `30`** — 30 fps; matches most experiment recordings.
- **OUTPUT_DIR = `submission/video/`** — All artifacts land here (named after the most common case — overridable).
- **SUPPLEMENTARY_DIR = `submission/supplementary/`** — Optional zip bundle root.
- **NARRATION_LANGUAGE = `English`** — Default. CoRL / ICRA / RSS are English-only. Default narration is **off** for `submission`, **on** for `showcase` / `teaser`; override with `— with-narration` / `— no-narration`.
- **VENUE_PROFILES** — Built into the helper. CORL: 250 MB / 180 s. ICRA: 100 MB / 180 s. RSS: 100 MB / 300 s. NEURIPS: 100 MB / 600 s. GENERIC: caller-supplied.
- **MODE_PROFILES** — Built into the helper. `submission` → use venue limits + anon scan. `showcase` → 100 MB / 90 s, no anon scan. `teaser` → 50 MB / 45 s, no anon scan.
- **VIDEO_HELPER** — canonical name `paper_video.py`, resolved per
  [`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2
  (Policy A — skill-local gate). Canonical location is
  `skills/paper-video/scripts/paper_video.py`; this skill is self-contained
  (Arch C, no shim in `tools/`). Resolve via:

  ```bash
  VIDEO_HELPER=""
  if [ -n "${CLAUDE_SKILL_DIR:-}" ] && [ -f "$CLAUDE_SKILL_DIR/scripts/paper_video.py" ]; then
    VIDEO_HELPER="$CLAUDE_SKILL_DIR/scripts/paper_video.py"
  fi
  if [ -z "$VIDEO_HELPER" ]; then
    cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
    if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
      ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
    fi
    VIDEO_HELPER=".aris/tools/paper_video.py"
    [ -f "$VIDEO_HELPER" ] || VIDEO_HELPER="tools/paper_video.py"
    [ -f "$VIDEO_HELPER" ] || { [ -n "${ARIS_REPO:-}" ] && VIDEO_HELPER="$ARIS_REPO/skills/paper-video/scripts/paper_video.py"; }
    [ -f "$VIDEO_HELPER" ] || VIDEO_HELPER=""
  fi
  [ -z "$VIDEO_HELPER" ] && {
    echo "ERROR: paper_video.py not resolved (layer 0: \$CLAUDE_SKILL_DIR/scripts/; layers 1-3: .aris/tools/, tools/, \$ARIS_REPO/skills/paper-video/scripts/)." >&2
    echo "       /paper-video cannot proceed. Fix: rerun bash tools/install_aris.sh." >&2
    exit 1
  }
  ```

  All invocations below use `python3 "$VIDEO_HELPER" <subcommand>`.

## Mode Profiles

A submission-review video and a camera-ready / project-page video are
**different artifacts** with different audiences, different anonymity rules,
and different optimal lengths. This skill exposes three modes; pick one
explicitly at the call site.

| Aspect | `submission` (default) | `showcase` | `teaser` |
|---|---|---|---|
| **Audience** | 3-4 skeptical reviewers | Public, citations, project page | Social media (X, BlueSky) |
| **Anonymity** | Strict (no logo / lab / URL / QR / email) | Free (lab logos, project URL, arXiv ID expected) | Free |
| **Default duration** | Venue cap (CoRL: 180 s) | 90 s | 45 s |
| **Default size cap** | Venue cap (CoRL: 250 MB) | 100 MB | 50 MB |
| **Captions** | **Mandatory** (assume muted playback) | Optional (audio narration carries) | Optional |
| **Voiceover narration** | Off by default | **On by default** | On by default |
| **Music / BGM** | Avoid (distracts reviewer) | Allowed (light) | Allowed |
| **Failure cases** | Encouraged (one honest failure) | Skip | Skip |
| **Comparison vs baselines** | Full side-by-side with numbers | One quick "vs prior" cut | Hero shot only |
| **Pace / cuts** | Slow, deliberate, label-heavy | Fast, energetic | Very fast, trailer-style |
| **Title cards** | Plain (white background, sans-serif) | Brand-styled, motion-graphic optional | Brand-styled, big text |
| **Closing card** | "See paper for details" | `arxiv.org/abs/...` + project URL | Project URL + arXiv |
| **Identifying info scan** | **On** (helper greps manifest for URL / email / @-handle) | Off | Off |

Pick the mode that matches the **deadline you are working against**:

- Submitting to the venue's CMT / OpenReview portal in the next 7 days → `submission`
- Paper just got accepted; building the project page, Twitter thread, talk preview → `showcase`
- Already have a showcase; need a 45-second cut for social → `teaser`

You can produce all three from the same raw clips — re-run with different
`— mode` and `— output`. The manifest will usually need pruning between
modes (showcase / teaser drop the failure-case shots).

## Scope

| Use case | Fit |
|---|---|
| Robotics demonstration video (CoRL / ICRA / RSS) | ✅ designed for this |
| NeurIPS / ICLR / ICML supplementary video | ✅ |
| Project-page short clip | ✅ |
| Conference oral / talk recording | ❌ use `/paper-talk` |
| Per-page slide narration | ❌ use `/slides-polish` |
| Photo-realistic generated B-roll | ❌ out of scope — bring your own clips |

## Workflow: MUST EXECUTE ALL STEPS

### Step 0: Pre-flight Check

Render this checklist explicitly before starting:

```text
📋 paper-video integration checklist:
   [ ] 1. python3 "$VIDEO_HELPER" preflight --workspace <cwd> --mode <MODE> --venue <VENUE> --json-out submission/video/preflight.json
   [ ] 2. Confirm preflight JSON says ok=true (ffmpeg + ffprobe + writable OUTPUT_DIR)
   [ ] 3. Plan shot list + narration (Step 1)
   [ ] 4. Assemble via python3 "$VIDEO_HELPER" assemble --manifest <manifest.json> --mode <MODE>
   [ ] 5. Verify via python3 "$VIDEO_HELPER" verify --video <mp4> --mode <MODE> --venue <VENUE> --manifest <manifest.json> --json-out submission/video/verify.json
   [ ] 6. (Optional) Package supplementary via python3 "$VIDEO_HELPER" package
```

1. Create `submission/video/` and (optional) `submission/supplementary/` if missing.
2. Confirm raw input exists. Typical sources:
   - `recordings/*.mp4` — screen / camera captures
   - `figures/` — already-rendered explainer images (turned into static title cards)
   - `wandb_videos/` — RL rollout exports
3. Run:

```bash
python3 "$VIDEO_HELPER" preflight \
  --workspace . \
  --mode "${MODE:-submission}" \
  --venue "${VENUE:-CORL}" \
  --json-out submission/video/preflight.json
```

4. If preflight is not `ok=true`, stop and report which dependency is missing
   (ffmpeg / ffprobe / writable output dir). Do not attempt fallbacks.

### Step 1: Claude Plans the Shot List

Turn the user request + paper context into a structured **shot manifest**.
This is a JSON file the helper consumes. Required structure:

```json
{
  "venue": "CORL",
  "title": "Title Card (optional, <=5s)",
  "narration_language": "English",
  "shots": [
    {
      "kind": "title_card",
      "text": "Method Name — Anonymous Submission",
      "duration": 3.0
    },
    {
      "kind": "clip",
      "source": "recordings/task_a_attempt_1.mp4",
      "start": 1.5,
      "end": 22.0,
      "caption": "Task A: pick-and-place under occlusion (1× speed)",
      "speed": 1.0
    },
    {
      "kind": "clip",
      "source": "recordings/task_b_baseline.mp4",
      "start": 0.0,
      "end": 18.0,
      "caption": "Baseline policy fails after 2 attempts",
      "speed": 2.0
    },
    {
      "kind": "title_card",
      "text": "10× faster training, 23% higher success rate",
      "duration": 4.0
    }
  ]
}
```

Planning rules (Claude enforces — these are mode-specific):

**Universal (all modes):**

- Lead with the result — first 5–10 s must show the strongest demonstration
- Caption every clip in `submission` (mandatory); optional in `showcase` / `teaser` if narration carries
- Speed up baseline failures (2×–4×); never speed up your own method

**`submission` mode (anonymous review):**

- Total budgeted duration ≤ venue MAX_SECONDS — leave 10 % headroom for transitions
- **No talking-head intros** — reviewers skip them
- **No identifying info during double-blind** — strip institution logos, name plates, watermarks
- **No external URLs / QR codes / contact info / email / Twitter handles** during anonymous review (the helper's `verify --mode submission --manifest <m>` greps for these and fails closed)
- **Show one honest failure case** if the venue values reproducibility (CoRL / ICRA / RSS)
- Captions are **mandatory** (reviewer commonly plays muted on a second monitor)
- Final card: plain "See paper for details" — no URL

**`showcase` mode (camera-ready / project page):**

- Default target ≈ 90 s — longer than this loses viewers on the project page
- Hero-shot driven: open with your best 3 seconds of footage, no title card preamble
- **Show lab logos, institution, project URL** — anonymity is over
- Voiceover narration is the default; aim for ~2.0 words / second
- Drop the failure cases unless the failure itself is the story
- Final card: arXiv ID + project URL + GitHub URL stacked vertically
- Light BGM at −18 dB is acceptable; never overpower narration

**`teaser` mode (social media):**

- Default target ≈ 45 s — Twitter / BlueSky video cap is short
- Trailer pacing — many cuts, big captions, fast comparison
- Heavy on hero shots and headline numbers; skip method details
- One result, one number, one CTA — anything more is too much for 45 s
- Final card: project URL only (3 s, big text)

Save the manifest to `submission/video/manifest.json`.

### Step 2: (Optional) Narration Script

Narration default is **mode-dependent**:

- `submission` — narration **off** (reviewers commonly play muted; captions are the channel)
- `showcase` — narration **on** (voiceover is the primary attention driver)
- `teaser` — narration **on**, terse

Override either way with `— with-narration` / `— no-narration`. When narration
is on, draft an English voiceover with these constraints:

- ~2.0 words / second for showcase, ~1.6 wps for teaser (matches faster cuts)
- ~432 words for a 180 s submission, ~180 for a 90 s showcase, ~70 for a 45 s teaser
- Tied to shot timing — every shot in `manifest.json` gets a `narration` field
- Read aloud — short sentences, active voice, no acronym soup
- Mention the headline number twice (intro + outro) for showcase; once for teaser

Persist as `submission/video/narration.md`. If the user has a TTS tool, the
helper's `narrate` subcommand can splice a WAV track later (out of MVP scope,
but the slot is reserved).

### Step 3: (Optional) Subtitle Track

If `— with-subtitles` is set, emit an SRT file `submission/video/subtitles.srt`
that the helper burns in. Subtitles are non-optional for accessibility on most
project pages, but reviewer videos usually rely on captions baked into shots.

### Step 4: Assemble via ffmpeg

Hand the manifest to the helper:

```bash
python3 "$VIDEO_HELPER" assemble \
  --manifest submission/video/manifest.json \
  --output submission/video/supplementary.mp4 \
  --mode "${MODE:-submission}" \
  --target-mb 230 \
  --target-resolution 1920x1080 \
  --target-fps 30 \
  --json-out submission/video/assemble.json
```

`--mode` is passed through to disambiguate output filenames in logs and to
trigger mode-aware default size/duration. For `showcase` / `teaser`, the
suggested filename is `submission/video/showcase.mp4` / `teaser.mp4` to keep
the three artifacts side-by-side.

The helper:

1. Trims each clip to `[start, end]` with `-ss / -to` and re-encodes at the
   target resolution / fps.
2. Applies `setpts=PTS/<speed>` for non-1× clips and drops/duplicates frames
   to keep the audio in sync.
3. Renders title cards from `text` via ffmpeg's `drawtext` over a solid
   background matching the venue palette (CoRL = white, NeurIPS = white).
4. Concatenates everything with the concat demuxer (`-c copy` impossible
   here because each input has different params, so we re-encode in one pass
   with `-filter_complex concat`).
5. Picks a target bitrate that lands the output just below `--target-mb`
   (default = MAX_MB − 20 MB safety margin).

If `assemble.json` has `ok=false`, the failing ffmpeg stderr is included
verbatim — do not retry blindly; read it, fix the manifest, rerun.

### Step 5: Verify Against Venue + Mode Gates

This is the **blocking gate**. The helper exits non-zero if any gate fails:

```bash
python3 "$VIDEO_HELPER" verify \
  --video submission/video/supplementary.mp4 \
  --mode "${MODE:-submission}" \
  --venue "${VENUE:-CORL}" \
  --manifest submission/video/manifest.json \
  --json-out submission/video/verify.json
```

`--manifest` is required when `--mode submission` so the anonymity scan can
run. Omit it for `showcase` / `teaser` (or pass it but skip the scan).

Gates checked (all modes):

- `size_bytes ≤ MAX_MB × 1024 × 1024` — **hard fail**
- `duration_seconds ≤ MAX_SECONDS` — **soft fail** (limits differ by mode)
- `video_codec ∈ {h264, hevc, av1}` — hard fail
- `audio_codec ∈ {aac, ac3, opus, none}` — hard fail
- `pixel_format == yuv420p` — hard fail (older players choke on yuv422/444)
- `faststart` MOOV atom at front — hard fail (silent stall on web players)
- `fps ≤ 60`, `width ≤ 3840`, `height ≤ 2160` — sanity

Additional `submission`-only gate:

- `no_identifying_strings` — manifest title cards / captions are grepped
  against a built-in blocklist (URLs, emails, `@handle`, `github.com`,
  `.edu` / `.ac.uk` domains) plus any caller-supplied `--anon-blocklist`
  regex. **Hard fail** when matched. This is the same check reviewers do
  manually; failing here means your video would expose your identity.

`verify.json` schema:

```json
{
  "ok": true,
  "video": "submission/video/supplementary.mp4",
  "mode": "submission",
  "venue": "CORL",
  "limits": {"max_mb": 250, "max_seconds": 180},
  "actual": {
    "size_mb": 231.4,
    "duration_seconds": 178.2,
    "video_codec": "h264",
    "audio_codec": "aac",
    "pixel_format": "yuv420p",
    "faststart": true,
    "fps": 30.0,
    "width": 1920,
    "height": 1080
  },
  "anon_scan": {"checked": true, "matches": []},
  "violations": [],
  "checkedAt": "2026-05-19T10:00:00Z"
}
```

If any gate fails, the helper writes `violations: [...]` with a one-line
remediation hint per violation. Do not claim "submission-ready" without
`ok=true`.

### Step 6: Claude Reviews the Final Video

Visual review pass (Claude opens the MP4 — only if the user is interactive
and the IDE can preview MP4 in line; otherwise skip):

- First 10 s leads with the strongest result?
- Captions readable at YouTube 480p quality?
- No accidental name plate / institution logo / Slack notification leaked?
- Baseline-vs-method comparison is unambiguous?
- Final card states the headline number?

Score 1-10. If <8, regenerate the manifest and rerun Step 4. Up to
**MAX_VIDEO_ITERATIONS = 3**.

### Step 7: (Optional) Supplementary Package

If the venue also accepts a "supplementary file" (CoRL: "further details
which the reviewers may decide to consult"), package it:

```bash
python3 "$VIDEO_HELPER" package \
  --include submission/video/supplementary.mp4 \
  --include submission/supplementary/ \
  --output submission/supplementary.zip \
  --max-mb 250 \
  --json-out submission/package.json
```

Conventional supplementary contents (Claude curates, helper packages):

- `supplementary.mp4` (the video; some venues want it inside the zip)
- `appendix.pdf` (additional results / proofs) — only if venue separates
  from main paper; CoRL puts appendix in the main PDF
- `code/` (minimal reproducer, README, requirements)
- `prompts/` (full prompts if the paper uses LLMs)
- `additional_videos/` (alternative angles, failure cases)

The helper enforces zip size limits via stored compression for already-
compressed inputs (`.mp4`, `.png`, `.pdf`) and `deflate` for the rest, and
fails closed if the bundle exceeds `--max-mb`.

### Step 8: Reference the Video (Mode-Dependent)

This step is **mandatory** but the form depends on mode and is done by
Claude editing the appropriate source — the helper does not touch text.

**`submission` mode** — edit the paper LaTeX, **no URLs**:

```latex
\textbf{Supplementary video.}\ A \unit[180]{s} demonstration video is provided in the
supplementary materials, showing %
\textbf{(a)} the proposed method on Task A and Task B in real-world setting,
\textbf{(b)} side-by-side comparison against the strongest baseline, and
\textbf{(c)} a representative failure case discussed in \Cref{sec:limitations}.
```

During **double-blind** review: **do not** include URLs, lab names, or
project-page links anywhere in the supplementary.

**`showcase` mode** — edit the project-page HTML (or camera-ready LaTeX
with the now-de-anonymized author info). URL embedding is encouraged:

```html
<video src="static/showcase.mp4" controls autoplay muted playsinline
       poster="static/hero.jpg" style="width:100%;max-width:960px"></video>
<p>
  <a href="https://arxiv.org/abs/YYMM.NNNNN">Paper</a> ·
  <a href="https://github.com/lab/project">Code</a> ·
  <a href="https://lab.edu/project">Project page</a>
</p>
```

Camera-ready LaTeX add-on (CoRL `[final]` mode):

```latex
\textbf{Project page and code.}\ Demo video, code, and trained checkpoints are available at \url{https://lab.edu/project}.
```

**`teaser` mode** — embed in the social-media post body. Twitter / BlueSky
auto-play, so put the headline number in the first frame, not the post
text. Caption suggestion:

```
[Method Name]: [headline-number] [task] in [setting] — paper + code in 🧵
arxiv.org/abs/YYMM.NNNNN
```

## Output Layout

After a successful run:

```
submission/
├── video/
│   ├── manifest.json           # Step 1
│   ├── narration.md            # Step 2 (optional)
│   ├── subtitles.srt           # Step 3 (optional)
│   ├── preflight.json          # Step 0
│   ├── assemble.json           # Step 4
│   ├── supplementary.mp4       # ⭐ deliverable
│   └── verify.json             # Step 5 — submission gate
├── supplementary/              # Step 7 (optional bundle)
│   ├── code/
│   ├── prompts/
│   └── ...
├── supplementary.zip           # Step 7 (optional packaged)
└── package.json                # Step 7 (optional zip verify)
```

## Failure Policy

This skill follows **Policy A (skill-local gate)** per
`shared-references/integration-contract.md` §2. If `preflight`, `assemble`,
`verify`, or `package` exit non-zero, the skill **stops** and surfaces the
helper's error verbatim. There are no fallbacks. A failed `verify` is not
"close enough" — reviewer upload portals enforce the same gates, silently.

## Idempotency Contract

- Re-running with an unchanged `manifest.json` produces an MP4 with the same
  duration / resolution but bit-for-bit identical output is not guaranteed
  (ffmpeg encoder non-determinism). Treat `verify.json.ok=true` as the
  acceptance criterion, not file hash.
- `preflight` is read-only except for writing `preflight.json`.
- `assemble` overwrites the output MP4. Save the prior one if you want to
  diff.
- `package` overwrites `supplementary.zip` only if the new bundle passes the
  size gate; on failure the prior zip is preserved.

## When to skip this skill

- If your venue does **not** require a video (most NLP venues, ICLR for
  non-robotics work) — skip.
- If you only need a 30 s teaser clip for a project page — overkill; just
  run ffmpeg directly.
- If the user wants a full conference talk recording (5–20 min) — use
  `/paper-talk` instead; this skill targets the 3-min reviewer demo.

## Defaults Summary

**By venue (used in `submission` mode):**

| Setting | Default | CoRL | ICRA | RSS | NeurIPS-supp |
|---|---|---|---|---|---|
| MAX_MB | 250 | 250 | 100 | 100 | 100 |
| MAX_SECONDS | 180 | 180 | 180 | 300 | 600 |
| Resolution | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 |
| FPS | 30 | 30 | 30 | 30 | 30 |
| Codec | h264 + aac | h264 + aac | h264 + aac | h264 + aac | h264 + aac |
| Faststart | yes | yes | yes | yes | yes |
| Anon scan | yes | yes | yes | yes | yes |

**By mode (overrides venue defaults when set):**

| Setting | `submission` | `showcase` | `teaser` |
|---|---|---|---|
| MAX_MB | venue (e.g. 250 for CoRL) | 100 | 50 |
| MAX_SECONDS | venue (e.g. 180 for CoRL) | 90 | 45 |
| Default narration | off | on | on |
| Default captions | on (mandatory) | optional | optional |
| Anon scan | on | off | off |
| Default output name | `supplementary.mp4` | `showcase.mp4` | `teaser.mp4` |

Override at the command line: `— mode: showcase — max-mb: 80 — max-seconds: 75`.
The helper treats CLI overrides as authoritative over both venue and mode
profiles.

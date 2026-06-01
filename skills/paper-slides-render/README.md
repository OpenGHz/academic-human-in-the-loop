# `/paper-slides-render`

Bridge skill between [`/paper-slides`](../paper-slides/SKILL.md) (PDF + script) and [`/paper-video`](../paper-video/SKILL.md) (venue-gated MP4). Synthesizes per-slide narration with `edge-tts`, rasterizes the deck with `pdftoppm`, composes per-slide ffmpeg segments, concatenates into a single 1080p30 H.264 MP4, and optionally burns word-aligned subtitles via `whisper`.

This README maps the **material flow** — which file feeds which, what each subcommand reads vs. writes, where caches live, and what the final deliverable depends on. For the operational manual (constants, phase prompts, failure policies), see [`SKILL.md`](SKILL.md).

---

## At a glance: end-to-end dependency

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  UPSTREAM (from /paper-slides)                                              │
│                                                                             │
│    slides/main.pdf          ◄── one PDF page per slide                      │
│    slides/TALK_SCRIPT.md    ◄── per-slide quoted narration (+ [VIDEO: …])   │
│                                                                             │
│    figures/<exp>.mp4        ◄── (optional) experiment rollout clips         │
│                                  referenced by [VIDEO: …] markers           │
└─────────────────────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  /paper-slides-render                                                       │
│                                                                             │
│    preflight  ─► slides/render/preflight.json                               │
│    parse      ─► slides/render/parse.json                                   │
│    narrate    ─► slides/render/audio/slide_NN.wav  (+ .meta.json cache)     │
│    render     ─► slides/render/png/slide_NN.png    (rasterize cache)        │
│                ─► slides/render/segments/slide_NN.mp4                       │
│                ─► slides/render/presentation.mp4   ⭐ no-subs MP4 first     │
│                ─► slides/render/srt/slide_NN.srt   (optional, post-concat)  │
│                ─► slides/render/subtitles.srt      (merged)                 │
│                ─► slides/render/presentation.mp4   ⭐ subtitles burned in   │
│                                                       (atomic replace)      │
│    verify     ─► slides/render/verify.json                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DOWNSTREAM                                                                 │
│                                                                             │
│    slides/render/presentation.mp4                                           │
│         │                                                                   │
│         └─► /paper-video --mode submission --venue CORL                     │
│                  ─► supplementary.mp4 (gated against 250 MB / 180 s, etc.)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

The skill is **Arch C** (self-contained Python helper at [`scripts/paper_slides_render.py`](scripts/paper_slides_render.py)). All five subcommands write a JSON envelope to `--json-out` alongside their main artifact, so an orchestrator (`/paper-talk`, `/paper-video`) can read state without parsing stdout.

---

## Per-slide dependency: what feeds one segment

For each slide `NN`, the helper resolves an independent chain. Caches break the chain in two places (PNG, WAV), so a script edit to slide 3 only re-renders slide 3.

```
main.pdf (page NN)                       TALK_SCRIPT.md (## Slide NN …)
        │                                          │
        │ pdftoppm -r 144 -png                     │ parse → speakable text
        │ -singlefile -f NN -l NN                  │   (quotes only;
        ▼                                          │    transitions / stage
   png/slide_NN.png                                │    directions stripped;
        │  cache key: PDF mtime                    │    VIDEO markers extracted)
        │  (skip if PNG newer than PDF)            ▼
        │                                  speakable_text + voice
        │                                          │
        │                                          │ edge-tts CLI / module
        │                                          ▼
        │                                  audio/slide_NN.wav
        │                                  audio/slide_NN.meta.json
        │                                          │  cache key:
        │                                          │  sha256(voice + text + rate)
        │                                          │  (skip if hash matches)
        │                                          │
        │  ┌──────────────────────────────────────┘
        │  │
        ▼  ▼
   ┌────────────────────────────────────────────────────────┐
   │  ffmpeg compose dispatch                               │
   │                                                        │
   │   no [VIDEO:] marker        ─► _ffmpeg_compose_slide   │
   │   (still PNG + narration)     (-loop 1 PNG + WAV,      │
   │                                fixed -t = narration)   │
   │                                                        │
   │   [VIDEO: clip.mp4]         ─► _ffmpeg_compose_        │
   │   (full-frame clip swap)      video_slide              │
   │                               (-stream_loop -1 clip +  │
   │                                WAV, apad to whole_dur) │
   │                                                        │
   │   [VIDEO: clip ON anchor]   ─► _ffmpeg_compose_        │
   │   (in-place overlay)          inplace_slide            │
   │                               (template-match anchor   │
   │                                in PNG, overlay clip)   │
   └────────────────────────────────────────────────────────┘
        │
        ▼
   segments/slide_NN.mp4
   (libx264 + aac, yuv420p, 30 fps, 1080p — codec parameters
    are IDENTICAL across all three compose paths, so the
    downstream concat is a `-c copy` no-reencode pass)
```

The three compose paths converging on identical codec parameters is what lets concat run as `-c copy` instead of a full re-encode — that's the main speed win.

---

## The full render pipeline (8 steps)

```
                         ┌────────────────────────────────────────┐
                         │ 1. PARSE TALK_SCRIPT.md                │
                         │    H2 headers → slide model            │
                         │    Extract quoted speakable text       │
                         │    Extract [VIDEO: …] markers          │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 2. PDF page-count sanity check         │
                         │    pdfinfo → halt if |pages-slides|≥2  │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 3. RASTERIZE: pdftoppm per page        │
                         │    Cache: PNG mtime ≥ PDF mtime        │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 4. TTS: edge-tts per slide             │
                         │    Cache: sha256(voice, text, rate)    │
                         │    Atomic .tmp → replace               │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 5. PROJECT total vs --max-seconds      │
                         │    Halt (exit 4) if over cap           │
                         │    BEFORE any expensive compose        │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 6. COMPOSE per-slide segments          │
                         │    Three paths (see "Per-slide" above) │
                         │    All emit identical codec params     │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 7. CONCAT demuxer + faststart          │
                         │    -c copy (no re-encode)              │
                         │    ⭐ no-subs presentation.mp4 ready   │
                         │       — main deliverable on disk —     │
                         └────────────────┬───────────────────────┘
                                          ▼
                         ┌────────────────────────────────────────┐
                         │ 8. (--with-subtitles only)             │
                         │    whisper align per slide             │
                         │       → SRT + cumulative offset        │
                         │    merge → subtitles.srt               │
                         │    burn-in re-encode pass              │
                         │    atomic replace presentation.mp4     │
                         │    Any failure here is SOFT-FAIL —     │
                         │    the no-subs MP4 stays as the final  │
                         └────────────────────────────────────────┘
```

**Two notes on this ordering**:

1. **Step 5 (projection)** halts before compose if `--max-seconds` is set and TTS already overflows. Catches venue-cap problems in ~30 s instead of 5 min.
2. **Step 8 (subtitles)** runs *after* the no-subs MP4 is on disk. The user can play it immediately; subtitles are non-blocking. If whisper crashes mid-align, the no-subs version stays as the final deliverable.

---

## Output layout

After a successful `render` (with `--with-subtitles` requested):

```
slides/render/
├── RENDER_STATE.json         # phase / status / SHA pinning for 24h resume
├── preflight.json            # ── subcommand envelopes
├── parse.json                #     (every subcommand mirrors stdout
├── narrate.json              #      to its --json-out path)
├── render.json
├── verify.json
│
├── audio/                    # ── TTS cache (content-hash keyed)
│   ├── slide_01.wav
│   ├── slide_01.meta.json    #    {voice, content_hash, generated_at}
│   └── …
│
├── png/                      # ── PDF rasterization cache (mtime keyed)
│   ├── slide_01.png
│   └── …
│
├── segments/                 # ── per-slide composed MP4 (not cached)
│   ├── slide_01.mp4
│   └── …
│
├── srt/                      # ── only if --with-subtitles
│   ├── slide_01.srt          #    per-slide whisper alignment
│   └── …
│
├── subtitles.srt             # ── merged per-slide SRT with cumulative offsets
└── presentation.mp4          # ⭐ FINAL DELIVERABLE
                              #    (subs burned in if step 8 succeeded;
                              #     otherwise no-subs MP4 from step 7)
```

Two cache layers and one non-cache:

| Layer | Cache key | What invalidates it |
|---|---|---|
| `png/slide_NN.png` | PDF `main.pdf` mtime | Recompile the slides → PNG re-rasterized |
| `audio/slide_NN.wav` | `sha256(voice + speakable_text + rate)` | Edit slide NN narration, swap voice, change `--rate` → only that WAV regenerates |
| `segments/slide_NN.mp4` | (none — always recomposed) | Every `render` invocation recomposes; cheap because codec params are stable |

The two-tier cache means: edit slide 3's quoted text → `render` re-runs **only** slide 3's edge-tts call + slide 3's compose. Slides 1, 2, 4, 5 reuse their cached PNG + WAV.

---

## Where each subcommand lives in the chain

```
preflight ─► reads:  workspace path, --with-subtitles flag,
                     optionally TALK_SCRIPT.md (for clip probe)
            writes: preflight.json (no artifacts)
            gate:   edge-tts + pdftoppm + ffmpeg + ffprobe + writable dir
                    (+ whisper if --with-subtitles)
                    (+ every [VIDEO:…] clip exists + trim in bounds
                       if --talk-script given)

parse     ─► reads:  TALK_SCRIPT.md (+ optionally main.pdf for page count)
            writes: parse.json (no artifacts — pure read-only)

narrate   ─► reads:  TALK_SCRIPT.md
            writes: audio/slide_NN.wav + .meta.json
                    narrate.json
            (TTS-only preview; no PNG, no compose)

render    ─► reads:  main.pdf, TALK_SCRIPT.md, [VIDEO:…] clip paths
            writes: png/, audio/, segments/, srt/ (optional),
                    subtitles.srt (optional), presentation.mp4, render.json
            (the full 8-step pipeline)

verify    ─► reads:  presentation.mp4, TALK_SCRIPT.md (for duration target)
            writes: verify.json (no artifacts — pure read-only)
            gate:   codec + audio-track + pix_fmt + faststart + duration drift
```

---

## TALK_SCRIPT.md → slide model

The parser converts each `## Slide N: title [MM:SS - MM:SS]` block into one slide entry. The dependency from script text to renderable artifacts:

```
TALK_SCRIPT.md
  │
  ├── H2 header        ─► slide_number, title, planned_start_seconds,
  │                       planned_end_seconds
  │
  ├── body text                                       (between header and
  │     │                                              next `## Slide` /
  │     │                                              `---` hrule)
  │     │
  │     ├── "quoted spans"  ─► speakable_text   ─► edge-tts → slide_NN.wav
  │     │                        (joined with
  │     │                         spaces, both
  │     │                         straight & curly
  │     │                         quotes detected)
  │     │
  │     ├── → *Transition*: …    (stripped — not narrated, not on slide)
  │     │
  │     ├── *[stage direction]*  (stripped — author-only annotation)
  │     │
  │     ├── [VIDEO: clip.mp4]       ─► VideoClipRef ─► full-frame replace
  │     │                                             of png/slide_NN.png
  │     │                                             at compose time
  │     │
  │     ├── [VIDEO: clip @ A-B]     ─► VideoClipRef ─► same, trimmed
  │     │                                             to source seconds A..B
  │     │
  │     └── [VIDEO: clip ON x.png]  ─► VideoClipRef ─► template-match x.png
  │                                                    inside png/slide_NN.png,
  │                                                    overlay clip in place
  │                                                    (multiple allowed)
  │
  └── (next `## Slide …` header)
```

[`VIDEO: …`] markers are honored **only** by this skill's MP4 output. They are silently inert in `slides/main.pdf` (LaTeX doesn't know about them) and in `slides/presentation.pptx` (`python-pptx` can't embed video shapes). See [SKILL.md → Embedding experiment videos](SKILL.md#embedding-experiment-videos) for full syntax and duration policy.

---

## Failure / soft-fail map

```
preflight    ┬─ missing edge-tts / pdftoppm / ffmpeg / ffprobe ─► exit 1 (hard)
             ├─ missing whisper AND --with-subtitles requested ─► exit 1 (hard)
             ├─ output dir not writable                        ─► exit 1 (hard)
             ├─ clip file missing / trim out of bounds         ─► exit 1 (hard)
             └─ whisper missing WITHOUT --with-subtitles       ─► not checked

parse        ┬─ malformed slide header                         ─► exit 1
             ├─ inverted trim range                            ─► exit 1
             └─ empty speakable text after extraction          ─► exit 1

render       ┬─ projected duration over --max-seconds          ─► exit 4
             │   (halts AFTER TTS, BEFORE any compose)
             ├─ ffmpeg compose failure                         ─► exit 3
             ├─ pdftoppm / edge-tts network failure            ─► exit 1 (after 1 retry)
             │
             └─ (subtitles only, post-concat:)
                ├─ whisper align failure per slide ─► soft-fail, skipReason="whisper-failed"
                ├─ SRT merge failure                ─► soft-fail, skipReason="alignment-merge-failed"
                └─ ffmpeg subtitle burn-in failure  ─► soft-fail, skipReason="ffmpeg-subtitle-burn-failed"
                   (no-subs presentation.mp4 stays as final)

verify       ─► every gate failure                              ─► exit 2
                (codec / audio / pix_fmt / faststart / duration drift / fps / resolution)
```

The only soft-fail in the entire skill is the subtitle path. Everything else fails closed.

---

## Material-by-material reference

| File | Produced by | Consumed by | Persistence |
|---|---|---|---|
| `slides/main.pdf` | `/paper-slides` Phase 4 | `pdftoppm`, `pdfinfo`, ffprobe of self by no consumer | external (kept) |
| `slides/TALK_SCRIPT.md` | `/paper-slides` Phase 8 | `parse`, `narrate`, `render`, `verify` | external (kept) |
| `figures/<exp>.mp4` | author, manually | `render` (via `[VIDEO:…]` marker) | external (kept) |
| `slides/render/preflight.json` | `preflight` | downstream orchestrator | overwritten each run |
| `slides/render/parse.json` | `parse` | downstream orchestrator, user review | overwritten |
| `slides/render/RENDER_STATE.json` | `render` (every phase) | resume logic (24 h window) | atomically replaced per phase |
| `slides/render/png/slide_NN.png` | `render` step 3 | `render` step 6 | cached by PDF mtime |
| `slides/render/audio/slide_NN.wav` | `render` step 4 | `render` step 6, step 8 (whisper) | cached by content hash |
| `slides/render/audio/slide_NN.meta.json` | `render` step 4 | cache check on rerun | atomically replaced |
| `slides/render/segments/slide_NN.mp4` | `render` step 6 | `render` step 7 (concat) | overwritten every render |
| `slides/render/concat.txt` | `render` step 7 | `ffmpeg -f concat` | regenerated, ephemeral |
| `slides/render/srt/slide_NN.srt` | `render` step 8 (`--with-subtitles`) | `render` step 8 (merge) | regenerated on rerun |
| `slides/render/subtitles.srt` | `render` step 8 (merged) | `render` step 8 (burn-in), manual proofreading | overwritten |
| **`slides/render/presentation.mp4`** | **`render` step 7 + (optional) step 8** | `verify`, `/paper-video` | ⭐ **final deliverable** |
| `slides/render/render.json` | `render` (end) | downstream orchestrator, drift report | overwritten |
| `slides/render/verify.json` | `verify` | gate check (Policy A) | overwritten |

---

## See also

- [`SKILL.md`](SKILL.md) — operational manual: constants, per-phase prompts, full `[VIDEO: …]` syntax, failure policy details
- [`../paper-slides/SKILL.md`](../paper-slides/SKILL.md) — upstream: produces `slides/main.pdf` + `slides/TALK_SCRIPT.md`
- [`../paper-video/SKILL.md`](../paper-video/SKILL.md) — downstream: gates this skill's `presentation.mp4` against venue limits
- [`../shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2 — Policy A (skill-local gate)

# `/paper-slides`

Turn a compiled paper (LaTeX source under `paper/`) into a complete conference talk deck: Beamer LaTeX, the compiled PDF, speaker notes, a full word-for-word talk script with anticipated Q&A, and an editable PowerPoint (on demand). One skill, nine phases, two STOP checkpoints.

This README is the user-facing tour. The operational manual lives in [`SKILL.md`](SKILL.md); when in doubt, that file is the source of truth.

---

## When to use this skill

Use `/paper-slides` after the paper is compiled — typically after Workflow 3 (`/paper-writing`) — and you need a deck for:

| Talk type | Duration | Slides | Audience |
|---|---|:---:|---|
| `poster-talk` | 3–5 min | 5–8 | Live human at your poster |
| `spotlight` | 5–8 min | 8–12 | Conference room |
| `oral` | 15–20 min | 15–22 | Conference room |
| `invited` | 30–45 min | 25–40 | Department / seminar |
| `supplementary-video` | ≈3 min (180 s hard, ≤250 MB) | 6–8 | Reviewer reading the PDF (CoRL / ICRA / RSS / NeurIPS-supp) |

The last row is venue-output-tuned, not live-audience-tuned — drop the chair-greeting and anticipated-Q&A, lean on `[VIDEO: ...]` markers for qualitative rollouts. Pairs with [`/paper-slides-render`](../paper-slides-render/SKILL.md) downstream.

**Do NOT use** for: writing the paper itself (`/paper-writing`), polishing an already-built deck (`/slides-polish`), turning slides into a narrated MP4 (`/paper-slides-render`), or assembling experiment clips into a submission video (`/paper-video`).

---

## Quick start

```bash
# Default — spotlight, NeurIPS colors, 15 min, PDF only (PPTX deferred)
/paper-slides "paper/"

# Override
/paper-slides "paper/" — talk_type: oral, venue: ICML, minutes: 20

# 3-min CoRL submission video deck
/paper-slides "paper/" — talk_type: supplementary-video, venue: CORL

# Build PPTX upfront (legacy / orchestrator-style)
/paper-slides "paper/" — with-pptx: true
```

The skill expects `paper/main.tex` (or `paper/main.pdf`) + `paper/sections/*.tex` + `paper/figures/`. If `slides/` already exists, it's copied to `slides-backup-<timestamp>/` first — no work is silently overwritten.

---

## The 9-phase workflow

Each phase ends by writing `slides/SLIDES_STATE.json`, so an interrupted run can resume within 24 h. Two phases pause for explicit user input.

| Phase | What it does | Output |
|:---:|---|---|
| **0** | Validate `paper/`; detect CJK; pick slide count from talk_type; back up `slides/` if present | state file |
| **1** | Extract content; draft a slide-by-slide outline (title + bullets + figure + time per slide) | `slides/SLIDE_OUTLINE.md` — **⛔ STOP for user approval** |
| **2** | Draft actual frame content per the strict presentation rules (one message/slide, max 6 lines, max 8 words/line, sentence fragments, bold key numbers) | (in-memory) |
| **3** | Generate `slides/main.tex` (beamer, venue-colored) | `slides/main.tex` |
| **4** | Compile with `latexmk` (or `xelatex` if CJK) | `slides/main.pdf` |
| **5** | Codex MCP review (`gpt-5.5` xhigh): story arc, density, time budget, figure visibility, hook, takeaway, progressive build | `slides/SLIDES_REVIEW.md` |
| **6** | Extract per-slide `\note{}` blocks + transition cues | `slides/speaker_notes.md` |
| **7** | **(opt-in)** PowerPoint export — see [PPTX behavior](#pptx-behavior) below | `slides/presentation.pptx` (+ `generate_pptx.py`) |
| **8** | Full word-for-word talk script + 8 anticipated-Q&A entries (or the supplementary-video variant) | `slides/TALK_SCRIPT.md` |

The **Phase 1 outline checkpoint is the most critical**: changing the outline is much cheaper than re-writing LaTeX. Say `go` to proceed, give specific edits ("merge 3-4", "add a demo slide", "cut the ablation"), or `stop` to save what's there.

---

## The two speaker-facing files

There are three places speaker text lives, and they serve different jobs:

| File | Granularity | Best used for |
|---|---|---|
| `slides/main.tex` (`\note{}` blocks per frame) | Bound to each slide | Live presentation with `pdfpc` / dual-screen — the notes travel with the slide |
| `slides/speaker_notes.md` | Short prompts | A separate paper card to glance at; 2–3 sentences per slide + timing hint + transition phrase |
| `slides/TALK_SCRIPT.md` | Full word-for-word | Practice reading aloud, recording, or feeding to TTS via `/paper-slides-render`. This is the **only file with the full manuscript** and the anticipated-Q&A block |

When Phase 7 builds the PPTX, the `\note{}` text also lands in PowerPoint's notes pane.

---

## PPTX behavior

Phase 7 (PowerPoint export) is **opt-in by default**:

- During iteration on the PDF, the PPTX would silently drift (LaTeX and `generate_pptx.py` don't auto-sync), so Phase 7 pauses for confirmation.
- When the PDF is final, answer `yes` / `生成` / `build it` at the checkpoint, and Phase 7 runs.
- For orchestrated runs (like `/paper-talk`) that need the PPTX immediately, pass `— with-pptx: true` or set `PPTX_AT_END = true`.

The Phase 7 STOP shows three options: `yes` (build now), `later` (skip but reserve the option), `no` (decline). The chosen status is recorded as `pptx_status` in `SLIDES_STATE.json` (`"built" | "deferred" | "declined" | "skipped-missing-dep"`).

To build the PPTX later, re-run `/paper-slides` with `— with-pptx: true` once the outline is already approved — Phase 1's STOP is skipped on resume.

---

## Modifying the deck after generation

The PDF, PPTX, and LaTeX source **do not auto-sync**. Strategy depends on what you're changing:

| Change | Where to edit | What to re-run |
|---|---|---|
| Last-minute typo / font tweak before the talk | `presentation.pptx` directly in PowerPoint/Keynote | nothing |
| Wording, bullet, bold, structure | `slides/main.tex` (source of truth) | `latexmk` → `main.pdf`; later, `/paper-slides — with-pptx: true` to re-emit PPTX |
| Change a figure | Replace under `slides/figures/` + update `\includegraphics{...}` | `latexmk` |
| Narration text (for `/paper-slides-render` MP4) | `slides/TALK_SCRIPT.md` | re-run `/paper-slides-render` |
| Section order, slide count, venue colors | Re-run `/paper-slides` from Phase 1 outline | full pipeline |

**Rule of thumb**: the LaTeX source is the source of truth; the PPTX is a derivative. Manual PPTX edits are lost the moment Phase 7 re-runs.

For per-slide visual polish (font scaling, layout drift, italic leak) without touching content, use [`/slides-polish`](../slides-polish/SKILL.md) instead of hand-editing.

---

## Downstream pipeline

`/paper-slides` produces inputs for two downstream skills:

```
/paper-slides
    ↓ slides/main.pdf + slides/TALK_SCRIPT.md
/paper-slides-render          ← TTS narration; honors [VIDEO: ...] markers
    ↓ slides/render/presentation.mp4
/paper-video --mode submission   ← venue gating (CoRL 180 s / 250 MB, etc.)
    ↓ supplementary.mp4
```

Set `talk_type: supplementary-video` to get a deck that's pre-tuned for this chain — Phase 8 emits a 3-minute self-contained overview script with experiment-roll-out hooks (`[VIDEO: figures/<exp>.mp4]`) that `/paper-slides-render` will swap into the rendered MP4.

For visual polish (font scaling, banner-as-tcolorbox, italic leak guard) the downstream is [`/slides-polish`](../slides-polish/SKILL.md). For orchestrating the whole talk pipeline end-to-end, use [`/paper-talk`](../paper-talk/SKILL.md).

---

## Output layout

After a complete run (with PPTX opted in):

```
slides/
├── main.tex                  # Beamer source (source of truth)
├── main.pdf                  # Compiled deck (primary deliverable)
├── presentation.pptx         # Editable PowerPoint (only if --with-pptx: true)
├── generate_pptx.py          # PPTX generator (only if PPTX was built)
├── SLIDE_OUTLINE.md          # Phase 1 outline
├── SLIDES_REVIEW.md          # Phase 5 Codex review
├── speaker_notes.md          # Phase 6 short prompts
├── TALK_SCRIPT.md            # Phase 8 full manuscript + Q&A
├── SLIDES_STATE.json         # Phase progress + pptx_status
└── figures/                  # Symlinked from paper/figures/
```

If `slides/` existed before the run, the previous version is at `slides-backup-<timestamp>/`.

---

## Defaults summary

| Setting | Default | Override |
|---|---|---|
| Venue | `NeurIPS` | `— venue: ICML \| ICLR \| CVPR \| AAAI \| ACL \| EMNLP \| ECCV \| CORL \| GENERIC` |
| Talk type | `spotlight` | `— talk_type: oral \| poster-talk \| invited \| supplementary-video` |
| Duration | `15` min | `— minutes: N` |
| Aspect ratio | `16:9` | `— aspect: 4:3` |
| Speaker notes | on | (constant: `SPEAKER_NOTES = false`) |
| PPTX export | **deferred** (Phase 7 checkpoint) | `— with-pptx: true` |
| Reviewer model | Codex MCP `gpt-5.5` (xhigh) | (constant; falls back silently if MCP unavailable) |

The full constant list and conditional-mode rules live in [`SKILL.md`](SKILL.md).

---

## Honest boundaries

- This skill **does not** validate the paper's claims, decide what to put on each slide, or verify that experiments are reproducible. It composes a deck *from* the compiled paper.
- The PPTX is a derivative — the LaTeX source is canonical. Don't expect manual PPTX edits to round-trip.
- The Codex MCP review (Phase 5) is a quality nudge, not a gate. If MCP is unavailable, the phase is skipped with a note in the state file; the run still produces all artifacts.
- The supplementary-video talk type targets the **CoRL/ICRA/RSS family of 3-min submission attachments**; venues with different ceilings (e.g. SIGGRAPH supp) may need manual budget adjustment.
- VIDEO markers in `TALK_SCRIPT.md` are honored **only** by `/paper-slides-render`'s MP4 output — not in `main.pdf` (LaTeX doesn't know about them) and not in `presentation.pptx` (`python-pptx` can't embed video shapes).

---

## See also

- [`SKILL.md`](SKILL.md) — operational manual: full constant list, per-phase prompts, conditional modes
- [`../paper-slides-render/SKILL.md`](../paper-slides-render/SKILL.md) — turn the deck + script into a narrated MP4
- [`../paper-video/SKILL.md`](../paper-video/SKILL.md) — assemble experiment clips into a venue-gated submission video
- [`../slides-polish/SKILL.md`](../slides-polish/SKILL.md) — per-page visual polish on an already-built deck
- [`../paper-talk/SKILL.md`](../paper-talk/SKILL.md) — end-to-end orchestrator (paper → outline → slides → polish → audit)

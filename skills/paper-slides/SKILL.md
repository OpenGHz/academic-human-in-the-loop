---
name: paper-slides
description: "Generate conference presentation slides (beamer LaTeX → PDF, with PPTX export deferred until the deck is final) from a compiled paper, with speaker notes and full talk script. Use when user says \"做PPT\", \"做幻灯片\", \"make slides\", \"conference talk\", \"presentation slides\", \"生成slides\", \"写演讲稿\", or wants beamer slides for a conference talk."
argument-hint: "[paper-directory-or-talk-length] [— style-ref: <source>] [— with-pptx: true|false]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex, mcp__codex__codex-reply
---

# Paper Slides: From Paper to Conference Talk

Generate conference presentation slides from: **$ARGUMENTS**

## Context

This skill runs **after** Workflow 3 (`/paper-writing`). It takes a compiled paper and generates a presentation slide deck for conference oral talks, spotlight presentations, or poster lightning talks.

Unlike posters (single page, visual-first), slides tell a **temporal story**: each slide builds on the previous one, with progressive revelation of the research narrative. A good talk makes the audience understand *why this matters* before showing *what was done*.

## Constants

- **VENUE = `NeurIPS`** — Target venue, determines color scheme. Supported: `NeurIPS`, `ICML`, `ICLR`, `AAAI`, `ACL`, `EMNLP`, `CVPR`, `ECCV`, `GENERIC`. Override via argument.
- **TALK_TYPE = `spotlight`** — Talk format. Options: `oral` (15-20 min), `spotlight` (5-8 min), `poster-talk` (3-5 min), `invited` (30-45 min), `supplementary-video` (≈3 min, submission attachment — self-contained overview). Determines slide count and content depth. The first four target a **live audience**; `supplementary-video` is **venue-output-tuned** (CoRL / ICRA / RSS / NeurIPS-supp) and ships next to the PDF.
- **TALK_MINUTES = 15** — Talk duration in minutes. Auto-adjusts slide count (~1 slide/minute for oral, ~1.5 slides/minute for spotlight). Override explicitly if needed.
- **SUPPLEMENTARY_VIDEO_BUDGET_SECONDS = 180** — Hard cap for the supplementary-video mode; matches CoRL / ICRA / RSS / NeurIPS-supp ceilings. Honored when `talk_type == supplementary-video`.
- **SUPPLEMENTARY_VIDEO_MAX_MB = 250** — Strict size cap (CoRL ceiling; ICRA & RSS use comparable limits). Surfaced as a hint to `/paper-slides-render` and gated by `/paper-video --mode submission` downstream.
- **ASPECT_RATIO = `16:9`** — Slide aspect ratio. Options: `16:9` (default, modern projectors), `4:3` (legacy).
- **SPEAKER_NOTES = true** — Generate `\note{}` blocks in beamer and corresponding PPTX notes. Set `false` for clean slides without notes.
- **PPTX_AT_END = false** — When `false` (default), Phase 7 (PowerPoint export) pauses for explicit user confirmation after Phase 6 instead of running automatically. The PDF iteration loop (Phases 0-6) is the source of truth; the PPTX is a derivative built only when the user says the deck is final. Set `true` to restore the pre-2026-05 always-emit behavior, or pass `— with-pptx: true` on a single invocation.
- **PAPER_DIR = `paper/`** — Directory containing the compiled paper.
- **OUTPUT_DIR = `slides/`** — Output directory for all slide files.
- **REVIEWER_MODEL = `gpt-5.6-sol`** — Model used via Codex MCP for slide review.
- **AUTO_PROCEED = false** — At each checkpoint, **always wait for explicit user confirmation**.
- **COMPILER = `latexmk`** — LaTeX build tool.
- **ENGINE = `pdflatex`** — LaTeX engine. Use `xelatex` for CJK text.

> 💡 Override: `/paper-slides "paper/" — talk_type: oral, venue: ICML, minutes: 20, aspect: 4:3`
>
> 💡 Submission video: `/paper-slides "paper/" — talk_type: supplementary-video, venue: CORL`
>
> 💡 Build PPTX upfront (legacy / orchestrator-style): `/paper-slides "paper/" — with-pptx: true`

## Optional: Style reference (`— style-ref: <source>`, opt-in)

Lets the user steer the talk's **structural** rhythm (story beats, theorem density, figure density inherited from the source paper) toward a reference paper. **Default OFF — when the user does not pass `— style-ref`, do nothing differently from before.**

Only when `— style-ref: <source>` appears in `$ARGUMENTS`, run the helper FIRST:

```bash
# Resolve $STYLE_HELPER via the canonical strict-safe chain (see
# shared-references/integration-contract.md §2). Policy A — gate:
# unresolved helper means --style-ref cannot be satisfied, so abort.
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
STYLE_HELPER=".aris/tools/extract_paper_style.py"
[ -f "$STYLE_HELPER" ] || STYLE_HELPER="tools/extract_paper_style.py"
[ -f "$STYLE_HELPER" ] || { [ -n "${ARIS_REPO:-}" ] && STYLE_HELPER="$ARIS_REPO/tools/extract_paper_style.py"; }
[ -f "$STYLE_HELPER" ] || {
  echo "ERROR: extract_paper_style.py not resolved at .aris/tools/, tools/, \$ARIS_REPO/tools/, or via ~/.aris/repo." >&2
  echo "       Fix: rerun bash tools/install_aris.sh or smart_update.sh (refreshes ~/.aris/repo), export ARIS_REPO, or copy the helper to tools/." >&2
  echo "       --style-ref cannot be satisfied; aborting." >&2
  exit 1
}
STYLE_STATUS=0
CACHE=$(python3 "$STYLE_HELPER" --source "<source>") || STYLE_STATUS=$?
case "$STYLE_STATUS" in
  0) ;;                                       # use $CACHE/style_profile.md as structural guidance
  2) echo "warning: style-ref skipped (missing optional dep)" >&2 ;;
  3) echo "error: --style-ref source failed; aborting slides" >&2 ; exit 1 ;;
  *) echo "error: helper failed unexpectedly; aborting slides" >&2 ; exit 1 ;;
esac
```

Sources accepted: local TeX dir / file, local PDF, arXiv id, http(s) URL. Overleaf URLs/IDs are rejected — clone via `/overleaf-sync setup <id>` first and pass the local clone path.

**Strict rules** (full contract in `tools/extract_paper_style.py` docstring):

- Use `style_profile.md` to align section-budget tendency and theorem-environment density. Talk-type slide count above still takes precedence.
- **Never copy speaker-note prose, slide titles, or examples** from anything reachable through the cache. The talk content is from the user's paper, not the reference.
- **Never pass `— style-ref` (or the cache contents) to the GPT-5.6-Sol reviewer sub-agent** — the reviewer must judge the talk's clarity on its own merits.

## Talk Type → Slide Count

| Talk Type | Duration | Slides | Content Depth |
|-----------|----------|:------:|---------------|
| `supplementary-video` | ≈3 min (180s hard, ≤250 MB strict) | 6-8 | Self-contained 3-min overview: title-pitch → problem → key idea → method → qualitative+quantitative results → 5s take-away. **No anticipated-Q&A.** Results are the largest single slot but motivation and method each get a real slide. |
| `poster-talk` | 3-5 min | 5-8 | Problem + 1 method slide + 1 result + conclusion |
| `spotlight` | 5-8 min | 8-12 | Problem + 2 method + 2 results + conclusion |
| `oral` | 15-20 min | 15-22 | Full story with motivation, method detail, experiments, analysis |
| `invited` | 30-45 min | 25-40 | Comprehensive: background, related work, deep method, extensive results, discussion |

> **Picking between `poster-talk` and `supplementary-video`**: both run ~3 min, but they serve different audiences. `poster-talk` is for a live human standing in front of your poster — keep Q&A prep, expect spontaneous follow-up, plan for interruptions. `supplementary-video` is a **self-contained 3-min overview of the work** that ships next to the PDF — drop the Q&A prep and the chair-greeting intro, lean on qualitative rollouts (`[VIDEO: ...]` markers, consumed by `/paper-slides-render`) where static figures fail, but keep problem + idea + method as real slides so a reviewer who watches only the video still understands the paper.

## Venue Color Schemes

Same as `/paper-poster-html`:

| Venue | Primary | Accent | Background | Text |
|-------|---------|--------|------------|------|
| NeurIPS | `#8B5CF6` | `#2563EB` | `#FFFFFF` | `#1E1E1E` |
| ICML | `#DC2626` | `#1D4ED8` | `#FFFFFF` | `#1E1E1E` |
| ICLR | `#059669` | `#0284C7` | `#FFFFFF` | `#1E1E1E` |
| CVPR | `#2563EB` | `#7C3AED` | `#FFFFFF` | `#1E1E1E` |
| GENERIC | `#334155` | `#2563EB` | `#FFFFFF` | `#1E1E1E` |

## State Persistence (Compact Recovery)

Persist state to `slides/SLIDES_STATE.json` after each phase:

```json
{
  "phase": 3,
  "venue": "NeurIPS",
  "talk_type": "spotlight",
  "slide_count": 10,
  "codex_thread_id": "019cfcf4-...",
  "status": "in_progress",
  "timestamp": "2026-03-18T15:00:00"
}
```

**On startup**: if `SLIDES_STATE.json` exists with `"status": "in_progress"` and within 24h → resume. Otherwise → fresh start.

## Workflow

### Phase 0: Input Validation & Setup

1. **Check prerequisites**:
   ```bash
   which pdflatex && which latexmk
   ```

2. **Verify paper exists**:
   ```bash
   ls $PAPER_DIR/main.tex || ls $PAPER_DIR/main.pdf
   ls $PAPER_DIR/sections/*.tex
   ls $PAPER_DIR/figures/
   ```

3. **Backup existing slides**: if `slides/` exists, copy to `slides-backup-{timestamp}/`

4. **Create output directory**: `mkdir -p slides/figures`

5. **Detect CJK**: if paper contains Chinese/Japanese/Korean, set ENGINE to `xelatex`

6. **Determine slide count**: from TALK_TYPE and TALK_MINUTES using the table above.

   > **If `talk_type == supplementary-video`**: total runtime is hard-capped at 180 s and the size ceiling is 250 MB. The deck must be a **self-contained overview** of the paper (the venue language is "providing an overview of the work" — CoRL, ICRA, RSS, NeurIPS-supp): problem → idea → method → results → close. Motivation and method each get a real slide. The anticipated-Q&A section is dropped entirely. Results are the largest single slot but **not** the only content. Target 6-8 slides with the budget shape in Phase 8 below.

7. **Check for resume**: read `slides/SLIDES_STATE.json` if it exists

**State**: Write `SLIDES_STATE.json` with `phase: 0`.

### Phase 1: Content Extraction & Slide Outline

Read `paper/sections/*.tex` and build a slide-by-slide outline.

**Slide template by talk type**:

#### Supplementary-video (6-8 slides, 180 s hard cap)

Submission attachment for CoRL / ICRA / RSS / NeurIPS-supp. **Not a live-audience talk.** A reviewer who watches only this video must walk away knowing what the paper is, why it matters, what was done, and what was found. The qualitative rollouts (via `[VIDEO: ...]` markers, consumed by `/paper-slides-render`) are the supplementary's distinct value-add over the static PDF.

| Slide | Purpose | Content Source | Figure / Clip? |
|:-----:|---------|----------------|:--------------:|
| 1 | Title + One-Sentence Pitch (~15 s) | Paper metadata + headline result | Title card |
| 2 | Problem & Gap (~25 s) | Introduction (problem + one-sentence gap, not a literature dump) | Static figure or short failure clip |
| 3 | Key Idea (~25 s) | Introduction (contribution) | Method teaser figure |
| 4 | Method-in-One-Picture (~25 s) | Method (condensed to one diagram) | Hero method figure |
| 5-(N-1) | Qualitative + Quantitative Results (~80 s total, 2-4 slides) | Experiments | **`[VIDEO: figures/<exp>.mp4]`** + one headline number per slide |
| N | Take-Away + Project Page (~10 s) | Conclusion (one sentence) + URL/QR | QR code |

**Critical**: ❌ no anticipated-Q&A, ❌ no "thank the chair", ❌ no separate related-work slide. ✅ at least 2 of the result slides should carry a `[VIDEO: ...]` marker pointing at a qualitative rollout (e.g. `figures/grasp.mp4`). ✅ slide-1 pitch must land the headline result in the first 15 seconds.

#### Oral (15-22 slides)

| Slide | Purpose | Content Source | Figure? |
|:-----:|---------|----------------|:-------:|
| 1 | Title | Paper metadata | No |
| 2 | Outline | Section headers | No |
| 3-4 | Motivation & Problem | Introduction | Optional |
| 5 | Key Insight | Introduction (contribution) | No |
| 6-9 | Method | Method section | Yes (hero figure) |
| 10-14 | Results | Experiments | Yes (per slide) |
| 15-16 | Analysis / Ablations | Experiments | Yes |
| 17 | Limitations | Conclusion | No |
| 18 | Conclusion / Takeaway | Conclusion | No |
| 19 | Thank You + QR | — | QR code |

#### Spotlight (8-12 slides)

| Slide | Purpose | Content Source | Figure? |
|:-----:|---------|----------------|:-------:|
| 1 | Title | Paper metadata | No |
| 2-3 | Problem + Why It Matters | Introduction | Optional |
| 4 | Key Insight | Contribution | No |
| 5-6 | Method | Method (condensed) | Yes (hero) |
| 7-9 | Results | Key results only | Yes |
| 10 | Takeaway | Conclusion | No |
| 11 | Thank You + QR | — | QR code |

#### Poster-talk (5-8 slides)

| Slide | Purpose | Content Source | Figure? |
|:-----:|---------|----------------|:-------:|
| 1 | Title | Paper metadata | No |
| 2 | Problem | Introduction (1 slide) | No |
| 3 | Method | Method (1 slide) | Yes |
| 4-5 | Results | Key result only | Yes |
| 6 | Takeaway + QR | Conclusion | QR |

**For each slide, specify**:
- Title (max 8 words)
- 3-5 bullet points (max 8 words each)
- Figure reference (if any) from paper/figures/
- Speaker note (2-3 sentences of what to say)
- Time allocation (in seconds)

**Output**: `slides/SLIDE_OUTLINE.md`

**🚦 Checkpoint:**

```
📊 Slide outline ready:
- Talk type: [TALK_TYPE] ([TALK_MINUTES] min)
- Slide count: [N] slides
- Figures used: [N] from paper/figures/
- Time budget: [breakdown]

Slide-by-slide outline:
1. [Title slide]
2. [Motivation — 1.5 min]
3. [Problem statement — 1 min]
...

Proceed to drafting? Or adjust the outline?
```

**⛔ STOP HERE and wait for user response.** This is the most critical checkpoint — the outline determines the entire talk flow.

Options:
- **"go"** → proceed to Phase 2
- **adjustments** (e.g., "merge slides 3-4", "add a demo slide", "cut the ablation") → revise
- **"stop"** → save to `slides/SLIDE_OUTLINE.md`

**State**: Write `SLIDES_STATE.json` with `phase: 1`.

### Phase 2: Slide-by-Slide Content Drafting

For each slide in the outline, draft the actual content.

**Presentation rules (enforced strictly)**:

| Rule | Rationale |
|------|-----------|
| **One message per slide** | If a slide has two ideas, split it |
| **Max 6 lines per slide** | More than 6 lines = wall of text |
| **Max 8 words per line** | Audience reads, not listens, if text is long |
| **Sentence fragments, not sentences** | "Improves F1 by 3.2%" not "Our method improves the F1 score by 3.2 percentage points" |
| **Figure slides: figure ≥60% area** | The figure IS the content; bullets are annotations |
| **Bold key numbers** | "Achieves **94.3%** accuracy" |
| **Progressive disclosure** | Use `\pause` or `\onslide` for complex slides |
| **No Related Work slide** | Unless invited talk (30+ min) |
| **Consistent across analogous slides** | Same-role boxes/panels keep identical size & style on every slide; fix alignment by **repositioning (centering), not resizing**. Keep parallel items parallel (e.g. every posed question ends with `?`) |
| **One idea per line** | Never weld two unrelated ideas with a `·` / `;` separator (a `·` is only for a short list of *parallel* items) — split to separate lines. Drop redundant conditionals that make a posed question self-answering (`unlock first if locked?` → `unlock first?`) |
| **Task-intro slides show real I/O** | For a "what is the task" slide, build a concrete `Question → Model → Answer` panel from the paper's actual prompt + choice list (Appendix prompt tables) and show the explored attempt as frames — beats abstract bullets for conveying the task |

**For each slide, produce**:
1. `\frametitle{}`
2. Content (itemize or figure + caption)
3. `\note{}` with speaker text (if SPEAKER_NOTES=true)

### Phase 3: Generate Slides LaTeX

Create `slides/main.tex` using beamer.

**Template structure**:

```latex
\documentclass[aspectratio=169]{beamer}

% Venue theme
\usepackage{xcolor}
\definecolor{primary}{HTML}{VENUE_PRIMARY}
\definecolor{accent}{HTML}{VENUE_ACCENT}

% Clean theme
\usetheme{default}
\usecolortheme{default}
\setbeamercolor{frametitle}{fg=primary}
\setbeamercolor{title}{fg=primary}
\setbeamercolor{structure}{fg=accent}
\setbeamercolor{itemize item}{fg=primary}
\setbeamercolor{itemize subitem}{fg=accent}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}{
  \hfill\insertframenumber/\inserttotalframenumber\hspace{2mm}\vspace{2mm}
}

% Packages
\usepackage{graphicx,amsmath,booktabs}
\graphicspath{{figures/}}

% Speaker notes (if enabled)
% \setbeameroption{show notes on second screen=right}

% Metadata
\title{PAPER TITLE}
\author{Author 1 \and Author 2}
\institute{Affiliation}
\date{VENUE YEAR}

\begin{document}

\begin{frame}
\titlepage
\end{frame}

% Content slides follow...

\begin{frame}{Motivation}
\begin{itemize}
  \item Bullet point 1
  \item Bullet point 2
  \item \textbf{Key insight in bold}
\end{itemize}
\note{Speaker note: explain the motivation...}
\end{frame}

% Figure slide example
\begin{frame}{Method Overview}
\centering
\includegraphics[width=0.85\textwidth]{method_overview.pdf}
\vspace{0.5em}
\begin{itemize}
  \item Key annotation about the figure
\end{itemize}
\note{Walk through the figure left to right...}
\end{frame}

% ... more slides ...

\begin{frame}{Thank You}
\centering
{\Large Questions?}\\[2em]
Paper: [URL or QR placeholder]\\
Code: [URL or QR placeholder]
\end{frame}

\end{document}
```

**Symlink figures**:
```bash
ln -sf ../paper/figures/*.pdf slides/figures/ 2>/dev/null
ln -sf ../paper/figures/*.png slides/figures/ 2>/dev/null
```

**Key formatting rules**:
- Title font: ≥28pt, venue primary color
- Body font: ≥20pt
- Footnotes: ≥14pt
- No navigation symbols
- Frame numbers in bottom-right
- Clean white background (no gradients, no decorative elements)

### Phase 4: Compile Slides

```bash
cd slides && latexmk -$ENGINE -interaction=nonstopmode main.tex
```

**Error handling loop** (max 3 attempts):
1. Parse error log
2. Fix: missing package, undefined command, file not found, overfull boxes
3. Recompile

**Verification**:
```bash
# Check slide count matches outline
pdfinfo slides/main.pdf | grep Pages
```

If page count differs significantly from outline (>2 slides off), investigate.

**State**: Write `SLIDES_STATE.json` with `phase: 4`.

### Phase 5: Codex MCP Review

Send the slide outline + selected LaTeX frames to GPT-5.6-Sol xhigh:

```
mcp__codex__codex:
  model: gpt-5.6-sol
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Review this [TALK_TYPE] presentation ([TALK_MINUTES] min) for [VENUE].

    Evaluate using these criteria (score 1-5 each):

    1. **Story arc** — Does the talk build a compelling narrative? (Problem → insight → method → evidence → takeaway)
    2. **Slide density** — Any slides with too much text? (Max 6 lines, 8 words/line)
    3. **Time budget** — Is [N] slides realistic for [TALK_MINUTES] minutes?
    4. **Figure visibility** — Will figures be readable on a projector?
    5. **Opening hook** — Do slides 2-3 grab attention? (Not "In this paper, we...")
    6. **Takeaway** — Is the final message clear and memorable?
    7. **Progressive build** — Are complex ideas revealed gradually?

    Slide outline:
    [PASTE SLIDE_OUTLINE.md]

    Selected frames (LaTeX):
    [PASTE KEY FRAMES]

    Provide:
    - Score for each criterion
    - Top 3 actionable fixes
    - Overall: Ready to present? (Yes / Needs revision / Major issues)
```

Apply fixes. Recompile if LaTeX was changed.

> ⚠️ If `mcp__codex__codex` is not available (no OpenAI API key), skip external review and proceed to Phase 6. Note the skip in `SLIDES_STATE.json`.

Save review to `slides/SLIDES_REVIEW.md`.

**State**: Write `SLIDES_STATE.json` with `phase: 5`.

### Phase 6: Speaker Notes

For each slide, ensure a `\note{}` block exists with:

1. **What to say** (2-3 complete sentences, conversational tone)
2. **Timing hint** (e.g., "spend 1 minute here", "quick — 20 seconds")
3. **Transition phrase** to the next slide (e.g., "So how do we actually implement this? Let me show you...")

Also generate `slides/speaker_notes.md` as a standalone backup:

```markdown
# Speaker Notes

## Slide 1: Title
[No speaking — wait for introduction]

## Slide 2: Motivation
"Thank you. So let me start with the problem we're trying to solve..."
[Time: 1.5 min]

## Slide 3: Problem Statement
"Specifically, the challenge is..."
→ Transition: "To address this, our key insight is..."
[Time: 1 min]

...
```

**State**: Write `SLIDES_STATE.json` with `phase: 6`.

### Phase 7: PowerPoint Export (opt-in)

**Gate**: Phase 7 runs the actual export **only** when one of these is true:

- `PPTX_AT_END == true` (the user flipped the constant, e.g. for legacy workflows)
- `— with-pptx: true` was passed in `$ARGUMENTS` for this invocation
- The user answers "yes" / "生成" / "build it" at the checkpoint below

Otherwise Phase 7 records that the PPTX was deferred (or declined) in `SLIDES_STATE.json` and continues to Phase 8 without producing `slides/presentation.pptx` or `slides/generate_pptx.py`. The PDF iteration loop (Phases 0-6) is the source of truth; the PPTX is a derivative that we want to build once, at the end, not on every iteration.

#### Checkpoint (skip if `PPTX_AT_END == true` or `— with-pptx: true`)

Present this message verbatim to the user before doing any export work:

```
📄 PDF is ready at slides/main.pdf — review it now.

The PPTX (slides/presentation.pptx) is a derivative of the LaTeX source. It's
cheap to regenerate once, but expensive to keep in sync if you're still
iterating, because main.tex and generate_pptx.py don't auto-sync. So:

  - "yes" / "生成" / "build it"        → build PPTX now and continue to Phase 8
  - "later" / "wait" / "skip for now"  → skip PPTX, continue to Phase 8 (you
                                         can ask later: re-run /paper-slides
                                         with — with-pptx: true once the deck
                                         is final *)
  - "no" / "never"                     → skip PPTX, mark SLIDES_STATE.json
                                         with pptx_status: "declined"

Recommended: iterate on the PDF until you're sure the deck is final, THEN say
"yes". Each PPTX build only takes a few seconds, but every iteration on
.pptx that doesn't round-trip through main.tex is silently lost the next
time Phase 7 runs.

* A focused `— pptx-only` rerun mode is a planned follow-up. For now,
  re-running /paper-slides with — with-pptx: true is the path; it skips Phase
  1's STOP checkpoint when SLIDES_STATE.json shows the outline already
  approved.
```

⛔ **STOP** here and wait for the user's answer.

#### Branch A — "yes" (or forced via `PPTX_AT_END == true` / `— with-pptx: true`)

Generate an editable PPTX using `python-pptx`:

```bash
python3 -c "import pptx" 2>/dev/null || pip install python-pptx
```

Write `slides/generate_pptx.py` that:

1. Creates a PPTX with correct aspect ratio (16:9 → 13.33" x 7.5"; 4:3 → 10" x 7.5")
2. For each beamer frame:
   - Creates a slide with matching layout
   - Title in venue primary color, bold
   - Bullet points with venue accent color markers
   - Figures embedded as images (from slides/figures/)
   - Speaker notes transferred to PPTX notes field
3. Title slide with special formatting (centered, larger title)
4. Thank You slide with centered text
5. Applies venue color scheme throughout

```bash
cd slides && python3 generate_pptx.py
# Output: slides/presentation.pptx
```

> ⚠️ If `python-pptx` is not installed, skip with a note: "Install `pip install python-pptx` to enable PowerPoint export." and write `SLIDES_STATE.json` with `pptx_status: "skipped-missing-dep"`.

Surface the output path. Then write `SLIDES_STATE.json` with `phase: 7, pptx_status: "built"`.

#### Branch B — "later" / "wait" / "skip for now"

Do **not** create `slides/generate_pptx.py` and do **not** run `python-pptx`. Surface one line: `PPTX deferred. Re-run /paper-slides with — with-pptx: true once the deck is final.` Then write `SLIDES_STATE.json` with `phase: 7, pptx_status: "deferred"` and continue to Phase 8.

#### Branch C — "no" / "never"

Same behavior as Branch B, but write `pptx_status: "declined"` instead. Continue to Phase 8.

**State**: Write `SLIDES_STATE.json` with `phase: 7` and the appropriate `pptx_status` (one of `"built" | "deferred" | "declined" | "skipped-missing-dep"`).

### Phase 8: Full Talk Script

Generate `slides/TALK_SCRIPT.md` — a complete, word-for-word script for the talk.

This is different from speaker notes (brief reminders). The talk script is a **full manuscript** that can be read aloud or used for practice.

```markdown
# Talk Script: [Paper Title]

**Venue**: [VENUE] [YEAR]
**Talk type**: [TALK_TYPE] ([TALK_MINUTES] min)
**Total slides**: [N]

---

## Slide 1: Title [0:00 - 0:15]

*[Wait for chair introduction]*

"Thank you [chair name]. I'm [author] from [affiliation], and today I'll be talking about [short title]."

---

## Slide 2: Motivation [0:15 - 1:30]

"Let me start with the problem. [Describe the real-world motivation in accessible terms]. This matters because [impact statement].

The current state of the art approaches this with [brief existing approach]. But there's a fundamental limitation: [gap statement]."

→ *Transition*: "So what's our key insight?"

---

## Slide 3: Key Insight [1:30 - 2:30]

"Our key observation is that [core insight in one sentence].

This leads us to propose [method name], which [one-sentence description]."

→ *Transition*: "Let me walk you through how this works."

---

## Slide 4-N: [Continue for each slide...]

...

---

## Slide [N]: Thank You [TALK_MINUTES:00]

"To summarize: we've shown that [main result]. The key takeaway is [memorable final message].

The paper and code are available at the QR code on screen. I'm happy to take questions."

---

## Time Budget Summary

| Slide | Topic | Duration | Cumulative |
|:-----:|-------|:--------:|:----------:|
| 1 | Title | 0:15 | 0:15 |
| 2 | Motivation | 1:15 | 1:30 |
| 3 | Key Insight | 1:00 | 2:30 |
| ... | ... | ... | ... |
| N | Thank You | 0:15 | [TALK_MINUTES]:00 |

**Total**: [sum] min (target: [TALK_MINUTES] min)

---

## Anticipated Q&A

### Q1: How does this compare to [strongest baseline]?
**A**: "[Specific comparison with numbers]. Our advantage is particularly clear in [specific scenario], where we see [X%] improvement."

### Q2: What are the main limitations?
**A**: "[Honest answer]. We see this as [future work direction]."

### Q3: How computationally expensive is this?
**A**: "[Training/inference cost]. Compared to [baseline], our method requires [comparison]."

### Q4: Does this generalize to [related domain]?
**A**: "[Answer based on paper's discussion section]."

### Q5: What's the most surprising finding?
**A**: "[Interesting insight from the experiments]."

### Q6: How sensitive is the method to [hyperparameter/design choice]?
**A**: "[Reference ablation study if available]."

### Q7: What's the next step for this research?
**A**: "[Future work from conclusion]."

### Q8: [Domain-specific question]
**A**: "[Answer]."
```

#### Conditional: `talk_type == supplementary-video`

When the user picked `supplementary-video`, the template above does **not** apply. Use the structure below instead — it is a self-contained 3-min overview of the paper for a reviewer who will watch the video *next to* the PDF, not in place of a live talk. The CoRL call asks for "an overview of the work" and caps at 180 s / 250 MB; ICRA / RSS / NeurIPS-supp are comparable.

```markdown
# Talk Script: [Paper Title]

**Mode**: supplementary-video (submission attachment; 3 min / 250 MB cap)
**Venue**: [VENUE] [YEAR]
**Total slides**: [6-8]

---

## Slide 1: Title + One-Sentence Pitch [0:00 - 0:15]

"This video is an overview of [paper title]. We tackle [task in one phrase], and we show that [headline result in one phrase]."

*[Title card; author list; venue. Optionally show project-page URL or QR — otherwise save for the outro.]*

→ *Transition*: "Here's the problem."

---

## Slide 2: Problem & Why It Matters [0:15 - 0:40]   ≈25 s

"[One sentence framing the real-world problem.] [One sentence stating why the existing state of the art falls short — the *gap*, not a literature dump.]"

*[A single grounding figure or short clip of the failure mode is ideal.]*

→ *Transition*: "Our idea."

---

## Slide 3: Key Idea [0:40 - 1:05]   ≈25 s

"Our key insight is [single sentence of the central idea]. This lets us [single sentence of what becomes possible]."

*[Method teaser figure.]*

→ *Transition*: "How it works."

---

## Slide 4: Method-in-One-Picture [1:05 - 1:30]   ≈25 s

"[Single sentence describing the architecture or pipeline.] [Single sentence describing the training or inference loop, whichever is the contribution.]"

*[Hero method diagram. No equations unless one *is* the contribution.]*

→ *Transition*: "Results."

---

## Slide 5–(N-1): Qualitative + Quantitative Results [1:30 - 2:50]   ≈80 s — the largest single block

The experiments section is the supplementary's distinct value-add over the PDF, but it is **not** the entire video. Allocate 1:00–1:30 here, split across 2–4 slides. For each result slide:

- Lead with the qualitative rollout: `[VIDEO: figures/<exp>.mp4]` marker on its own line (consumed by `/paper-slides-render` at compose time; the still PNG is swapped for the clip with auto-loop + silent-pad).
- One sentence of setup, one sentence of what-to-look-for, **one quantitative number** per slide that the rollout cannot convey on its own.
- Include at least one comparison-to-baseline slide if the paper claims a comparison — reviewers expect to see it move, not just read the table.

Example shape (one of 2–4 result slides):

```
## Slide 5: Grasping on Unseen Objects [1:30 - 1:55]

[VIDEO: figures/grasp_rollout.mp4]

"Our policy grasps the unseen object in 1.8 seconds, compared to 4.2 seconds for the strongest baseline. Watch the gripper adapt mid-trajectory when the object slips."
```

---

## Slide N: Take-Away + Project Page [2:50 - 3:00]   ≈10 s

"[One sentence stating the take-away in plain language.] Paper, code, and additional rollouts are at [URL]."

*[QR code or URL. **No "thank you", no Q&A invitation** — there is no audience.]*

---

## Time Budget Summary

| Slide | Topic | Duration | Cumulative |
|:-----:|-------|:--------:|:----------:|
| 1 | Title + Pitch | 0:15 | 0:15 |
| 2 | Problem & Gap | 0:25 | 0:40 |
| 3 | Key Idea | 0:25 | 1:05 |
| 4 | Method | 0:25 | 1:30 |
| 5–(N-1) | Results (qualitative + quantitative) | 1:20 | 2:50 |
| N | Take-away + Link | 0:10 | 3:00 |

**Total**: 3:00 (hard cap; CoRL / ICRA / RSS / NeurIPS-supp)
```

**Differences vs. the default oral template — call these out explicitly to keep the LLM from drifting back to the oral arc:**

- ❌ **No anticipated-Q&A section.** A reviewer cannot ask follow-ups.
- ❌ **No "thank the chair" intro, no "thank the audience" outro.** There is no audience.
- ❌ **No standalone related-work slide.** The *gap* belongs in Slide 2; a literature dump does not belong in 3 minutes.
- ✅ **Problem + Key Idea + Method each get a real slide.** This is what differentiates a 3-min overview from a results reel.
- ✅ **Results are the single largest slot (~1:20 of 3:00 ≈ 45%) but not the only content.** The qualitative rollouts (via `[VIDEO: ...]` markers, consumed by `/paper-slides-render` v2) are the supplementary's distinct value-add over the static PDF.
- ✅ **Slide-1 pitch lands the headline result in the first 15 seconds.** A reviewer who skims only the opening should already know what the paper claims.
- ✅ **Calibrate written speakable text for TTS pacing (~155 wpm), not human-presenter pacing (~130 wpm).** Edge-TTS will overflow a 4-minute script if you write at oral-talk density.

After generating the TALK_SCRIPT.md, recommend the user advance to `/paper-slides-render` (which honors the `[VIDEO: ...]` markers) and then `/paper-video --mode submission --venue <V>` (which enforces the 180 s / 250 MB CoRL ceiling).

### Final Output Summary

```
📊 Slide generation complete:
- Talk type: [TALK_TYPE] ([TALK_MINUTES] min) for [VENUE]
- Files:
  slides/
  ├── main.tex              # Beamer LaTeX source
  ├── main.pdf              # Compiled slides (primary output)
  ├── presentation.pptx     # Editable PowerPoint (only if PPTX_AT_END==true or — with-pptx: true)
  ├── SLIDE_OUTLINE.md      # Slide-by-slide outline
  ├── SLIDES_REVIEW.md      # GPT-5.6-Sol review feedback
  ├── speaker_notes.md      # Per-slide speaker notes
  ├── TALK_SCRIPT.md        # Full word-for-word talk script + Q&A
  ├── SLIDES_STATE.json     # State persistence (includes pptx_status)
  ├── generate_pptx.py      # PPTX generation script (only if PPTX was built)
  └── figures/              # Symlinked from paper/figures/

Next steps:
1. Iterate on the PDF (slides/main.pdf) — the LaTeX source (slides/main.tex) is the source of truth. When the deck is final, re-run /paper-slides with — with-pptx: true to produce the editable PPTX.
2. Practice with TALK_SCRIPT.md (read aloud, time yourself)
3. Edit presentation.pptx for visual tweaks (animations, custom graphics) — once it has been built
4. Review Anticipated Q&A section before the talk
5. Do a dry run with a colleague
```

**State**: Write `SLIDES_STATE.json` with `phase: 8, status: "completed"`.

## Recommended Follow-up: `/slides-polish`

After this skill produces the initial Beamer + PPTX, the typical drift is
**typography proportion + per-slide layout**, not content. Run
`/slides-polish` as a focused post-generation polish phase: it does
per-page Codex review against a reference visual (e.g., a prior academic
talk), bumps PPTX fonts to projector-readable sizes, fixes text-frame
overflow, and applies a fix-pattern catalog (italic style leaks, em-dash
spacing, image aspect ratio, Chinese-font hints, anonymity placeholders).

`/slides-polish` is read-only on content (no claim / number / citation
edits) and preserves speaker notes verbatim. Invocation:

```
/slides-polish slides/ — reference: <ref-pdf> [— style: generic | why-rf | <venue>]
```

Skip it for short decks (< 5 slides) or when a complete redesign is
needed (re-run `/paper-slides` instead).

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- **One message per slide.** If a slide has two ideas, split it into two slides.
- **Minimal change on edits.** When the user asks to fix one thing, change only that — "adjust position, keep the size" means reposition (e.g., center), not resize; don't restyle or refactor unrequested elements across the deck.
- **Task-intro slides demonstrate, not describe.** Prefer a concrete `Question → Model → Answer` panel (drawn from the paper's prompt + choices) plus the explored attempt as frames, over abstract bullets.
- **Do NOT fabricate data.** All numbers must come from `paper/sections/*.tex`.
- **Bullet points only** — never full sentences on slides. Sentence fragments are fine.
- **Figure slides: figure ≥60% of slide area.** The figure IS the content.
- **Progressive disclosure**: Use `\pause` or `\onslide` for complex method slides.
- **De-AI polish**: Remove watch words from all slide text and talk script.
- **Do NOT hallucinate citations.** Reference only papers cited in the paper.
- **Opening hook matters**: Never start with "In this paper, we..." — start with the problem or a provocative question.
- **Font size minimums**: Title ≥28pt, body ≥20pt, footnotes ≥14pt.
- **Feishu notifications are optional.** If `~/.claude/feishu.json` exists, send notifications. If absent, skip.

## Parameter Pass-Through

```
/paper-slides "paper/" — talk_type: oral, venue: ICML, minutes: 20, aspect: 4:3, notes: false
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `venue` | NeurIPS | Conference for color scheme |
| `talk_type` | spotlight | oral/spotlight/poster-talk/invited |
| `minutes` | 15 | Talk duration |
| `aspect` | 16:9 | Aspect ratio (16:9 / 4:3) |
| `notes` | true | Generate speaker notes |
| `engine` | pdflatex | LaTeX engine |
| `auto proceed` | false | Skip checkpoints |

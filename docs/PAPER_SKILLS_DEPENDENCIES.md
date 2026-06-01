# Paper-Pipeline Skill Dependencies

A map of the **12 core skills** that turn a research idea + experimental results into a submitted paper plus its talk / poster / video supplements. Read this before deciding "which skill do I invoke now?" or "if I edit X, what downstream re-runs do I need?"

For a complete catalog of every skill in the repo (audits, helpers, orchestrators outside this path), see [`SKILLS_CATALOG.md`](SKILLS_CATALOG.md). For workflow-level shorthand (W1–W6), see [`AGENT_GUIDE.md`](../AGENT_GUIDE.md).

---

## TL;DR

The pipeline has **one trunk** (paper PDF) and **three downstream branches** (talk, poster, video). Each branch can be skipped independently.

```
                    ┌─────────────────────────────────┐
                    │   TRUNK — produces the paper    │
                    │   PDF that everything else      │
                    │   downstream depends on.        │
                    └─────────────────────────────────┘
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       ▼                          ▼                          ▼
  ┌──────────┐              ┌──────────┐              ┌──────────┐
  │   TALK   │              │  POSTER  │              │  VIDEO   │
  │  branch  │              │  branch  │              │  branch  │
  └──────────┘              └──────────┘              └──────────┘
```

---

## The 12 skills

| # | Skill | Role | Branch | Producer of |
|:-:|---|---|---|---|
| 1 | [`/paper-plan`](../skills/paper-plan/SKILL.md) | Outline → claims↔evidence matrix | TRUNK | `PAPER_PLAN.md` |
| 2 | [`/paper-figure`](../skills/paper-figure/SKILL.md) | Data → plots + comparison tables | TRUNK | `figures/fig*.pdf`, `figures/latex_includes.tex` |
| 3 | [`/paper-write`](../skills/paper-write/SKILL.md) | Sectioned LaTeX drafter | TRUNK | `paper/main.tex`, `paper/sections/*.tex`, `paper/references.bib` |
| 4 | [`/paper-compile`](../skills/paper-compile/SKILL.md) | LaTeX → PDF + page-limit gate | TRUNK | `paper/main.pdf` |
| 5 | [`/paper-writing`](../skills/paper-writing/SKILL.md) | Trunk orchestrator (1 + 2 + 3 + 4 + audits) | TRUNK | the whole `paper/` tree |
| 6 | [`/paper-writing-polish-loop`](../skills/paper-writing-polish-loop/SKILL.md) | Craft-only prose polish (no content edits) | TRUNK | `WRITING_POLISH_SUGGESTIONS.md`, in-place section edits |
| 7 | [`/paper-slides`](../skills/paper-slides/SKILL.md) | Paper → Beamer deck + speaker notes + talk script (+ PPTX on demand) | TALK | `slides/main.pdf`, `slides/TALK_SCRIPT.md`, `slides/presentation.pptx` (opt-in) |
| 8 | [`/slides-polish`](../skills/slides-polish/SKILL.md) | Per-page Codex review of `.pptx` | TALK | `slides/presentation_polished.pptx` |
| 9 | [`/paper-slides-render`](../skills/paper-slides-render/SKILL.md) | Beamer + talk script → narrated MP4 | TALK / VIDEO | `slides/render/presentation.mp4` |
| 10 | [`/paper-talk`](../skills/paper-talk/SKILL.md) | Talk-branch orchestrator (7 → 8 → audits) | TALK | `.aris/paper-talk/FINAL_REPORT.md` |
| 11 | [`/paper-poster`](../skills/paper-poster/SKILL.md) | Paper → A0/A1 poster (article + tcbposter) | POSTER | `poster/main.pdf`, `poster/poster_components.pptx` |
| 12 | [`/paper-video`](../skills/paper-video/SKILL.md) | Raw clips + manifest → venue-gated submission MP4 | VIDEO | `submission/video/supplementary.mp4` |

The **orchestrators** ([`/paper-writing`](../skills/paper-writing/SKILL.md), [`/paper-talk`](../skills/paper-talk/SKILL.md)) compose multiple leaf skills; the **leaves** (everything else) can also be invoked directly.

---

## TRUNK — the paper PDF

```
┌─ inputs ──────────────────────────────────────────────────────────┐
│  NARRATIVE_REPORT.md     AUTO_REVIEW.md     experiment results    │
│  IDEA_REPORT.md          PAPER_PREFERENCES.md                     │
└───────────────────┬───────────────────────────────────────────────┘
                    ▼
        ┌──────────────────────┐
        │   /paper-plan        │ ── claims ↔ evidence matrix
        │   (Phases 1-7)       │ ── section structure + page budget
        └──────────┬───────────┘ ── GAP_REPORT.md if citations short
                   │
                   │ writes: PAPER_PLAN.md
                   ▼
        ┌──────────────────────┐
        │   /paper-figure      │ ── data → plots + LaTeX tables
        │   (Steps 1-8)        │ ── DEDUP gate (no figure↔table redundancy)
        └──────────┬───────────┘
                   │ writes: figures/fig*.pdf,
                   │         figures/latex_includes.tex,
                   │         figures/TABLE_*.tex
                   ▼
        ┌──────────────────────┐
        │   /paper-write       │ ── reads PAPER_PLAN + figures/latex_includes
        │   (Phases 1-8)       │ ── enforces MIN_REFERENCES floor
        └──────────┬───────────┘ ── enforces GAP_REPORT markers for missing data
                   │
                   │ writes: paper/main.tex, paper/sections/*.tex,
                   │         paper/references.bib, paper/math_commands.tex
                   ▼
        ┌──────────────────────┐
        │   /paper-compile     │ ── latexmk → PDF
        │   (Steps 1-8)        │ ── page-shrink gate vs MAX_PAGES
        └──────────┬───────────┘
                   │ writes: paper/main.pdf, compile.log
                   ▼
        ┌──────────────────────┐
        │ (optional)           │
        │ /paper-writing-      │ ── craft-only prose pass
        │ polish-loop          │ ── HARD INVARIANT: no content changes
        │ (Phases 1-3)         │ ── Codex + Claude dual review
        └──────────┬───────────┘
                   │ writes: in-place edits to paper/sections/*.tex
                   ▼
              ┌────────────┐
              │  paper.pdf │  ⭐ TRUNK COMPLETE — this is what
              └────────────┘     the three branches all depend on
```

**[`/paper-writing`](../skills/paper-writing/SKILL.md)** is the **trunk orchestrator** that chains `paper-plan → paper-figure → paper-write → paper-compile → polish-loop → audits` end-to-end. Invoke it when you want to go from `NARRATIVE_REPORT.md` to a compiled PDF in one shot; invoke the leaves directly when you're iterating on a single phase.

---

## TALK branch — slides + narrated MP4

```
                ┌──────────────────┐
                │  TRUNK output    │  paper/main.pdf, paper/main.tex,
                │  (paper.pdf)     │  paper/sections/*.tex, paper/figures/
                └────────┬─────────┘
                         ▼
              ┌─────────────────────┐
              │  /paper-slides      │ ── Phase 1: outline (⛔ STOP for approval)
              │  (Phases 0-8)       │ ── Phase 4: latexmk → slides/main.pdf
              └─────────┬───────────┘ ── Phase 7: PPTX (⛔ STOP, opt-in)
                        │                                                            ── Phase 8: TALK_SCRIPT.md
                        │
       ┌────────────────┼────────────────────┐
       │                │                    │
  writes:          writes:               writes:
  slides/main.pdf  slides/                  slides/TALK_SCRIPT.md
  slides/main.tex   presentation.pptx        slides/speaker_notes.md
                   (only on opt-in!)
       │                │                    │
       ▼                ▼                    ▼
       │     ┌─────────────────────┐         │
       │     │  /slides-polish     │         │
       │     │  (Phases 0-5)       │         │
       │     │  per-page Codex     │         │
       │     │  review + fix loop  │         │
       │     └─────────┬───────────┘         │
       │               │                     │
       │     writes: slides/                 │
       │     presentation_polished.pptx      │
       │                                     │
       └──────────────────────────────┬──────┘
                                      ▼
                          ┌──────────────────────┐
                          │ /paper-slides-render │ ── reads main.pdf + TALK_SCRIPT.md
                          │ (Phases 0-3)         │ ── edge-tts + pdftoppm + ffmpeg
                          └──────────┬───────────┘ ── optional [VIDEO: …] markers
                                     │
                          writes: slides/render/presentation.mp4
                                     │
                                     ▼
                          ┌─ feeds into ─┐
                          │ /paper-video │ ── venue gating (CoRL / NeurIPS-supp)
                          │ --mode       │
                          │ submission   │
                          └──────────────┘
```

**Two non-obvious dependencies inside the talk branch**:

1. **PPTX is opt-in by default** — `/paper-slides` Phase 7 pauses for confirmation. The orchestrator [`/paper-talk`](../skills/paper-talk/SKILL.md) always passes `— with-pptx: true` so the downstream `/slides-polish` (which targets `.pptx` only) has a file to work on. If you invoke `/paper-slides` directly without the flag, then try to invoke `/slides-polish "slides/presentation.pptx"`, the polish step will fail "file not found" — re-run `/paper-slides — with-pptx: true` first.
2. **`/paper-slides-render` doesn't touch `.pptx`** — it reads `main.pdf` and `TALK_SCRIPT.md` only. PDF and PPTX outputs of `/paper-slides` ignore the `[VIDEO: …]` markers (LaTeX doesn't know them; `python-pptx` can't embed video shapes); only the rendered MP4 honors them.

[`/paper-talk`](../skills/paper-talk/SKILL.md) is the **talk-branch orchestrator** that chains `/paper-slides → /slides-polish → audits`. The assurance ladder (`draft` / `polished` / `conference-ready`) controls which sub-steps fire.

---

## POSTER branch

```
                ┌──────────────────┐
                │  TRUNK output    │
                └────────┬─────────┘
                         ▼
              ┌─────────────────────┐
              │  /paper-poster      │ ── article + tcbposter LaTeX
              │  (Phases 0-8)       │ ── 4-column IMRAD layout
              └─────────┬───────────┘ ── A0 / A1 PDF + editable PPTX + SVG
                        │
                writes: poster/main.tex,
                        poster/main.pdf,
                        poster/poster_components.pptx,
                        poster/poster.svg,
                        POSTER_CONTENT_PLAN.md,
                        POSTER_SPEECH.md
```

The poster branch is **single-skill** — `/paper-poster` produces everything in one go. It uses the **article class + tcbposter**, NOT beamer (architectural constraint to avoid TeX grouping overflow). No downstream consumers.

---

## VIDEO branch

```
                ┌──────────────────────────────────────┐
                │  Author-provided raw clips           │
                │  (recordings/*.mp4, figures/*.mp4)   │
                │  + submission/video/manifest.json    │
                │    (shot list, captions, trims)      │
                └────────────────┬─────────────────────┘
                                 ▼
                       ┌─────────────────────┐
                       │   /paper-video      │ ── ffmpeg assembles clips
                       │   (Steps 0-8)       │ ── anonymity scan
                       │   3 modes:          │ ── venue size / duration gates
                       │     submission      │
                       │     showcase        │
                       │     teaser          │
                       └─────────┬───────────┘
                                 │
                       writes: submission/video/supplementary.mp4,
                               submission/supplementary.zip (optional),
                               verify.json
```

The video branch can run **independently of the paper trunk** — user supplies raw clips. The link to the talk branch is informal: a typical workflow is `/paper-slides-render` → `presentation.mp4` → feed as one shot in `/paper-video`'s manifest if the user wants a narrated-deck section in the supplementary.

---

## Cross-branch file dependency reference

Every file that crosses a skill boundary, in one table.

| File | Producer | Consumer(s) | Notes |
|---|---|---|---|
| `NARRATIVE_REPORT.md` | external / user | `/paper-plan`, `/paper-writing` | research-experience report; pipeline input |
| `PAPER_PLAN.md` | `/paper-plan` | `/paper-figure`, `/paper-write`, `/paper-writing` | claims ↔ evidence matrix |
| `figures/fig*.pdf` | `/paper-figure` (auto) or manual | `/paper-write`, `/paper-poster`, `/paper-slides` | data plots; manual figures (architecture diagrams) must pre-exist |
| `figures/latex_includes.tex` | `/paper-figure` | `/paper-write` | `\includegraphics{…}` snippets |
| `figures/TABLE_*.tex` | `/paper-figure` | `/paper-write` | comparison tables (booktabs) |
| `paper/main.tex` + `paper/sections/*.tex` | `/paper-write`, `/paper-writing-polish-loop` | `/paper-compile`, `/paper-slides`, `/paper-poster` | LaTeX source — single source of truth for the paper |
| `paper/references.bib` | `/paper-write` | `/paper-compile`, `/citation-audit` (out of scope) | enforced MIN_REFERENCES floor |
| `paper/main.pdf` | `/paper-compile` | `/paper-slides`, `/paper-poster`, the user | compiled PDF; gates `MAX_PAGES` |
| `slides/main.pdf` | `/paper-slides` (Phase 4) | `/paper-slides-render`, `/slides-polish` (as visual reference) | beamer deck |
| `slides/main.tex` | `/paper-slides` (Phase 3) | `/slides-polish` (Beamer side) | beamer source |
| `slides/TALK_SCRIPT.md` | `/paper-slides` (Phase 8) | `/paper-slides-render` | per-slide quoted narration + `[VIDEO: …]` markers |
| `slides/speaker_notes.md` | `/paper-slides` (Phase 6) | the user (live talk) | short prompts per slide |
| `slides/presentation.pptx` | `/paper-slides` (Phase 7, **opt-in**) | `/slides-polish`, the user | editable; **deferred by default** |
| `slides/presentation_polished.pptx` | `/slides-polish` | the user | versioned copy; original PPTX never overwritten |
| `slides/render/presentation.mp4` | `/paper-slides-render` | `/paper-video` (optionally), the user | TTS-narrated MP4 |
| `poster/main.pdf` | `/paper-poster` | the user | A0 / A1 poster |
| `submission/video/manifest.json` | author-authored | `/paper-video` | shot list (clip paths, trims, captions, speed) |
| `submission/video/supplementary.mp4` | `/paper-video` | submission system | venue-gated |

---

## Re-run impact matrix — "if I edit X, what re-runs?"

| Edit | Force re-run | Optional re-run |
|---|---|---|
| `paper/sections/*.tex` (content) | `/paper-compile` | `/paper-slides`, `/paper-poster`, `/paper-writing-polish-loop` |
| `paper/sections/*.tex` (prose-only via `/paper-writing-polish-loop`) | `/paper-compile` | — (slides/poster content unaffected) |
| `figures/<one>.pdf` swapped manually | `/paper-compile` | — (slides/poster use the figure via `\includegraphics`; PDF re-resolves) |
| `figures/<one>` regenerated via `/paper-figure` | `/paper-compile` | re-run `/paper-figure` checks DEDUP gate vs tables |
| `slides/main.tex` hand-edited | `latexmk` (or re-`/paper-slides` Phase 4) | `/slides-polish` if Beamer-side changed; `/paper-slides-render` if PDF visual changed |
| `slides/TALK_SCRIPT.md` hand-edited | `/paper-slides-render` | — (PDF / PPTX unaffected) |
| `slides/presentation.pptx` hand-edited in PowerPoint | **nothing** | ⚠ but next `/paper-slides — with-pptx: true` overwrites it (PPTX is a derivative) |
| `paper/main.tex` re-built then talk wanted | `/paper-slides` from Phase 1 (outline) | — slides content depends on the paper; iterate the outline first |
| Manifest reordered for video | `/paper-video assemble + verify` | — |

**Rule of thumb**: the LaTeX source under `paper/` is the **single source of truth** for the paper; the LaTeX source under `slides/` is the source of truth for the talk; the PPTX is a **derivative** with no round-trip back. Same with the poster (`poster/main.tex` is canonical) and the video (the manifest is canonical).

---

## When to invoke each orchestrator vs. each leaf

| Situation | Use | Reason |
|---|---|---|
| Going from `NARRATIVE_REPORT.md` to PDF in one shot | [`/paper-writing`](../skills/paper-writing/SKILL.md) | trunk orchestrator; chains plan → figure → write → compile + audits |
| Just rebuilding the PDF after a section edit | [`/paper-compile`](../skills/paper-compile/SKILL.md) | leaf |
| Going from paper to "presentable talk" (slides + polish + audits) | [`/paper-talk`](../skills/paper-talk/SKILL.md) | talk-branch orchestrator |
| Just regenerating slides after a paper rev | [`/paper-slides`](../skills/paper-slides/SKILL.md) | leaf; start at Phase 1 outline |
| Just rendering MP4 from existing deck + script | [`/paper-slides-render`](../skills/paper-slides-render/SKILL.md) | leaf |
| Polishing an already-built PPTX | [`/slides-polish`](../skills/slides-polish/SKILL.md) | leaf |
| Making a poster | [`/paper-poster`](../skills/paper-poster/SKILL.md) | single-skill branch |
| Assembling a submission video from raw clips | [`/paper-video`](../skills/paper-video/SKILL.md) | independent leaf; user-driven manifest |
| Craft-only prose polish (no content changes) | [`/paper-writing-polish-loop`](../skills/paper-writing-polish-loop/SKILL.md) | leaf |

---

## What this map does NOT cover

- **Audit skills** (`/paper-claim-audit`, `/citation-audit`, `/experiment-audit`) — invoked by orchestrators at the `conference-ready` assurance level; not pipeline producers.
- **Helper / planning skills** (`/figure-spec`, `/figures-prep`, `/figure-description`, `/paper-illustration*`, `/paper-plan` precursors like `/experiment-plan`) — they couple to `/paper-figure` and `/paper-plan` but are not on the critical path.
- **Source-control** (`/overleaf-sync`, `/arxiv` submission helpers) — they wrap the outputs of this pipeline but don't change the producer/consumer graph.
- **Resubmission flow** (`/resubmit-pipeline`) — re-runs trunk + branches with a venue swap; uses these same 12 skills as building blocks.

If you need a wide-angle view of every skill, see [`docs/SKILLS_CATALOG.md`](SKILLS_CATALOG.md).

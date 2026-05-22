---
name: paper-illustration-plan
description: "Read a paper PDF, method note, or project brief and draft ready-to-render prompts for both a teaser (Figure 1) and an architecture/pipeline figure, with shared terminology and palette. Iterates via dialogue with the user, then hands off to /paper-illustration-image2 for rendering. Use when user says '生成论文配图描述', 'plan paper figures', 'draft figure prompts', 'plan teaser and architecture', 'two-figure plan', 'figure plan for paper'."
argument-hint: [paper-pdf-or-method-file]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, mcp__codex__codex, mcp__codex__codex-reply
---

# Paper Illustration Plan

Read a paper and produce **two coherent figure prompts** that
`/paper-illustration-image2` can render directly:

- a **teaser** (Figure 1 — the one-pane story)
- an **architecture / pipeline** figure (the engineering blueprint)

This skill **does not render images**. It is the planning half of a two-skill
pipeline:

```text
/paper-illustration-plan  →  prompt files  →  /paper-illustration-image2
       (this skill)                              (existing renderer)
```

## Core Design Philosophy

```text
User supplies a paper PDF / method note / draft
        │
        ▼
 ┌───────────────┐
 │   Claude      │  Step 1: Extract paper essentials (problem, insight,
 │  (Reader)     │           modules, I/O, key result, terminology)
 └──────┬────────┘
        │
        ▼
 ┌───────────────┐
 │   Claude      │  Step 2: Draft TWO coherent briefs
 │  (Planner)    │   - Teaser: narrative, one-pane story
 │               │   - Architecture: modular blueprint
 │               │   - Shared palette + terminology
 └──────┬────────┘
        │
        ▼
 ┌───────────────┐
 │ User dialogue │  Step 3: Iterate on both briefs together
 │  (Refine)     │   - Apply changes to the right file(s)
 │               │   - Keep terminology/colors consistent
 └──────┬────────┘
        │
        ▼
 ┌───────────────┐
 │   Output      │  Step 4: Save approved prompts
 │   Files       │   - figures/ai_generated/plans/*.md
 └──────┬────────┘
        │
        ▼
   Hand off to /paper-illustration-image2 for rendering
```

## Constants

- **PLANS_DIR = `figures/ai_generated/plans/`** — Output directory for plan files
- **TEXT_LANGUAGE = `English`** — Default figure-prompt language
- **DEFAULT_PLAN = `teaser + architecture`** — Both by default; user may opt out of either
- **HANDOFF_SKILL = `/paper-illustration-image2`** — Downstream renderer that consumes these plans
- **NO_RENDER_HERE = `true`** — This skill must NOT call image-generation tools

## Inputs

`$ARGUMENTS` may be:

1. A paper PDF path (e.g. `OpenVLA.pdf`)
2. A method note (Markdown / plaintext)
3. Free-form text describing the work
4. Empty — ask the user what to plan from

Read PDFs with the `Read` tool's `pages` argument when the file is large
(≤20 pages per call). Skim TOC + figures first, then read abstract, intro,
and the method section in depth.

## Workflow

### Step 0: Setup

1. Create `figures/ai_generated/plans/` if it does not exist.
2. Resolve `$ARGUMENTS` to a file or prompt-text. If nothing is provided, ask the
   user one short question ("Which paper / brief should I plan from?") and stop.
3. Confirm scope in one line:
   - default: **teaser + architecture**
   - allow opting out: "only teaser" or "only architecture"
4. If a plan already exists at `PLANS_DIR`, ask whether to refine the existing
   plan or start fresh.

### Step 1: Read and Extract

Read the paper (skim, then deep-read the method section). While reading, also
identify any **existing architecture / pipeline figure that the paper itself
references**:

- **PDF input** — When you Read the PDF, the architecture figure is **embedded
  inside the paper**; you see it visually. Note its page, its caption, and what
  it depicts (modules, arrows, grouping). The paper's existing figure is the
  structural source of truth.
- **LaTeX input** — Grep / scan the source for `\includegraphics{...}` calls
  whose surrounding `\caption{...}` mentions *architecture*, *pipeline*,
  *overview*, *framework*. Record the referenced file path.
- **Method note / free-form text input** — Likely no existing figure; mark as
  `none`.

Do NOT scan arbitrary filesystem paths looking for figures — the paper is the
authoritative index of which figure is the architecture figure.

Extract a structured brief into `figures/ai_generated/plans/paper_brief.md`:

```markdown
# Paper Brief — <Title>

## Problem
- one or two sentences

## Insight / Approach
- the core idea in plain language

## System I/O
- Inputs: ...
- Outputs: ...

## Modules
- module 1: <name> — <one-line role>
- module 2: ...

## Data flow
- input → module A → module B → output
- include side-paths (loss, retrieval, supervision, etc.)

## Key capability / Result
- what makes this paper Figure-1-worthy

## Terminology
- preferred names for each concept (use these exact strings in BOTH figures)

## Existing architecture figure in the paper
- `none` | <description of what the paper's existing architecture figure shows;
  for PDF: page number + visual summary; for LaTeX: \includegraphics path +
  caption + visual summary>
- If present, this becomes the **structural reference** the architecture prompt
  must replicate (same modules, same connections, same grouping). Only the
  illustrative style differs.
```

Keep `paper_brief.md` short and source-of-truth — both prompt files refer back to
it for terminology.

### Step 2: Draft Two Coherent Briefs

Draft a **teaser prompt** and an **architecture prompt** that share terminology
and palette intent. Each is a complete, ready-to-render image prompt that
`/paper-illustration-image2` can consume verbatim.

#### Teaser (Figure 1) — narrative, one-pane

A teaser is NOT a block diagram. It tells the paper's story in one visual:

- show the **problem domain** on the left (or as input)
- show the **paper's contribution** as the central transformation
- show the **outcome / capability** on the right (or as output)
- include lightweight scene cues that make the domain immediately obvious
- one strong horizontal flow
- stop short of decorative clip-art; stay paper-ready

Write `figures/ai_generated/plans/teaser_prompt.md`:

```markdown
# Teaser Prompt

## Figure type
Paper Figure 1 teaser — narrative one-pane illustration.

## Narrative arc (left → right)
1. <Input / problem scene>
2. <Core mechanism / contribution>
3. <Output / capability demonstration>

## Visual elements
- ...

## Style
- Academic, CVPR/NeurIPS-style first-page teaser
- Clean white background, restrained palette
- English labels, sans-serif
- Grayscale-safe

## Emphasize
- ...

## Avoid
- ...
```

#### Architecture (Pipeline) — modular blueprint

The architecture figure is the engineering view:

- show every module from the paper brief
- show the exact data flow with thick, dark arrows
- label inputs and outputs explicitly
- group related modules

**Default behavior — use the paper's existing architecture figure as a
structural reference.** If `paper_brief.md` recorded an existing architecture
figure, the new prompt must **replicate that figure's structure**: same modules,
same connection topology, same grouping, same left-to-right (or top-to-bottom)
flow. Only the illustrative style (palette, typography, rounded blocks, gentle
gradients) is regenerated. State this constraint explicitly in the prompt so the
renderer does not silently re-layout.

When no existing figure is referenced in the paper (free-form input or
method note), draft the architecture prompt from `paper_brief.md` from scratch.

Write `figures/ai_generated/plans/architecture_prompt.md`:

```markdown
# Architecture Prompt

## Figure type
Paper architecture / pipeline diagram.

## Structural reference
- `<source: e.g. paper PDF p.4 Figure 2, or figures/arch.pdf via \includegraphics>`
  | `none — drafted from paper_brief.md`
- If a reference is given, the renderer MUST preserve modules, connections,
  grouping, and flow direction. Only the illustrative style is regenerated.

## Modules (left → right unless otherwise noted)
1. <module name> — <role>
2. ...

## Data flow
- <module A> → <module B>: <what flows>
- ...

## Grouping
- <group 1>: <modules>
- ...

## Style
- CVPR/NeurIPS architecture figure
- Clean white background, restrained palette
- English labels, sans-serif
- Grayscale-safe; thick dark arrows

## Emphasize
- ...

## Avoid
- ...
```

#### Shared style guide

Both prompts must agree on palette, terminology, and rendering constraints.
Write `figures/ai_generated/plans/shared_style.md`:

```markdown
# Shared Style Guide

## Palette (consistent across teaser and architecture)
- <module type 1>: <color hint, e.g. "soft blue">
- <module type 2>: <color hint>
- arrows: dark gray / black
- background: white

## Terminology (must match in both figures)
- "Vision encoder" not "image encoder" / "img enc"
- "Action token" not "control output"
- ...

## Universal constraints
- English labels
- Sans-serif typography
- Grayscale-safe
- No glow, drop shadow, 3D perspective, rainbow gradient, decorative icons
```

### Step 3: Present and Iterate

Present the three drafts inline to the user, then iterate via dialogue:

- "only teaser" change → update `teaser_prompt.md`
- "only architecture" change → update `architecture_prompt.md`
- terminology / palette change → update `shared_style.md` AND propagate to both
  prompt files (rename / re-color in lockstep)
- "make teaser more X" or "architecture missing Y" → targeted edits

Optional cross-figure consistency check: if `mcp__codex__codex` is available,
ask it once for a short text-only critique — "is terminology consistent between
the teaser and the architecture; does the teaser convey the same story the
architecture realizes". Treat its reply as input to the next iteration. Do not
block on it.

Iterate until the user explicitly accepts (e.g. "ok 这样就好", "accept",
"looks good"). Do NOT auto-finalize without explicit acceptance.

### Step 4: Save and Hand Off

When the user accepts, the final files live at:

```text
figures/ai_generated/plans/
├── paper_brief.md          # extracted essentials
├── teaser_prompt.md        # ready-to-render prompt for Figure 1 (teaser)
├── architecture_prompt.md  # ready-to-render prompt for architecture/pipeline
└── shared_style.md         # palette + terminology + universal constraints
```

Print a hand-off block telling the user how to render:

```text
Plans saved under figures/ai_generated/plans/. Render with:

  /paper-illustration-image2 figures/ai_generated/plans/teaser_prompt.md
  /paper-illustration-image2 figures/ai_generated/plans/architecture_prompt.md

(/paper-illustration-image2 auto-detects plan files in figures/ai_generated/plans/
 and concatenates shared_style.md as additional style context.)
```

Do NOT call any image-generation tool from this skill.

## Hand-off Contract with `/paper-illustration-image2`

When the renderer is invoked with a plan file:

- It reads the prompt body from `teaser_prompt.md` or `architecture_prompt.md`
  instead of re-deriving from scratch.
- If `figures/ai_generated/plans/shared_style.md` exists in the same directory,
  it is concatenated as a style prefix so both figures stay consistent.
- Renderer Steps 2–7 (layout optimization, style verification, generation,
  review, refine, finalize) proceed unchanged.

## Key Rules

1. Plan two figures by default — teaser + architecture. Allow user to opt out
   of either.
2. Both prompts MUST share terminology and palette via `shared_style.md`.
3. The teaser is narrative (one-pane story); the architecture is modular
   (engineering blueprint). Do not let the teaser turn into another block
   diagram.
4. If the paper already contains an architecture / pipeline figure, default to
   using it as the **structural reference** for the architecture prompt
   (same modules, same connections, same grouping; only style is regenerated).
   Identify it by reading the paper itself — do NOT scan arbitrary filesystem
   paths.
5. Iterate via dialogue with the user before saving the final versions.
6. Every change that touches terminology or palette updates `shared_style.md`
   AND propagates to both prompt files.
7. Save plans as Markdown files under `figures/ai_generated/plans/`, ready to
   be consumed by `/paper-illustration-image2`.
8. Do NOT render images in this skill — hand off to `/paper-illustration-image2`.
9. Prefer English labels unless the user requests another language.
10. Stop on explicit user acceptance; do not auto-finalize.
11. Keep prompts paper-ready (grayscale-safe, restrained palette, no slide-deck
    decoration).

## Output Structure

```text
figures/ai_generated/plans/
├── paper_brief.md          # extracted essentials
├── teaser_prompt.md        # Figure 1 teaser
├── architecture_prompt.md  # architecture / pipeline
└── shared_style.md         # palette + terminology + universal constraints
```

## Model Summary

| Stage | Agent / Tool | Purpose |
|-------|--------------|---------|
| Step 0 | Claude | Resolve input, confirm scope |
| Step 1 | Claude (+ Read on PDF) | Extract paper essentials into `paper_brief.md` |
| Step 2 | Claude | Draft teaser, architecture, and shared style |
| Step 3 | Claude + user (+ optional `mcp__codex__codex` critique) | Iterate until accepted |
| Step 4 | Claude | Save final files and print hand-off block |
| (Render) | `/paper-illustration-image2` | Out of scope — separate skill |

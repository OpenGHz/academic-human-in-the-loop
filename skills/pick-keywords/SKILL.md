---
name: pick-keywords
description: "Suggest paper keywords for the `\\keywords{}` / `\\begin{IEEEkeywords}` block. Venue-aware: for `IEEE_CONF` targeting IROS/ICRA it picks 3–5 terms from the IEEE RAS controlled vocabulary (`shared-references/icra-keywords.md`); for CoRL/NeurIPS/ICLR/CVPR it proposes free-form terms that match the paper's actual contribution. Use when user says \"选关键词\", \"pick keywords\", \"IEEEkeywords\", \"suggest keywords\", or is filling in the keyword block during paper-write."
argument-hint: "[abstract-or-narrative-path] [— venue: <venue>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex, mcp__codex__codex-reply
---

# Pick Keywords: Venue-Aware Keyword Selection

Suggest paper keywords for: **$ARGUMENTS**

## Constants

- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP for a second opinion on the shortlist. Must be an OpenAI model.
- **DEFAULT_VENUE = `ICLR`** — Fallback if neither `— venue:` nor the input document declares one.
- **N_KEYWORDS_MIN = 3, N_KEYWORDS_MAX = 5** — Standard for both PMLR (CoRL) and IEEE (ICRA/IROS) venues. Fewer than 3 signals weak categorization; more than 5 dilutes routing.

## Inputs (auto-detect, first hit wins)

1. **Explicit `$ARGUMENTS`** — a path to an abstract, a full narrative report, or an inline description.
2. **`paper/sections/0_abstract.tex`** or **`paper/sections/abstract.tex`** — the drafted abstract.
3. **`NARRATIVE_REPORT.md`** / **`STORY.md`** in the project root.
4. **`PAPER_PLAN.md`** — the outline from `/paper-plan` (has claims-evidence matrix that reveals the contribution).

If none of these exist, ask the user for a one-paragraph description of the paper before proceeding.

## Venue Resolution

Priority: `— venue:` CLI arg > input document's `## Target Venue` section > `DEFAULT_VENUE`. Parse case-insensitively; strip year suffix (`"ICRA 2026"` → `IEEE_CONF` with robotics flag; `"CoRL 2026"` → `CORL`).

Set `VOCABULARY_MODE` from the resolved venue:

| Resolved venue | narrative mentions robot / manipulation / etc. | `VOCABULARY_MODE` |
|---|---|---|
| `IEEE_CONF` | yes | `ICRA_CONTROLLED` |
| `IEEE_CONF` | no | `IEEE_FREE` |
| `CORL` | any | `PMLR_FREE` |
| `ICLR` / `NeurIPS` / `ICML` / `CVPR` / `ACL` / `AAAI` / `ACM` | any | `ML_FREE` |
| `IEEE_JOURNAL` | any | `IEEE_FREE` |

## Workflow

### Step 1: Extract the paper's contribution vector

Read the input (abstract preferred, narrative fallback). Produce a compact JSON-like sketch — **do not write it to a file**, keep in memory:

```
{
  "contribution_type": "method | system | benchmark | theory | survey",
  "domain": ["manipulation", "locomotion", ...],
  "learning_paradigm": "supervised | imitation | reinforcement | self-supervised | none",
  "sensing_modalities": ["vision", "tactile", "proprioception", ...],
  "platform": ["real-robot", "simulation", "sim-to-real"],
  "key_technical_ideas": ["memory of successful trajectories", "field-of-view augmentation", ...]
}
```

This sketch guides the keyword search — it is NOT the output.

### Step 2: Generate candidates

#### If `VOCABULARY_MODE = ICRA_CONTROLLED`

1. Read [`../shared-references/icra-keywords.md`](../shared-references/icra-keywords.md) into working memory. This is the authoritative IEEE RAS PaperPlaza vocabulary.
2. For each element of the contribution vector, scan the vocabulary for matches:
   - `contribution_type = system` + `domain contains manipulation` → look at *Manipulation and Grasping* and *Manipulation and Grasping 2* categories.
   - `learning_paradigm = imitation` → check *Robot Learning 4* (Imitation Learning).
   - `learning_paradigm = reinforcement` → check *Robot Learning 2*.
   - `platform contains real-robot` + `domain contains manipulation` → `Perception for Grasping and Manipulation` is often a good third keyword.
3. Cross-reference with `## Selection Heuristics for Common Robotics Papers` at the bottom of the vocabulary file — if the paper matches one of the archetypes there, use its recipe as a strong prior.
4. Build a candidate list of 6–8 keywords (ranked by centrality), each tagged with the source category.
5. Apply anti-patterns from the vocabulary file: prune candidates that violate "all-same-category" or "keyword because it sounds impressive" rules.

#### If `VOCABULARY_MODE ∈ {PMLR_FREE, ML_FREE, IEEE_FREE}`

1. Free-form generation, but constrained by these principles:
   - **Match the community's actual usage.** For NeurIPS/ICLR: prefer terms that appear as CMT/OpenReview area chair topics (e.g., `representation learning`, `diffusion models`, `robot learning`). For CoRL: `imitation learning`, `manipulation`, `robot learning`, `sim-to-real`. For CVPR: `object detection`, `3D vision`, `video understanding`.
   - **No hyphens where the community uses spaces** (`vision language models` not `Vision-Language Models` in most ML venues) — but for IEEE venues, follow standard title case.
   - **Ordering: most-specific-first**. `Diffusion policy` before `Imitation learning` before `Robot learning`.
2. Draft 6–8 candidates, each tagged with rationale.

### Step 3: Codex second opinion

Send the abstract + candidate list to Codex MCP. Ask **one** focused question, do not chain:

```
You are helping choose 3–5 paper keywords for {venue}.
Below is the abstract and 6–8 candidates I generated.
{if VOCABULARY_MODE == ICRA_CONTROLLED: state that keywords MUST come from
 the attached IEEE RAS controlled vocabulary; paste vocabulary here.}

Return exactly 3–5 keywords, one per line, in priority order (most-central
first). After the list, one sentence per keyword explaining WHY it was
chosen and what alternative it beat. Do not add keywords outside the
candidate pool.

Abstract:
{abstract text}

Candidates:
- {kw 1}  — {my rationale}
- {kw 2}  — ...
...
```

Model: `gpt-5.5`. Effort: `medium`. This is a judgment call, not a research task.

### Step 4: Report

Emit exactly this shape to the user (stdout, not a file):

```
Recommended keywords for {venue} ({VOCABULARY_MODE}):

1. {keyword 1}     — {one-sentence why}
2. {keyword 2}     — {one-sentence why}
3. {keyword 3}     — {one-sentence why}
4. {keyword 4}     — {one-sentence why}   (optional)
5. {keyword 5}     — {one-sentence why}   (optional)

LaTeX snippet:

{if PMLR/CoRL:}
\keywords{{keyword 1}, {keyword 2}, {keyword 3}}

{if IEEE:}
\begin{IEEEkeywords}
{keyword 1}, {keyword 2}, {keyword 3}
\end{IEEEkeywords}

{if ICRA_CONTROLLED — extra reminder:}
> ⚠ Also select these exact strings in the PaperPlaza submission form.
> The `\begin{IEEEkeywords}` block and the portal selections must match,
> or the area chair may route the paper wrong.
```

Do NOT auto-edit `main.tex` or `sections/`. The user reviews and pastes.

### Step 5: (Optional) Overwrite the block on request

If the user follows up with "put them in" / "更新到论文" / "apply", locate the `\keywords{...}` or `\begin{IEEEkeywords} ... \end{IEEEkeywords}` block in `paper/main.tex` (or `paper/sections/*.tex` if that's where it lives) and replace it. Preserve surrounding blank lines. Do NOT touch anything else.

## Output Contract

- Never invent an ICRA vocabulary term. If in `ICRA_CONTROLLED` mode and Codex proposes a term not in the file, drop it silently and note "Codex proposed `X`; not in vocabulary, dropped."
- Never emit more than 5 or fewer than 3 keywords.
- Never edit the paper without an explicit follow-up instruction from the user.
- Always report which mode (`ICRA_CONTROLLED` / `PMLR_FREE` / etc.) drove the selection — the user needs this to know whether the terms are portal-strict.

## When NOT to Use

- If the paper is not yet drafted (no abstract, no narrative). Run `/paper-plan` first.
- If the target venue is `IEEE_JOURNAL` — journals have different (often narrower) keyword lists per journal (T-RO vs. RA-L vs. T-PAMI vs. T-Cyber). Consult the specific journal's Author Guide, not this skill.
- To pick arXiv categories (`cs.RO`, `cs.LG`, ...). Use `/arxiv-metadata` for that.

## References

- [`../shared-references/icra-keywords.md`](../shared-references/icra-keywords.md) — the IEEE RAS controlled vocabulary (authoritative for IROS/ICRA).
- [`../shared-references/venue-checklists.md`](../shared-references/venue-checklists.md) — the IROS/ICRA preferences subsection points here.
- [`../arxiv-metadata/SKILL.md`](../arxiv-metadata/SKILL.md) — for arXiv primary categories and ACM class codes.

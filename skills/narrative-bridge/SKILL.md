---
name: narrative-bridge
description: "Workflow 2.5: Bridge between auto-review loop and paper writing. Synthesizes NARRATIVE_REPORT.md from `review-stage/AUTO_REVIEW.md`, `CLAIMS_FROM_RESULTS.md`, `EXPERIMENT_LOG.md`, and `figures/` data — the document `/paper-writing` expects as input. Use when user says \"写 NARRATIVE_REPORT\", \"narrative report\", \"从 review 到 narrative\", \"准备投稿叙事\", \"bridge W2 to W3\", or has finished `/auto-review-loop` and needs the narrative report before invoking `/paper-writing`."
argument-hint: "[topic-or-claim-override] [— style-ref: <source>] [— venue: <venue>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# Workflow 2.5: Narrative Bridge

Synthesize `NARRATIVE_REPORT.md` from Workflow 2 outputs so `/paper-writing` can run end-to-end. Context: **$ARGUMENTS**

## Overview

This skill bridges Workflow 2 (auto-review loop) and Workflow 3 (paper writing). It reads everything `/auto-review-loop` produced — verified claims, method description, experiment numbers, latest remaining weaknesses — and composes them into the single artifact `/paper-plan` consumes.

```
Workflow 2 output:                       This skill:                              Workflow 3 input:
review-stage/AUTO_REVIEW.md         →   read → map → synthesize → review     →   NARRATIVE_REPORT.md
CLAIMS_FROM_RESULTS.md                  (no fabrication, source-cited)            ready for /paper-writing
findings.md / EXPERIMENT_LOG.md
figures/*.json
```

## Constants

- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP for narrative quality review. Must be an OpenAI model.
- **REVIEWER_BACKEND = `codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` per `shared-references/reviewer-routing.md`.
- **TARGET_VENUE = `ICLR`** — Default venue (informs Title / Target Venue sections). Override per `/paper-plan` venue list.
- **REVIEW = true** — Run a single Codex MCP review pass over the synthesized narrative for fabrication / overclaim / unsourced numbers. Set `false` to skip.
- **TEMPLATE_PATH = `templates/NARRATIVE_REPORT_TEMPLATE.md`** — Canonical schema. Fall back chain: `.aris/templates/NARRATIVE_REPORT_TEMPLATE.md` → `$ARIS_REPO/templates/NARRATIVE_REPORT_TEMPLATE.md`.
- **OUTPUT_PATH = `NARRATIVE_REPORT.md`** — Project root (where `/paper-plan` looks). Timestamped copy lives alongside it.
- **NO_FABRICATION = true** — Every number, claim, and figure description must trace to an input file. When evidence is missing, emit `<!-- DATA_NEEDED: ... -->` markers instead of inventing content. Do not override.

> 💡 Override: `/narrative-bridge — venue: NeurIPS, review: false`

## Activation Predicate

Fires when **at least one** of these exists (best-effort: the more inputs present, the higher fidelity):

```bash
[ -f review-stage/AUTO_REVIEW.md ] || [ -f AUTO_REVIEW.md ] \
  || [ -f CLAIMS_FROM_RESULTS.md ] \
  || [ -f EXPERIMENT_LOG.md ] \
  || [ -f findings.md ] \
  || ls figures/*.json 2>/dev/null | head -1
```

If **none** exist, do not invent a narrative — ask the user whether they actually want `/paper-plan` directly with a topic string instead.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write `NARRATIVE_REPORT_{YYYYMMDD_HHmmss}.md` first, then copy to `NARRATIVE_REPORT.md`
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log both files to `MANIFEST.md` under stage `paper-writing`
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting (NARRATIVE itself can be Chinese; downstream `/paper-write` re-renders LaTeX in English regardless)
> - **[Citation Discipline](../shared-references/citation-discipline.md)** — every numeric claim cites its source file path

## Inputs

The skill consumes (in priority order; missing files degrade gracefully into `DATA_NEEDED` markers):

| Source | What this skill pulls from it | Maps to |
|---|---|---|
| `review-stage/AUTO_REVIEW.md` (fallback `./AUTO_REVIEW.md`) | `## Method Description`; latest round's `Score`/`Verdict`/`Remaining Weaknesses` | Core Story, Known Weaknesses |
| `CLAIMS_FROM_RESULTS.md` | Structured claims + supporting evidence + integrity_status | Claims |
| `EXPERIMENT_LOG.md` | Per-run methods/datasets/metrics/baselines | Experiments → Setup, Experiments → Experiment N |
| `findings.md` | Cross-stage discoveries, negative results | Known Weaknesses, Core Story |
| `figures/*.json` / `figures/*.csv` | Actual numeric tables, plot data | Experiment tables, Figures (data source paths) |
| `refine-logs/FINAL_PROPOSAL.md` | Method name + architectural sketch | Core Story (method paragraph) |
| `refine-logs/EXPERIMENT_PLAN.md` | Hardware / baselines / dataset list | Experiments → Setup |
| `idea-stage/IDEA_REPORT.md` (fallback `./IDEA_REPORT.md`) | Motivation, prior-art positioning | Core Story (problem paragraph), Related Work |
| `references.bib` or `research-wiki/papers/` | Related work seed | Related Work |

## Workflow

### Phase 1: Discover & Read

1. Run the activation predicate. If false, prompt the user.
2. Detect template via fallback chain in `TEMPLATE_PATH`. Read it — it is the authoritative section schema.
3. Read every input that exists. Tag each fact you extract with its source path so Phase 4 can cite it.
4. If `CLAIMS_FROM_RESULTS.md` is missing **but** `review-stage/AUTO_REVIEW.md` shows a `## Method Description` + experiment results:
   - Invoke `/result-to-claim` to generate it. This restores the canonical W2 termination output.
   - If `/result-to-claim` is unavailable, extract claims directly from the latest round's verdict in `AUTO_REVIEW.md` and label them `[provisional — no /result-to-claim run]`.
5. Present a one-screen input inventory:
   ```
   📚 Narrative inputs detected:
   - review-stage/AUTO_REVIEW.md (N rounds, latest score X/10)
   - CLAIMS_FROM_RESULTS.md (K claims, integrity=pass|warn|fail|unavailable)
   - EXPERIMENT_LOG.md (M experiments)
   - figures/ (P JSON / Q CSV files)
   - findings.md, refine-logs/FINAL_PROPOSAL.md  [or: missing]
   Proceeding to synthesis.
   ```

### Phase 2: Section-by-Section Synthesis

Walk the template's section list and fill each from inputs. **Never invent content** — when a slot has no evidence, emit a `DATA_NEEDED` marker.

#### `# Narrative Report: [Title]`
- If `refine-logs/FINAL_PROPOSAL.md` proposes a method name → use `<Method Name>: <Effect> in <Setting>` pattern.
- Else mark `<!-- DATA_NEEDED: title — derive from method name + main claim -->`.

#### `## Core Story` (2-3 paragraphs)
1. **Problem paragraph** ← `idea-stage/IDEA_REPORT.md` motivation OR `findings.md` opening context. Cite e.g. `(see idea-stage/IDEA_REPORT.md §Motivation)`.
2. **Method paragraph** ← `review-stage/AUTO_REVIEW.md` § Method Description (verbatim if 1-2 paragraphs; otherwise condense). Cite source.
3. **Result paragraph** ← latest `AUTO_REVIEW` round's Verdict + headline metric from `EXPERIMENT_LOG.md`. Numbers MUST come from a real file — quote the file path in a `<!-- src: figures/xxx.json -->` comment.

#### `## Claims`
- **Primary path**: copy each entry from `CLAIMS_FROM_RESULTS.md`, preserving its `claim_supported` status (`yes`/`partial`/`no`). For each, append: `(evidence: <experiment-id> in EXPERIMENT_LOG.md, see figures/<file>)`.
- **Partial / no claims** stay in the list with explicit hedging — do NOT silently upgrade to `yes`. Overclaiming is the most common reason `/paper-claim-audit` fails downstream.
- If integrity_status == `fail` or `warn` (from `CLAIMS_FROM_RESULTS.md`), inject a top-of-section banner:
  ```
  > ⚠️ INTEGRITY: {status} — see EXPERIMENT_AUDIT.md. Claims below are flagged.
  ```

#### `## Experiments`
- **Setup** ← `refine-logs/EXPERIMENT_PLAN.md` (models, data, hardware, baselines). Fall back to scanning `EXPERIMENT_LOG.md`.
- **Experiment N** blocks ← one per logical experiment in `EXPERIMENT_LOG.md`. For each:
  - Markdown table from `figures/<expN>.json` or `figures/<expN>.csv` — **only numbers that exist in the file**. If the JSON contains baselines, include them; if not, do not invent baseline rows.
  - **Interpretation** sentence ← latest `AUTO_REVIEW` round's commentary on this experiment, if any; else one-line factual summary (no editorializing).

#### `## Figures`
- Scan `figures/` for JSON/CSV. For each, describe **what plot it could become** + the source path. Example: `**Figure 1**: bar chart — methods × accuracy on GSM8K/MATH/MMLU. Data: figures/main_results.json`.
- Do NOT list figures that have no underlying data file.
- For architecture / pipeline diagrams: if `review-stage/AUTO_REVIEW.md` has a `## Method Description`, add `**Figure: Architecture diagram** — derive from AUTO_REVIEW.md § Method Description via /paper-illustration`. Otherwise emit `<!-- DATA_NEEDED: architecture diagram — describe pipeline in 1-2 paragraphs first -->`.

#### `## Known Weaknesses`
- ← latest `AUTO_REVIEW` round's `Remaining Weaknesses` list, verbatim or lightly edited.
- Plus any `claim_supported == no | partial` from `CLAIMS_FROM_RESULTS.md` reformulated as a limitation.
- Do not delete weaknesses to make the narrative look stronger. Reviewers will find them; better to surface them now and pre-empt.

#### `## Related Work`
- ← `idea-stage/IDEA_REPORT.md` references section, OR scan `references.bib`, OR scan `research-wiki/papers/`.
- Group by category (3-5 categories typical). If none of these exist, emit `<!-- DATA_NEEDED: related work — run /research-lit before /paper-plan -->`.

#### `## Proposed Title` and `## Target Venue`
- Title: synthesize from method name + main claim + setting (avoid generic "X for Y").
- Venue: use `TARGET_VENUE` constant unless argument overrides.

### Phase 3: Numeric Audit (before review)

Before handing to the reviewer, run a self-check:

1. **Number-to-source mapping**: every number in the narrative must appear in at least one of `figures/*.json`, `figures/*.csv`, or `EXPERIMENT_LOG.md`. Grep each numeric token:
   ```bash
   grep -oE '\b[0-9]+\.[0-9]+\b' NARRATIVE_REPORT_*.md \
     | sort -u \
     | while read n; do
         grep -rlF "$n" figures/ EXPERIMENT_LOG.md 2>/dev/null \
           || echo "UNSOURCED: $n"
       done
   ```
2. Any `UNSOURCED:` line → either (a) replace with a `DATA_NEEDED` marker or (b) trace to source and add a `<!-- src: ... -->` comment.
3. Replace any survived `[X.XX]` / `XX%` template placeholders with real numbers or `DATA_NEEDED`.

### Phase 4: Codex MCP Review (when REVIEW = true)

**Skip this step if `REVIEW` is `false`.**

Send the draft to Codex for a single-pass adversarial read:

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    You are auditing a NARRATIVE_REPORT.md draft that will feed /paper-plan and downstream /paper-write.

    The draft must satisfy:
    1. Every numeric claim has a traceable source (figures/*.json / EXPERIMENT_LOG.md). Flag UNSOURCED.
    2. No claim is overclaimed beyond what /result-to-claim labeled `yes`. `partial` and `no` must be hedged.
    3. Known Weaknesses matches the latest AUTO_REVIEW round's "Remaining Weaknesses" — none silently dropped.
    4. Method Description (§Core Story paragraph 2) matches AUTO_REVIEW.md verbatim or faithfully condenses it.
    5. Figures section references only data files that exist on disk.

    Output:
    - verdict: PASS | NEEDS_FIXES | FAIL
    - issues: numbered list, each with section + specific fix
    - if PASS: one-line "ready for /paper-plan"
```

Apply Codex's fixes (or annotate `<!-- REVIEWER_NOTE: ... -->` if context-dependent). If verdict is `FAIL`, dump the issues into `paper-stage/NARRATIVE_REVIEW.md` and stop — do not write `NARRATIVE_REPORT.md` until the user resolves them.

Save the trace per `shared-references/review-tracing.md` (Policy C — never silently skip).

### Phase 5: Write & Manifest

1. Write timestamped: `NARRATIVE_REPORT_{YYYYMMDD_HHmmss}.md` at project root.
2. Copy to `NARRATIVE_REPORT.md` (the fixed name `/paper-plan` reads).
3. Append two rows to `MANIFEST.md`:
   ```
   | {ts} | /narrative-bridge | NARRATIVE_REPORT_{ts}.md | paper-writing | synthesized from W2 outputs (N claims, M experiments, K data files) |
   | {ts} | /narrative-bridge | NARRATIVE_REPORT.md | paper-writing | latest copy |
   ```
4. Append one line to `findings.md`:
   ```
   - [{ts}] narrative-bridge: NARRATIVE_REPORT.md synthesized. Claims yes/partial/no = X/Y/Z. Unsourced numbers resolved = N. DATA_NEEDED markers remaining = M.
   ```
5. If `DATA_NEEDED` markers remain, list them for the user with the fix command. Example:
   ```
   ⚠️  3 DATA_NEEDED markers remain:
     - Related Work (line 87)   → /research-lit "<topic>"
     - Figure 4 (line 112)      → /paper-figure  (data exists but no description)
     - Architecture (line 116)  → /paper-illustration

   /paper-plan will still run, but these slots will become <!-- DATA_NEEDED --> in the LaTeX output.
   ```

### Phase 6: Hand-off

Print exactly one suggested next command:

```
✅ NARRATIVE_REPORT.md ready.
Next: /paper-writing "NARRATIVE_REPORT.md" — venue: {TARGET_VENUE}
```

Do not invoke `/paper-writing` automatically — the user should confirm the narrative reads correctly first.

## Key Rules

- **No fabrication.** If you cannot find a number in `figures/` or `EXPERIMENT_LOG.md`, you do not write that number. Use `<!-- DATA_NEEDED: ... -->`. This is the same contract `/paper-write` uses to emit data markers downstream.
- **No silent claim upgrades.** `partial` stays `partial`. Overclaiming here propagates straight into `/paper-write` and surfaces in `/paper-claim-audit` rejections.
- **Source every numeric token.** Either inline (`73.4% on PG-19, src: figures/main.json`) or via `<!-- src: ... -->`. Phase 3 catches the rest.
- **Latest weaknesses, not cherry-picked.** Use the last `AUTO_REVIEW` round's `Remaining Weaknesses` — that is what the external reviewer still flagged after all repair rounds. Earlier-round weaknesses may have been fixed.
- **Template is authoritative.** If the user has customized `templates/NARRATIVE_REPORT_TEMPLATE.md` (e.g., extra Reproducibility section), follow their schema, not the one in this SKILL.md.
- **Idempotent.** Running `/narrative-bridge` twice on the same project state must produce byte-identical output (modulo timestamp). No randomness, no LLM-flavored prose variation.

## Anti-patterns (do NOT do these)

- ❌ Pull baseline numbers from memory of the literature — only numbers in this project's files.
- ❌ Round up `partial` claims to `yes` because the narrative reads better that way.
- ❌ Skip Known Weaknesses to make the paper look stronger.
- ❌ Emit a `Figure 1: training curve` without checking `figures/` actually has training-curve data.
- ❌ Auto-trigger `/paper-writing` on completion — the user must review the narrative first.
- ❌ Overwrite a user-edited `NARRATIVE_REPORT.md` without warning: if the existing file has no timestamp twin in `MANIFEST.md`, ask before overwriting.

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call (Phase 4), save the trace following `shared-references/review-tracing.md` (Policy C — forensic; never silently skip). Use `save_trace.sh` (resolved per `shared-references/integration-contract.md` §2) or write files directly to `.aris/traces/narrative-bridge/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).

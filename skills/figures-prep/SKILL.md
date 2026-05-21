---
name: figures-prep
description: "Prepare the `figures/` directory needed by `/paper-writing` by extracting structured JSON data from sources the NARRATIVE_REPORT.md explicitly cites. The Figures section of NARRATIVE_REPORT.md is the authoritative spec — this skill never modifies the narrative, only follows its references. Hard-blocks on missing data so downstream `/paper-figure` never silently skips a figure. Use when user says \"准备 figures 数据\", \"figures prep\", \"抽取实验数据\", \"figure data extraction\", \"从 narrative 抽 figures\", or has a NARRATIVE_REPORT.md but no figures/ yet."
argument-hint: "[narrative-report-path] [— gate: strict|advisory]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex, mcp__codex__codex-reply
---

# Figures Prep: NARRATIVE → figures/

Extract structured data files into `figures/` for: **$ARGUMENTS**

## Role in the Pipeline

```
/narrative-bridge → NARRATIVE_REPORT.md
                       │
                       ▼  (this skill, invoked from narrative-bridge or standalone)
                  /figures-prep
                       │
                       ▼
                  figures/*.json + figures/MANUAL_FIGURES.md + figures/MANIFEST.md
                       │
                       ▼
                  /paper-writing → /paper-figure → /paper-write → PDF
```

The skill produces the second of the two inputs `/paper-writing` consumes. `NARRATIVE_REPORT.md` is treated as **read-only authoritative spec** — its `## Figures` section dictates what to extract; this skill never edits a single line of it.

## Constants

- **EXTRACTOR_MODEL = `gpt-5.5`** — Codex MCP model for figure-brief parsing, source resolution, and number extraction. Must be an OpenAI model.
- **EXTRACTOR_BACKEND = `codex`** — Codex MCP at `xhigh` reasoning effort. The extraction is structurally light per call but high-stakes for numerical fidelity.
- **GATE_MODE = `strict`** — Default behavior on missing data: hard-block (exit non-zero, write report, do not produce a partial manifest). Override with `— gate: advisory` to continue with `DATA_NEEDED` markers (advisory mode is for early exploration, not for paths feeding `/paper-writing`).
- **NARRATIVE_PATH = `NARRATIVE_REPORT.md`** — Default narrative location. Override by passing a path as the first argument. The `figures/` directory is created **next to** `NARRATIVE_REPORT.md`, not at project root, so multi-idea repositories stay scoped.
- **OUTPUT_DIR = `<dirname of NARRATIVE>/figures/`** — Where data JSON, `MANIFEST.md`, and `MANUAL_FIGURES.md` go.
- **NO_FABRICATION = true** — Every number written must come from a source file resolved from NARRATIVE references. When a number cannot be found in any cited source, the skill records `DATA_NEEDED` for that figure and (in strict mode) blocks. Do not override.
- **MERGE = `auto`** — When two figure briefs reference identical sources and produce compatible schemas, merge into a single JSON file (recorded in MANIFEST.md against multiple `figure_id`s). Codex makes the call per Phase 3.

> 💡 Override: `/figures-prep research/ideas/X/NARRATIVE_REPORT.md — gate: advisory`

## Activation Predicate

Fires when:

```bash
[ -f NARRATIVE_REPORT.md ] || [ -f "$1" ]
```

If no narrative exists, exit with a single line pointing the user at `/narrative-bridge` first — do not attempt to synthesize figure plans from raw data.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write `figures/MANIFEST_{YYYYMMDD_HHmmss}.md` first, then copy to `figures/MANIFEST.md`. Data JSON files are content-addressable (re-runs overwrite identical names), not timestamped.
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log each generated JSON and the MANIFEST to the project-level `MANIFEST.md` under stage `paper-writing`.
> - **[Output Language Protocol](../shared-references/output-language.md)** — JSON field names use English regardless of project language (downstream `/paper-figure` is language-agnostic; English keys avoid Unicode surprises).
> - **[Citation Discipline](../shared-references/citation-discipline.md)** — every numeric value in extracted JSON has a `_provenance` sidecar entry mapping it back to a source file path + locator (line range, table id, or JSON key path).

## Inputs

This skill resolves all data sources **from references inside NARRATIVE_REPORT.md**. It does not assume any project layout.

| Source | What this skill pulls from it |
|---|---|
| `NARRATIVE_REPORT.md` § Figures | Authoritative figure / table spec: id, type, description, data-source hints, pattern hint |
| `NARRATIVE_REPORT.md` body (Experiments, Claims) | Secondary source-path mentions when the Figures entry is terse (e.g. "Source: E01 results.md") |
| Any path referenced by the above | Read as-is — `.md`, `.json`, `.csv`, `.log`, directory listings, even template-style references |

The skill does not assume `experiments/`, `raw_data/`, `results/`, or any other directory exists. If NARRATIVE points to `weird/path/x.parquet`, the skill reads that path.

## Workflow

### Phase 0: Locate Narrative & Prepare Output Dir

1. Resolve `NARRATIVE_PATH`:
   - First positional argument if provided
   - Else `NARRATIVE_REPORT.md` in CWD
   - Else fail with one-line pointer to `/narrative-bridge`
2. Compute `OUTPUT_DIR = $(dirname NARRATIVE_PATH)/figures/`. Create it if absent.
3. If `OUTPUT_DIR/MANIFEST.md` already exists, read it — Phase 6 will diff against the prior run to report which JSONs are new / overwritten / unchanged.

### Phase 1: Parse the Figures Section

Use a Codex MCP call (small, structured) to extract a machine-readable inventory from the `## Figures` section:

```
mcp__codex__codex:
  model: gpt-5.5
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Read the ## Figures section of the NARRATIVE below. For each numbered entry
    (Figure 1, Table 1, etc.), output a JSON object with these fields:

    - figure_id: e.g. "Fig 1", "Table 1"
    - figure_type: one of {bar, line, scatter, heatmap, box, comparison_table,
                           schematic, architecture, pipeline, qualitative, hero, other}
    - kind: "data_figure" if figure_type ∈ {bar, line, scatter, heatmap, box,
                                            comparison_table, other-data};
            "manual_figure" otherwise.
    - description: the prose description of what the figure should show.
    - pattern_hint: any expected pattern the author flagged (e.g. "should show
                    five +0.40 to +0.48 uplift bars on a single axis"). null if none.
    - source_hints: array of every path-like or document-like reference the
                    entry mentions (file paths, "E01 results.md", directory names,
                    cross-reference to ## Experiments tables, etc.).

    Output: a JSON array, one object per figure/table entry, IN ORDER.
    No prose, no markdown — just the JSON.

  attachments:
    - NARRATIVE_REPORT.md (figures section only — slice between ## Figures and the next ## heading)
```

Save the inventory to `OUTPUT_DIR/.figures-prep/inventory.json` for downstream phases and re-run diffing.

### Phase 2: Source Resolution (no hardcoded paths)

For each figure's `source_hints`, resolve to concrete files **using only what the narrative says** — never guess based on conventional ARIS folder names.

For each hint, classify and resolve:

1. **Explicit existing file path** (`raw_data/x/y.json`, relative to narrative dir or project root) → read directly.
2. **Semi-structured reference** (`E01 results.md per-task tables`, `M01 method document`) →
   - Look in the body of NARRATIVE_REPORT.md (Experiments / Setup / Method sections) for the literal phrase `E01` / `M01` and any path it pairs with there
   - Then `find` the narrative's directory (and one parent up) for files whose basename matches the surfaced identifier; if there are matches, list them and pick by Codex judgment
3. **Directory reference** → list contents, hand list to Codex along with the figure brief, ask which file(s) inside are relevant
4. **Code/repo cross-reference** (`scripts/run_group_gated_eval.py`) → record path but do not read for data extraction (these are method references, not data)
5. **Unresolved** → flag for Phase 6 gate

Write `OUTPUT_DIR/.figures-prep/sources.json`:
```json
{
  "Fig 1": {
    "resolved": ["raw_data/real/results/E01.json", "experiments/E01-evidence-compiler-vs-vlm/results.md"],
    "unresolved": [],
    "method_refs": []
  },
  ...
}
```

### Phase 3: Merge Planning (`MERGE = auto`)

Hand the inventory + sources to Codex and ask for a merge plan:

```
mcp__codex__codex:
  prompt: |
    Given these figure inventories and resolved sources, propose a merge plan.

    Two figures may merge into ONE output JSON file iff:
    (a) their resolved sources are identical or strictly nested, AND
    (b) the data needed can be expressed in one coherent schema (e.g. both want
        per-task accuracy across the same task set).

    Do NOT merge:
    - figures that need different aggregations of the same source (e.g. headline
      bar chart vs. per-chain breakdown — different rollups)
    - figures with different x-axes / metrics

    Output: array of merge groups, each with `members` (figure_ids) and
    `output_basename` (slug, e.g. "main_results", "modality_ablation").

  inputs:
    - inventory.json
    - sources.json
```

Save plan as `OUTPUT_DIR/.figures-prep/merge_plan.json`. Manual figures are always in their own (degenerate) group.

### Phase 4: Per-Group Data Extraction

For each `data_figure` merge group, one Codex call:

```
mcp__codex__codex:
  model: gpt-5.5
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Extract structured data for these figure(s): {figure_briefs}.

    Source files (FULL CONTENTS BELOW):
    --- {source_path_1} ---
    {file_1_content}
    --- {source_path_2} ---
    {file_2_content}

    Output a single JSON object that:
    1. Has semantically named fields (NOT "col1"/"value1"). Field names should
       match terminology in the figure description and source files.
    2. Preserves per-seed / per-episode / per-run arrays — do NOT pre-average.
    3. Includes a `_provenance` sub-object mapping each top-level numeric field
       to {"source": "<path>", "locator": "<line range or table row id>"}.
    4. For any value the figure brief implies but you cannot find in the source
       files, emit "DATA_NEEDED: <reason>" as the string value. Do not fabricate.

    Schema is yours to design — pick what best fits the figure type (e.g. one
    bar chart wants {x_labels: [...], values: [...]}; a heatmap wants {rows:
    [...], cols: [...], data: [[...], ...]}).

    Output: pure JSON, no prose.
```

Write to `OUTPUT_DIR/{output_basename}.json`. Do **not** write partial JSON if extraction errors — fail loudly so Phase 6 catches it.

### Phase 5: Manual-Figure Placeholders

For each `manual_figure` group, do NOT call an image generator. Append to `OUTPUT_DIR/MANUAL_FIGURES.md`:

```markdown
## Fig 4 — Pipeline schematic

**Description (from NARRATIVE):** ...

**Source references:** methods/M01-evidence-compiler.md

**Suggested next steps** (pick one):
- `/paper-illustration "<one-line spec derived from description>"` — Gemini renderer
- `/paper-illustration-image2 "<one-line spec>"` — Codex native image renderer
- Hand-draw with draw.io / TikZ, save to `figures/fig4_pipeline.pdf`

The downstream `/paper-figure` skill will detect any of the above outputs and
preserve them; `/paper-write` will auto-include them in LaTeX.
```

### Phase 6: Gate (`GATE_MODE = strict` default)

Scan all generated JSONs:

```bash
# Block-condition checklist:
#  - Any figure_id in inventory has no entry in sources.json with `unresolved == []`
#  - Any JSON contains a string value starting with "DATA_NEEDED:"
#  - Any merge group failed extraction (no output JSON written)
```

If any block-condition is true:

**Strict mode (default):** Write `OUTPUT_DIR/GATE_REPORT.md` with a per-figure breakdown:

```markdown
# /figures-prep — Gate Report (BLOCKED)

The following figures cannot be prepared cleanly. Resolve each item below, then re-run.

## Fig 2 — Modality ablation heatmap

- **Missing data:** HY-Embodied row 7 accuracy on lamp (n missing)
- **Source consulted:** experiments/E02-ablation-evidence-sources/results.md
- **NARRATIVE reference:** "Cross-task ablation table (HY-Embodied-0.5-X, n=21 unless noted)"
- **Fix options:**
  1. Add the missing number to experiments/E02-ablation-evidence-sources/results.md and re-run /figures-prep
  2. If the experiment was not run, update NARRATIVE_REPORT.md § Figures to remove this row from Fig 2

...
```

Then exit non-zero. Do **not** write `MANIFEST.md` — a present MANIFEST signals a clean state to `/paper-writing`.

**Advisory mode (`— gate: advisory`):** Write GATE_REPORT.md but also write MANIFEST.md flagged with `status=partial`, and exit zero. Use only for exploratory iteration; `/paper-writing` will refuse to start with a partial manifest.

### Phase 7: Manifest (only on clean state)

If Phase 6 passes, write `OUTPUT_DIR/MANIFEST_{ts}.md` then copy to `OUTPUT_DIR/MANIFEST.md`:

```markdown
# figures/ Manifest — generated by /figures-prep at {ts}

NARRATIVE source: NARRATIVE_REPORT.md (sha256: {hash})
Status: ready

| ID(s) | Kind | Output | Sources |
|-------|------|--------|---------|
| Fig 1 | data | figures/main_results.json | raw_data/real/results/E01.json, experiments/E01/results.md |
| Fig 2 | data | figures/modality_ablation.json | experiments/E02/results.md, raw_data/real/results/E02.json |
| Fig 3 | data | figures/door_perchain.json | experiments/E02/results.md |
| Fig 4 | manual | MANUAL_FIGURES.md (pending user action) | methods/M01-evidence-compiler.md |
| Table 1 | data | figures/main_results.json (shared with Fig 1) | (same as Fig 1) |
| Table 2 | data | figures/modality_ablation.json (shared with Fig 2) | (same as Fig 2) |

## Provenance

Per-figure number-to-source mapping is embedded in each JSON's `_provenance` field.
```

Append to project-root `MANIFEST.md` per Output Manifest Protocol.

Append one line to project-root `findings.md`:
```
- [{ts}] figures-prep: figures/ ready for /paper-writing. {N_data} data JSONs, {N_manual} manual placeholders, 0 DATA_NEEDED.
```

### Phase 8: Hand-off

Print exactly one suggested next command:

```
✅ figures/ ready ({N_data} data files, {N_manual} manual placeholders).
Next:
  - If MANUAL_FIGURES.md is non-empty: address those first
    (/paper-illustration or hand-draw)
  - Then: /paper-writing "NARRATIVE_REPORT.md" — venue: {VENUE}
```

Do not invoke `/paper-writing` automatically.

## Key Rules

- **NARRATIVE is read-only.** This skill must not edit `NARRATIVE_REPORT.md` for any reason — not to add Source: lines, not to renumber figures, not to fix typos. If the narrative's Figures section is ambiguous, that is a `/narrative-bridge` problem, not a `/figures-prep` problem.
- **Paths come from NARRATIVE, never from convention.** Do not glob for `experiments/`, `raw_data/`, `results/`, or any other ARIS-conventional directory unless NARRATIVE itself mentions them. The whole point of this skill is to be project-layout-agnostic.
- **Hard-block by default.** A clean `figures/` directory is one with zero `DATA_NEEDED` markers. The gate is what makes downstream `/paper-figure` safe — if you let a `DATA_NEEDED` slip through, `/paper-figure` will silently skip that figure and the PDF ships with a hole.
- **One output per merge group.** Resist the temptation to produce one JSON per figure when two figures share a data source — the merge plan from Phase 3 is the source of truth, and MANIFEST.md maps figure_ids to shared JSONs.
- **Provenance over compression.** Every numeric value should be traceable back to a source path + locator. Do not trim `_provenance` to save bytes — it is what makes the extraction auditable.
- **No `paper-figure` invocation.** This skill produces data JSON only; rendering is `/paper-figure`'s job. Calling `/paper-figure` here would couple two phases that should stay separate.
- **No image generation.** Manual figures get listed in `MANUAL_FIGURES.md`; the user (or downstream `/paper-illustration*`) handles them.
- **Idempotent on clean state.** Re-running `/figures-prep` against an unchanged NARRATIVE + unchanged sources must produce byte-identical output JSONs (modulo timestamp on MANIFEST).

## Anti-patterns (do NOT do these)

- ❌ Edit NARRATIVE_REPORT.md to "fix" a missing source reference. If it is missing, that is a gate failure, and the user must resolve in the narrative.
- ❌ Default-search `experiments/`, `raw_data/`, `results/` when NARRATIVE doesn't mention them. The skill must work on a project where the user calls their data dir `runs/` or `data_v3/`.
- ❌ Average per-seed numbers before saving JSON. `/paper-figure` needs raw arrays to compute error bars.
- ❌ Invent baseline rows the source files don't contain. Reviewers compare numbers against the codebase; fabricated baselines are caught by `/paper-claim-audit`.
- ❌ Write `MANIFEST.md` when the gate failed. Downstream skills use MANIFEST presence as a green-light signal.
- ❌ Call `/paper-illustration` or `/paper-figure` from within this skill. Stay in your lane.
- ❌ Read CWD-relative paths when NARRATIVE_PATH is absolute and elsewhere. Resolve all source paths relative to `dirname(NARRATIVE_PATH)` first, falling back to project root.

## Review Tracing

Each `mcp__codex__codex` call (Phase 1 parse, Phase 2 source-resolution disambiguation, Phase 3 merge planning, Phase 4 extraction) is saved per `shared-references/review-tracing.md` (Policy C — never silently skip). Traces live in `.aris/traces/figures-prep/<date>_run<NN>/`. Respect `--- trace:` parameter (default `full`).

## Integration with narrative-bridge

`/narrative-bridge` invokes this skill in its Phase 1.5 (after NARRATIVE is synthesized or confirmed unchanged) via the `Skill` tool. The contract:

- `/figures-prep` exits zero iff `figures/MANIFEST.md` was written cleanly
- On non-zero exit, `/narrative-bridge` surfaces `GATE_REPORT.md` to the user and exits without printing "ready for /paper-writing"
- The user resolves the gated items in their source files (or revises NARRATIVE), then re-runs `/narrative-bridge` (which idempotently re-invokes this skill)

This is intentionally asymmetric to `/narrative-bridge`'s own graceful-degradation behavior: a NARRATIVE with `<!-- DATA_NEEDED -->` markers is still a useful artifact; a `figures/` with missing JSONs causes silent failures downstream. Hard-block here, graceful-degrade in the narrative.

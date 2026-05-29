---
name: paper-writing-polish-loop
description: "Writing-only polish loop, 3 phases: (1) global pass on whole-paper concerns, (2) per-section loop one section at a time, (3) optional second global pass. In every phase, Claude and Codex (as 'professional embodied-AI writer', gpt-5.5 xhigh, fresh thread — never codex-reply) run in **parallel** via a background Agent, each producing **all** writing-craft suggestions they can find — no artificial cap, so a problem-dense paper gets exhaustive coverage. Overlapping pairs auto-apply (high-confidence: two peers agree). Non-overlapping suggestions land in WRITING_POLISH_SUGGESTIONS.md and are presented to the user in **priority batches** (HIGH → MEDIUM → LOW) to manage decision fatigue. Standard HUMAN_CHECKPOINT syntax (go / 1 3 5 / skip 2,4 / stop / free-text) per batch. Recompile is deferred to end-of-phase. For robotics / embodied-AI papers. Use when user says \"优化写作\", \"polish writing\", \"writing polish loop\", \"写作打磨\", \"craft pass\", or wants a writing-craft-focused pass distinct from content/theory review."
argument-hint: "[paper-directory]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex
---

# Paper Writing Polish Loop: Claude × Codex Dual Coach (3-Phase)

Polish the writing craft of the paper at: **$ARGUMENTS**

## Context

This skill is a **focused, three-phase writing-craft loop**. It is **NOT** a replacement for `/auto-paper-improvement-loop` — that skill handles content claims, theory consistency, visual presentation, page-shrink, kill-argument, citation floor, restatement regression, and more. This skill handles **only writing craft**: vocabulary, sentence patterns, paragraph rhythm, section construction, figure/table caption phrasing, rhetorical transitions, opener/closer patterns.

The three phases:

1. **Phase 1 — Global pass.** Both Claude and Codex read **only the global / cross-section** parts of `embodied-ai-paper-writer` (top-level `SKILL.md` + `flow-transitions.md` + `language-phrasebank.md` + `figures-tables-playbook.md`), look at the whole paper as one artifact, and produce **every global craft issue they can find** — contribution-noun-phrase consistency across abstract↔intro↔conclusion, 6-move rhetorical arc, tense / voice consistency, abstract self-containment, paired condition-label axis, load-bearing modifier sweep, etc. No artificial cap; the only filter is the craft-only scope.
2. **Phase 2 — Per-section loop.** For each section file in `main.tex`'s `\input` order, both Claude and Codex read **only that section's `.tex`** plus the **corresponding per-section playbook** (e.g., `0_abstract.tex` pairs with `abstract-intro-playbook.md`). Every craft issue they can find in that section. Recompile is deferred to the end of the phase.
3. **Phase 3 — Optional second global pass.** Ask the user; if yes, re-run Phase 1 logic on the now-polished paper to catch any new arc / consistency issues introduced by per-section edits. If no, finalize.

**Why no suggestion cap.** A cap forces both sides to self-censor and pick "top-N", which biases against problem-dense papers — exactly the papers that most need a thorough pass. The cost of an uncapped pass is more reading for the user, but the priority-batched checkpoint (HIGH → MEDIUM → LOW) keeps each decision step short, and the user can `stop` at any batch.

Use this loop when the paper is content-stable but the prose needs tightening — e.g., near final submission, after the experiments are locked, or when reviewer feedback singled out "writing quality" without flagging content issues.

**This skill is designed for robotics / embodied-AI papers.** Both Claude and Codex consult `skills/embodied-ai-paper-writer/SKILL.md` as their shared craft manual. For non-robotics papers, prefer `/auto-paper-improvement-loop` which uses `shared-references/writing-principles.md` instead.

## Why this differs from `/auto-paper-improvement-loop`

| Aspect | auto-paper-improvement-loop | paper-writing-polish-loop |
|---|---|---|
| Codex role | senior ML reviewer (scores 1-10, gives verdict) | professional writing coach (gives every craft issue it can find, no scoring) |
| Scope | content + theory + visual + structure + writing | writing craft only |
| Suggestion count | implicit cap via review prose | **uncapped** — both sides emit every craft issue they can find |
| Rounds / phases | 2 rounds (review → fix → recompile × 2) | **3 phases (global → per-section loop → optional global re-run); 1-2 recompiles total** |
| Granularity | whole paper per round | **global pass + per-section loop + optional global re-run** |
| Playbook loading | optional whole manual | **Phase 1/3: cross-section playbooks only; Phase 2: per-section playbook keyed by file basename** |
| Sees PAPER_PREFERENCES.md? | only Claude (Codex is reviewer → context-naive) | **both** (Codex is coach, not reviewer) |
| Sees embodied-ai-paper-writer? | optionally as background reference | **mandatory for both sides** |
| Inline user feedback? | optional `HUMAN_CHECKPOINT` per round | always — priority-batched (HIGH → MEDIUM → LOW) per phase, and once per section in Phase 2 |
| EDIT_WHITELIST / MIN_REFERENCES | enforced | out of scope (craft-only edits) |
| codex-reply allowed? | only when `REVIEWER_BIAS_GUARD = false` | **never** (fresh thread only) |
| Claude × Codex execution | sequential (review → fix → recompile) | **parallel** every phase, every section (background Agent) |

If you want both content AND writing polish, run `/auto-paper-improvement-loop` first, then this skill at the end for a final craft pass.

## Constants

- **SUGGESTION_CAP = none** — Neither Claude nor Codex is told to limit the number of suggestions in any phase. Both sides emit every craft issue they can find within the playbook scope. The user's protection against decision fatigue is the priority-batched checkpoint in Sub-procedure B (HIGH → MEDIUM → LOW batches, each its own checkpoint, `stop`-able at any batch), NOT a cap. **Rationale:** a problem-dense paper is exactly the case that benefits most from a thorough pass; capping forces self-censorship that biases against such papers.
- **SUGGESTION_OUTPUT_FORMAT = NDJSON** — Both sides emit one JSON object per line (newline-delimited JSON). This is the cap-free output format's truncation insurance: if a long Codex response is cut mid-stream by transport limits, every complete line before the cut is still parseable; only the trailing partial line is lost. A single JSON array, by contrast, becomes unparseable on any truncation.
- **CHECKPOINT_BATCH_BY_PRIORITY = true** — Pending non-overlap suggestions are split into HIGH / MEDIUM / LOW batches; the user sees one batch at a time. `stop` at any batch exits the rest of the phase.
- **WRITER_MODEL = `gpt-5.5`** — Model used via `mcp__codex__codex` for the Codex side.
- **WRITER_REASONING = `xhigh`** — `model_reasoning_effort` for the Codex call.
- **GLOBAL_PLAYBOOKS** = `["flow-transitions.md", "language-phrasebank.md", "figures-tables-playbook.md"]` — read in Phase 1 + Phase 3 only. These cover cross-section concerns: arc / openers / pivots / connectors (`flow-transitions.md`), rhetorical phrasebook (`language-phrasebank.md`), and figure/table conventions that span sections (`figures-tables-playbook.md`).
- **SECTION_TO_PLAYBOOK_MAP** — basename-prefix → playbook list (matched case-insensitively against the section file's basename without `.tex`):
  - `0_abstract`, `abstract`, `1_intro*`, `intro*` → `["abstract-intro-playbook.md"]`
  - `2_related*`, `related*`, `3_method*`, `method*`, `approach*` → `["method-relatedwork-playbook.md"]`
  - `4_main_results`, `4_results`, `results*`, `5_ablation*`, `ablation*`, `experiments*`, `evaluation*` → `["experiments-results-playbook.md"]`
  - `6_limitations`, `limitations*`, `7_conclusion`, `conclusion*`, `discussion*`, `future*`, `A_appendix*`, `appendix*` → `["closing-appendix-playbook.md"]`
  - Title (parsed from `\title{}` in `main.tex`) → `["titles.md"]` (Phase 1 only; appended to global playbooks if a `\title{}` is found)
  - Fallback for unmatched files → `[]` (skip Phase-2 iteration for that section; log it)
- **OUTPUT_MD = `WRITING_POLISH_SUGGESTIONS.md`** — Cumulative log written to the paper directory. Grows across Phase 1 → Phase 2 (per section) → Phase 3.
- **STATE_FILE = `WRITING_POLISH_STATE.json`** — Compact-recovery state file, written after each phase / section / sub-step.
- **PRESERVE_PDF_SNAPSHOTS = true** — Keep `main_polish_before.pdf` and `main_polish_final.pdf` for visual diff.

## Inputs

Both Claude AND Codex receive the same input set in every phase. This is the explicit divergence from `/auto-paper-improvement-loop`'s Reviewer Independence Protocol — here Codex is a coach, not a reviewer, so author-side context is on the table.

1. **Compiled paper** — `<paper-dir>/main.pdf` + all `<paper-dir>/sections/*.tex` (or whatever `.tex` files `main.tex` `\input`s).
2. **`skills/embodied-ai-paper-writer/SKILL.md`** — **mandatory** craft manual. Phase 1 + Phase 3 also load `GLOBAL_PLAYBOOKS`; Phase 2 loads only the playbook(s) keyed by the current section's basename via `SECTION_TO_PLAYBOOK_MAP`. Content is read from files at runtime — not inlined into prompts (the full playbook set is ~170 KB and would dominate the prompt).
3. **`<paper-dir>/PAPER_PREFERENCES.md`** (if present) — per-paper standing orders. Both sides respect bullets in `## Hard don'ts`, `## Notation`, `## Style / tone`, `## Section-specific`. Missing file → treat as empty; do not error. Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md).

If `skills/embodied-ai-paper-writer/SKILL.md` cannot be resolved (e.g., the submodule is not initialized), abort with a clear error pointing to `git submodule update --init skills/embodied-ai-paper-writer`. Do NOT silently proceed without the craft manual — the whole skill is built around it.

## Workflow

### Step 0: Preserve Original & Resolve Craft Manual

```bash
PAPER_DIR="$1"  # parsed from $ARGUMENTS
cp "$PAPER_DIR/main.pdf" "$PAPER_DIR/main_polish_before.pdf"
mkdir -p "$PAPER_DIR/.polish"
```

**Resolve `embodied-ai-paper-writer/SKILL.md` via the canonical chain** (see [`../shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2). Do NOT `find` the whole filesystem — it is slow and ambiguous.

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
EAPW=".aris/skills/embodied-ai-paper-writer/SKILL.md"
[ -f "$EAPW" ] || EAPW="skills/embodied-ai-paper-writer/SKILL.md"
[ -f "$EAPW" ] || { [ -n "${ARIS_REPO:-}" ] && EAPW="$ARIS_REPO/skills/embodied-ai-paper-writer/SKILL.md"; }
[ -f "$EAPW" ] || {
  echo "ERROR: embodied-ai-paper-writer/SKILL.md not resolved." >&2
  echo "       Tried: .aris/skills/, ./skills/, \$ARIS_REPO/skills/." >&2
  echo "       Fix: rerun bash tools/install_aris.sh, export ARIS_REPO," >&2
  echo "       or run: git submodule update --init skills/embodied-ai-paper-writer" >&2
  exit 1
}
EAPW_DIR=$(dirname "$EAPW")           # e.g. /home/.../skills/embodied-ai-paper-writer
EAPW_REFS="$EAPW_DIR/references"      # playbook directory — pass to both Claude and Codex
echo "Craft manual resolved: $EAPW"
```

Both Claude and Codex are told to read `$EAPW` (the top-level SKILL.md) plus a phase-specific subset of `$EAPW_REFS/*.md` playbooks. Pass these as **absolute paths** into the Codex prompt — never assume Codex's CWD matches Claude's.

### Step 0.1: Compute SECTION_LIST from `main.tex`

```bash
# Extract \input{...} order from main.tex, ignoring commented lines.
# Output is one section path (without .tex) per line, in document order.
SECTION_LIST=$(grep -E '^[^%]*\\input\{' "$PAPER_DIR/main.tex" \
  | sed -E 's/.*\\input\{([^}]+)\}.*/\1/' \
  | sed -E 's/\.tex$//')

if [ -z "$SECTION_LIST" ]; then
  # Fallback: main.tex inlines or uses \include
  SECTION_LIST=$(find "$PAPER_DIR/sections" -name '*.tex' 2>/dev/null \
    | sed -E "s|^$PAPER_DIR/||; s/\.tex$//" \
    | sort)
fi
echo "SECTION_LIST:"; echo "$SECTION_LIST"
```

Match each entry against `SECTION_TO_PLAYBOOK_MAP` by basename-prefix (case-insensitive). Unmatched entries are logged and skipped in Phase 2.

Also check for `\title{...}` in `main.tex` — if present, the title is in scope for Phase 1 / Phase 3 (append `titles.md` to the global playbook list).

### Step 0.2: Write Initial State

```json
{
  "phase": "phase1_collecting",
  "paper_dir": "<paper-dir>",
  "section_list": ["sections/0_abstract", "sections/1_introduction", ...],
  "current_section_index": null,
  "current_priority_batch": null,
  "status": "in_progress",
  "timestamp": "<ISO-8601>"
}
```

---

### Sub-procedure A: Parallel Coach Pass

**Used by Phase 1, every Phase 2 section iteration, and Phase 3.** Parameters:

- `<INPUT_SCOPE>` — what the two sides read (e.g., "the whole paper as one artifact" or "the single file `sections/0_abstract.tex`").
- `<PLAYBOOK_PATHS>` — `$EAPW` + a phase-/section-specific list of `$EAPW_REFS/*.md` files.
- `<FOCUS>` — phase-specific focus string (e.g., "GLOBAL issues only" for Phase 1; "this section's craft only" for Phase 2).
- `<OUT_DIR>` — `<paper-dir>/.polish/<namespace>/` where `<namespace>` is `phase1`, `phase2_<section-basename>`, or `phase3`.

No suggestion-count parameter — both sides are instructed to find every craft issue within `<FOCUS>`.

**Mechanism: spawn an Agent with `run_in_background: true` that wraps the `mcp__codex__codex` call.** The Agent returns Codex's JSON output to a file. Claude continues to its own analysis immediately. When the Agent completes, Claude is notified automatically (do not poll, do not sleep) and proceeds to overlap detection.

In the same message, issue both:

1. `Agent(subagent_type=general-purpose, run_in_background=true, ...)` — wraps the Codex call (full prompt below).
2. `Read` tool calls for the inputs Claude needs (`<INPUT_SCOPE>` files, `<PLAYBOOK_PATHS>`, `<paper-dir>/PAPER_PREFERENCES.md`).

#### A.1 — Claude emits every craft issue it finds (NDJSON, foreground, while Codex runs)

After the Reads return in the same batch, Claude analyzes (pure reasoning, no extra tool calls):

1. The relevant principles from `<PLAYBOOK_PATHS>` (already loaded).
2. `<paper-dir>/PAPER_PREFERENCES.md` (if present).
3. The text in scope per `<INPUT_SCOPE>`.
4. The compiled PDF at `<paper-dir>/main.pdf` (only when figure/table visual cues matter for `<FOCUS>`).

Claude writes **NDJSON** (one JSON object per line, no surrounding array) to `<OUT_DIR>/claude_suggestions.ndjson` — every distinct craft issue within `<FOCUS>` gets its own line. There is **no upper limit**; emit as many as the playbook scope yields. If the paper is unusually problem-dense, the output may have 30+ lines; if it is clean, it may have 3.

One line per suggestion, each line a complete JSON object:

```jsonl
{"id":"C1","priority":"HIGH","section":"abstract","file":"<paper-dir>/sections/0_abstract.tex","line_range":"4-8","issue":"Opening sentence buries the contribution under three filler phrases.","evidence_quote":"In recent years, robotics has seen tremendous progress, and we propose a novel method that...","proposed_fix":"Replace with a punchline-first opener naming the capability achieved, per abstract-intro-playbook.md §Move-1.","craft_principle":"abstract-intro-playbook.md §Move-1: lead with the capability, not the field context."}
{"id":"C2","priority":"MEDIUM",...}
```

Rules for Claude's suggestions:
- **Craft only** — no content claims, no new experiments, no theory changes, no new citations, no section reordering as an auto-apply.
- **Each suggestion must cite a specific principle** from a playbook in `<PLAYBOOK_PATHS>` (file + section). If a suggestion cannot be grounded in a loaded playbook, drop it.
- **Evidence quote must be verbatim** from the paper (Claude must be able to grep-find it).
- **Respect `## Hard don'ts`** — never propose an edit that would violate a hard-don't; pick a different issue instead.
- **Honor `<FOCUS>`** — Phase 1 / 3 suggestions must be global (cross-section); Phase 2 suggestions must be local to the section in `<INPUT_SCOPE>`.
- **No artificial cap** — emit every issue that meets the rules above. If the same craft principle applies to 5 sentences, that's 5 suggestions (one per sentence), not 1. Reviewers will collapse them at apply time if redundant.
- **Priority labels are mandatory and meaningful** — HIGH = changes the paper's reception (e.g., contribution buried, claim/evidence misalignment); MEDIUM = noticeable craft weakness a careful reviewer flags; LOW = polish-grade tightening. The user sees one priority batch at a time, so accurate labels matter.
- **Unique `id`** — `C1`, `C2`, … in emission order; never collide with Codex's `X*` ids.

#### A.2 — Codex emits every craft issue it finds (NDJSON, background Agent, fresh thread)

The Agent invokes `mcp__codex__codex` (never `codex-reply` — fresh thread always):

```
mcp__codex__codex:
  model: gpt-5.5
  config: {"model_reasoning_effort": "xhigh"}
  cwd: <absolute path to repo root where $EAPW was resolved>
  prompt: |
    You are a professional embodied-AI paper writing coach, distilled from
    63 top robotics papers (CoRL, RSS, ICRA, IROS, Science Robotics, 2022-2026).
    You are NOT a reviewer scoring this paper. You are a co-author helping it
    land at a top robotics venue.

    ## Read these files first (in this order, before drafting suggestions)

    1. <ABSOLUTE_EAPW_PATH> — your craft manual (skills/embodied-ai-paper-writer/SKILL.md).
       Use ONLY the global / cross-section parts (Universal Rules, Scenario E,
       Step 0 terminology) for this call. Do NOT route via the per-section
       problem table; the relevant playbook(s) are listed below.

    2. The following playbook files — these are the ONLY playbooks in scope
       for this call. Do NOT load others.
         <PLAYBOOK_FILE_LIST>

    3. <PAPER_DIR>/PAPER_PREFERENCES.md — author's standing orders.
       Respect every bullet in ## Hard don'ts, ## Notation, ## Style / tone,
       and ## Section-specific. If a craft fix you would otherwise suggest
       violates a hard-don't, suggest something else instead.
       (If this file does not exist, ignore this step.)

    4. The text in scope: <INPUT_SCOPE_DESCRIPTION>
       (paths: <INPUT_SCOPE_PATHS>)

    5. <PAPER_DIR>/main.pdf — the compiled paper, for figure/table visual cues
       (only consult if your <FOCUS> involves figures/tables).

    ## Focus

    <FOCUS_PARAGRAPH>

    ## Task

    Identify **every** writing-craft improvement that fits the focus above.
    There is NO upper limit and NO target count — be exhaustive. A problem-
    dense paper should yield many suggestions; a clean section may yield few.
    The user is protected from decision fatigue by a downstream priority-
    batched checkpoint, not by you self-censoring.

    These are *craft* fixes — vocabulary, sentence patterns, paragraph
    rhythm, section construction, figure/table caption phrasing, rhetorical
    transitions, opener/closer patterns.

    Explicitly NOT in scope:
    - content claims (do not suggest adding/removing experiments or numbers)
    - theory changes (do not suggest modifying theorems or proofs)
    - new citations (do not suggest \cite{...} additions)
    - section reordering as an auto-apply (flag for human attention only)
    - figures themselves (only captions)

    ## Output format — NDJSON, one suggestion per line

    Output STRICTLY as newline-delimited JSON: **one complete JSON object
    per line**, no surrounding array, no commentary, no markdown fences,
    no preamble, no postscript.

    Finish writing one line before starting the next. This way, if your
    response is ever truncated mid-stream, every complete line before the
    cut is still parseable; only the trailing partial line would be lost.

    Schema for each line:

    {"id":"X1","priority":"HIGH|MEDIUM|LOW","section":"<name>","file":"<PAPER_DIR>/sections/<file>.tex","line_range":"<L1-L2>","issue":"<one-sentence diagnosis>","evidence_quote":"<verbatim snippet from paper, ≤200 chars>","proposed_fix":"<concrete rewrite or rule, 1-3 sentences>","craft_principle":"<playbook file and section, e.g. abstract-intro-playbook.md §Move-1>"}

    Constraints per line:
    - id must be unique: X1, X2, X3, … in emission order.
    - Each suggestion must cite a specific craft principle from a playbook
      file loaded above. If you cannot cite one, drop the suggestion.
    - Each evidence_quote must be verbatim text from the in-scope paper text
      (grep-findable).
    - priority is mandatory: HIGH = changes the paper's reception (buried
      contribution, claim/evidence misalignment); MEDIUM = noticeable craft
      weakness a careful reviewer flags; LOW = polish-grade tightening.
    - Emit suggestions in any order; the downstream tool re-sorts by priority.
```

Substitute these placeholders before sending: `<ABSOLUTE_EAPW_PATH>`, `<PLAYBOOK_FILE_LIST>` (a bullet list of absolute paths under `$EAPW_REFS/`), `<INPUT_SCOPE_DESCRIPTION>`, `<INPUT_SCOPE_PATHS>` (absolute paths), `<FOCUS_PARAGRAPH>`, `<PAPER_DIR>`. Save the returned threadId only for state-file bookkeeping; do not use it for any continuation.

#### A.3 — Join: wait for the Agent, parse Codex's NDJSON

When the background Agent completes, you will be notified (do not poll, do not sleep). Read the Agent's output file. Parse line-by-line:

- Strip any leading/trailing markdown fences or commentary the model may have wrapped around the NDJSON (defensive, even though the prompt forbids them).
- For each non-empty line, attempt `json.loads`; on success, validate required fields (`id`, `priority`, `section`, `file`, `line_range`, `issue`, `evidence_quote`, `proposed_fix`, `craft_principle`).
- Collect parsed lines into `<OUT_DIR>/codex_suggestions.ndjson` (one validated object per line). Discard lines that fail to parse — they are almost always either a partial truncation (the last line) or model-emitted commentary (never a structurally complete-but-wrong suggestion).
- Count parsed vs discarded lines and log: `Codex emitted <P> suggestions, <D> lines discarded (likely truncation)`.

Truncation handling: if `D ≥ 1` AND the last raw line is partial JSON (no closing `}`), surface a notice — "Codex response appears truncated; got `<P>` complete suggestions, last line cut. Proceed with what we have? (y/n)". If the user says no, re-invoke Sub-procedure A; if yes, proceed with the parsed `<P>`. If `P == 0` after parsing, do not silently proceed — surface the raw output and ask the user.

By this point Claude's `claude_suggestions.ndjson` should already be on disk. Sub-procedure A returns the two file paths to its caller.

---

### Sub-procedure B: Overlap → Auto-Apply → Checkpoint → Apply

**Used by Phase 1, every Phase 2 section iteration, and Phase 3.** Parameters:

- `<NAMESPACE>` — `phase1`, `phase2_<section>`, or `phase3`. Used as the OUTPUT_MD heading and as a key for state and `.polish/` subdirs.
- `<CLAUDE_JSON>`, `<CODEX_JSON>` — the two files Sub-procedure A produced.
- `<SCOPE_LABEL>` — human-readable label printed in the checkpoint (e.g., "Phase 1 — Global", "Phase 2 — abstract").

#### B.1 — Overlap Detection

Claude reads `claude_suggestions.ndjson` + `codex_suggestions.ndjson` (each may have any number of entries). A pair `(C_i, X_j)` is an **OVERLAP** iff BOTH:

1. **Section match** — they target the same section, OR their `file:line_range` windows share ≥50% intersection by line count.
2. **Fix-intent match** — they invoke the same craft principle (same playbook file + same section), OR they target the same sentence/paragraph for rewrite with semantically aligned proposed fixes.

Bucket every suggestion into one of:

- `OVERLAP_PAIRS` — list of `(C_i, X_j)` pairs.
- `CLAUDE_ONLY` — `C_i` with no matching `X_j`.
- `CODEX_ONLY` — `X_j` with no matching `C_i`.

A single suggestion can only belong to one bucket. If `C_2` matches both `X_1` and `X_3`, pick the closer match and put the other in `_ONLY`. For each `OVERLAP_PAIR`, write a 1-sentence justification (goes into OUTPUT_MD for audit).

The overlap bucket can be empty (no agreement); the `_ONLY` buckets can be large (problem-dense paper). Both are normal — proceed regardless.

#### B.2 — Auto-Apply Overlap (Hard-Don't Gated)

For each `(C_i, X_j)` in `OVERLAP_PAIRS`:

1. **Synthesize the fix.** Prefer the cleaner of the two `proposed_fix` formulations — usually Codex's (it is the dedicated writer), but if Claude's is more specific or actionable, use Claude's. If they materially conflict, log both and skip (treat as if non-overlapping and surface in the Pending list).
2. **Re-read `<paper-dir>/PAPER_PREFERENCES.md ## Hard don'ts`.** If a bullet blocks the fix (e.g., "Do not rewrite Theorem 1", "Do not paraphrase the abstract's first sentence"), do NOT apply. Log status as `blocked_by_hard_dont: <quoted bullet>`.
3. **Apply via `Edit`** to the target `.tex` file. The edit must be exact — find the `evidence_quote` in the file and replace with the new wording. If the quote no longer matches (a prior overlap edit shifted surrounding context), surface the conflict to the user rather than guessing — do NOT do fuzzy matching.
4. **Log status** as one of: `applied`, `blocked_by_hard_dont`, `conflict_skipped`.

#### B.3 — Append to `WRITING_POLISH_SUGGESTIONS.md`

Append (do not overwrite — phases accumulate) a section under `## <SCOPE_LABEL>` heading. The Pending entries are split into priority batches up front; each batch becomes its own subsection. Use this skeleton:

```markdown
## <SCOPE_LABEL>

Generated: <ISO-8601 date> | Codex thread: <threadId>
Claude emitted: <count> | Codex emitted: <count> | Overlap pairs: <count>

### Auto-Applied — Overlap (Claude × Codex)

| # | Section | File:Lines | Issue | Fix | Principle | Status |
|---|---------|------------|-------|-----|-----------|--------|
| A1 | … | … | … | … | … | applied |

### Pending User Decision — Non-Overlap

Total pending: <N_HIGH> HIGH, <N_MED> MEDIUM, <N_LOW> LOW. Presented in priority batches.

#### Batch 1 — HIGH (<N_HIGH> items)

##### H1 [HIGH, Codex-only] <section> — <issue summary>
- File: `<file>`, lines L1-L2
- Quote: "…"
- Proposed fix: …
- Craft principle: …
- Why pending: …

##### H2 [HIGH, Claude-only] …

#### Batch 2 — MEDIUM (<N_MED> items)

##### M1 …
##### M2 …

#### Batch 3 — LOW (<N_LOW> items)

##### L1 …
##### L2 …

### Reply Guide (per batch)

Each batch is a separate checkpoint. For each batch you can:

- `go` / `apply all` — apply every item in this batch.
- `1 3 5` — apply only items 1, 3, 5 in this batch (1-indexed within the batch, e.g., `1` means `H1` in the HIGH batch).
- `skip 2,4` — apply all items in this batch except 2 and 4.
- `stop` / `none` — apply nothing more for any remaining batches in this phase; finalize the phase as-is.
- free-text — treated as additional instructions; Claude blends with the chosen items in this batch.

Within an item index list, items not mentioned are dropped (not deferred). Across batches: a batch you `go` through still hands you the next batch; only `stop` exits the phase early.

Persistence: if a reply contains "always", "never", "in this paper", "every time", or names a recurring style/notation rule, the loop offers to pin it to `PAPER_PREFERENCES.md` before applying (approve / edit / skip — fixes proceed either way). Once pinned, it gates every remaining batch in the phase, every later section in Phase 2, and Phase 3.
```

Compute `N_HIGH`, `N_MED`, `N_LOW` from the combined `CLAUDE_ONLY ∪ CODEX_ONLY` set after grouping by `priority`. Within a priority, sort: Claude entries before Codex entries (deterministic), and within each source by emission `id` (`C1`, `C2`, …; `X1`, `X2`, …). Renumber as `H1..H<N_HIGH>`, `M1..M<N_MED>`, `L1..L<N_LOW>` so the user's reply maps cleanly per batch.

#### B.4 — Priority-Batched HUMAN_CHECKPOINT Loop

Iterate over the non-empty priority batches in order `[HIGH, MEDIUM, LOW]`. For each batch:

1. Print:

   ```
   📋 <SCOPE_LABEL> — Batch <K>/<TOTAL_BATCHES>: <PRIORITY> (<N> items)
       Overlap already auto-applied: <overlap_applied_count>
       HIGH pending overall: <N_HIGH>  MEDIUM: <N_MED>  LOW: <N_LOW>
       See WRITING_POLISH_SUGGESTIONS.md → "## <SCOPE_LABEL>" → "Batch <K>"
   Reply: "go" / "1 3 5" / "skip 2,4" / "stop" / free-text
   ```

2. **Wait for the user's inline reply.** Parse with the same logic as `/auto-paper-improvement-loop` Step 2b / `/auto-review-loop` Phase B:

   - `go` / `continue` / `ok` / `proceed` / `apply all` → apply all items in **this batch** → continue to next batch.
   - Space/comma-separated digit list → apply only those indices **in this batch** → continue to next batch. Items not listed are dropped (User-Skipped) — they do not roll over to the next batch.
   - `skip <list>` → apply all items in this batch except those indices → continue to next batch.
   - `stop` / `none` / `done` → apply nothing more in this batch; **abort the phase**. Remaining batches (and remaining Phase 2 sections, if applicable) are logged as User-Skipped. Return `STOPPED` to the caller.
   - Anything else → free-text. Try to extract an index list with a brief clarifying ask if genuinely unparseable; otherwise treat as "additional instruction merged with all items in this batch" and apply.

3. **Persistence prompt** — if the reply contains `always`, `never`, `in this paper`, `every time`, or corrects a recurring style/notation pattern, propose a diff to `<paper-dir>/PAPER_PREFERENCES.md` before applying this batch's fixes. Show the diff inline. Ask `y / edit / skip` — fixes proceed regardless. The pinned bullet immediately gates this batch's apply and every subsequent batch in the phase. Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md) Write Protocol.

4. **Apply this batch's selected items** (see B.5 below) before moving to the next batch.

After the last batch (LOW) returns, B.4 returns `OK`.

**Edge cases:**

- A priority bucket with zero items is skipped silently (no checkpoint printed).
- If the OVERLAP_PAIRS auto-apply produced everything and there is no Pending in any priority, B.4 prints a one-line "no pending items — proceeding" and returns `OK` immediately.

#### B.5 — Apply Selected Items (per batch)

Called by B.4 once per batch, after the user's reply is parsed. For each selected item:

1. **Re-read `<paper-dir>/PAPER_PREFERENCES.md ## Hard don'ts`** against the fix (same gate as B.2). The user may have just added a new hard-don't via the persistence prompt — re-read every time.
2. **Apply via `Edit`** to the target `.tex` file. Same exact-match rule as B.2 — no fuzzy matching.
3. **Log status** as `user_approved_applied` / `blocked_by_hard_dont` / `conflict_skipped`.

For free-text instructions, treat them as additional craft fixes to apply within the same batch, constrained to the craft-only scope (no content/theory/citations).

**Do not recompile here.** Recompile is owned by the phase driver.

---

### Phase 1 — Global Pass

**Step 1.0 — Setup.** State `phase: phase1_collecting`.

**Step 1.1 — Invoke Sub-procedure A** with:

- `<INPUT_SCOPE>` = "the whole paper as one artifact — every `\input`-ed `.tex` file"
- `<INPUT_SCOPE_PATHS>` = absolute paths to every entry in `SECTION_LIST`
- `<PLAYBOOK_PATHS>` = `$EAPW`, `$EAPW_REFS/flow-transitions.md`, `$EAPW_REFS/language-phrasebank.md`, `$EAPW_REFS/figures-tables-playbook.md`, plus `$EAPW_REFS/titles.md` if `\title{...}` is present in `main.tex`
- `<OUT_DIR>` = `<paper-dir>/.polish/phase1/`
- `<FOCUS>` paragraph (substitute verbatim into the Codex prompt):

  > Identify **every GLOBAL** issue — concerns that span sections or apply to the whole paper. Examples: contribution-noun-phrase consistency across abstract↔intro↔conclusion (Universal Rule 2), tense usage across Abstract/Method/Experiments/Conclusion (Rule 3), voice / person consistency, 6-move rhetorical arc (Scenario E), abstract self-containment (Rule 14), Related-Work header consistency (Rule 15), paired condition-label axis (Rule 18), load-bearing modifier sweep (Rule 20), figure/table caption conventions that cross sections, claim↔evidence alignment at paper level. **Do not propose** section reordering as an auto-apply — flag it for human attention only. **Do not propose** per-section line-level rewrites that have no cross-section justification; those are Phase 2's job. There is no upper limit; emit every distinct issue you find within these bounds.

**Step 1.2 — Invoke Sub-procedure B** with `<NAMESPACE> = phase1`, `<SCOPE_LABEL> = "Phase 1 — Global Pass"`. If Sub-procedure B returns `STOPPED`, skip Phase 2 entirely and jump to Finalize.

**Step 1.3** — State `phase: phase1_done`. **No recompile here** — deferred to Phase 2's end or Finalize.

### Phase 2 — Per-Section Loop

**Step 2.0 — Setup.** Append `## Phase 2 — Per-Section Loop` heading to OUTPUT_MD. State `phase: phase2_starting`.

**Step 2.1 — For each `<section>` in `SECTION_LIST`** (in `\input` order):

1. Update state `current_section_index := i`, `phase: phase2_section:<basename>_collecting`.
2. Resolve `PLAYBOOKS := SECTION_TO_PLAYBOOK_MAP[<section>]`. If empty → append a `### Phase 2 — <section> (skipped: no playbook mapping)` line to OUTPUT_MD and `continue`.
3. **Invoke Sub-procedure A** with:
   - `<INPUT_SCOPE>` = "the single section file `<section>.tex`"
   - `<INPUT_SCOPE_PATHS>` = absolute path to `<section>.tex` only
   - `<PLAYBOOK_PATHS>` = `$EAPW` + `$EAPW_REFS/<playbook>` for each `<playbook>` in `PLAYBOOKS`
   - `<OUT_DIR>` = `<paper-dir>/.polish/phase2_<basename>/`
   - `<FOCUS>` paragraph:

     > Focus **only on this section** (`<section>.tex`). Find **every** craft issue local to this section: section opener, paragraph rhythm, sentence patterns, opener/closer of moves, figure/table captions that live in this section, vocabulary specific to this section. **Do not suggest cross-section consistency fixes** (those are Phase 1's job). **Do not suggest** moving content to another section. There is no upper limit; a verbose section may yield many suggestions, a tight one may yield few.

4. **Invoke Sub-procedure B** with `<NAMESPACE> = phase2_<basename>`, `<SCOPE_LABEL> = "Phase 2 — <section>"`. If Sub-procedure B returns `STOPPED`, **break the loop** and proceed to Step 2.2 — the user explicitly chose to stop the whole phase. Remaining sections are recorded as "not visited" in OUTPUT_MD, NOT rolled into Phase 3.

**Step 2.2 — Recompile once** after the loop completes (or after `STOPPED`):

```bash
cd "$PAPER_DIR" && latexmk -C && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tee compile.log
```

Verify (both should be 0):

```bash
grep -c "LaTeX Warning.*undefined" compile.log
grep -c "Citation.*undefined" compile.log
```

If compile fails: surface the error to the user. Do NOT silently roll back — partial edits are visible in `git diff`. Offer:
- Fix the LaTeX error and re-run from this point.
- Revert all polish-loop edits via `git checkout -- "<paper-dir>/sections/"`.

State `phase: phase2_done`.

### Phase 3 — Optional Second Global Pass

**Step 3.0 — Prompt the user:**

```
✅ Phase 2 complete. <X> per-section fixes applied across <Y> sections.

Want to re-run the global pass now that sections are polished? (Phase 3)
This re-reads only the cross-section playbooks and flags any new arc /
consistency issues introduced by per-section edits.

Reply: "yes" / "no"   (default: no — anything other than yes is treated as no)
```

**Step 3.1 — If `yes`:** State `phase: phase3_collecting`. Repeat Phase 1 logic verbatim:

- `<NAMESPACE> = phase3`, `<SCOPE_LABEL> = "Phase 3 — Global Pass (Re-Run)"`
- Same `<PLAYBOOK_PATHS>`, same `<FOCUS>` paragraph (no cap; uncovers any new global issues introduced by Phase 2 edits).
- After Sub-procedure B returns, **recompile** (same block as Step 2.2). Overwrites `main.pdf`.
- State `phase: phase3_done`.

**Step 3.2 — If `no`:** skip to Finalize.

### Finalize: Step 9 — Polish `WRITING_POLISH_SUGGESTIONS.md`

Make sure every phase's section in OUTPUT_MD has:
- Auto-Applied table with statuses
- User-Approved Applied entries (moved from Pending)
- User-Skipped entries (moved from Pending)
- User-Custom-Instruction entries (free-text replies, with resulting edits)

Append a `## Compile Result` section: page count from `pdfinfo`, undefined-ref / citation counts from the last `compile.log`, any remaining overfull warnings.

Copy the final PDF:

```bash
cp "$PAPER_DIR/main.pdf" "$PAPER_DIR/main_polish_final.pdf"
```

State `phase: done`, `status: completed`.

### Finalize: Step 10 — Summary

Report to user:

```
✅ Writing polish complete.

  Phase 1 (global):
    Auto-applied (overlap):       N1
    User-approved (non-overlap):  M1
    Skipped:                      K1
    Blocked by hard-don't:        L1

  Phase 2 (per-section, <Y> sections):
    Auto-applied (overlap):       N2
    User-approved (non-overlap):  M2
    Skipped:                      K2
    Blocked by hard-don't:        L2

  Phase 3 (global re-run):        ran / skipped
    [if ran: same 4-line breakdown]

  PDFs:
    main_polish_before.pdf      ← original
    main_polish_final.pdf       ← final (= main.pdf)

  Log: WRITING_POLISH_SUGGESTIONS.md
```

## State Persistence (Compact Recovery)

`<paper-dir>/WRITING_POLISH_STATE.json` is written after each phase / section / sub-step:

```json
{
  "phase":
    "phase1_collecting" | "phase1_overlap" | "phase1_auto_applying" |
    "phase1_batch:HIGH_awaiting_user" | "phase1_batch:HIGH_applying" |
    "phase1_batch:MEDIUM_awaiting_user" | "phase1_batch:MEDIUM_applying" |
    "phase1_batch:LOW_awaiting_user" | "phase1_batch:LOW_applying" |
    "phase1_done" |
    "phase2_starting" |
    "phase2_section:<basename>_collecting" | "phase2_section:<basename>_overlap" |
    "phase2_section:<basename>_auto_applying" |
    "phase2_section:<basename>_batch:<P>_awaiting_user" |
    "phase2_section:<basename>_batch:<P>_applying" |
    "phase2_recompiling" | "phase2_done" |
    "phase3_prompt" | "phase3_collecting" | "phase3_overlap" |
    "phase3_auto_applying" |
    "phase3_batch:<P>_awaiting_user" | "phase3_batch:<P>_applying" |
    "phase3_recompiling" | "phase3_done" |
    "finalizing" | "done",
  "paper_dir": "<paper-dir>",
  "section_list": ["sections/0_abstract", "sections/1_introduction", "..."],
  "current_section_index": 0,
  "current_priority_batch": "HIGH" | "MEDIUM" | "LOW" | null,
  "phase1_counts": {
    "claude_emitted": E_C, "codex_emitted": E_X, "overlap": N,
    "pending_high": NH, "pending_medium": NM, "pending_low": NL,
    "applied": K, "blocked": L, "skipped": S
  },
  "phase2_per_section": {
    "0_abstract": {"claude_emitted": …, "codex_emitted": …, "overlap": …,
                    "pending_high": …, "pending_medium": …, "pending_low": …,
                    "applied": …, "blocked": …, "skipped": …},
    "1_introduction": {"…": "…"}
  },
  "phase3_run": true,
  "phase3_counts": { /* same shape as phase1_counts */ },
  "codex_threadIds": {
    "phase1": "<id>",
    "phase2_0_abstract": "<id>",
    "phase3": "<id>"
  },
  "status": "in_progress" | "completed" | "failed",
  "timestamp": "<ISO-8601>"
}
```

**On startup**: if `WRITING_POLISH_STATE.json` exists with `status: in_progress` AND timestamp within 24 hours, read it + `WRITING_POLISH_SUGGESTIONS.md` to recover context, then resume from the saved phase / section. Otherwise (file absent, `status: completed`, or older than 24 hours), start fresh.

**Never reuse a saved `codex_threadId`** — recovery starts a fresh Codex thread for any re-invoked Sub-procedure A. The threadId is recorded only so the user can audit which Codex session produced the saved suggestions.

## Key Rules

- **Fresh Codex thread, always** — use `mcp__codex__codex`, never `mcp__codex__codex-reply`. No "since last phase" framing in the prompt.
- **embodied-ai-paper-writer is mandatory, not optional** — if the submodule is not present, abort with a clear error. The skill is built around this craft manual.
- **Both sides see PAPER_PREFERENCES.md** — explicit divergence from `/auto-paper-improvement-loop`. Codex is a coach here, not a reviewer.
- **Phase-scoped playbooks** — Phase 1 / 3 load ONLY `GLOBAL_PLAYBOOKS`; Phase 2 loads ONLY the per-section playbook keyed by basename. Mixing breaks the global-vs-local separation that makes this skill distinct.
- **Craft only** — never apply edits that add citations, change numbers, modify theorems, or reorder sections. Section reordering, even when both sides agree, is flagged for human attention only — never auto-applied.
- **Exact-match edits only** — `evidence_quote` must be grep-findable; apply via `Edit` with the exact string. No fuzzy matching, no LLM-judged "close enough" replacements.
- **Hard-don't gate runs at every apply point** — B.2 (auto-overlap), B.5 (user-approved), and after a mid-loop `PAPER_PREFERENCES.md` append. Re-read the file each time; the user may have just added a bullet.
- **Recompile is deferred and explicit** — never per-section, never silently. Only at the end of Phase 2 and the end of Phase 3 (if it ran).
- **No silent rollback** — if a recompile fails, surface the error. User chooses to fix or revert.
- **Preserve PDF snapshots** — `main_polish_before.pdf` (taken at Step 0) and `main_polish_final.pdf` (taken at Finalize) for visual diff.
- **Parallel by default** — every Sub-procedure A call kicks off the Codex Agent before Claude's foreground analysis. Never sequence them.
- **No suggestion cap** — both sides find every craft issue within scope. A problem-dense paper is the case that most needs exhaustive coverage; capping forces self-censorship that biases against such papers. Decision-fatigue management lives in the priority-batched checkpoint, not in a cap.
- **NDJSON output, never a JSON array** — one suggestion per line, every line a complete JSON object. This makes truncated responses partially recoverable (every complete line before the cut is usable; only the trailing partial line is lost). A JSON array becomes unparseable on any truncation.
- **Priority-batched checkpoint** — Pending non-overlap is split into HIGH / MEDIUM / LOW batches. Each batch is its own checkpoint; `stop` exits the rest of the phase. Empty batches are skipped silently. Index lists (e.g., `1 3 5`) are 1-indexed **within the current batch** — `1` means `H1` in the HIGH batch, `M1` in the MEDIUM batch.
- **Skipped items do not roll over** — items the user passes over via `skip <list>` or non-mention are recorded as `User-Skipped` and never re-presented in Phase 3 or any later batch. A user `stop` in Phase 1 still allows the user to choose Phase 3 at its prompt, but no Phase 1 items roll into Phase 3's input.

## Output

```
<paper-dir>/
├── main.pdf                              # = main_polish_final.pdf
├── main_polish_before.pdf                # snapshot at Step 0
├── main_polish_final.pdf                 # after all applied fixes
├── WRITING_POLISH_SUGGESTIONS.md         # full log; sections per phase
├── WRITING_POLISH_STATE.json             # compact-recovery state
└── .polish/
    ├── phase1/
    │   ├── claude_suggestions.ndjson    # one suggestion per line, no cap
    │   └── codex_suggestions.ndjson     # one suggestion per line, no cap
    ├── phase2_0_abstract/
    │   ├── claude_suggestions.ndjson
    │   └── codex_suggestions.ndjson
    ├── phase2_1_introduction/
    │   └── …
    ├── …  # one dir per Phase-2 section iterated
    └── phase3/                           # only if Phase 3 ran
        ├── claude_suggestions.ndjson
        └── codex_suggestions.ndjson
```

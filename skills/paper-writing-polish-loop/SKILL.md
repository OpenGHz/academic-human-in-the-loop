---
name: paper-writing-polish-loop
description: "Writing-only polish loop. Claude and Codex (as 'professional embodied-AI writer', gpt-5.5 xhigh, fresh thread — never codex-reply) independently read the paper + skills/embodied-ai-paper-writer/SKILL.md + PAPER_PREFERENCES.md, each produces top-5 writing-craft suggestions. Overlapping pairs auto-apply (high-confidence: two peers agree). Non-overlapping suggestions land in WRITING_POLISH_SUGGESTIONS.md ranked by priority; the loop asks inline which to apply via standard HUMAN_CHECKPOINT syntax (go / 1 3 5 / skip 2,4 / stop / free-text). User reply triggers automatic fix-application + recompile — no re-invocation needed. For robotics / embodied-AI papers. Use when user says \"优化写作\", \"polish writing\", \"writing polish loop\", \"写作打磨\", \"craft pass\", or wants a writing-craft-focused pass distinct from content/theory review."
argument-hint: "[paper-directory] [— suggestions-per-side: <N>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex
---

# Paper Writing Polish Loop: Claude × Codex Dual Coach

Polish the writing craft of the paper at: **$ARGUMENTS**

## Context

This skill is a **focused, single-round writing-craft loop**. It is **NOT** a replacement for `/auto-paper-improvement-loop` — that skill handles content claims, theory consistency, visual presentation, page-shrink, kill-argument, citation floor, restatement regression, and more. This skill handles **only writing craft**: vocabulary, sentence patterns, paragraph rhythm, section construction, figure/table caption phrasing, rhetorical transitions, opener/closer patterns.

Use this loop when the paper is content-stable but the prose needs tightening — e.g., near final submission, after the experiments are locked, or when reviewer feedback singled out "writing quality" without flagging content issues.

**This skill is designed for robotics / embodied-AI papers.** Both Claude and Codex consult `skills/embodied-ai-paper-writer/SKILL.md` as their shared craft manual. For non-robotics papers, prefer `/auto-paper-improvement-loop` which uses `shared-references/writing-principles.md` instead.

## Why this differs from `/auto-paper-improvement-loop`

| Aspect | auto-paper-improvement-loop | paper-writing-polish-loop |
|---|---|---|
| Codex role | senior ML reviewer (scores 1-10, gives verdict) | professional writing coach (gives top-5 craft fixes, no scoring) |
| Scope | content + theory + visual + structure + writing | writing craft only |
| Rounds | 2 (review → fix → recompile × 2) | 1 (dual-suggest → overlap auto-apply → ask user → final apply) |
| Sees PAPER_PREFERENCES.md? | only Claude (Codex is reviewer → context-naive) | **both** (Codex is coach, not reviewer) |
| Sees embodied-ai-paper-writer? | optionally as background reference | **mandatory for both sides** |
| Inline user feedback? | optional `HUMAN_CHECKPOINT` per round | always — after auto-applied overlap |
| EDIT_WHITELIST / MIN_REFERENCES | enforced | out of scope (craft-only edits) |
| codex-reply allowed? | only when `REVIEWER_BIAS_GUARD = false` | **never** (fresh thread only) |

If you want both content AND writing polish, run `/auto-paper-improvement-loop` first, then this skill at the end for a final craft pass.

## Constants

- **SUGGESTIONS_PER_SIDE = 5** — Number of top suggestions each side produces. Override via `— suggestions-per-side: <N>`. Sweet spot: 5 balances overlap probability against decision-fatigue length of the user-facing md.
- **WRITER_MODEL = `gpt-5.5`** — Model used via `mcp__codex__codex` for the Codex side.
- **WRITER_REASONING = `xhigh`** — `model_reasoning_effort` for the Codex call.
- **OUTPUT_MD = `WRITING_POLISH_SUGGESTIONS.md`** — Cumulative log of all suggestions and applied fixes, written to the paper directory.
- **STATE_FILE = `WRITING_POLISH_STATE.json`** — Compact-recovery state file, written after each major step.
- **PRESERVE_PDF_SNAPSHOTS = true** — Keep `main_polish_before.pdf` and `main_polish_final.pdf` for visual diff.

## Inputs

Both Claude AND Codex receive the same input set. This is the explicit divergence from `/auto-paper-improvement-loop`'s Reviewer Independence Protocol — here Codex is a coach, not a reviewer, so author-side context is on the table.

1. **Compiled paper** — `<paper-dir>/main.pdf` + all `<paper-dir>/sections/*.tex` (or whatever `.tex` files `main.tex` `\input`s).
2. **`skills/embodied-ai-paper-writer/SKILL.md`** — **mandatory** craft manual. Both sides read this first, then follow its problem-routing table to load 1-3 relevant `references/*.md` playbook files (e.g., `abstract-intro-playbook.md`, `method-relatedwork-playbook.md`, `experiments-results-playbook.md`, `figures-tables-playbook.md`, `closing-appendix-playbook.md`, `flow-transitions.md`, `language-phrasebank.md`, `titles.md`). Content is read from files at runtime — not inlined into prompts (the full playbook set is ~170 KB and would dominate the prompt).
3. **`<paper-dir>/PAPER_PREFERENCES.md`** (if present) — per-paper standing orders. Both sides respect bullets in `## Hard don'ts`, `## Notation`, `## Style / tone`, `## Section-specific`. Missing file → treat as empty; do not error. Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md).

If `skills/embodied-ai-paper-writer/SKILL.md` cannot be resolved (e.g., the submodule is not initialized), abort with a clear error pointing to `git submodule update --init skills/embodied-ai-paper-writer`. Do NOT silently proceed without the craft manual — the whole skill is built around it.

## Workflow

### Step 0: Preserve Original

```bash
PAPER_DIR="$1"  # parsed from $ARGUMENTS
cp "$PAPER_DIR/main.pdf" "$PAPER_DIR/main_polish_before.pdf"
```

Verify the submodule is present:

```bash
if [ ! -f skills/embodied-ai-paper-writer/SKILL.md ]; then
  echo "ERROR: skills/embodied-ai-paper-writer/SKILL.md not found." >&2
  echo "       Run: git submodule update --init skills/embodied-ai-paper-writer" >&2
  exit 1
fi
```

Write initial state:

```json
{
  "phase": "collecting_claude_suggestions",
  "paper_dir": "<paper-dir>",
  "suggestions_per_side": 5,
  "status": "in_progress",
  "timestamp": "<ISO-8601>"
}
```

### Step 1: Claude Produces Top-5

Claude reads in this order:

1. `skills/embodied-ai-paper-writer/SKILL.md` (full).
2. The problem-routing table at the top of that SKILL.md → identify 1-3 relevant `references/*.md` playbook files for the paper's needs → load them.
3. `<paper-dir>/PAPER_PREFERENCES.md` (if present).
4. All `<paper-dir>/sections/*.tex` files.
5. The compiled PDF at `<paper-dir>/main.pdf` (for figure/table visual cues).

Then Claude produces exactly `SUGGESTIONS_PER_SIDE` suggestions in this JSON schema. Write to `<paper-dir>/.polish/claude_suggestions.json`:

```json
{
  "claude_suggestions": [
    {
      "id": "C1",
      "priority": "HIGH",
      "section": "abstract",
      "file": "<paper-dir>/sections/0_abstract.tex",
      "line_range": "4-8",
      "issue": "Opening sentence buries the contribution under three filler phrases.",
      "evidence_quote": "In recent years, robotics has seen tremendous progress, and we propose a novel method that...",
      "proposed_fix": "Replace with a punchline-first opener naming the capability achieved, per abstract-intro-playbook.md §Move-1.",
      "craft_principle": "abstract-intro-playbook.md §Move-1: lead with the capability, not the field context."
    }
  ]
}
```

Rules for Claude's suggestions:
- **Craft only** — no content claims, no new experiments, no theory changes, no new citations.
- **Each suggestion must cite a specific principle** from the embodied-ai-paper-writer manual (file + section).
- **Evidence quote must be verbatim** from the paper (Claude must be able to grep-find it).
- **Respect `## Hard don'ts`** — if a hard-don't blocks the only suggestion Claude was going to make for a section, pick a different section.

Update state to `phase: collecting_codex_suggestions`.

### Step 2: Codex Produces Top-5 (Fresh Thread)

Invoke `mcp__codex__codex` (never `codex-reply` — fresh thread always):

```
mcp__codex__codex:
  model: gpt-5.5
  config: {"model_reasoning_effort": "xhigh"}
  cwd: <absolute path to repo root>
  prompt: |
    You are a professional embodied-AI paper writing coach, distilled from
    63 top robotics papers (CoRL, RSS, ICRA, IROS, Science Robotics, 2022-2026).
    You are NOT a reviewer scoring this paper. You are a co-author helping it
    land at a top robotics venue.

    ## Read these files first (in this order, before drafting suggestions)

    1. skills/embodied-ai-paper-writer/SKILL.md — your craft manual.
       Follow its problem-routing table at the top. Based on the paper's
       sections, load the 1-3 most relevant references/*.md playbook files
       (e.g., abstract-intro-playbook.md, method-relatedwork-playbook.md,
       experiments-results-playbook.md, figures-tables-playbook.md,
       closing-appendix-playbook.md, flow-transitions.md,
       language-phrasebank.md, titles.md).

    2. <PAPER_DIR>/PAPER_PREFERENCES.md — author's standing orders.
       Respect every bullet in ## Hard don'ts, ## Notation, ## Style / tone,
       and ## Section-specific. If a craft fix you would otherwise suggest
       violates a hard-don't, suggest something else instead.
       (If this file does not exist, ignore this step.)

    3. <PAPER_DIR>/sections/*.tex — the paper source.

    4. <PAPER_DIR>/main.pdf — the compiled paper, for figure/table visual cues.

    ## Task

    Identify the {SUGGESTIONS_PER_SIDE} most impactful **writing-craft**
    improvements that would strengthen this paper for a robotics venue
    submission.

    These are *craft* fixes — vocabulary, sentence patterns, paragraph
    rhythm, section construction, figure/table caption phrasing, rhetorical
    transitions, opener/closer patterns.

    Explicitly NOT in scope:
    - content claims (do not suggest adding/removing experiments or numbers)
    - theory changes (do not suggest modifying theorems or proofs)
    - new citations (do not suggest \cite{...} additions)
    - structural rewrites (do not suggest reordering whole sections)
    - figures themselves (only captions)

    ## Output

    Output STRICTLY as a single JSON object — no commentary, no markdown
    fences, no preamble, no postscript. Just the JSON:

    {
      "codex_suggestions": [
        {
          "id": "X1",
          "priority": "HIGH" | "MEDIUM" | "LOW",
          "section": "<which section, e.g. 'abstract'>",
          "file": "<PAPER_DIR>/sections/<file>.tex",
          "line_range": "<L1-L2>",
          "issue": "<one-sentence diagnosis>",
          "evidence_quote": "<verbatim snippet from paper, ≤200 chars>",
          "proposed_fix": "<concrete rewrite or rule, 1-3 sentences>",
          "craft_principle": "<which playbook file and section, e.g. 'abstract-intro-playbook.md §Move-1'>"
        }
        // exactly {SUGGESTIONS_PER_SIDE} entries
      ]
    }

    Constraints:
    - Each suggestion must cite a specific craft principle from a playbook file.
    - Each evidence_quote must be verbatim text from the paper (grep-findable).
    - Distribute suggestions across sections — do not give all 5 on the abstract.
    - Rank by priority HIGH > MEDIUM > LOW within the list.
```

Substitute `{SUGGESTIONS_PER_SIDE}` and `<PAPER_DIR>` with actual values before sending. Save the returned threadId only for state-file bookkeeping; do not use it for any continuation.

Parse Codex's JSON output (strip any surrounding fences if present). Write to `<paper-dir>/.polish/codex_suggestions.json`.

If Codex's output is malformed (not parseable as JSON, missing required fields, fewer than `SUGGESTIONS_PER_SIDE` entries), surface the raw output to the user and ask for a re-run rather than guessing — do NOT fabricate suggestions to fill the gap.

Update state to `phase: detecting_overlap`.

### Step 3: Overlap Detection (Claude)

Claude compares the two lists. A pair `(C_i, X_j)` is an **OVERLAP** iff BOTH:

1. **Section match** — they target the same section, OR their `file:line_range` windows share ≥50% intersection by line count.
2. **Fix-intent match** — they invoke the same craft principle (same playbook file + same section), OR they target the same sentence/paragraph for rewrite with semantically aligned proposed fixes.

Bucket all 10 suggestions (5 from each side) into:

- `OVERLAP_PAIRS` — list of `(C_i, X_j)` pairs.
- `CLAUDE_ONLY` — `C_i` with no matching `X_j`.
- `CODEX_ONLY` — `X_j` with no matching `C_i`.

Note: a single suggestion can only belong to one bucket. If `C_2` matches both `X_1` and `X_3`, pick the closer match and put the other in `_ONLY`.

Document the overlap reasoning briefly — for each `OVERLAP_PAIR`, note in 1 sentence why they were judged a match. This goes into `OUTPUT_MD` for audit.

Update state to `phase: auto_applying_overlap`, write `overlap_count` and `pending_count`.

### Step 4: Auto-Apply Overlap (Hard-Don't Gated)

For each `(C_i, X_j)` in `OVERLAP_PAIRS`:

1. **Synthesize the fix.** Prefer the cleaner of the two `proposed_fix` formulations — usually Codex's (it is the dedicated writer), but if Claude's is more specific or actionable, use Claude's. If they materially conflict, log both and skip (treat as if non-overlapping and surface in the Pending list).

2. **Check `PAPER_PREFERENCES.md ## Hard don'ts`.** If a bullet blocks the fix (e.g., "Do not rewrite Theorem 1", "Do not paraphrase the abstract's first sentence"), do NOT apply. Log status as `blocked_by_hard_dont: <quoted bullet>`.

3. **Apply via `Edit`** to the target `.tex` file. The edit must be exact — find the `evidence_quote` in the file and replace with the new wording. If the quote no longer matches (e.g., a prior overlap edit shifted the surrounding context), surface the conflict to the user rather than guessing — do NOT do fuzzy matching.

4. **Log status** as one of: `applied`, `blocked_by_hard_dont`, `conflict_skipped`.

### Step 5: Build `WRITING_POLISH_SUGGESTIONS.md`

Write to `<paper-dir>/WRITING_POLISH_SUGGESTIONS.md`:

```markdown
# Writing Polish Suggestions

Generated: <ISO-8601 date>
Paper: <paper-dir>
Craft manual: skills/embodied-ai-paper-writer/SKILL.md
Author preferences: <paper-dir>/PAPER_PREFERENCES.md (or "not present")
Codex thread: <threadId>

## Auto-Applied — Overlap of Claude × Codex

Each row is a suggestion that BOTH sides flagged independently. High confidence.

| # | Section | File:Lines | Issue | Fix | Principle | Status |
|---|---------|------------|-------|-----|-----------|--------|
| A1 | abstract | sections/0_abstract.tex:4-8 | filler opener | punchline-first rewrite | abstract-intro-playbook.md §Move-1 | applied |
| A2 | method | sections/2_method.tex:42-50 | passive voice cluster | active-voice rewrite | language-phrasebank.md §passive→active | blocked_by_hard_dont: "Do not paraphrase the method derivation" |

## Pending User Decision — Non-Overlap

Ordered by priority (HIGH → LOW). Tied priorities: Claude before Codex.

### P1 [HIGH, Codex-only] Introduction — overuse of "novel"

- File: `sections/1_intro.tex`, lines 12-15
- Quote: "We propose a novel multi-modal robotic policy that leverages a novel attention mechanism..."
- Proposed fix: Replace each "novel" with a concrete verb. "We develop a multi-modal robotic policy that uses an attention mechanism..."
- Craft principle: language-phrasebank.md §filler-adjectives — "novel" carries no information; replace with verb that names the actual contribution.
- Why pending: Claude's top-5 focused on the method and experiments sections; abstract/intro filler did not make Claude's HIGH cut.

### P2 [HIGH, Claude-only] Method — paragraph 3 transitions

- File: `sections/2_method.tex`, lines 78-95
- Quote: "...the model is trained on demonstrations. Next, we evaluate..."
- Proposed fix: Add a 1-sentence motivation bridge between the training and evaluation paragraphs, per flow-transitions.md §motivation-bridge.
- Craft principle: flow-transitions.md §motivation-bridge — abrupt section transitions force reviewers to reconstruct the logic; a 1-sentence bridge prevents the drop-out.
- Why pending: Codex focused on caption phrasing in this section, not on transitions.

### P3 [MEDIUM, Codex-only] ...

### P4 [MEDIUM, Claude-only] ...

### P5 [LOW, Codex-only] ...

## Reply Guide

Reply inline with one of:

- `go` or `apply all` — apply every Pending item above.
- `1 3 5` — apply only P1, P3, P5 (space- or comma-separated indices).
- `skip 2,4` — apply all Pending except P2, P4.
- `stop` or `none` — apply nothing more; finalize as-is.
- free-text (e.g., `apply 1 and 3, but for 3 also change "leverages" to "uses"`) — treated as additional instructions; Claude blends with the chosen Pending fixes.

Persistence: if your reply contains "always", "never", "in this paper", "every time", or names a recurring style/notation rule, the loop will offer to pin it to `PAPER_PREFERENCES.md` before applying (you can approve, edit, or skip — fixes proceed either way).
```

Update state to `phase: awaiting_user`.

### Step 6: Inline HUMAN_CHECKPOINT

Print to the user:

```
📋 Writing polish — review complete.

  Overlap auto-applied: N (see WRITING_POLISH_SUGGESTIONS.md "Auto-Applied" table)
  Pending your decision: M (see "Pending User Decision" section)

Reply: "go" / "1 3 5" / "skip 2,4" / "stop" / free-text instructions
```

Then **wait for the user's inline reply**. Parse using the same logic as `/auto-paper-improvement-loop` Step 2b / `/auto-review-loop` Phase B:

- `go` / `continue` / `ok` / `proceed` / `apply all` → apply all Pending.
- Space/comma-separated digit list → apply only those indices.
- `skip <list>` → apply all except those indices.
- `stop` / `none` / `done` → skip Step 7, jump to Step 8.
- Anything else → treat as free-text instruction merged with Pending; ask a brief clarifying question if it is genuinely unparseable, but default to "best-effort merge with the highest-priority Pending items".

**Persistence prompt** — if the reply contains `always`, `never`, `in this paper`, `every time`, or corrects a recurring style/notation pattern, propose a diff to `<paper-dir>/PAPER_PREFERENCES.md` before applying fixes. Show the diff inline. Ask `y / edit / skip` — fixes proceed regardless of the answer (this is a side-channel for future runs, not a gate on the current run). Standard pattern per [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md) Write Protocol.

### Step 7: Apply Selected Non-Overlap Fixes

For each selected Pending item:

1. Re-verify `PAPER_PREFERENCES.md ## Hard don'ts` against the fix (same gate as Step 4). The user may have just added a new hard-don't via the persistence prompt — re-read the file.
2. Apply via `Edit` to the target `.tex` file. Same exact-match rule as Step 4 — no fuzzy matching.
3. Log status as `user_approved_applied` / `blocked_by_hard_dont` / `conflict_skipped`.

For free-text instructions, treat them as additional craft fixes to apply, but constrain to the same craft-only scope (no content/theory/citations).

### Step 8: Recompile

```bash
cd "$PAPER_DIR" && latexmk -C && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tee compile.log
cp main.pdf main_polish_final.pdf
```

Verify:

```bash
# Should both be 0
grep -c "LaTeX Warning.*undefined" compile.log
grep -c "Citation.*undefined" compile.log
```

If compile fails: surface the error to the user. Do NOT silently roll back — the user's edits are partially applied and visible in `git diff`. Offer two options:
- Fix the compile error and retry.
- Revert the polish loop's edits via `git checkout -- <paper-dir>/sections/`.

### Step 9: Finalize `WRITING_POLISH_SUGGESTIONS.md`

Update the md:

- Move applied Pending items from "Pending User Decision" to a new "User-Approved Applied" section.
- Move skipped items to a "User-Skipped" section.
- Record any free-text instructions in a "User-Custom-Instruction" section with the resulting edits.
- Append a "Compile Result" section: page count, any remaining overfull warnings, undefined-ref count.

Update state to `phase: done`, `status: completed`.

### Step 10: Summary

Report to user:

```
✅ Writing polish complete.

  Auto-applied (overlap):       N
  User-approved (non-overlap):  M
  Skipped:                      K
  Blocked by hard-don't:        L

  PDFs:
    main_polish_before.pdf      ← original
    main_polish_final.pdf       ← final (= main.pdf)

  Log: WRITING_POLISH_SUGGESTIONS.md
```

## State Persistence (Compact Recovery)

`<paper-dir>/WRITING_POLISH_STATE.json` is written after each major step:

```json
{
  "phase": "collecting_claude_suggestions" | "collecting_codex_suggestions" | "detecting_overlap" | "auto_applying_overlap" | "awaiting_user" | "applying_user_fixes" | "recompiling" | "done",
  "paper_dir": "<paper-dir>",
  "suggestions_per_side": 5,
  "claude_suggestions_path": "<paper-dir>/.polish/claude_suggestions.json",
  "codex_suggestions_path": "<paper-dir>/.polish/codex_suggestions.json",
  "codex_threadId": "<saved-for-bookkeeping-only>",
  "overlap_count": N,
  "pending_count": M,
  "status": "in_progress" | "completed" | "failed",
  "timestamp": "<ISO-8601>"
}
```

**On startup**: if `WRITING_POLISH_STATE.json` exists with `status: in_progress` AND timestamp within 24 hours, read it + `WRITING_POLISH_SUGGESTIONS.md` to recover context, then resume from the saved phase. Otherwise (file absent, `status: completed`, or older than 24 hours), start fresh.

**Never reuse the saved `codex_threadId`** — recovery starts a fresh Codex thread for Step 2 if resuming pre-overlap-detection. The threadId is recorded only so the user can audit which Codex session produced the saved suggestions.

## Key Rules

- **Fresh Codex thread, always** — use `mcp__codex__codex`, never `mcp__codex__codex-reply`. No "since last run" framing in the prompt.
- **embodied-ai-paper-writer is mandatory, not optional** — if the submodule is not present, abort with a clear error. The skill is built around this craft manual.
- **Both sides see PAPER_PREFERENCES.md** — this is the explicit divergence from `/auto-paper-improvement-loop`. Codex is a coach here, not a reviewer.
- **Craft only** — never apply edits that add citations, change numbers, modify theorems, or reorder sections. If a suggestion drifts into content territory, drop it and pick a different craft fix.
- **Exact-match edits only** — `evidence_quote` must be grep-findable; apply via `Edit` with the exact string. No fuzzy matching, no LLM-judged "close enough" replacements.
- **Hard-don't gate runs at every apply point** — Step 4 (auto-overlap), Step 7 (user-approved), and after a mid-loop `PAPER_PREFERENCES.md` append. Re-read the file each time; the user may have just added a bullet.
- **No silent rollback** — if compile fails after Step 8, surface the error. User chooses to fix or revert.
- **Preserve PDF snapshots** — `main_polish_before.pdf` and `main_polish_final.pdf` for visual diff.

## Output

```
<paper-dir>/
├── main.pdf                         # = main_polish_final.pdf
├── main_polish_before.pdf           # original snapshot
├── main_polish_final.pdf            # after all applied fixes
├── WRITING_POLISH_SUGGESTIONS.md    # full log
├── WRITING_POLISH_STATE.json        # compact-recovery state
└── .polish/
    ├── claude_suggestions.json      # raw Claude top-5
    └── codex_suggestions.json       # raw Codex top-5 (parsed from mcp__codex__codex output)
```

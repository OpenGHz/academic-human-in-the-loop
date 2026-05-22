# PAPER_PREFERENCES.md — Per-Paper Standing Orders

Authoritative spec for the per-paper preferences file. Defines location, schema, read protocol, write protocol, and how this mechanism composes with the other per-paper artifacts (`NARRATIVE_REPORT.md`, `PAPER_PLAN.md`, `PAPER_IMPROVEMENT_LOG.md`).

> **Quick map**: this file is the **spec**; the actual standing orders live at `<paper-dir>/PAPER_PREFERENCES.md`, one per paper. Every paper-touching skill reads that file at the start of its workflow and treats its contents as user constraints that override defaults.

## Why This File Exists

The global auto-memory at `~/.../memory/` captures user-level preferences ("this user prefers terse responses", "this user is a Go developer"). But preferences attached to a *specific paper* — "in this paper, π_θ is the policy not the agent", "do not move Theorem 1 to appendix", "the reviewer killed 'novel' last round, don't use it" — don't belong in global memory: they're not about the user, they're about the artifact.

Without a per-paper persistence layer, user feedback given verbally in chat (or at `human-checkpoint:true` prompts) gets forgotten after a few rounds of `/auto-paper-improvement-loop` or after a session boundary. The agent then re-makes the same mistake the user already corrected.

`PAPER_PREFERENCES.md` is the missing per-paper layer. It sits alongside the paper in git, travels with the paper across sessions, and is read by every paper-touching skill at startup.

## Three-Layer Memory Architecture

| Layer | Scope | Where | Updated when |
|---|---|---|---|
| **Global auto-memory** | User-level (preferences, role, feedback patterns across all projects) | `~/.../memory/MEMORY.md` + topic files | Agent saves at conversation events |
| **Per-paper preferences** | One specific paper (notation, style don'ts, hard constraints, section-specific rules) | `<paper-dir>/PAPER_PREFERENCES.md` | User edits directly OR agent proposes append after checkpoint feedback |
| **Session context** | Current conversation only | In-memory, plans, TodoWrite | Each turn |

The three layers are read in increasing-specificity order: global memory sets the user-default behavior, `PAPER_PREFERENCES.md` overrides for this paper, session context overrides for this turn. When they conflict, the narrower scope wins.

## File Location

`<paper-dir>/PAPER_PREFERENCES.md` — at the root of the paper directory, next to `main.tex` / `paper.tex`.

**Why paper/ root, not paper/.aris/**:
- Visible to the user without opening hidden directories.
- Commits naturally with the paper in git.
- A new collaborator opening the paper directory sees the standing orders immediately.

This is in contrast to operational artifacts like `paper/.aris/improvement-log.json` that are agent-internal bookkeeping; `PAPER_PREFERENCES.md` is a human-edited document.

## Schema

```markdown
---
paper: <slug or title>
last-updated: YYYY-MM-DD
---

# Paper-Specific Preferences

## Style / tone
- <rule>. Reason: <why — often a past reviewer comment or strong user preference>.

## Notation
- <symbol or term> is <meaning>. Do not call it <forbidden alternative>.

## Section-specific
- §<section>: <rule>.
- <section name>: <must-keep / must-not> instruction.

## Hard don'ts
- Do not <action>.

## Open questions
- <question the user hasn't decided yet — the agent should ask, not guess>
```

All sections are optional. A minimal file may contain only `## Hard don'ts`. Headings should be stable so skills can grep for them, but missing sections are fine.

### Field semantics

- `paper` — slug for cross-referencing (e.g., in commit messages). Should be stable; never rename mid-paper.
- `last-updated` — bumped on every edit. Skills compare this against their own last-read timestamp if they cache.
- Each bullet should be **self-contained**: a future agent reading only the bullet (without the surrounding chat history) must be able to apply it. Include the *why* when the reason is non-obvious or comes from a past incident.

## Read Protocol

Every paper-touching skill reads `<paper-dir>/PAPER_PREFERENCES.md` at the start of its workflow (typically as Step 0 or Inputs). Required for:

- `/paper-plan` — read before designing the section matrix.
- `/paper-write` — read before drafting each section.
- `/paper-figure` and `/figures-prep` — read for figure-specific don'ts (e.g., "do not change the color of method A's curve to red — reserved for ablation").
- `/paper-illustration` — read before generating prompts.
- `/paper-compile` — read before applying page-shrink heuristic (some "Hard don'ts" forbid moving specific content).
- `/auto-paper-improvement-loop` — read at the top of each round; also at every `human-checkpoint:true` to remind the user what's already pinned.
- `/citation-audit` — read for citation-specific rules (e.g., "do not cite Chen 2024 — it's the wrong context").
- `/resubmit-pipeline` — read at Phase 0 so resubmit edits respect the paper's standing orders.
- `/reference-backfill` — read before searching, so the search avoids forbidden citation contexts.

**Treat the file as user-binding constraints.** A bullet in `## Hard don'ts` overrides defaults from `paper-write`, `shared-references/writing-principles.md`, etc. If a hard constraint conflicts with a global heuristic (e.g., the page-shrink heuristic wants to move Theorem 1 to appendix, but `## Hard don'ts` says "Do not move Theorem 1"), the per-paper file wins — halt and surface to the user per the [`page-shrink-heuristic`](page-shrink-heuristic.md) failure-mode protocol.

**If the file does not exist**, treat it as empty. Do not error; do not prompt to create it. The file is created on-demand (see Write Protocol below).

## Write Protocol

Two write paths, in order of preference:

### Path 1: User edits directly

The primary path. Users open `PAPER_PREFERENCES.md` and add bullets. Agents must not assume edits without confirmation.

### Path 2: Agent-proposed append

When the user gives feedback in chat or at a `human-checkpoint:true` prompt that is **general for this paper** (not a one-off fix to a single sentence), the agent should propose appending it to `PAPER_PREFERENCES.md`:

> User: "stop using 'novel' — reviewer killed us on it last round"
>
> Agent: "Pinning this as a standing order. Proposing to add to PAPER_PREFERENCES.md:
> ```
> ## Style / tone
> - Never use "novel" / "we propose a novel". Reason: prior reviewer flagged it. Replace with concrete verb (develop, design, introduce).
> ```
> Approve? (y / edit / skip)"

The agent must **always show the diff and ask** before writing. Never silently append.

### Heuristic: when is feedback "general for this paper"?

- **Append to PAPER_PREFERENCES.md** when feedback uses language like "always", "never", "every time", "in this paper", "the convention is", or when the user is correcting a recurring pattern (notation, terminology, style).
- **Apply as one-off** when feedback names a specific location ("change line 42", "the third paragraph of §2 should…") or is a content fix (rewriting a sentence, adding a citation here).

When unsure, ask: "Should I pin this as a standing order for this paper, or treat it as a one-off?"

### Heuristic: when NOT to append

- Don't append routine writing-quality feedback that already lives in `shared-references/writing-principles.md` (e.g., "use active voice"). Use the shared docs as the default; pin only the *deviations from default* that this paper requires.
- Don't append session-local task state ("we're working on §3 next") — that belongs in TodoWrite or a plan.
- Don't append speculative future work ("we might add a discussion section later") — that belongs in PAPER_PLAN.md.

## Lifecycle and Composition with Other Per-Paper Artifacts

Each per-paper artifact has a distinct role. `PAPER_PREFERENCES.md` is **standing orders** — the rules to follow when working on this paper.

| Artifact | Role | Voice | Mutability |
|---|---|---|---|
| `NARRATIVE_REPORT.md` | Paper content spec (what the paper says, story-level) | Author's narrative | Stable; updated when story changes |
| `PAPER_PLAN.md` | Paper organization (section matrix, page budget, figure plan) | Structural blueprint | Updated at plan revisions |
| `PAPER_IMPROVEMENT_LOG.md` | Audit trail (what was done in each improvement round) | Append-only history | Append-only; never edit past entries |
| `PAPER_PREFERENCES.md` | Standing orders (rules to follow) | Imperative, second-person to the agent | Edited live; bullets removed when no longer relevant |

When the same fact would fit in two places, prefer the one with stronger semantics:

- "The paper argues X" → NARRATIVE_REPORT.md (content)
- "§3 has 1.5 pages of budget" → PAPER_PLAN.md (organization)
- "Round 4 moved Lemma 2 to appendix" → PAPER_IMPROVEMENT_LOG.md (history)
- "Never move Theorem 1 to appendix" → PAPER_PREFERENCES.md (rule)

## Relationship to Global Auto-Memory

Per-paper preferences and global memory must not duplicate each other:

- **Pin to global auto-memory** when the rule applies across all the user's papers ("user prefers double-blind anonymization throughout the draft", "user always wants `\citep` not `\cite`").
- **Pin to PAPER_PREFERENCES.md** when the rule is specific to this paper ("π_θ is the policy here", "do not cite Chen 2024 in this paper because of the wrong context").

If the agent saves a per-paper rule to global memory by mistake, it will leak into other projects. If the agent saves a global rule to PAPER_PREFERENCES.md, it won't apply to the next paper. When in doubt, ask the user which scope they intend.

## Maintenance Hygiene

The file can grow stale. Skills that read it should not blindly apply every bullet — a quick sanity check:

- If a bullet references a section that no longer exists (e.g., "§5: keep the robot example" but the paper has been restructured to 4 sections), flag it to the user rather than silently ignoring or silently applying to the wrong section.
- If two bullets conflict (the user added a new one without removing the old), halt and ask the user to reconcile.
- When `last-updated` is more than ~90 days old and the paper has gone through major revisions, suggest a sweep: "PAPER_PREFERENCES.md was last updated YYYY-MM-DD. Want me to review which bullets still apply?"

The user owns the file. Agents may *propose* edits and removals, but must not delete or rewrite bullets without confirmation.

## Initial Scaffolding

When does the file first appear? Two natural points:

1. **`/narrative-bridge`** (or whichever skill creates a new paper directory) — scaffold an empty `PAPER_PREFERENCES.md` with just the frontmatter and a comment explaining the file. The user can then fill it in.
2. **First time a paper-touching skill receives general-for-this-paper feedback** — create the file with the new bullet on first append.

Either is fine. Scaffolding early is gentler (no surprise file creation mid-loop); on-demand creation is leaner (no empty file if the user has no standing orders).

The scaffold template:

```markdown
---
paper: <paper-slug>
last-updated: <today>
---

# Paper-Specific Preferences

<!-- Standing orders for this paper. Bullets here override defaults from
shared-references/ and global auto-memory. See
skills/shared-references/paper-preferences.md for the spec. -->

## Hard don'ts
<!-- (none yet) -->
```

## How Skills Should Invoke This

- **Read at workflow start**, not lazily. The file is small; the cost is negligible; lazy reads create bugs where a bullet only kicks in halfway through a workflow.
- **Cite the bullet in agent output when applied.** E.g., "Skipping 'novel' per PAPER_PREFERENCES.md (## Style / tone)." This makes it traceable for the user and surfaces stale bullets faster.
- **Surface conflicts loudly.** When a hard don't would block an otherwise-default action (e.g., page-shrink wants to move a forbidden theorem), halt and surface — don't silently work around it.
- **Don't read it twice in the same workflow.** A skill that calls sub-skills (e.g., `/resubmit-pipeline` calling `/citation-audit`) should pass the loaded preferences down rather than re-reading; otherwise the sub-skill may diverge from the parent's view.

## Anti-Patterns

- ❌ Treating PAPER_PREFERENCES.md as a TODO list. It's standing orders, not pending tasks. Use TodoWrite or PAPER_PLAN.md for tasks.
- ❌ Writing imperative rules with no reason. A bullet without context becomes uninterpretable when the original reason fades; future-you (or future-agent) cannot judge edge cases. Always include a `Reason:` clause when the rule isn't self-evident.
- ❌ Stuffing entire narrative paragraphs into the file. The file is a bullet list of rules, not a discussion document. Long context belongs in NARRATIVE_REPORT.md.
- ❌ Letting the agent silently rewrite the file. Every edit must be diff-confirmed by the user.
- ❌ Copying global memory into the file. If the rule applies across all papers, it belongs in `~/.../memory/`, not here.

## Failure Modes

If `PAPER_PREFERENCES.md` is malformed (broken YAML frontmatter, non-markdown structure), treat the file as empty for the current workflow and surface a warning to the user with the parse error. Do not attempt to auto-fix — the user owns the file.

If the file is present but `last-updated` is missing or in the future, warn but proceed. The field is informational; do not block on it.

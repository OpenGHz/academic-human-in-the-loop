---
name: title-decider
description: Interactively decide and lock a paper's title through discussion, then persist the decision so downstream skills inherit it. Use whenever the user wants to choose, propose, critique, compare, refine, or finalize a paper/manuscript title, or name the method/framework — triggers include "确定标题", "定标题", "标题怎么取", "取个标题", "起个名字", "方法叫什么", "decide title", "finalize title", "lock the title", "paper title", "title suggestions", "name the paper", "name my method/framework", "which title is better". Use proactively when the user is weighing title candidates even if they don't say the word "title". NOT for section headings, figure captions, slide titles, or naming non-paper artifacts.
argument-hint: [optional seed title or positioning note]
allowed-tools: Bash(*), WebSearch, WebFetch, Read, Glob, Grep, Edit, Write, AskUserQuestion
---

# Title Decider

Help the user converge on a paper title **through discussion**, then **persist the decision and its rationale** so every downstream skill (`paper-plan`, `paper-write`, `paper-writing`, `embodied-ai-paper-writer`, abstract drafting, `paper-slides`, …) inherits the same title, framework name, and terminology — instead of each one silently re-inventing them.

A title is a one-line contract about *what the paper claims and how it is scoped*. Getting it right early prevents terminology drift across the whole pipeline. This skill is the place where that contract is negotiated and written down.

## Constants

- **OUTPUT = `idea-stage/TITLE.md`** — Where the decision is persisted. This is a **project file**, not a memory and not the paper's LaTeX — it is the hand-off record downstream skills read. Saving is the default on confirmation. Override with `— output: <path>`; suppress the standalone file with `— no-save` (then only print the block). History is left to git — don't write timestamped copies in a versioned repo.
- **COLLISION_CHECK = on** — Before recommending any coined framework/method **name**, web-search to confirm it is not already an established named method. Default on; `— no-collision-check` to skip (e.g. offline).

> 💡 Overrides:
> - `/title-decider "Seed: Try Once, Then Optimal: ..."` — start from a seed title
> - `/title-decider — output: refine-logs/TITLE.md` — custom path
> - `/title-decider — no-save` — discuss only, write nothing

## What this skill is NOT

It does not invent claims. The title must reflect what the paper *actually* argues and *actually* evaluates — pull that from the idea docs, the novelty report, and the results, not from what sounds impressive. If you find yourself proposing a title the evidence can't back, stop and say so.

## Phase A — Gather the positioning (don't start from a blank page)

Before proposing anything, load what already fixes the title's content. Read whatever exists; skip silently what doesn't:

- **Idea / proposal docs** — `Glob` for `**/idea*.md`, `**/PROPOSAL*.md`, `ref_docs/idea/*`, or whatever the user points at. Extract: the one-line goal, the core mechanism, the claimed contribution, and the explicit **non-goals**.
- **Idea / novelty / related-work** — `idea-stage/IDEA_REPORT.md` (the W1 deliverable `/novelty-check` and `/idea-creator` write: method, novelty verdict, closest-prior-work table, positioning; falls back to legacy `idea-stage/NOVELTY_*.md` on older projects), `literature/related_work.md`, `research-wiki/`. Extract: the **closest prior work** and the **delta** (this is what the title must differentiate against), plus any **naming-collision risks** already flagged.
- **Results / claims** — if a results or claims file exists, confirm the title's scope matches what was actually measured (e.g. an *efficiency* claim needs efficiency metrics, not success-rate).

From these, write yourself a short internal brief: **claim axis** (what is the paper's headline contribution — efficiency? capability? a new benchmark?), **mechanism/framework** (what to name), **scope** (domain + setting), and the **one differentiator** that must survive in the title.

## Phase B — Generate and critique candidates

Compose titles from four slots, and treat each as a deliberate choice:

1. **Hook** (optional, before the colon) — a short memorable phrase. Earns its place only if it's accurate, not just catchy.
2. **Contribution / phenomenon** — often the subject of the subtitle; the thing the paper establishes.
3. **Framework/method name** — the coinage that becomes the citeable handle. Give an **acronym** on first definition; named methods get cited and used as baselines more readily.
4. **Scope** — domain + setting (the `for …` tail).

Run every candidate through the **title-craft checklist** — these are the failure modes that repeatedly bite (each maps to a real mistake; explain the *why* to the user, don't just assert):

- **The name must be faithful to what the artifact *is*.** If the memory stores images *and* language, don't call it "Language Memory" — the name would hide a core design choice. Name the container by its honest contents.
- **Avoid `X-efficient` when you mean `avoids X`.** "Exploration-efficient" reads as *better exploration*; if the method *removes* later exploration, say "amortizing exploration" / "fewer probes" / "amortized". Pick the word that names the actual effect.
- **Don't deny a capability you keep.** If the method preserves a fallback (e.g. still explores on failure), don't title it "X-free" — it contradicts the design.
- **Put the differentiator in the subtitle, not the name.** The one contrast vs the closest prior work (e.g. *language* abstraction vs *action* replay) is what defends novelty — make sure a reader sees it.
- **Modifier hygiene.** Three stacked compound modifiers before one noun ("A-ing, B-Cross C-Oriented Memory") read as a pile-up. Move one to a head noun or a `for …`/`via …` phrase, or separate with a comma.
- **Attach each modifier to the noun it actually describes.** If it's the *memory* that is cross-episode (not the *manipulation*), write "Cross-Episode … Memory for … Manipulation", not "… Memory for Cross-Episode … Manipulation" — the latter both misattributes and reads ambiguously.
- **Scope honesty.** A narrow domain word (e.g. "articulated objects") signals a narrow contribution; include it only if you mean it. Conversely don't over-claim generality the experiments don't cover.

Surface 4–8 candidates **grouped by what they emphasize** (e.g. "leads with efficiency" vs "leads with mechanism"), each with a one-line note on its trade-off. Name your top pick and *why*. Brevity and signal beat exhaustiveness — don't bury the user in 20 near-identical strings.

## Phase C — Collision check (when `COLLISION_CHECK = on`)

For any **coined name** you're about to recommend, `WebSearch` the exact phrase (+ the field, e.g. "robot manipulation VLA") to check it isn't an established method, and note the result. A name that's already taken (or that maps onto a well-known concept with a different meaning) is a liability — surface it rather than letting the user discover it at review time. This mirrors the anti-collision discipline of `/novelty-check`; reuse its findings if a novelty report already flagged naming risks.

## Phase D — Iterate to confirmation

This is a conversation, not a one-shot. Present, take the user's reaction, refine. Use `AskUserQuestion` only when a genuine fork needs a decision (e.g. "lead with efficiency or with the mechanism?"); otherwise stay conversational. Keep a running shortlist and the *reasons* for each cut — those reasons are half the value of the output file.

**Confirmation is explicit.** Treat the title as decided only when the user clearly says so ("定", "就这个", "lock it", "yes that one"). Don't assume agreement from silence or a lukewarm "looks fine".

## Phase E — Persist the decision (default, on confirmation)

When the user confirms, write **OUTPUT** (`idea-stage/TITLE.md`) using the template below (`mkdir -p idea-stage` first if needed). Overwrite in place — **history is git's job**, so don't litter the directory with timestamped copies in a versioned repo. (If the project isn't under version control, mention that to the user and let them decide whether they want a manual snapshot.)

Capture **not just the title** but the discussion's durable residue — the rejected alternatives and *why*, the terminology rulings, the collision check — because those are exactly the decisions a downstream skill (or a future you) would otherwise re-litigate or violate.

### `idea-stage/TITLE.md` template

```markdown
# Paper Title

## Canonical title
> <THE FINAL TITLE, verbatim, one line>

**Short title / running head:** <≤6 words, or "—">
**Framework name + acronym:** <Name (ACRONYM)>, or "—"
**Status:** decided <YYYY-MM-DD>

## Title components
- **Hook:** <text or "—">
- **Contribution / phenomenon:** <…>
- **Mechanism / framework:** <…>
- **Scope (domain + setting):** <…>

## Positioning encoded in the title
- **Claim axis:** <e.g. efficiency — NOT success rate (success rate = non-regression guardrail)>
- **Closest prior work + the differentiator the title carries:** <paper → the contrast, e.g. language abstraction vs action replay>

## Terminology rulings (use consistently across all downstream writing)
- **Use:** <canonical term> — <one-line gloss>
- **The name means / does NOT mean:** <e.g. "Instance-Oriented Memory" stores image keys + language values; do NOT call it "Language Memory">
- **Define on first use:** <e.g. "instance" = appearance-defined object instance/model>
- **Avoid:** <term> — <why> (e.g. "exploration-efficient" misreads; "object-centric memory" collides with X; "exploration-free" contradicts the kept fallback)

## Rejected alternatives (and why)
| Candidate | Rejected because |
|---|---|
| <title> | <reason> |

## Naming-collision check
- <coined name> — searched <date>: <not an existing named method / collides with X> <link if relevant>

## Notes for downstream skills
- **Companion W1 deliverable — read this for full idea + novelty context:** `idea-stage/IDEA_REPORT.md` (the ranked-idea report `/novelty-check` / `/idea-creator` own: method, novelty verdict + score, closest-prior-work table, positioning). `TITLE.md` is the naming/terminology contract; `IDEA_REPORT.md` is the substance behind it — keep them consistent. Also: `literature/related_work.md` (full landscape).
- <anything paper-plan / paper-write / abstract drafting should honor — e.g. "lead the abstract's first sentence with the amortization framing", "report success rate as a guardrail column, not a headline">
```

Always emit the companion-deliverable pointer above (it tells downstream skills where the fuller idea/novelty context lives); fill the rest from the discussion. If `idea-stage/IDEA_REPORT.md` is absent, point instead to whatever idea/novelty artifact exists (`literature/related_work.md`, `research-wiki/`) and say so.

## Phase E.5 — Patch the literature landscape by default (when the discussion surfaced it)

Title discussions routinely turn up things that belong in the **literature landscape** (`literature/related_work.md`, a `/research-lit` output, or the novelty report), not just in `TITLE.md` — e.g. sharpening the differentiator vs the closest prior work, re-scoping the claim axis, a competitor that the framing now hinges on, or a terminology ruling that corrects a stale "this space is empty" statement. **When that happens, patch the landscape by default — do not stop to ask.** A discussion that produced the insight has already done the work; making the user re-request the write just loses it.

Apply the same discipline as `/novelty-check`'s landscape-patch phase: **mirror the file's existing structure and voice; correct, don't only append** (if the discussion narrowed or falsified a claim the landscape makes, fix that claim in place rather than leaving a contradiction); and keep `TITLE.md` and the landscape consistent (the positioning/terminology in both must agree). Skip only if `— no-patch` is set, there is no landscape file in play, or the file is read-only — and never silently overwrite content that contradicts the new framing; correct it and let the diff show the change.

## Phase F — Hand off

After writing, tell the user the path and that downstream skills will pick it up. Point them to the natural next step (`/paper-plan`, abstract drafting, or `/embodied-ai-paper-writer`), and note that those should **read `idea-stage/TITLE.md` first** so the title, framework name, and terminology stay consistent. If `— no-save` was set, print the filled template inline instead and say it was not persisted.

## Downstream contract (for skills that consume this)

Downstream skills should `Read idea-stage/TITLE.md` before generating any title, framework name, abstract opening, or terminology, and treat its **Canonical title**, **Framework name**, and **Terminology rulings** as authoritative. If a downstream skill needs to deviate, it should surface the conflict to the user, not silently rename.

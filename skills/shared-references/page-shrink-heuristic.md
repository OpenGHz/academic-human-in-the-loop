# Page-Shrink Heuristic

Authoritative protocol for what to cut, in what order, when a paper exceeds its venue page limit. Originated in `/resubmit-pipeline` and lifted here so first-submission flows (`/paper-write`, `/auto-paper-improvement-loop`, `/paper-compile`) can apply the same ordered remediation instead of each emitting a one-line "consider moving content to appendix" hint.

> **Quick map**: page-limit *detection* lives in each compile/format gate (e.g., `/paper-compile` Step 6, `/auto-paper-improvement-loop` Step 8); page-limit *remediation* — this file — is shared. Detection answers "are we over?"; remediation answers "what do I cut, in what order, without breaking the science?"

## When to Apply

Apply this heuristic when any of the following fires:

- `/paper-compile` Step 6 reports `main_body_pages > MAX_PAGES`.
- `/auto-paper-improvement-loop` Step 8 format-check reports `PAGES > <venue limit>`.
- `/resubmit-pipeline` Phase 0.5 or Phase 4 detects overflow during venue-shrink (e.g., workshop camera-ready → 9-page main).
- `/paper-plan` Step 5 page-budget feasibility shows the planned section sizes sum above `MAX_PAGES` (apply at plan time so you don't write content you'll delete).

Skip the heuristic and stop early as soon as the page count is within the limit. Each step has a real cost in reader experience; don't apply more than you need.

## Before you cut: page *count* is not page *fill*

A trim is only warranted if content actually overflows. The PDF page **count** (`pdfinfo … | grep Pages`, or a compile gate's `PAGES`) answers "are we within the limit?" but says **nothing about how full the last page is.** A document can report N pages while page N holds only a few spilled lines (e.g., the tail of the bibliography) — it is really ~N−1 pages with a near-empty last page.

So **before applying any step below, confirm real overflow by measuring the last page's fill**, not just its existence:

```bash
pdftotext -f <lastpage> -l <lastpage> main.pdf - | sed '/^$/d' | wc -l   # non-blank lines actually on the last page
```

If the last page is nearly empty, you are within budget with margin to spare: do **not** trim, and do **not** claim the paper is "tight" — there may even be room to *add*. Never assert margin/headroom (or recommend a trim) from the page count alone; verify last-page fill first, or hedge until you have. Page count answers "within limit?"; last-page fill answers "how much room?".

## The Ordered Heuristic

Apply in order. Stop the moment the page count drops to ≤ limit. The order is calibrated **least-risky → most-risky**: early steps are pure editorial cleanup; later steps reorganize how the paper reads.

1. **Compress conclusion.** Future-work paragraphs typically run 1–2 paragraphs; cut each to 2–3 sentences. Save: **0.3–0.7 pages.** Pure editorial — reviewers rarely re-read future work in depth.
2. **Tighten abstract / intro hedging.** Cut "in this paper, we" → "we"; cut "it is well known that" → straight to point; collapse double adverbs ("very significantly improves" → "improves"); drop "to the best of our knowledge". Save: **0.2–0.4 pages.** Editorial. Tightens prose without losing claims.
3. **Move marginal figures to appendix.** Figures whose information is not load-bearing for the main argument (e.g., visualizations that illustrate but don't change the takeaway; ablations that don't get cited from the methods section). Save: **0.5–1 page per figure.** Changes reading rhythm — flag these in the rebuttal letter for camera-ready add-back if reviewers ask.
4. **Move proof sketches / extended remarks to appendix.** Keep theorem **statements** plus one-line proof intuition in main; full proofs (and detailed remarks) go to appendix. Save: **0.5–2 pages.** Changes the argument structure — readers who want to verify the proof now flip pages — but theorem statements stay where they're cited from.
5. **Compress related-work prose.** Convert cite-by-citation comparisons into a comparison table; merge paragraph-per-paper segments into single-sentence-per-paper batches grouped by theme. Save: **0.3–0.5 pages.** Stylistic shift; some venues prefer prose related-work, so check the venue checklist before applying.

## Hard Constraints (never crossed)

These hold across all five steps. Crossing them silently is a regression:

- ❌ **Never remove experiments.** A page-limit fix that drops a baseline or an ablation is a content cut masquerading as formatting.
- ❌ **Never remove theorems from main.** Move *proofs* to appendix; theorem statements stay in main (otherwise the paper's contributions become invisible).
- ❌ **Never remove citations.** This is paired with the `MIN_REFERENCES` floor in `/paper-writing` and the bib-freeze rule in `/citation-audit --soft-only`. Page pressure does not justify dropping references.
- ❌ **Never use `\sloppy`, font shrinkage, or margin tweaks to hide overflow.** These are venue-format violations that get desk-rejected.

## Failure Mode

If after step 5 the paper is still over the limit, **halt and surface to the user** — do not silently continue cutting. Emit verdict `BLOCKED` with `reason_code: page_shrink_failed_under_constraints` and present the user with the choice:

- **Relax a constraint** (e.g., approve removing a specific ablation, splitting one figure across two columns, or — last resort — choosing a different target venue with a larger limit).
- **Re-scope the contribution** (e.g., promote a sub-claim out of main, leaving its proof exclusively in appendix as a "discussion").

This is a user-decision boundary by design. The heuristic's job is to do everything safe; deciding what *unsafe* compromise is acceptable belongs to the author.

## How Skills Should Invoke This

- **At detection time, name the heuristic explicitly** in the error/warning message — e.g., `Main body is 10 pages (limit: 9). Apply shared-references/page-shrink-heuristic.md.` This is more useful than a one-line "move content to appendix" hint because the user (and the next skill in the pipeline) can follow the ordered steps without re-deriving them.
- **Don't paraphrase the steps** in each calling skill. Reference this file; consistency across skills is the whole reason it exists. Local elaboration is fine when there's a venue-specific quirk (e.g., CoRL's mandatory `\section{Limitations}` counted toward the budget — that constraint composes with this heuristic but is not part of it).
- **Track which step was applied** in any audit log or improvement log (`PAPER_IMPROVEMENT_LOG.md`, `RESUBMIT_REPORT.json`, etc.) so reviewers of the audit trail can see why a figure moved or a proof shifted.

## Composition with Other Constraints

| Other constraint | Interaction |
|---|---|
| `MIN_REFERENCES` floor (paper-writing) | Step 5's "compress related-work prose" must not drop unique `\cite{}` keys below the floor. Compressing format (prose → table) is fine; deleting references is forbidden (see hard constraints). |
| `--soft-only` bib freeze (citation-audit / resubmit-pipeline) | Reinforces the "never remove citations" hard constraint. Page pressure is not a soft-only override path. |
| Edit whitelist (auto-paper-improvement-loop, resubmit-pipeline) | If the whitelist forbids edits to `sections/proofs/*.tex`, step 4 is unavailable; jump to step 5 and, if needed, escalate to the user. Don't violate the whitelist to satisfy the page limit. |
| CoRL `\section{Limitations}` mandate | The Limitations section counts toward MAX_PAGES; do **not** move it to appendix as part of step 3 or step 4 — it must remain in main. |
| Venue-specific style (IEEE: references count toward limit) | The heuristic targets are the same, but the *budget* is different. Detection layer accounts for this; the heuristic itself doesn't change. |

## Why This Order, Briefly

Each step trades reader experience for page count. The trade rate worsens as you descend:

- Steps 1–2 (conclusion + hedging) cost ~nothing — reviewers don't notice.
- Step 3 (marginal figures) costs a small amount of "intuition aid" — readers who want the figure can find it in appendix.
- Step 4 (proof sketches) costs verification ergonomics — readers who want to check the proof flip pages.
- Step 5 (related-work compression) costs scholarly texture — readers get a quicker landscape but less narrative.

Stopping early matters because the cost is monotonic. A paper that hits the limit at step 2 is in better shape than one that needed step 5.

---
name: reference-backfill
description: "Diagnose-then-fill workflow for adding missing citations to a paper when MIN_REFERENCES floor is unmet. Use whenever the user hits `GAP_REFERENCES`, `under_min_references`, `reference floor`, says \"补引用\", \"引用不够\", \"reference count is low\", \"need more citations\", \"paper-write blocked by reference floor\", or any layer of the paper pipeline (paper-plan / paper-write / citation-audit / auto-paper-improvement-loop) refuses to advance because the unique cite-key count fell below the floor. Drives the full loop: locate the structural gap, pick the right search backend per topic, add real-context citations (not filler), and re-verify the floor — instead of letting Claude just dump random papers into the bib."
argument-hint: "[paper-dir] [— target: <N>] [— focus: <section>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill, Agent
---

# Reference Backfill: Close the Citation Floor Gap

Backfill citations for: **$ARGUMENTS**

This skill closes the gap between current cite-key count and `MIN_REFERENCES` (default 30). It is a **diagnosis → search → integration → re-verify** loop — not a "stuff the bib with more entries" script. Bare bib entries don't count toward the floor; only `\cite{}` invocations do, and a citation in the wrong place is worse than a missing one (see `citation-audit`'s `wrong_context` failure mode).

## When This Skill Triggers

Run this skill when **any** of the following is true:

- `paper/GAP_REFERENCES.md` exists (written by `/paper-write` Step 8 hard gate).
- `paper/PAPER_IMPROVEMENT_LOG.md` contains a `## GAP_REFERENCES (Round N)` block (written by `/auto-paper-improvement-loop` Step 4.6).
- `paper/CITATION_AUDIT.json` has `reason_code: under_min_references`.
- `paper/PAPER_PLAN.md` contains a `GAP_REFERENCES` block from `/paper-plan` Step 5.
- The user says any variant of "补引用" / "reference count is low" / "paper blocked by floor".

Skip this skill if the floor is already met — adding citations for the sake of adding them dilutes the bibliography and invites `wrong_context` findings later.

## Constants

- **MIN_REFERENCES = `30`** — Floor inherited from `/paper-writing`. Override via `— target: <N>`. Never silently lower; the floor exists so reviewers can trust the related-work coverage.
- **PAPER_DIR = `paper/`** — Default paper directory. First positional argument overrides.
- **DENSITY_FLOORS** — Per-section sanity thresholds (used to find the **structural** gap, not as hard gates):
  - Related Work ≥ 15 cite invocations
  - Introduction ≥ 8
  - Method (per comparator subsection) ≥ 2
  - Experiments (per baseline) ≥ 1
- **DBLP_BIBTEX = true** — Inherited from `/paper-write`. New entries must come from DBLP/CrossRef/arXiv real records; never LLM-generated bib.
- **REAL_CITE_REQUIRED = true** — Every new bib entry MUST be referenced by at least one `\cite{}` in the body before this skill declares done. Bare bib entries don't count toward the floor and will be pruned by `--uncited`.

## Inputs

1. **Paper directory** with `main.tex`, `sections/*.tex`, and a `.bib` file.
2. **Whichever gap report triggered the run** — read it to learn the current count, target floor, and any per-section hints the upstream gate left.
3. **Optional: `NARRATIVE_REPORT.md`** — useful for understanding what the paper actually claims, so the new citations attach to real load-bearing sentences.

## Workflow

### Phase 0: Identify the Gap Source

Read whichever of these exists (in priority order — they may overlap):

```bash
ls paper/GAP_REFERENCES.md \
   paper/PAPER_IMPROVEMENT_LOG.md \
   paper/CITATION_AUDIT.json \
   paper/PAPER_PLAN.md 2>/dev/null
```

Extract: **current cite-key count**, **target floor**, **deficit = floor − current**, and any **section-level hints** the upstream gate noted (e.g., "Related Work has only 4 cites").

If no gap report exists but the user invoked this skill anyway, run the count yourself before doing anything else — you may discover the floor is already met and this skill is a no-op.

### Phase 1: Count + Density Map (Diagnose Where to Add)

Don't sprinkle citations evenly. Find the **structurally under-cited sections** and target them.

```bash
# Total unique cite-keys (the canonical floor metric)
TOTAL=$(grep -rhoE '\\(cite|citep|citet|citeauthor|citeyear)\{[^}]*\}' paper/ \
  | sed -E 's/\\(cite|citep|citet|citeauthor|citeyear)\{//; s/\}$//' \
  | tr ',' '\n' \
  | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' \
  | grep -v '^$' \
  | sort -u \
  | wc -l)
echo "Current unique cite-keys: ${TOTAL}"

# Per-file density — find which sections are under-cited
echo "--- Per-section cite density ---"
for f in paper/sections/*.tex paper/main.tex; do
  [ -f "$f" ] || continue
  c=$(grep -oE '\\(cite|citep|citet)\{[^}]*\}' "$f" 2>/dev/null | wc -l)
  printf "%4d  %s\n" "$c" "$f"
done | sort -n
```

Compare each section against `DENSITY_FLOORS`. Sections under threshold are your **primary targets**; sections above threshold are off-limits unless reviewers explicitly complained about coverage there. If `— focus: <section>` was passed, restrict to that section.

Write a short plan to `paper/.aris/reference-backfill/plan.md`:

```markdown
# Reference Backfill Plan

- Current: 24 / 30 (deficit: 6)
- Primary targets:
  - sections/6.related.tex (8 cites; below 15 floor — needs ≥ 5 more)
  - sections/1.intro.tex (3 cites; below 8 floor — needs ≥ 2 more)
- Topics to search (derived from section headings + claim text):
  - "self-refine vs cross-model review"
  - "evidence compilation for procedural reasoning"
  - ...
```

### Phase 2: Extract Load-Bearing Claims (Where Each Citation Will Land)

For each target section, pull the sentences that **make a claim about prior work** but don't yet cite anything. These are the "citation magnets" — the legitimate spots a new reference can attach to.

```bash
# Heuristic: claim verbs + no \cite on the same sentence
grep -nE '\b(prior work|previous|existing|established|recent|standard|well[- ]known|widely used|conventional|state[- ]of[- ]the[- ]art|SoTA|baseline)\b' paper/sections/6.related.tex \
  | grep -vE '\\(cite|citep|citet)'
```

Eyeball the matches — the goal is **a sentence that is currently making an unsupported empirical or attributive claim**. These are where new citations belong. If a section has no such sentences, adding citations there is filler — go back to Phase 1 and pick a different section, or rewrite the section to actually engage with prior work.

Record the (file, line, claim) triples in `plan.md` under "Citation magnets".

### Phase 3: Search — Pick the Right Backend per Topic

Each topic gets routed to one or more of these search skills via the `Skill` tool. Pick by domain, not habit:

| Topic domain | Skill | Why |
|---|---|---|
| ML / NLP / CV / RL — generic | `/research-lit "<topic>"` | Default. arXiv + Semantic Scholar coverage, fast. |
| Communications / wireless / networking / NTN / Wi-Fi / cellular / MAC/PHY | `/comm-lit-review "<topic>"` | Routes to IEEE Xplore / ScienceDirect / ACM DL first — much higher hit rate than arXiv-only sources. |
| Citation graph, institutional affiliations, funding, recent works missing from arXiv | `/openalex "<topic>"` | OpenAlex covers a wider corpus than arXiv. |
| Web-fresh / hard-to-find / cross-disciplinary | `/gemini-search "<topic>"` | Use as a backstop when the above leave the topic under-covered. |
| Single arXiv ID you want to vet before citing | `/alphaxiv <id>` | Single-paper deep-dive; NOT a discovery tool. |

Run searches **in parallel** when topics are independent — multiple `Skill` calls in one message, not serial. For each topic, ask the search skill for ~5–10 candidates with title + venue + year + 1-line "what this paper actually argues" — that last field is what lets you avoid `wrong_context` citations.

**Search prompt template** (passed as `args` to the search skill):

```
Topic: <topic, e.g., "cross-model review for hallucination detection in LLM reasoning">
Need: <N> candidate papers, ranked by relevance.
For each: title, venue, year, arXiv/DOI, AND a 1-sentence summary of what the paper ACTUALLY argues (so we don't cite it for a claim it doesn't make).
Prefer: published versions over preprints; recent (last 3 years) where the field is active.
```

### Phase 4: Select Candidates (the gating step)

For each candidate, ask three questions before keeping it:

1. **Does the paper's actual contribution match the claim it would support?**
   If the claim is "self-refine produces correlated errors" and the candidate is Self-Refine (Madaan et al. 2023), the answer is NO — Self-Refine demonstrates iterative improvement, not correlated errors. Drop it. (This is the canonical `wrong_context` failure that `citation-audit` will catch later; catching it here saves a round-trip.)
2. **Is the venue/year credible?** Skip workshop posters and unpublished preprints for load-bearing claims unless nothing better exists.
3. **Do we already cite this paper?** Run `grep -r "\\cite{<candidate-key>}" paper/` — if yes, this candidate doesn't increase the unique count; pick something else.

Keep the survivors. If after filtering you have fewer than the deficit, run more searches (Phase 3) on adjacent topics — don't lower the bar.

### Phase 5: Fetch Real BibTeX

For each surviving candidate, fetch the real entry from DBLP or CrossRef. **Never LLM-generate bib entries** — citation-audit will flag hallucinated authors/years.

```bash
# DBLP (preferred for CS venues)
curl -s "https://dblp.org/search/publ/api?q=<title-or-author-year>&format=json" | jq .

# CrossRef (good for journals)
curl -s "https://api.crossref.org/works?query.bibliographic=<title>&rows=3" | jq .

# arXiv API (for preprints — but verify the published version exists first)
curl -s "https://export.arxiv.org/api/query?search_query=ti:<title>"
```

The `paper-write` skill has `DBLP_BIBTEX = true` machinery — reuse its helpers if present (`grep -r "dblp" paper-write/`). Append the new BibTeX entries to the project's `.bib` file, **deduplicating by DOI/arXiv-ID** to avoid creating two keys for the same paper.

### Phase 6: Insert `\cite{}` Calls

For each new bib entry, find its corresponding "citation magnet" sentence from Phase 2 and insert the cite — but **rewrite the sentence so the citation is doing work**, not just appended.

**Bad:**
```latex
Prior work has explored related directions \citep{newkey2024}.
```

**Good:**
```latex
\citet{newkey2024} introduce a cross-model verifier that catches single-LLM
hallucinations missed by self-feedback, demonstrating that independent reviewers
reduce false-positive rates by ~30\% in our setting.
```

The "good" version tells the reader **what the cited paper does** and **why it's relevant here** — this is what survives a `citation-audit` `wrong_context` pass.

If a candidate's claim doesn't fit cleanly into any magnet sentence, **rewrite the surrounding paragraph** to engage with the prior work, or drop the candidate. Don't manufacture sentences just to host a `\cite{}`.

### Phase 7: Recompile

```bash
cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Confirm:
- 0 undefined references
- 0 undefined citations
- BibTeX picked up every new key (check `paper/main.bbl`)

If `bibtex` errors on a malformed entry, fix the bib (likely a missing brace or stray Unicode from the search result) and rerun. **Do not** silently drop the broken entry — that's how you slip back below the floor without noticing.

### Phase 8: Re-verify the Floor (the closing gate)

Run the same count from Phase 1 and confirm `count ≥ target`:

```bash
TOTAL=$(grep -rhoE '\\(cite|citep|citet|citeauthor|citeyear)\{[^}]*\}' paper/ \
  | sed -E 's/\\(cite|citep|citet|citeauthor|citeyear)\{//; s/\}$//' \
  | tr ',' '\n' \
  | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' \
  | grep -v '^$' \
  | sort -u \
  | wc -l)
echo "Post-backfill unique cite-keys: ${TOTAL} (target: ${MIN_REFERENCES})"
```

If still below target: loop back to Phase 1 — but first check that every newly added bib entry is actually `\cite{}`d (`comm -23 <(bib keys) <(\cite keys)` to spot orphans). Orphan entries are the most common reason this gate stalls.

Then re-trigger the **originating gate** to confirm it now passes:

| Originating gate | Re-trigger |
|---|---|
| `/paper-plan` Step 5 | Re-run `/paper-plan` (cheap; recomputes Citation Plan) |
| `/paper-write` Step 8 | Re-run only the Reference Floor Gate snippet from `/paper-write` Step 8 |
| `/citation-audit` `under_min_references` | Re-run `/citation-audit` (or just the count check; full re-audit is expensive — only redo it if the user is at submission time) |
| `/auto-paper-improvement-loop` Step 4.6 | Re-run `/auto-paper-improvement-loop` from the round that halted |

### Phase 9: Manifest

Write `paper/.aris/reference-backfill/MANIFEST.md`:

```markdown
# Reference Backfill Manifest

- **Run date**: <UTC ISO-8601>
- **Originating gate**: <path to gap report>
- **Pre-count**: 24
- **Target floor**: 30
- **Post-count**: 31
- **New entries** (key → file:line where first cited):
  - newkey2024foo → sections/6.related.tex:42
  - ...
- **Sections touched**: sections/1.intro.tex, sections/6.related.tex
- **Searches run**: /research-lit (3 topics), /openalex (1 topic)
- **Re-verified**: yes (PASS)
```

This manifest is what `/citation-audit` and the improvement loop will consult later if they wonder where a citation came from.

## Anti-Patterns (don't do these)

- ❌ **Lowering `MIN_REFERENCES` to pass the gate.** The floor is set at `/paper-writing` for a reason; lowering it here doesn't fix the underlying coverage problem and will be caught by the next gate down the line. Use `— target: <N>` only with explicit user sign-off for genuinely short papers.
- ❌ **Adding bib entries without `\cite{}`.** Orphan entries don't count toward the floor and `--uncited` will recommend pruning them — net effect: zero progress.
- ❌ **Sprinkling one new cite into every section.** Reviewers notice. Concentrate new citations where the structural gap actually is (Phase 1 density map).
- ❌ **LLM-generated bib entries.** They hallucinate authors, years, and venues. Always go through DBLP / CrossRef / arXiv. `paper-write`'s `DBLP_BIBTEX = true` is the canonical path.
- ❌ **Citing a paper for a claim it doesn't make.** This is `wrong_context` — caught by `/citation-audit` as `FAIL`. Phase 4's first filter exists specifically to prevent this.
- ❌ **Skipping Phase 8.** If you don't re-verify, the originating gate will just re-fire and you'll have churned the bib for nothing.

## Key Rules

- **Diagnose before searching.** Phase 1's density map tells you where to add. Without it, you're guessing.
- **Searches run in parallel.** Multiple `Skill` calls in one message — independent topics shouldn't be serial.
- **Every new bib entry needs a real `\cite{}` and a sentence that does work.** A citation that doesn't earn its place is worse than no citation.
- **Re-verify the originating gate, not just the count.** Different gates have different decision tables (e.g., `citation-audit` blends count with `wrong_context` and `metadata_drift`).
- **Idempotent.** Re-running this skill after a partial pass should pick up from the current state — read `MANIFEST.md` if it exists and skip work already done.

## Output Contract

- `paper/.aris/reference-backfill/plan.md` — Phase 1 + Phase 2 plan
- `paper/.aris/reference-backfill/MANIFEST.md` — Phase 9 final manifest
- Mutations: `paper/<references>.bib` (appended), `paper/sections/*.tex` (cite insertions + sentence rewrites)
- No mutations to `NARRATIVE_REPORT.md` (read-only, per the broader pipeline's clean-handoff principle)

## See Also

- `/research-lit`, `/comm-lit-review`, `/openalex`, `/gemini-search`, `/alphaxiv` — the search backends this skill orchestrates
- `/paper-write` — Step 8 Reference Floor Gate (originating gate)
- `/citation-audit` — `under_min_references` reason code + `wrong_context` finding
- `/auto-paper-improvement-loop` — Step 4.6 Reference Floor Regression check
- `/paper-plan` — Step 5 Citation Scaffolding (earliest gap report)

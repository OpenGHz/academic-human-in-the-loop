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
- **PAPER_LIBRARY** — Local path(s) for paper retrieval. Resolution order (first non-empty wins):
  1. `— paper-library: <path>` CLI override (comma-separated paths accepted).
  2. **Path-like tokens in the user's free-form prompt** — see "Prompt path extraction" below. Catches the common case where the user *says* "我的文献在 `~/my-papers/` 里" without using the formal flag. The skill echoes the extracted path(s) back in `plan.md` and proceeds; the user can correct in-band by re-invoking with `— paper-library: <correct path>`.
  3. `## Paper Library` section in `CLAUDE.md` (project- or user-level).
  4. `papers/` or `literature/` under the paper directory.
  5. None — skip the local phase entirely and go straight to web.

**Prompt path extraction** (resolution step 2): scan `$ARGUMENTS` for tokens matching any of:
- `~/...` or `$HOME/...`
- absolute paths starting with `/`
- relative paths starting with `./` or `../`
- bare directory names ending with `/` that exist on disk relative to CWD
- `.bib` file paths

For each candidate, verify the path actually exists (`test -e <path>`) before adopting it. Silently ignore non-existent tokens — users often paste fragments. Always log the extracted paths to `plan.md` under `## PAPER_LIBRARY resolution` so the user can audit; if extraction is ambiguous (multiple candidates of unclear intent), pick the first existing one and note the alternates as "candidates not selected".
- **SEARCH_STRATEGY = `local_first`** — Two-pass routing: pass 1 hits Zotero / Obsidian / local PDFs only; pass 2 hits the web only for topics where pass 1 returned fewer than `LOCAL_HITS_THRESHOLD` usable candidates. Override with `— strategy: web_only` (skip local) or `— strategy: parallel` (run both passes concurrently — faster but burns more web quota and risks redundant hits).
- **LOCAL_HITS_THRESHOLD = `3`** — Per-topic minimum from the local pass before the web pass is skipped for that topic. Set per topic, not globally — a topic with 4 strong local hits skips the web; a sibling topic with 0 local hits still gets the web pass.

## Inputs

1. **Paper directory** with `main.tex`, `sections/*.tex`, and a `.bib` file.
2. **Whichever gap report triggered the run** — read it to learn the current count, target floor, and any per-section hints the upstream gate left.
3. **Optional: `NARRATIVE_REPORT.md`** — useful for understanding what the paper actually claims, so the new citations attach to real load-bearing sentences.
4. **`<paper-dir>/PAPER_PREFERENCES.md`** (if present) — read at Phase 0. Bullets in `## Notation`, `## Hard don'ts`, and `## Section-specific` may forbid specific citations or constrain how new ones are introduced (e.g., "do not cite Chen 2024 — wrong context", "Related Work must keep prose form, not table"). The search filter (Phase 4) and insertion (Phase 6) must respect these bullets. Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md). Missing file → treat as empty.

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

### Phase 3: Search — Local-First, Web for the Gaps

Default strategy (`SEARCH_STRATEGY = local_first`) is a two-pass routing: **pass 1** exhausts the user's existing materials (Zotero, Obsidian, local PDFs); **pass 2** hits the web only for topics that pass 1 couldn't satisfy. Reason: papers the user already has on disk are almost always more relevant than fresh web hits — they were curated for a reason — and they cost nothing in quota or latency.

Skip directly to pass 2 only if `— strategy: web_only` was passed or if `PAPER_LIBRARY` resolved to nothing AND no Zotero/Obsidian MCP is available.

#### Pass 1 — Local sources (Zotero / Obsidian / on-disk PDFs)

Drive this through `/research-lit` with `— sources: zotero, obsidian, local` (or the `comm-lit-review` equivalent for communications topics). These skills already handle the local plumbing — MCP availability detection, PDF text extraction, BibTeX export — so don't re-implement it here. Pass `PAPER_LIBRARY` explicitly so the search skill knows which directory to scan.

**Pass 1 prompt template:**

```
Topic: <topic>
Need: <deficit> candidate papers, ranked by relevance.
Local only — skip web sources. Use Zotero, Obsidian, and local PDFs at:
  <PAPER_LIBRARY>
For each: title, venue, year, BibTeX key (if already in Zotero/local bib), AND a
1-sentence summary of what the paper ACTUALLY argues (so we don't cite it for a
claim it doesn't make).
```

Invoked via `Skill` tool with `args: <topic> — sources: zotero, obsidian, local — paper library: <PAPER_LIBRARY>`.

**Why these candidates are especially valuable:** if a paper is already in Zotero, it likely already has a BibTeX key the user maintains — reuse that key instead of generating a new one (avoids `wrong_context` from author-name mismatches and keeps the user's bib ecosystem consistent). Annotations and Obsidian notes also tell you *how the user thinks about this paper*, which makes Phase 6 sentence rewrites much more accurate.

Record per-topic results in `plan.md` as `local_hits`:

```markdown
- Topic: "cross-model review for hallucination detection"
  - local_hits: 4 (3 from Zotero, 1 from papers/ dir)
  - web pass needed: no (≥ LOCAL_HITS_THRESHOLD)
```

#### Pass 2 — Web sources (only for under-covered topics)

For each topic where `local_hits < LOCAL_HITS_THRESHOLD`, run a web search. Route by domain — habit-pick is a common source of low-quality coverage:

| Topic domain | Skill | Why |
|---|---|---|
| ML / NLP / CV / RL — generic | `/research-lit "<topic>" — sources: web` | arXiv + Semantic Scholar coverage, fast. |
| Communications / wireless / networking / NTN / Wi-Fi / cellular / MAC/PHY | `/comm-lit-review "<topic>"` | Routes to IEEE Xplore / ScienceDirect / ACM DL first — much higher hit rate than arXiv-only sources for these fields. |
| Citation graph, institutional affiliations, funding, recent works missing from arXiv | `/openalex "<topic>"` | OpenAlex covers a wider corpus than arXiv. |
| Web-fresh / hard-to-find / cross-disciplinary | `/gemini-search "<topic>"` | Backstop when the above leave the topic under-covered. |
| Single arXiv ID you want to vet before citing | `/alphaxiv <id>` | Single-paper deep-dive; NOT a discovery tool. |

Run pass 2 searches **in parallel** when topics are independent — multiple `Skill` calls in one message, not serial.

**Pass 2 prompt template** (passed as `args`):

```
Topic: <topic>
Need: <deficit_for_this_topic> candidate papers, ranked by relevance.
For each: title, venue, year, arXiv/DOI, AND a 1-sentence summary of what the paper ACTUALLY argues (so we don't cite it for a claim it doesn't make).
Prefer: published versions over preprints; recent (last 3 years) where the field is active.
Already-cited (skip these): <list keys already in our bib>
```

The "already-cited" list is essential — otherwise the web pass keeps surfacing papers you already have, wasting candidates that don't lift the unique-key count.

#### Strategy overrides

| Flag | Behavior | When to use |
|---|---|---|
| `— strategy: local_first` (default) | Pass 1 then pass 2 only for gaps | Routine backfill; minimizes quota |
| `— strategy: web_only` | Skip pass 1 | When the user explicitly wants fresh literature, or `PAPER_LIBRARY` is empty |
| `— strategy: parallel` | Both passes concurrently | Time-critical (e.g., submission deadline) — accept the redundancy cost |
| `— strategy: local_only` | Pass 1 only, fail the phase if deficit unmet | Air-gapped or no-web environments — surfaces explicitly that the user needs to expand their local library |

### Phase 4: Select Candidates (the gating step)

For each candidate, ask three questions before keeping it:

1. **Does the paper's actual contribution match the claim it would support?**
   If the claim is "self-refine produces correlated errors" and the candidate is Self-Refine (Madaan et al. 2023), the answer is NO — Self-Refine demonstrates iterative improvement, not correlated errors. Drop it. (This is the canonical `wrong_context` failure that `citation-audit` will catch later; catching it here saves a round-trip.)
2. **Is the venue/year credible?** Skip workshop posters and unpublished preprints for load-bearing claims unless nothing better exists.
3. **Do we already cite this paper?** Run `grep -r "\\cite{<candidate-key>}" paper/` — if yes, this candidate doesn't increase the unique count; pick something else.

Keep the survivors. If after filtering you have fewer than the deficit, run more searches (Phase 3) on adjacent topics — don't lower the bar.

### Phase 5: Fetch Real BibTeX

For each surviving candidate, fetch the real entry from DBLP or CrossRef. **Never LLM-generate bib entries** — citation-audit will flag hallucinated authors/years.

**Local-pass candidates** typically come pre-keyed (Zotero exports a BibTeX entry; on-disk PDFs often live next to a `.bib`). Reuse the existing key verbatim — making up a new key for a paper the user already maintains in Zotero creates two records for one paper and breaks downstream syncs. Only fall through to DBLP/CrossRef for candidates that **don't** already have a key in the user's ecosystem.

#### Tool choice (read before you run anything)

**Use `Bash` + `curl` for these endpoints. Do NOT use `WebFetch`.**

`WebFetch` is gated by Anthropic-side domain safety verification and frequently returns `Unable to verify if domain <host> is safe to fetch` for `arxiv.org`, `dblp.org`, `api.crossref.org`, `export.arxiv.org`, `openreview.net`, and similar academic API hosts. That failure is **server-side** — a local proxy will not fix it. `curl` runs in your local shell and bypasses that gate entirely, so it is the correct tool for every bib-fetch in this phase.

Also: `WebFetch` returns HTML-summarized prose, not structured BibTeX. Even when it succeeds on an arXiv abstract page, it cannot give you `@inproceedings{...}` with venue/pages/DOI — only the JSON/XML API endpoints below can.

If `curl` itself fails (DNS / timeout / connection refused — a real network issue), enable the local terminal proxy once before declaring failure:

```bash
export {HTTP_PROXY,HTTPS_PROXY,ALL_PROXY,http_proxy,https_proxy,all_proxy}=http://127.0.0.1:7890
```

Then retry the same `curl`. Only escalate to "network unreachable" if `curl` still fails with the proxy.

#### Endpoints (in order of preference)

```bash
# DBLP — preferred for CS venues. Returns published-version metadata (conf/journal,
# year, BibTeX key) AND the arXiv preprint record in one query, so you can prefer
# the published version per Phase 4.
curl -s "https://dblp.org/search/publ/api?q=<title-or-author-year>&format=json" | jq .

# Fetch the BibTeX itself from DBLP by record key (e.g. conf/iclr/WangZWLSWH0025):
curl -s "https://dblp.org/rec/<key>.bib"

# CrossRef — good for journals; returns DOI + full citation metadata as JSON.
curl -s "https://api.crossref.org/works?query.bibliographic=<title>&rows=3" | jq .

# arXiv API — for preprints only, AFTER confirming no published version exists
# in DBLP/CrossRef. Use `export.arxiv.org/api/query`, NEVER `arxiv.org/abs/<id>`
# (the latter is an HTML page, not an API).
curl -s "https://export.arxiv.org/api/query?search_query=ti:<title>"
```

Run these in parallel across candidates — one `Bash` message with multiple `curl` calls — not serially.

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
- ❌ **Using `WebFetch` on `arxiv.org` / `dblp.org` / `crossref.org` / `openreview.net` in Phase 5.** It hits Anthropic-side domain safety verification and returns `Unable to verify if domain X is safe to fetch` — a server-side block that a local proxy cannot bypass. It also returns HTML prose, not structured BibTeX. Use `Bash` + `curl` against the API endpoints in Phase 5 instead. `WebFetch` is fine for arbitrary lab/blog/news URLs where you genuinely need an HTML page summarized, but it is the wrong tool for bib metadata.
- ❌ **Citing the arXiv preprint when DBLP shows a published version.** DBLP's response often returns both records for the same paper (e.g., `conf/iclr/...` and `journals/corr/abs-XXXX.YYYYY`). Phase 4 mandates the published key; the preprint record only exists to confirm identity.

## Key Rules

- **Diagnose before searching.** Phase 1's density map tells you where to add. Without it, you're guessing.
- **Local before web.** Pass 1 (Zotero / Obsidian / on-disk PDFs) runs first; pass 2 (web) runs only for topics under `LOCAL_HITS_THRESHOLD`. Local hits are higher quality (the user already curated them) and free.
- **Searches run in parallel within a pass.** Multiple `Skill` calls in one message — independent topics shouldn't be serial.
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

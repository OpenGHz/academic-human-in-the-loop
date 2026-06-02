---
name: novelty-check
description: Verify research idea novelty against recent literature. Use when user says "查新", "novelty check", "有没有人做过", "check novelty", or wants to verify a research idea is novel before implementing.
argument-hint: "[method-or-idea-description]"
allowed-tools: Bash(*), WebSearch, WebFetch, Grep, Read, Glob, Edit, Write, mcp__codex__codex
---

# Novelty Check Skill

Check whether a proposed method/idea has already been done in the literature: **$ARGUMENTS**

## Constants

- REVIEWER_MODEL = `gpt-5.6-sol` — Model used via Codex MCP. Must be an OpenAI model (e.g., `gpt-5.6-sol`, `o3`, `gpt-4o`)
- **PRIOR_ART = none** — Optional pre-loaded prior-art set that seeds the check. When supplied, these papers are treated as known prior art in **Phase A.5** *before* the skill runs its own web search, so a prior `/research-lit` survey (or any curated list) widens coverage and reduces missed prior work. Accepts a file path (`references.bib`, a landscape `.md`, or a `research-wiki/` directory) or an inline comma/semicolon-separated paper list. Default `none` = behave exactly as before (web-only, self-contained).
- **OUTPUT = `idea-stage/NOVELTY_<slug>.md`** — Where the standalone Novelty Report (Phase D.6) is written, `<slug>` derived from the idea. Saving is the default (with a timestamped copy per output-versioning). Suppressed when running composed under an orchestrator, or with `— no-save`.

> 💡 Overrides:
> - `/novelty-check "idea" — prior-art: refine-logs/landscape.md` — seed from a saved literature survey
> - `/novelty-check "idea" — prior-art: research-wiki/` — seed from the persistent wiki
> - `/novelty-check "idea" — prior-art: references.bib` — seed from an existing bib
> - `/novelty-check "idea" — prior-art: "Smith 2025 (arXiv 2501.01234); Lee 2024 NeurIPS"` — inline list
> - `/novelty-check "idea" — output: refine-logs/NOVELTY.md` — custom standalone report path
> - `/novelty-check "idea" — no-save` — print the report only, write no standalone file
> - `/novelty-check "idea" — composed: idea-stage/IDEA_REPORT.md` — fold into an orchestrator's report instead of a standalone file

## Instructions

Given a method description, systematically verify its novelty:

### Phase A: Extract Key Claims
1. Read the user's method description
2. Identify 3-5 core technical claims that carry the claimed delta:
   - What is the method?
   - What problem does it solve?
   - What is the mechanism?
   - What makes it different from obvious baselines?

### Phase A.5: Load Supplied Prior Art (only when `— prior-art:` is set)

**Skip this phase entirely if `PRIOR_ART = none` (default).** When a `— prior-art:` value is supplied, load it as a *seed* prior-art set **before** searching:

1. **Resolve the source**:
   - **File** (`*.bib` / `*.md` / `*.json`): `Read` it. For `references.bib`, extract title / author / year / `eprint` / `doi` per entry. For a landscape `.md` (e.g. from `/research-lit`), `Grep` the paper table and citation lines.
   - **Directory** (e.g. `research-wiki/`): `Glob research-wiki/papers/**/*.md` and read each page's frontmatter (title, arXiv id, thesis).
   - **Inline list**: parse the comma/semicolon-separated references directly.
2. **Build the seed set**: `{title, arxiv_id|doi, one-line claim}` for each supplied paper. These are *candidate* prior art, not yet adjudicated.
3. **Map onto core claims** from Phase A: for each claim, note which supplied papers already look related, so Phase B's search and Phase C's delta analysis focus on the real overlap.

> The supplied set **widens** the starting coverage — it is **not a ceiling**. Phase B still runs its own multi-source web search to catch what the supplied survey missed, and Phase C adjudicates novelty against the **union** of supplied + newly-found papers. Never treat "not in the supplied set" as "novel."

### Phase B: Multi-Source Literature Search
For EACH core claim, search using ALL available sources:

1. **Web Search** (via `WebSearch`):
   - Search arXiv, Google Scholar, Semantic Scholar
   - Use specific technical terms from the claim
   - **Query along three axes — not just reworded synonyms. Missed prior work most often uses different terminology than your method name:**
     1. **Method axis** — your method/technique name and its close variants
     2. **Problem axis** — the problem/task itself, phrased as someone solving it *without* your method
     3. **Alias axis** — known aliases, neighboring task names, and the terms competing sub-communities would use
   - Run **at least one query per axis per claim** (≥3 total); add more reformulations when results look thin
   - Include year filters for 2024-2026

2. **Known paper databases**: Check against:
   - ICLR 2025/2026, NeurIPS 2025, ICML 2025/2026
   - Recent arXiv preprints (2025-2026)

3. **Read abstracts**: For each potentially overlapping paper, WebFetch its abstract and related work section

4. **Capture FULL metadata at first contact — do not defer.** The moment a paper looks like it will enter the Closest Prior Work table or the bibtex, `WebFetch` its **arXiv abstract page** (`https://arxiv.org/abs/<id>`) and record the **exact title** and the **complete author list, all authors in order** — not "first author + others", not the ID alone. WebSearch result snippets routinely omit authors; that is a retrieval gap, not a reason to leave the field blank. **It is laziness, not discipline, to write a paper into the report with an ID but no authors and plan to "backfill later".** If a `WebFetch` fails (socket/timeout), retry once (and try the local proxy per global prefs for `Bash`-based fetches); only if it still fails may you mark the author field `[authors-unverified: fetch failed]` and say so explicitly in the report.

### Phase C: Cross-Model Verification
Call REVIEWER_MODEL via Codex MCP (`mcp__codex__codex`) with xhigh reasoning.
When the method description plus the Phase-B paper list is more than a short
note, avoid pasting it inline into the MCP prompt. Write a dossier file such as
`NOVELTY_DOSSIER.md` (or a project-local equivalent) containing the method
description, core claims, candidate papers, and the exact questions below, then
send only the file path:
```
mcp__codex__codex:
  model: gpt-5.6-sol
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Read the novelty dossier at <absolute path to NOVELTY_DOSSIER.md> and
    follow all instructions in it.
```
Dossier contents should include:
- The proposed method description
- All papers found in Phase B
- Ask: "Is this method novel? What is the closest prior work? What is the delta?"
- The NOVELTY VERDICT LIMITS block below, verbatim — the reviewer judges under it

### The verdict limits

Copy this block **verbatim** into the reviewer's briefing; the report in
Phase D is judged under it too.

```
=== NOVELTY VERDICT LIMITS (these bound how you judge, never how widely you search) ===
Search exhaustively; judge calibrated. Two failures waste months equally:
passing an idea a published paper already contains, and killing a viable idea
because the territory has neighbors.
1. Proximity is information, not a verdict. Someone working nearby goes in the
   report; it is not by itself a reason to reject.
2. ABANDON has exactly one qualification: a specific published paper already
   contains this result — name that paper. No named paper, no ABANDON.
3. Crowded-but-deltaed is PROCEED: state the delta in one sentence a reviewer
   could verify. Thin or contested delta is PROCEED WITH CAUTION — say what
   would make it carry, not why it should die. CAUTION is not a safe middle:
   if you cannot name the specific thing that makes the delta thin, the
   verdict is PROCEED.
4. Concurrent or competing work is not a veto. That is a race — report it and
   let the user decide whether to run it.
5. A direct attack on a central problem is legitimate novelty when nobody has
   executed it well. "This area is hot" does not mean "this area is taken."
6. This check is an early gate, never the last one — more triage, pilots, or
   external review still stand between any idea and a paper, whatever order
   this run uses. A wrongly passed idea dies cheaply at one of them; a wrongly
   killed idea is never seen again. When torn between two verdicts, choose the
   more permissive one.
Say plainly when an idea clears the check. Do not manufacture overlap.
```

### Phase D: Novelty Report
Output a structured report:

```markdown
## Novelty Check Report

### Proposed Method
[1-2 sentence description]

### Core Claims
1. [Claim 1] — Closest: [paper] — What stays unknown or different: [delta]
2. [Claim 2] — Closest: [paper] — What stays unknown or different: [delta]
...

### Closest Prior Work
| Paper | Year | Venue | Overlap | Key Difference |
|-------|------|-------|---------|----------------|

### Overall Novelty Assessment
- Score: X/10 (anchor: 5/10 = has clear neighbors but a defensible delta worth
  a pilot; reserve 1-3 for results a named published paper already contains)
- Recommendation: PROCEED / PROCEED WITH CAUTION / ABANDON (per the verdict
  limits: crowded-but-deltaed ground is PROCEED; ABANDON must name the paper)
- Key differentiator: [what makes this unique, if anything]
- Risk: [what a reviewer would cite as prior work]

### Suggested Positioning
[State the delta honestly in one sentence a reviewer could verify]
```

### Phase D.5: Patch the Literature Landscape (DEFAULT — whenever the check ran against a landscape `.md`)

**This is default behavior, not opt-in.** If the novelty check was seeded from or pointed at a literature-landscape Markdown file — i.e. the argument is such a file, `— prior-art:` resolved to a landscape `.md`, or the user's open/working file is one (e.g. `literature/related_work.md`, a `/research-lit` output) — then **write the findings back into that file by default**, without waiting to be asked. A novelty check that surfaces a closer competitor than the landscape contains has *already done the work*; leaving the landscape stale wastes it and risks the next reader re-deriving a now-falsified "this space is empty" claim.

Patch the file with three edits, mirroring the file's existing style and structure:
1. **A new "Round-N additions" block** (continue the file's existing round numbering) listing every newly-found paper not already in the landscape, grouped into the file's themes (or a new theme if it's a genuinely new line), each row with venue/year, one-line method, relevance/delta to the idea, and a verified arXiv ID + status mark.
2. **Re-scope the synthesis honestly.** If the check found a closer neighbor than the landscape's stated closest prior work, update the "closest neighbor"/"gaps" framing so it reflects reality — including *narrowing* any gap claims the new paper undercuts. Do not only add; **correct**.
3. **Append verified bibtex entries** for the new papers — with **complete author lists** captured in Phase B step 4 (never `author={others}`). Also opportunistically fix any `author={others}` placeholders you notice in pre-existing entries while you are in the file.
4. **Update the file's provenance header** with a one-line note: which skill updated it, the date, the headline finding, and the cross-model score.

**Opt-out / scope:** skip this phase only if the user passed `— no-patch`, the check was a bare inline idea with no landscape file in play, or the landscape file is read-only/not writable. When skipping because there is no file, offer in the report to create one. Never silently overwrite content that contradicts the new findings — *correct* it in place and let the diff show the change.

### Phase D.6: Save the Novelty Report (standalone by default; fold in when composed)

The Phase D report is the verdict artifact — PROCEED/ABANDON, the closest-prior-work table, and the positioning a reviewer will test you on. Don't let it evaporate into the conversation. **This is distinct from Phase D.5:** D.5 patches a pre-existing *input* landscape file; this step persists *this check's own report* (and is the only persistence path when there is no input landscape and no `research-wiki/`).

- **Standalone (DEFAULT — no `— composed:` directive):** Write the Phase D report to `OUTPUT` (default `idea-stage/NOVELTY_<slug>.md`, or the `— output:` path). Follow [`shared-references/output-versioning.md`](../shared-references/output-versioning.md): write a timestamped `NOVELTY_<slug>_<YYYYMMDD_HHmmss>.md` (get the stamp via `date +%Y%m%d_%H%M%S`) **and** the fixed-name `NOVELTY_<slug>.md`. Create the parent dir if needed. Skip the write only with `— no-save`.
- **Composed (only when `— composed: <canonical-report-path>` is passed):** Do **not** write a standalone file. Return the report's conclusions (verdict, closest prior work, positioning) for the orchestrator to fold into its canonical deliverable, citing the `.aris/traces/…` path rather than duplicating the reviewer transcript. Per [`shared-references/output-composition.md`](../shared-references/output-composition.md), never infer composed mode from a report file merely existing on disk — the directive must be explicit, and `— standalone` always wins a conflict.

Phase E (wiki ingest) and Review Tracing run in **both** modes — they are persistence/audit, not the human-facing report.

### Phase E: Persist Closest Prior Work to Research Wiki (only when `research-wiki/` exists)

**Skip entirely (no action, no error) if `research-wiki/` is absent.** When it exists, persist the **Closest Prior Work** this check surfaced — it is the highest-value related-work set for later paper writing (exactly what a reviewer will cite against you), and every entry already passed `verify_papers.py`, so it should compound into the wiki instead of evaporating with the verdict.

Resolve `$WIKI_SCRIPT` per the canonical chain in [`shared-references/wiki-helper-resolution.md`](../shared-references/wiki-helper-resolution.md) (Variant B — warn-and-skip):

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null)}"
WIKI_SCRIPT=".aris/tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || WIKI_SCRIPT="tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && WIKI_SCRIPT="$ARIS_REPO/tools/research_wiki.py"; }
[ -f "$WIKI_SCRIPT" ] || {
  echo "WARN: research_wiki.py not found; novelty verdict still reported, wiki ingest skipped. Fix: bash tools/install_aris.sh, export ARIS_REPO, or cp <ARIS-repo>/tools/research_wiki.py tools/." >&2
  WIKI_SCRIPT=""
}
```

When `$WIKI_SCRIPT` is non-empty, for **each** paper in the Closest Prior Work table:

```bash
# Ingest the prior-art paper (dedup handled by the helper — an existing arXiv id is skipped).
[ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
    --arxiv-id <id> --thesis "<one-line closest-prior-work summary>" --tags novelty-check,prior-art
```

- Use `--arxiv-id` when available; for venue-only papers with no arXiv mirror, pass `--title/--authors/--year [--external-id-doi <doi>]` instead (same form as `/research-lit`).
- **Do not hand-write `research-wiki/papers/<slug>.md`** — `ingest_paper` handles slug, metadata fetch, dedup, index/query_pack rebuild, and log append in one call.
- **Optional edge (best-effort):** if an idea/claim node for the idea under check already exists in the wiki, link it — direction is `idea → paper`, matching the wiki's edge convention (see [`research-wiki/SKILL.md`](../research-wiki/SKILL.md) edge table). Otherwise just ingest the papers (the prior-art set is the value) and skip the edge:
  ```bash
  [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" add_edge research-wiki/ \
      --from "idea:<slug>" --to "paper:<slug>" \
      --type competes_with \
      --evidence "<one sentence: the overlap this novelty check found>"
  ```
  `competes_with` is the edge type for closest-prior-work overlap (added to the wiki vocabulary for exactly this novelty-check use).
- If the helper is unavailable, log the gap and let `/research-wiki sync` backfill later — **never fail the novelty verdict over a wiki-ingest miss.**

### Important Rules
- Two failures waste months equally: a false novelty claim, and a viable idea
  abandoned because the territory has neighbors. Be brutally honest in both
  directions — and when an idea clears the check, say so plainly.
- Novelty can live in the combination or the finding even when every
  individual claim rates LOW — judge the idea, not each claim in isolation.
  Known parts arranged to reveal something unknown are novel.
- "Applying X to Y" earns novelty by what the application reveals — a
  non-obvious interaction, failure mode, or insight. Judge the revelation, not
  the template.
- Check both the method AND the experimental setting for novelty
- If the method is not novel but the FINDING would be, say so explicitly
- Always check the most recent 6 months of arXiv — the field moves fast
- **Metadata completeness is not optional.** Every paper that reaches the Closest Prior Work table, the wiki, or the bibtex must carry its **exact title and full author list**, fetched from the arXiv abstract page (Phase B step 4). `author={others}`, "first author et al.", or an ID with no authors is an incomplete result, not a finished one — fetch it now, never "backfill later". The only acceptable gap is an *explicitly flagged* `[authors-unverified: fetch failed]` after a real retry failed.
- **Anti-hallucination for Closest Prior Work.** Every paper in the prior-work table must pass pre-search verification via `verify_papers.py` (canonical name resolved per [`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2; 3-layer arXiv / CrossRef / Semantic Scholar fallback inside the helper itself). Policy D1 (primary + degraded-output fallback): if the helper is unresolved **or** its invocation fails, tag candidate entries `[UNVERIFIED]` and surface the uncertainty rather than dropping them. Never fabricate arXiv IDs, DOIs, or titles from memory. Full protocol in [`shared-references/citation-discipline.md`](../shared-references/citation-discipline.md) § Pre-Search Verification Protocol.

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md` (Policy C — forensic; never silently skip). Use `save_trace.sh` (resolved per the chain in `shared-references/integration-contract.md` §2) or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).

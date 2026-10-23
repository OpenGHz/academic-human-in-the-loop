---
name: paper-write
description: "Draft LaTeX paper section by section from an outline. Use when user says \"写论文\", \"write paper\", \"draft LaTeX\", \"开始写\", or wants to generate LaTeX content from a paper plan."
argument-hint: "[venue-or-section] [— style-ref: <source>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, mcp__codex__codex, mcp__codex__codex-reply, mcp__antigravity__antigravity, mcp__antigravity__antigravity-reply, mcp__grok__grok, mcp__grok__grok-reply, mcp__claude-review__review, mcp__claude-review__review_reply, mcp__claude-review__review_start, mcp__claude-review__review_reply_start, mcp__claude-review__review_status
---

# Paper Write: Section-by-Section LaTeX Generation

> **Before each reviewer slot**, follow [Selectable Reviewers](../shared-references/reviewer-backends.md):
> resolve invocation → `.aris/reviewer.json` → Claude Code default (Codex MCP)
> with `reviewer_route.py` through the canonical helper resolver, preserving this
> slot's tier, fresh contexts, source/image inputs and deterministic gates.
> Codex examples/pins below apply only to `backend=codex`; other routes use their
> own first-call/reply contract. Save the route and actual returned identity;
> unavailable selections are `REVIEW_UNAVAILABLE`. Classify acceptance from actual
> families/completion/scope. Forward invocation reviewer/model/effort overrides
> to reviewer-bearing children. Generation workers are unchanged.


Draft a LaTeX paper based on: **$ARGUMENTS**

## Constants

- **REVIEWER_MODEL = `gpt-6-astra`** — Model used via Codex MCP for section review. For `backend=codex`, use an OpenAI model.
- **TARGET_VENUE = `ICLR`** — Default venue. Supported: `ICLR`, `NeurIPS`, `ICML`, `CVPR` (also ICCV/ECCV), `ACL` (also EMNLP/NAACL), `AAAI`, `ACM` (ACM MM, SIGIR, KDD, CHI, etc.), `CORL` (Conference on Robot Learning, PMLR), `IEEE_JOURNAL` (IEEE Transactions / Letters, e.g., T-PAMI, JSAC, TWC, TCOM, TSP, TIP), `IEEE_CONF` (IEEE conferences, e.g., ICC, GLOBECOM, INFOCOM, ICASSP). Determines style file and formatting. **RA-L** (IEEE Robotics and Automation Letters) is a journal, but its review submission uses the RAS conference format. Resolve `RA-L` / `RAL` to `IEEE_CONF` for the submission draft, and switch to the journal format only for the accepted version. See the RA-L section of `../shared-references/venue-checklists.md`.
- **ANONYMOUS = true** — If true, use anonymous author block. Set `false` for camera-ready. Note: most IEEE venues do NOT use anonymous submission — set `false` for IEEE. **Exception: IEEE RAS venues are double-anonymous.** This covers RAS's fully sponsored journals, such as RA-L and T-RO (since 2025-01-01), as well as ICRA (per the 2027 CFP) and IROS. Keep `true` until acceptance for these, and check the current CFP for CASE.
- **MAX_PAGES = 9** — Main body page limit. For ML conferences: counts from first page to end of Conclusion section, references and appendix NOT counted. **For IEEE venues: references ARE counted toward the page limit.** Typical limits: IEEE journal = no strict limit (but 12-14 pages typical for Transactions, 4-5 for Letters; RA-L = 8 pages including references by default (pages 7–8 cost $175 each); use 6 or 7 only if the user explicitly asks, never shrink to 6 on your own), IEEE conference = 5-8 pages including references.
- **DBLP_BIBTEX = true** — Fetch real BibTeX from DBLP/CrossRef instead of LLM-generated entries. Eliminates hallucinated citations. Zero install required. Set `false` to use legacy behavior (LLM search + `[VERIFY]` markers).
- **MIN_REFERENCES = `30`** — Hard floor inherited from `/paper-writing`. Counted as unique `\cite{}` / `\citep{}` / `\citet{}` keys across all `*.tex` files in `paper/`. Enforced in Step 8: Final Checks — write completion is blocked when below the floor.

## Inputs

1. **PAPER_PLAN.md** — outline with claims-evidence matrix, section plan, figure plan (from `/paper-plan`)
2. **NARRATIVE_REPORT.md** — the research narrative (primary source of content)
3. **Generated figures** — PDF/PNG files in `figures/` (from `/paper-figure`)
4. **LaTeX includes** — `figures/latex_includes.tex` (from `/paper-figure`)
5. **Bibliography** — existing `.bib` file, or will create one
6. **`<paper-dir>/PAPER_PREFERENCES.md`** (if present) — per-paper standing orders. Read at workflow start, before drafting any section. Bullets in `## Hard don'ts`, `## Notation`, `## Style / tone`, and `## Section-specific` override defaults from this skill and from `../shared-references/writing-principles.md`. When you apply a bullet, cite it in your output (e.g., "Skipping 'novel' per PAPER_PREFERENCES.md §Style/tone"). Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md). Missing file → treat as empty; do not error.
7. **`../embodied-ai-paper-writer/SKILL.md`** (only when the paper is robotics / embodied-AI) — domain-specific writing-craft coach distilled from 63 top robotics papers (CoRL, RSS, ICRA, IROS, Science Robotics). Triggered when the resolved venue is `CORL` or RSS/ICRA/IROS/Humanoids/ISRR, or when PAPER_PLAN.md / NARRATIVE_REPORT.md mentions robot, manipulation, locomotion, navigation, sim2real, embodied agent, VLA, real-robot experiments, teleoperation, etc. Use it for vocabulary, notation, sentence patterns, paragraph flow, section openers, figure/table caption conventions, and rhetorical pivots specific to robotics venues. **It is a style/craft reference, not a content advisor** — it does NOT decide what to claim. Compose its guidance with `../shared-references/writing-principles.md` (this skill's defaults still apply); when the two conflict, the embodied-AI guidance takes precedence for craft-level decisions (e.g., section opener patterns), the shared-references take precedence for cross-skill protocols (e.g., em-dash budget).
8. **`idea-stage/TITLE.md`** (if present, from `/title-decider`) — canonical title and **Terminology rulings**; authoritative. Use the ruled terms verbatim in every section, caption and table title; never introduce a synonym for a ruled term. If a new term gets settled while you work, add it to the rulings (see `/title-decider`, Downstream contract) instead of only using it locally.

If no PAPER_PLAN.md exists, ask the user to run `/paper-plan` first or provide a brief outline.

## Orchestra-Guided Writing Overlay

Keep the existing `insleep` workflow, file layout, and defaults. Use the shared references below only when they improve writing quality:

- Read `../shared-references/writing-principles.md` before drafting the Abstract, Introduction, Related Work, or when prose feels generic.
- Read `../shared-references/venue-checklists.md` during the final write-up and submission-readiness pass.
- Read `../shared-references/citation-discipline.md` only when the built-in DBLP/CrossRef workflow is insufficient.

These references are support material, not extra workflow phases.

## Optional: Style reference (`— style-ref: <source>`, opt-in)

Lets the user steer **structural** style (section ordering, theorem density, sentence cadence, figure density, bibliography style) toward a reference paper. **Default OFF — when the user does not pass `— style-ref`, do nothing differently from before.**

Only when `— style-ref: <source>` appears in `$ARGUMENTS`, run the helper FIRST, before drafting:

```bash
# Resolve $STYLE_HELPER via the canonical strict-safe chain (see
# shared-references/integration-contract.md §2). Policy A — gate:
# unresolved helper means --style-ref cannot be satisfied, so abort.
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
STYLE_HELPER=".aris/tools/extract_paper_style.py"
[ -f "$STYLE_HELPER" ] || STYLE_HELPER="tools/extract_paper_style.py"
[ -f "$STYLE_HELPER" ] || { [ -n "${ARIS_REPO:-}" ] && STYLE_HELPER="$ARIS_REPO/tools/extract_paper_style.py"; }
[ -f "$STYLE_HELPER" ] || {
  echo "ERROR: extract_paper_style.py not resolved at .aris/tools/, tools/, \$ARIS_REPO/tools/, or via ~/.aris/repo." >&2
  echo "       Fix: rerun bash tools/install_aris.sh or smart_update.sh (refreshes ~/.aris/repo), export ARIS_REPO, or copy the helper to tools/." >&2
  echo "       --style-ref cannot be satisfied; aborting." >&2
  exit 1
}
STYLE_STATUS=0
CACHE=$(python3 "$STYLE_HELPER" --source "<source>") || STYLE_STATUS=$?
case "$STYLE_STATUS" in
  0) ;;                                       # use $CACHE/style_profile.md as structural guidance
  2) echo "warning: style-ref skipped (missing optional dep)" >&2 ;;
  3) echo "error: --style-ref source failed; aborting draft" >&2 ; exit 1 ;;
  *) echo "error: helper failed unexpectedly; aborting draft" >&2 ; exit 1 ;;
esac
```

Sources accepted: local TeX dir / file, local PDF, arXiv id (`2501.12345` or `arxiv:2501.12345`), http(s) URL. Overleaf URLs and project IDs are rejected — clone via `/overleaf-sync setup <id>` first and pass the local clone path.

**Strict rules** (full contract in `tools/extract_paper_style.py` docstring):

- Use `style_profile.md` as **structural** guidance only. Match section count, section ordering tendency, theorem-environment density, caption-length distribution, sentence cadence, math display ratio, citation style.
- **Never copy prose, claims, examples, or terminology** from anything reachable through the cache. The profile is intentionally aggregate; if you need substance, use the user's own outline.
- **Never pass `— style-ref` (or the cache contents) to reviewer / auditor sub-agents.** Cross-model review independence (`../shared-references/reviewer-independence.md`) requires reviewers see only the artifact and the user's prompt, not the author's stylistic context.

### `<!-- DATA_NEEDED -->` markers (when `GAP_REPORT.md` exists)

If `/paper-plan` ran with `— style-ref:` it will have emitted `GAP_REPORT.md` alongside `PAPER_PLAN.md`. This file lists structural slots (ablation tables, scaling experiments, failure-case analyses, …) the exemplar implies but the user has **no evidence to fill**.

When `GAP_REPORT.md` is present and a section slot is classified as `status: missing`:

1. **Do not fabricate numerical results, figure references, or qualitative claims** to fill that slot.
2. Emit an HTML-comment placeholder at the exact location the missing content would go:

   ```latex
   <!-- DATA_NEEDED: GAP_S5_ABLATION — ablation table comparing X across the 3 axes implied by exemplar -->
   ```

3. Slot ID and one-line description come straight from `GAP_REPORT.md`. **Never invent Slot IDs.** Never reword the description to be more confident than the report.
4. The marker is intentionally an HTML comment so it is invisible in the rendered PDF but **searchable via `grep -r "DATA_NEEDED" sec/`** for human triage / `/experiment-bridge` follow-up.
5. For `status: partial`, write what the user has and emit `<!-- DATA_NEEDED: <Slot ID> — <what specifically is short> -->` at the gap point in the same paragraph (do not split the section).

**Carve-out from "no placeholder" rule.** The default `/paper-write` discipline (no placeholders such as "see supplementary" or "TBD") still applies for everything **except** GAP_REPORT-listed missing slots. The marker is the principled way to surface genuine evidence deficits without compromising claim integrity.

Original idea: @zhangpelf in [#217](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/issues/217).

## Templates

### Venue-Specific Setup

The skill includes conference templates in `templates/`. Select based on TARGET_VENUE:

**ICLR:**
```latex
\documentclass{article}
\usepackage{iclr2026_conference,times}
% \iclrfinalcopy  % Uncomment for camera-ready
```

**NeurIPS:**
```latex
\documentclass{article}
\usepackage[preprint]{neurips_2025}
% \usepackage[final]{neurips_2025}  % Camera-ready
```

**ICML:**
```latex
\documentclass[accepted]{icml2025}
% Use [accepted] for camera-ready
```

**CoRL** (Conference on Robot Learning, PMLR):
```latex
\documentclass{article}
\usepackage{corl_2026}            % Anonymous initial submission (default)
% \usepackage[final]{corl_2026}    % Camera-ready: authors visible + CoRL footnote
% \usepackage[preprint]{corl_2026} % arXiv preprint: authors visible, no CoRL footnote
% Required: 4-6 sentence single-paragraph abstract; \keywords{...} (2-3 keywords) after abstract.
% To choose keywords, run /pick-keywords (venue-aware; uses IEEE RAS controlled vocabulary for IROS/ICRA, free-form otherwise).
% bib style auto-set to corlabbrvnat by the corl_2026 package; uses natbib (\citep / \citet).
```

**IEEE Journal** (Transactions, Letters; for RA-L, the accepted version only):
```latex
\documentclass[journal]{IEEEtran}
\usepackage{cite}  % IEEE uses \cite{}, NOT natbib
% Author block uses \author{Name~\IEEEmembership{Member,~IEEE}}
```

**IEEE Conference** (ICC, GLOBECOM, INFOCOM, ICASSP, etc.; also ICRA / IROS and the RA-L review submission, which need the RAS margin preamble already in `templates/ieee_conference.tex`):
```latex
\documentclass[conference]{IEEEtran}
\usepackage{cite}  % IEEE uses \cite{}, NOT natbib
% Author block uses \IEEEauthorblockN / \IEEEauthorblockA
```

### Project Structure

Generate this file structure:

```
paper/
├── main.tex                    # master file (includes sections)
├── iclr2026_conference.sty     # or neurips_2025.sty / icml2025.sty / IEEEtran.cls + IEEEtran.bst
├── math_commands.tex           # shared math macros
├── references.bib              # bibliography (filtered — only cited entries)
├── sections/
│   ├── 0_abstract.tex
│   ├── 1_introduction.tex
│   ├── 2_related_work.tex
│   ├── 3_method.tex            # or preliminaries, setup, etc.
│   ├── 4_experiments.tex
│   ├── 5_conclusion.tex
│   └── A_appendix.tex          # proof details, extra experiments
└── figures/                    # symlink or copy from project figures/
```

**Section files are FLEXIBLE**: If the paper plan has 6-8 sections, create corresponding files (e.g., `4_theory.tex`, `5_experiments.tex`, `6_analysis.tex`, `7_conclusion.tex`).

## Workflow

### Step 0: Backup and Clean

If `paper/` already exists, back up to `paper-backup-{timestamp}/` before overwriting. Never silently destroy existing work.

**CRITICAL: Clean stale files.** When changing section structure (e.g., 5 sections → 7 sections), delete section files that are no longer referenced by `main.tex`. Stale files (e.g., old `5_conclusion.tex` left behind when conclusion moved to `7_conclusion.tex`) cause confusion and waste space.

### Step 1: Initialize Project

1. Create `paper/` directory
2. Copy venue template from `templates/` — the template already includes:
   - All standard packages (amsmath, hyperref, cleveref, booktabs, etc.)
   - Theorem environments with `\crefname{assumption}` fix
   - Anonymous author block
3. Generate `math_commands.tex` with paper-specific notation
4. Create section files matching PAPER_PLAN structure

**Author block (anonymous mode):**
```latex
\author{Anonymous Authors}
```

### Step 2: Generate math_commands.tex

Create shared math macros based on the paper's notation:

```latex
% math_commands.tex — shared notation
\newcommand{\R}{\mathbb{R}}
\newcommand{\E}{\mathbb{E}}
\DeclareMathOperator*{\argmin}{arg\,min}
\DeclareMathOperator*{\argmax}{arg\,max}
% Add paper-specific notation here
```

### Step 3: Write Each Section

Process sections in order. For each section:

1. **Read the plan** — what claims, evidence, citations belong here
2. **Read NARRATIVE_REPORT.md** — extract relevant content, findings, and quantitative results
3. **Draft content** — write complete LaTeX (no fabricated placeholders). **Exception:** if `GAP_REPORT.md` exists and the section has slots with `status: missing`, emit `<!-- DATA_NEEDED: <Slot ID> — <description> -->` at those points instead of inventing data — see the DATA_NEEDED markers subsection above.
4. **Insert figures/tables** — use snippets from `figures/latex_includes.tex`
5. **Add citations** — for ML conferences (ICLR/NeurIPS/ICML/CVPR/ACL/AAAI): use `\citep{}` / `\citet{}` (natbib). **For IEEE venues**: use `\cite{}` (numeric style via `cite` package). Never mix natbib and cite commands.

Before drafting the front matter, re-read the one-sentence contribution from `PAPER_PLAN.md`. The Abstract and Introduction should make that takeaway obvious before the reader reaches the full method.

#### Section-Specific Guidelines

**§0 Abstract:**
- Use the 5-part flow from `../shared-references/writing-principles.md`: what, why hard, how, evidence, strongest result
- Must be self-contained (understandable without reading the paper)
- Start with the paper's specific contribution, not generic field-level background
- Include one concrete quantitative result
- 150-250 words (check venue limit)
- No citations, no undefined acronyms
- No `\begin{abstract}` — that's in main.tex

**§1 Introduction:**
- Open with a compelling hook (1-2 sentences, problem motivation)
- State the gap clearly ("However, ...")
- Give a brief approach overview before the reader gets lost in details
- List 2-4 specific, falsifiable contributions as a numbered or bulleted list
- Preview the strongest result early instead of saving it for the experiments section
- Keep §1 at the level of the story: the overall question, the approach and its key insight, the headline result, and the contributions. Keep field- or venue-required research questions in §1; place detailed questions with the section or subsection that answers them
- Keep contribution bullets concise, usually 1-2 lines, and qualitative by default, without numbers; the results carry the figures. When a contribution is a gain on a specific metric or benchmark, stating that number can make it sharper. Falsifiable means a reviewer can check the bullet against evidence the paper provides (a theorem, an experiment, a measured comparison), not that it contains a number
- A contribution that is an artifact (a method, framework, dataset or benchmark) can be named as a noun phrase, since the artifact is the contribution. A contribution that is a finding is stated as what the paper establishes, with the authors as subject ("We show that ...", "We identify ..."), not as a noun phrase that lists the result ("A large advantage when ..."). Recast finding-style claims from PAPER_PLAN.md this way while keeping their meaning and scope
- Each claim in §1 carries the conditions that make it true. When PAPER_PLAN.md or a claims ledger asks for further qualifiers next to a claim, place those that do not change what the claim says as Key Rule 3 does, rather than repeating them in §1; a qualifier that would change the claim narrows the claim itself. The Abstract keeps what it needs to stand alone
- End with a brief roadmap ("The rest of this paper is organized as...")
- Include the main result figure if space allows
- Target: 1-1.5 pages
- Methods should begin by page 2-3 at the latest

**§2 Related Work:**
- **MINIMUM 1 full page** (3-4 substantive paragraphs). Short related work sections are a common reviewer complaint.
- Organize by category. Under the one-paragraph-per-category default below, start each category's paragraph with a bold, unnumbered run-in heading (`\textbf{Category Name.}`) followed by the prose. When categories need several paragraphs, use `\subsection{Category Name}` headings instead (A., B., ... in IEEEtran). Do not use `\paragraph` for these headings: IEEEtran renders it as an italic a), b), c) heading
- Organize methodologically, by assumption class, or by research question; do not write paper-by-paper mini-summaries
- Each category: 1 paragraph summarizing the line of work + 1-2 sentences positioning this paper
- Do NOT just list papers — synthesize and compare
- End each paragraph with how this paper relates/differs

**§3 Method / Preliminaries / Setup:**
- Define notation early (reference math_commands.tex)
- Put measured results, such as how accurate a labelling or extraction procedure is or how much two variants differ, in the experiments beside the claim they support, with a pointer from the method section if the reader needs one there. A brief empirical reason or sanity check that explains a design choice may stay in the method section, with its source stated (Key Rules, "Say where a finding comes from"). Drop training observations that no method choice or result depends on, such as a collapsed latent. When the method section is the experimental setup, its settings and values stay there
- Use `\begin{definition}`, `\begin{theorem}` environments for formal statements
- For theory papers: include proof sketches of key results in main body, full proofs in appendix
- For theory papers: include a **comparison table** of prior bounds vs. this paper
- Include algorithm pseudocode if applicable (`algorithm2e` or `algorithmic`)
- Target: 1.5-2 pages

**§4 Experiments:**
- Start with experimental setup (datasets, baselines, metrics, implementation details)
- Main results table/figure first
- Then ablations and analysis
- Every claim from the introduction must have supporting evidence here
- For each major experiment, make explicit what claim it supports and what the reader should notice
- Target: 2.5-3 pages

**§5 Conclusion:**
- Summarize contributions (NOT copy-paste from intro — rephrase)
- Limitations (2-4 material, specific limits — dataset scale, compute regime, assumption X; real ones only, never invented to fill a count. This section is the ONLY home for generic caveats)
- Future work (1-2 concrete directions)
- Ethics statement and reproducibility statement (if venue requires)
- Target: 0.5 pages

**Appendix:**
- Proof details (full proofs of main-body theorems)
- Additional experiments, ablations
- Implementation details, hyperparameter tables
- Additional visualizations

### Step 3.5: Theory Paper Consistency Pass (theory papers only)

Run this pass after drafting all sections and before building the bibliography.

**Trigger heuristic:** treat the paper as theory-heavy if `PAPER_PLAN.md` labels it as theory/analysis, or if the drafted sections contain 5 or more formal result environments (`\begin{theorem}`, `\begin{lemma}`, `\begin{proposition}`, `\begin{corollary}`).

**Proof source search:** search the workspace for any standalone full-proof source file whose name or contents indicate a canonical proof version (`proof`, `appendix`, `full`, `complete`, `supplement`, `supplementary`). If such a file exists, prompt the user exactly:

`Inline full proofs from {file}? [Y/n]`

Default to `Y`.

If the user accepts:
- import the full theorem/lemma statement plus proof block into the appendix source (`A_appendix.tex` or the appendix file named by the plan)
- use the main-body theorem statement as the canonical public statement; the appendix copy must match it unless the main-body statement is being revised in the same pass
- do **not** leave placeholders such as "see supplementary proof document" or "proof omitted for brevity"
- preserve theorem labels, equation labels, and proof structure exactly
- keep the main body proof sketches short, but never let the appendix be a sketch-only placeholder when a full proof source exists

If no standalone full-proof source exists:
- use proof sketches only when they are actually written as proof sketches, not placeholders
- do not fabricate an external proof document reference

**Restatement audit:**
- Compare every theorem/lemma/proposition statement that is restated in the appendix against the main-body version
- Do not diff proof bodies; only audit statements, hypotheses, case splits, quantifiers, domains, notation, variable names, and terminology for defined objects
- Treat `stationary` vs `terminal`, changed assumption names, or missing case splits as mismatches unless explicitly documented
- If the appendix needs different wording, add an explicit notation bridge instead of silently renaming concepts
- Resolve all mismatches before Step 4

**Empirical motivation:** in a real theory-paper run, the default behavior generated `"see supplementary proof document"` placeholders in the appendix. The author had to manually pull hundreds of lines of full proofs from a standalone proofs file (e.g. `proof_full.tex`). Without this pass, theory papers ship with sketch-only appendices that fail at theory venues.

### Step 4: Build Bibliography

**CRITICAL: Only include entries that are actually cited in the paper.**

1. Scan all citation references in the drafted sections (`\citep{}`/`\citet{}` for ML conferences, `\cite{}` for IEEE venues)
2. Build a citation key list
3. For each citation key:
   - Check existing `.bib` files in the project/narrative docs
   - If not found and **DBLP_BIBTEX = true**, use the verified fetch chain below
   - If not found and **DBLP_BIBTEX = false**, search arXiv/Scholar for correct BibTeX
   - **NEVER fabricate BibTeX entries** — mark unknown ones with `[VERIFY]` comment
4. Write `references.bib` containing ONLY cited entries (no bloat)

#### Verified BibTeX Fetch (when DBLP_BIBTEX = true)

Three-step fallback chain — zero install, zero auth, all real BibTeX:

**Step A: DBLP (best quality — full venue, pages, editors)**
```bash
# 1. Search by title + first author
curl -s "https://dblp.org/search/publ/api?q=TITLE+AUTHOR&format=json&h=3"
# 2. Extract DBLP key from result (e.g., conf/nips/VaswaniSPUJGKP17)
# 3. Fetch real BibTeX
curl -s "https://dblp.org/rec/{key}.bib"
```

**Step B: CrossRef DOI (fallback — works for arXiv preprints)**
```bash
# If paper has a DOI or arXiv ID (arXiv DOI = 10.48550/arXiv.{id})
curl -sLH "Accept: application/x-bibtex" "https://doi.org/{doi}"
```

**Step C: Mark `[VERIFY]` (last resort)**
If both DBLP and CrossRef return nothing, mark the entry with `% [VERIFY]` comment. Do NOT fabricate.

**Why this matters:** LLM-generated BibTeX frequently hallucinates venue names, page numbers, or even co-authors. DBLP and CrossRef return publisher-verified metadata. Upstream skills (`/research-lit`, `/novelty-check`) may mention papers from LLM memory — this fetch chain is the gate that prevents hallucinated citations from entering the final `.bib`.

If the DBLP/CrossRef flow is not enough, load `../shared-references/citation-discipline.md` for stricter fallback rules before adding placeholders.

**Automated bib cleaning** — use this Python pattern to extract only cited entries:

```python
import re
# 1. Grep all \citep{...}, \citet{...}, and \cite{...} from all .tex files
# 2. Extract unique keys (handle multi-cite like \citep{a,b,c} or \cite{a,b,c})
# 3. Parse the full .bib file, keep only entries whose key is in the cited set
# 4. Write the filtered bib
```

This prevents bib bloat (e.g., 948 lines → 215 lines in testing).

**Enforced Bib Hygiene Validation** — run immediately after the filtered `references.bib` is written.

```bash
python3 - <<'PY'
import io, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

try:
    import bibtexparser
except ImportError:
    sys.exit("Missing dependency: pip install bibtexparser")

ROOT = Path("paper")
tex_paths = [ROOT / "main.tex", *sorted((ROOT / "sections").glob("*.tex"))]
tex = "\n".join(p.read_text(errors="ignore") for p in tex_paths if p.exists())

cited = set()
for m in re.finditer(r'\\cite[a-zA-Z]*\{([^}]*)\}', tex):
    cited.update(k.strip() for k in m.group(1).split(',') if k.strip())

with (ROOT / "references.bib").open() as fh:
    bib = bibtexparser.load(fh)

entries = {e["ID"]: e for e in bib.entries}
dead = sorted(set(entries) - cited)
if dead:
    print("DEAD ENTRIES:")
    for key in dead:
        print("  ", key)

def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()

def dblp_hits(title):
    q = urllib.parse.quote(title)
    url = f"https://dblp.org/search/publ/api?q={q}&format=json&h=3"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    return [h.get("info", {}) for h in data.get("result", {}).get("hits", {}).get("hit", [])]

def crossref_entry(doi):
    req = urllib.request.Request(f"https://doi.org/{doi}", headers={"Accept": "application/x-bibtex"})
    with urllib.request.urlopen(req, timeout=20) as r:
        parsed = bibtexparser.loads(r.read().decode("utf-8", "ignore"))
    return parsed.entries[0] if parsed.entries else {}

for key in sorted(cited & set(entries)):
    e = entries[key]
    title = e.get("title", "").strip("{}")
    hits = dblp_hits(title) if title else []
    hit = hits[0] if hits else None
    source = "DBLP"
    if hit is None and e.get("doi"):
        try:
            hit = crossref_entry(e["doi"])
            source = "CrossRef"
        except Exception:
            hit = None
    if hit is None:
        print(f"VERIFY {key}: no DBLP/CrossRef hit")
        continue

    issues = []
    year_a = str(e.get("year", "")).strip()
    year_b = str(hit.get("year", "")).strip()
    if year_a and year_b and year_a != year_b:
        issues.append(f"year {year_a} != {year_b}")

    venue_a = e.get("journal") or e.get("booktitle") or ""
    venue_b = hit.get("journal") or hit.get("booktitle") or hit.get("venue") or ""
    if norm(venue_a) and norm(venue_b) and norm(venue_a) != norm(venue_b):
        issues.append(f"venue {venue_a} != {venue_b}")

    authors_a = [norm(a) for a in re.split(r'\s+and\s+', e.get("author", "")) if a.strip()]
    authors_b = [norm(a) for a in re.split(r'\s+and\s+', hit.get("author", "")) if a.strip()]
    if authors_a and authors_b and authors_a[:2] != authors_b[:2]:
        issues.append("author list differs")

    if issues:
        print(f"MISMATCH {key} ({source}): " + "; ".join(issues))
PY
```

If `DEAD ENTRIES` is printed, remove those keys from `references.bib` before continuing.
If `VERIFY` or `MISMATCH` is printed, do not invent metadata:
- prefer DBLP when it returns a clear hit
- if DBLP misses and a DOI is available, fall back to CrossRef
- if both disagree or still cannot verify, keep the entry only with a `% [VERIFY]` marker
- uncited entries must be deleted, not left behind as dead bibliography bloat

**Citation reachability rule:** an entry is dead if its key does not appear in any `\cite...{}` command in `paper/main.tex` or any `paper/sections/*.tex` file.

**Empirical motivation:** in a real submission run, several dead bib entries sat in `references.bib` for many improvement rounds, and at least one entry had a key/year mismatch. Neither was flagged by the existing automated cleaning.

**Citation verification rules (from claude-scholar + Imbad0202):**
1. Every BibTeX entry must have: author, title, year, venue/journal
2. Prefer published venue versions over arXiv preprints (if published)
3. Use consistent key format: `{firstauthor}{year}{keyword}` (e.g., `ho2020denoising`)
4. Double-check year and venue for every entry
5. Remove duplicate entries (same paper with different keys)

### Step 5: Scientific Writing Quality Pass (5 audit passes)

After drafting all sections, run five sequential audit passes. Based on Sainani's "Writing in the Sciences" methodology: every word must earn its place.

**Pass 1: Clutter Extraction** — Strip sentences to cleanest components.

| Cluttered phrase | Replace with |
|------------------|--------------|
| Due to the fact that | Because |
| In order to | To |
| A number of | Several |
| It is worth noting that | (delete — just state the point) |
| It is important to note that | (delete) |
| At the present time | Now |
| On the basis of | Based on |
| In light of the fact that | Because |
| Have an effect on | Affect |
| Give rise to | Cause |

Also remove redundancies: "completely eliminate" → "eliminate", "future plans" → "plans", "unexpected surprise" → "surprise".

Remove AI-isms: delve, pivotal, landscape, tapestry, underscore, noteworthy, intriguingly.

**Pass 2: Active Voice and Verb Vitality** — Identify who did what.

- Spot passive: "to-be" verb + past participle ("was observed", "were analyzed")
- Convert: find the actor, reconstruct as Subject–Verb–Object
- Resurrect smothered verbs (nominalizations):
  - "We made an investigation" → "We investigated"
  - "Failure of the system occurs" → "The system fails"
  - "Provides a description of" → "Describes"

Passive voice IS acceptable for: established facts, methods where agent is irrelevant, or when required by venue style.

**Pass 3: Sentence Architecture** — Structure and flow. Vary paragraph shape:
if every paragraph runs problem → method → benefit → summary, the mold numbs
the reader — break it.

- Flag sentences > 40 words for splitting
- Ensure subject and verb are close together (no long parenthetical insertions between them)
- Put familiar context first, new information later
- Place the most important point near the end of the sentence
- Let each paragraph do one job
- Don't start consecutive sentences with "This" or "We"
- Check paragraph transitions — each paragraph's first sentence should connect to the previous

**Pass 4: Keyword Consistency** — The Banana Rule.

**Do not call a "banana" an "elongated yellow fruit" to avoid repetition.** If the Methods say "obese group," the Results must not switch to "heavier group." Synonym variation for technical terms forces the reader to wonder whether a new category has been introduced.

- Start from `idea-stage/TITLE.md` **Terminology rulings** (if present): search the draft, captions and table titles for the synonyms of each ruled term and for every word on its Avoid list
- Extract all key terms from Method section (group names, variable names, technique names, abbreviations)
- Verify exact same terms appear in Results, Discussion, Tables, Figure captions
- Flag every synonym substitution for a defined term
- Acronym austerity: flag non-standard acronyms created only for convenience; verify every acronym is defined at first use
- Do not treat a word the paper mentions only in passing (once, in an earlier parenthetical) as a defined term, and do not let "by construction" or "by design" stand in for a reason the reader has not been given; state the mechanism instead ("the perturbations change only how the robot moves to these targets", not "unchanged by the perturbations by construction")
- Resolve ambiguous references such as "the rules below" by naming the target and citing its section. When reporting a selection among defined options, give each arm's chosen option by its defined name; an umbrella term that is none of them ("sequential execution") can hide that the arms chose differently

**Pass 5: Numerical and Citation Integrity**

- Does sample size (N) in Abstract match Table 1?
- Do percentages in Results match raw numbers in Tables?
- Are significant figures consistent and appropriate?
- Do Figure graphics match Table values?
- Flag statistics cited only through secondary sources (reviews, textbooks) — recommend verifying primary source
- No protocol-history labels (registered / pre-registered (unless a public registry entry is cited), planned, follow-up, original protocol, post hoc, exploratory, stage names, run codenames, labels for data sets or experiments that are not defined where the set is introduced or that substitute collection history for what is compared) in the body, captions, table titles or footnotes; every fact such a label carried that changes how a number reads is written as method (see `../shared-references/writing-principles.md`, "The Paper Is Not a Tech Report")

### Step 6: Cross-Review with REVIEWER_MODEL

Send the complete draft to GPT-6-Astra xhigh:

> Resolve this reviewer slot first; the following is the `backend=codex` example.

```
mcp__codex__codex:
  model: gpt-6-astra
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Review this [VENUE] paper draft (main body, excluding appendix).

    Judge claim calibration in BOTH directions. Recommend narrowing only when the
    current scope or modality exceeds the evidence; do not ask for extra hedges
    around a supported result. Flag stacked hedges, self-defence ("we do not
    claim"), instruction confessions ("we do not address X"), and generic caveats
    outside Limitations as writing defects to remove. Tone fixes must never alter
    facts, negation, modality, scope, comparison direction, or numbers.

    Focus on:
    1. Does each claim from the intro have supporting evidence?
    2. Is the writing clear, concise, and free of AI-isms?
    3. Any logical gaps or unclear explanations?
    4. Does it fit within [MAX_PAGES] pages (to end of Conclusion)?
    5. Is related work sufficiently comprehensive (≥1 page)?
    6. For theory papers: are proof sketches adequate?
    7. Are figures/tables clearly described and properly referenced?
    8. Would a skim reader understand the contribution from the title, abstract, introduction, and Figure 1?

    For each issue, specify: severity (CRITICAL/MAJOR/MINOR), location, and fix.

    [paste full draft text]
```

Apply CRITICAL and MAJOR fixes. Document MINOR issues for the user.

### Step 7: Reverse Outline Test (from Research-Paper-Writing-Skills)

After drafting all sections:

1. **Extract topic sentences** — pull the first sentence of every paragraph
2. **Read them in sequence** — they should form a coherent narrative on their own
3. **Check claim coverage** — every claim from the Claims-Evidence Matrix must appear
4. **Check evidence mapping** — every experiment/figure must support a stated claim
5. **Fix gaps** — if a topic sentence doesn't advance the story, rewrite the paragraph

### Step 8: Final Checks

Before declaring done:

- [ ] All `\ref{}` and `\label{}` match (no undefined references)
- [ ] All citation commands (`\citep{}`/`\citet{}` for ML conferences, `\cite{}` for IEEE) have corresponding BibTeX entries
- [ ] **Reference floor gate** — unique cite-key count ≥ `MIN_REFERENCES` (see check below)
- [ ] No author information in anonymous mode
- [ ] Figure/table numbering is correct
- [ ] Page count within MAX_PAGES (main body to Conclusion end) — if over, apply [`../shared-references/page-shrink-heuristic.md`](../shared-references/page-shrink-heuristic.md) in order; never delete experiments, theorems, or citations to fit
- [ ] No TODO/FIXME/XXX markers left in the text
- [ ] No `[VERIFY]` markers left unchecked
- [ ] Abstract is self-contained (understandable without reading the paper)
- [ ] **Abstract contains ZERO em-dashes** (`—` / `---`) — hard gate, see [`../shared-references/writing-principles.md`](../shared-references/writing-principles.md) §Punctuation. Run:
  ```bash
  # paper/sections/0_abstract.tex holds the abstract text and main.tex \input's it inside
  # \begin{abstract}; awk does not follow \input, so read the file too.
  { cat paper/sections/0_abstract.tex 2>/dev/null
    awk '/\\begin\{abstract\}/,/\\end\{abstract\}/' paper/sections/*.tex paper/main.tex; } \
    | grep -oE "—|---" | wc -l
  ```
  Non-zero count blocks completion; surface offending sentences and rewrite.
- [ ] **Abstract within its length limit**: the venue's word limit if it sets one, otherwise §0's 250-word default. Check a character limit, if the venue sets one, separately on the text entered in the submission form.
  A rough count for the standard layout, with comments stripped but escaped `\%` kept (stripping from every `%` cuts each line at its first percentage and undercounts):
  ```bash
  perl -pe 's/(?<!\\)%.*//' paper/sections/0_abstract.tex | wc -w
  ```
  This counts source tokens: a command that prints nothing, such as `\looseness=-1`, still counts, and a macro counts once whatever it prints. If the abstract is written inside `main.tex`, count that block instead, and near the limit recount on the rendered text.
  If over, cut repeated detail and secondary numbers first, and keep the claim's scope and what the abstract needs to stand alone.
- [ ] Main-body em-dash count ≤ 2 (same reference)
- [ ] Title is specific and informative (not generic)
- [ ] Related work is ≥1 full page
- [ ] references.bib contains ONLY cited entries (no bloat)
- [ ] **No stale section files** — every .tex in `sections/` is `\input`ed by `main.tex`
- [ ] **Section files match main.tex** — file numbering and `\input` paths are consistent
- [ ] Venue-specific required sections/checklists satisfied (read `../shared-references/venue-checklists.md` if needed)
- [ ] A skim reader can recover the main claim from the title, abstract, introduction, and Figure 1/captions

#### Reference Floor Gate (`MIN_REFERENCES`)

Count unique cite-keys across `*.tex` files in the paper directory and compare against `MIN_REFERENCES`:

```bash
# Count unique \cite{}, \citep{}, \citet{}, \citeauthor{}, \citeyear{} keys.
# Handles multi-key forms like \citep{a,b,c} and ignores commented-out lines.
COUNT=$(grep -rhoE '\\(cite|citep|citet|citeauthor|citeyear)\{[^}]*\}' paper/ \
  | sed -E 's/\\(cite|citep|citet|citeauthor|citeyear)\{//; s/\}$//' \
  | tr ',' '\n' \
  | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' \
  | grep -v '^$' \
  | sort -u \
  | wc -l)
echo "Unique cite-keys: ${COUNT} (floor: ${MIN_REFERENCES})"
```

**If `COUNT < MIN_REFERENCES`:** do NOT declare write complete. Emit a `GAP_REFERENCES.md` next to `main.tex` listing the current count, the floor, and the recommended remediation:

1. Re-open Related Work and add 1-paragraph treatments of comparator work missing citations.
2. Re-run `/research-lit "<topic>"` and `/openalex` to surface fresh references for under-cited claims.
3. After adding new `\cite{}` calls, re-run `/paper-compile` so BibTeX picks up the new keys, then re-run this gate.

Do not lower `MIN_REFERENCES` to pass the gate; it is set at the `/paper-writing` orchestrator and propagated here intentionally. Override only via the orchestrator's `— min-references: <n>` CLI flag.

## Key Rules

=== CONFIDENT PROSE, HONEST LIMITS (never upgrades claims) ===
1. Calibrate each claim to the evidence's actual scope and modality, then state
   that calibrated claim directly. Necessary assumptions, uncertainty, and
   scope are part of the claim; stacked hedges and defensive throat-clearing
   are not.
2. If the current claim is unsupported, narrow it to a version the evidence
   supports or cut it. Do not substitute a softer-sounding synonym for fixing
   scope, modality, comparison, or aggregation.
3. Put generic caveats and broader boundary discussion in one Limitations
   section. Outside it, remove generic disclaimers such as "further research
   is needed", "may not generalize", and "should be interpreted with caution".
   Claim-defining scope, assumptions, and statistical qualifications stay
   attached to the claims they make true. Caveats that do not change what a
   claim says (results outside its stated scope, untested settings, another
   result's limits) are written once: broader boundaries in the
   venue-appropriate Limitations location, result-specific ones with the
   results they qualify, not beside every restatement of the claim. A
   counterexample inside the claim's scope narrows the claim instead.
4. Aim for 2-4 material, specific limitations (dataset scale, compute regime,
   assumption X). Real ones only — never invent one to meet a count, never
   apologize generically, never repeat the same limitation through the paper.
5. Writing instructions are not manuscript content. "Do not mention X" means
   omit X, not write "we do not address/claim/discuss X". Never expose
   drafting instructions, requested omissions, reviewer feedback, or revision
   history in manuscript prose.
6. Replace self-defence ("we do not claim", "our goal is merely") with a
   positive, evidence-matched statement of what the paper does establish. If
   the defensive sentence carries a real boundary, keep that boundary in the
   claim or Limitations; do not delete truth-conditional content.
7. Tone-only edits never alter facts, negation, modality, scope, assumptions,
   comparison direction, aggregation, numbers, formulas, or citations. Genuine
   overclaims must still be narrowed; supported claims wrapped in redundant
   caution must be stated directly.
8. One causal spine: gap -> question -> insight -> consequence -> evidence ->
   implication. Every section advances it. Make the method feel inevitable:
   the gap creates a concrete question, the key insight answers it, the method
   follows from the insight, each major experiment tests a consequence of it,
   and the conclusion states exactly what the evidence establishes.
   Front-load the contribution; never narrate the drafting or revision process.
9. The paper is a launch, not a progress report. Organize the narrative
   around the work's strongest genuine advantage — a new capability, problem,
   mechanism or viewpoint, wider applicability, lower cost, a better tradeoff.
   Material that does not form an advantage stays out of the main line. If the
   results cannot carry the original story, rebuild the story around the
   strongest evidence instead of defending the original one.
10. Pick the contest the paper wins. Do not build the narrative on a metric
    where the method is not ahead; frame the comparison around the task
    definition, evaluation dimension or constraint that reflects what the
    method is for, and say explicitly which contest it wins. Unfavorable
    numbers still appear — tables stay complete. Where the evidence supports
    it, explain them as a goal difference or a deliberate tradeoff rather
    than narrating a defeat ("underperforms", "fails to surpass"); where it
    does not, state the underperformance neutrally, narrow the claim, and
    keep it in Limitations if it is material. Never elevate a local
    observation into a verdict on the whole method, and never invent a
    tradeoff to cover a weakness.
11. Every experiment has an argumentative duty: it shows the method works,
    shows the gain comes from the key mechanism, shows value in the target
    scenario, or rules out the most likely alternative explanation. An
    experiment carrying none of these is cut, shortened, moved to the
    appendix, or redesigned. The experiments section is an argument, not a
    results warehouse.
12. State the advantage yourself — under which condition it appears, why it
    appears, what it solves — rather than expecting the reviewer to find it
    in a table. Abstract and introduction open like a launch: an important
    unsolved problem, the gap in existing methods, this paper's distinct
    idea, the heaviest result. The conclusion reinforces what was solved,
    proposed and proven and why it matters; no new self-negation or widened
    limitations in the last paragraph.


- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- **Do NOT generate author names, emails, or affiliations** — use anonymous block or placeholder
- **Write complete sections, not outlines** — the output should be compilable LaTeX
- **One file per section** — modular structure for easy editing
- **Every claim must cite evidence** — cross-reference the Claims-Evidence Matrix
- **Say where a finding comes from** — a finding that is neither common knowledge nor self-evident must not read as an established fact; make its source clear. Cite prior work where citations are allowed. For the paper's own result, a restatement outside the passage that presents its evidence points to the section, figure or table that shows it, or says "we found that ..." when the evidence is not shown elsewhere (e.g. a tuning run behind a design choice). In the Abstract, Introduction or Conclusion, a summary with the authors as subject ("we show that ...") is enough to identify the paper as the source; the Abstract still has no citations or body cross-references (§0 Abstract)
- **Compile-ready** — the output should compile with `latexmk` without errors (modulo missing figures)
- **Calibrate, don't hedge** — match each claim to its evidence's actual scope and modality, then state it directly; generic caveats live in Limitations only (the CONFIDENT PROSE, HONEST LIMITS block above is the contract)
- **Launch, not progress report** — organize around the strongest genuine advantage, pick the contest the paper wins, give every experiment an argumentative duty; unfavorable numbers stay in the tables, explained as tradeoffs where the evidence supports that and stated neutrally where it does not — never narrated as defeats, never dressed as a tradeoff they are not (rules 9-12 above)
- **Venue style matters** — ML conferences (ICLR/NeurIPS/ICML) use `natbib` (`\citep`/`\citet`); **IEEE venues use `cite` package (`\cite{}`, numeric)**. Never mix.
- **Page limit rules differ by venue** — ML conferences: main body to Conclusion, references/appendix NOT counted. **IEEE: references ARE counted toward the page limit.**
- **Clean bib** — references.bib must only contain entries that are actually `\cite`d
- **Section count is flexible** — match PAPER_PLAN structure, don't force into 5 sections
- **Backup before overwrite** — never destroy existing `paper/` directory without backing up
- **Front-load the contribution** — do not hide the payoff until the experiments or appendix
- **Order results by argument, not by lab notebook** — present experiments in the sequence that best builds the case, never in the order they happened to run
- **Controls and ablations sit next to the claim they test** — not pooled in a distant subsection where the reader has forgotten what was at stake

## Writing Quality Reference

- `../shared-references/writing-principles.md` — story framing, abstract/introduction patterns, sentence-level clarity, reviewer reading order
- `../shared-references/venue-checklists.md` — ICLR/NeurIPS/ICML/IEEE submission requirements to check before declaring done
- `../shared-references/citation-discipline.md` — stricter fallback for ambiguous citations

Keep using the reverse-outline test and anti-inflation polish from the main workflow above; the shared references are there to improve quality without adding a new phase.

## Acknowledgements

Writing methodology adapted from [Research-Paper-Writing-Skills](https://github.com/Master-cai/Research-Paper-Writing-Skills) (CCF award-winning methodology). Citation verification from [claude-scholar](https://github.com/Galaxy-Dawn/claude-scholar) and [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills). This hybrid pack's writing-guidance overlay is adapted from Orchestra Research's paper-writing materials.

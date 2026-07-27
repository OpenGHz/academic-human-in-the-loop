---
name: paper-compile
description: "Compile LaTeX paper to PDF, fix errors, and verify output. Use when user says \"编译论文\", \"compile paper\", \"build PDF\", \"生成PDF\", or wants to compile LaTeX into a submission-ready PDF."
argument-hint: "[paper-directory]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob
---

# Paper Compile: LaTeX to Submission-Ready PDF

Compile the LaTeX paper and fix any issues: **$ARGUMENTS**

## Constants

- **COMPILER = `latexmk`** — LaTeX build tool. Handles multi-pass compilation automatically.
- **ENGINE = `pdflatex`** — LaTeX engine. Options: `pdflatex` (default), `xelatex` (for CJK/custom fonts), `lualatex`.
- **MAX_COMPILE_ATTEMPTS = 3** — Maximum attempts to fix errors and recompile.
- **PAPER_DIR = `paper/`** — Directory containing LaTeX source files.
- **MAX_PAGES** — Page limit. ML conferences: main body to Conclusion end (excluding references & appendix). ICLR=9, NeurIPS=9, ICML=8. **IEEE venues: references ARE included in page count.** IEEE journal ≈ 12-14 pages, IEEE conference ≈ 5-8 pages (all inclusive).

## Workflow

### Step 1: Verify Prerequisites

Check that the compilation environment is ready:

```bash
# Check LaTeX installation
which pdflatex && which latexmk && which bibtex

# If not installed, provide instructions:
# macOS: brew install --cask mactex-no-gui
# Ubuntu: sudo apt-get install texlive-full
# Server: conda install -c conda-forge texlive-core
```

Verify all required files exist:

```bash
# Must exist
ls $PAPER_DIR/main.tex

# Should exist
ls $PAPER_DIR/references.bib
ls $PAPER_DIR/sections/*.tex
ls $PAPER_DIR/figures/*.pdf 2>/dev/null || ls $PAPER_DIR/figures/*.png 2>/dev/null
```

### Step 2: First Compilation Attempt

**Prefer the canonical helper `build_paper.sh`** — do NOT hand-roll a `latexmk` invocation when it
resolves. It adds paper-dir resolution (`--paper` → `$OVERLEAF_PAPER_DIR`/`$PAPER_DIR` →
`.overleaf-sync.conf` → `./paper`), a post-build intermediate scrub, and page-count reporting.

```bash
# Resolve the helper (shared-runtime chain, per shared-references/integration-contract.md §2)
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
PAPER_BUILDER=".aris/tools/build_paper.sh"
[ -f "$PAPER_BUILDER" ] || PAPER_BUILDER="tools/build_paper.sh"
[ -f "$PAPER_BUILDER" ] || { [ -n "${ARIS_REPO:-}" ] && PAPER_BUILDER="$ARIS_REPO/tools/build_paper.sh"; }
[ -f "$PAPER_BUILDER" ] || PAPER_BUILDER=""
```

**Failure policy: fall back, don't block.** The helper is a convenience wrapper, not a gate — if it
does not resolve, the inline `latexmk` path below produces the same PDF.

```bash
if [ -n "$PAPER_BUILDER" ]; then
  # --keep-aux is REQUIRED here: the default post-build scrub deletes main.log,
  # which Step 3 parses for error diagnosis.
  bash "$PAPER_BUILDER" --paper "$PAPER_DIR" --main main --clean --keep-aux 2>&1 | tee compile.log
else
  cd $PAPER_DIR
  latexmk -C                                                                    # clean previous artifacts
  latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tee compile.log
fi
```

### Step 3: Error Diagnosis and Auto-Fix

If compilation fails, read `compile.log` and fix common errors:

**Missing packages:**
```
! LaTeX Error: File `somepackage.sty' not found.
```
→ Install via `tlmgr install somepackage` or remove the `\usepackage` if unused.

**Undefined references:**
```
LaTeX Warning: Reference `fig:xyz' on page 3 undefined
```
→ Check `\label{fig:xyz}` exists in the correct figure environment.

**Missing figures:**
```
! LaTeX Error: File `figures/fig1.pdf' not found.
```
→ Check if the file exists with a different extension (.png vs .pdf). Update the `\includegraphics` path.

**Citation undefined:**
```
LaTeX Warning: Citation `smith2024' undefined
```
→ Add the missing entry to `references.bib` or fix the citation key.

**`[VERIFY]` markers in text:**
→ Search for `[VERIFY]` markers left by `/paper-write`. These indicate unverified citations or facts. Search for the correct information or flag to the user.

**Overfull hbox:**
```
Overfull \hbox (12.5pt too wide) in paragraph at lines 42--45
```
→ Minor: usually ignorable. If severe (>20pt), rephrase the text or adjust figure width.

**BibTeX errors:**
```
I was expecting a `,' or a `}'---line 15 of references.bib
```
→ Fix BibTeX syntax (missing comma, unmatched braces, special characters in title).

**`\crefname` undefined for custom theorem types:**
→ Ensure `\crefname{assumption}{Assumption}{Assumptions}` and similar are in the preamble after `\newtheorem{assumption}`.

### Step 4: Iterative Fix Loop

```
for attempt in 1..MAX_COMPILE_ATTEMPTS:
    compile()
    if success:
        break
    parse_errors()
    auto_fix()
```

For each error:
1. Read the error message from `compile.log`
2. Locate the source file and line number
3. Apply the fix
4. Recompile

**Stuck after 2 attempts?** If Codex plugin is installed, invoke `/codex:rescue` — Codex can independently read the LaTeX source and `compile.log` to spot issues Claude missed (e.g., conflicting packages, encoding problems, subtle macro errors). If not installed, continue with Claude's own diagnosis.

### Step 5: Post-Compilation Checks

After successful compilation, verify the output:

```bash
# Check PDF exists and has content
ls -la main.pdf
# Check page count
pdfinfo main.pdf | grep Pages

# macOS: open for visual inspection
# open main.pdf
```

**Visual review (automated):**
If the compiled PDF exists, read it directly to check visual presentation:
- Figure quality: readable labels, legible text, distinguishable colors
- Layout: no orphaned section headers, no awkward page breaks
- Figures appear near their first text reference (not pages away)
- Tables: aligned columns, consistent decimal precision
- No overfull content visibly extending past margins

This is a quick visual scan, not a full review — the improvement loop does deeper visual review.

**Automated checks:**

- [ ] PDF file exists and is > 100KB (not empty/corrupt)
- [ ] Total page count is reasonable (MAX_PAGES + appendix + references)
- [ ] No "??" in the PDF (undefined references — grep the log)
- [ ] No "[?]" in the PDF (undefined citations — grep the log)
- [ ] Figures are rendered (not missing image placeholders)

```bash
# Check for undefined references
grep -c "LaTeX Warning.*undefined" compile.log

# Check for missing citations
grep -c "Citation.*undefined" compile.log
```

### Step 6: Page Count Verification

**CRITICAL**: Verify paper fits within MAX_PAGES.

**For ML conferences (ICLR/NeurIPS/ICML/CVPR/ACL/AAAI):** Main body = first page through end of Conclusion section (not necessarily §5 — could be §6, §7, or §8 depending on structure). References and appendix are NOT counted.

**For IEEE venues:** The TOTAL page count (including references) must fit within the limit. There is no separate "main body" counting — everything up to and including the references counts.

**Precise check using `pdftotext`:**
```bash
# Extract text and find where Conclusion ends vs References begin
pdftotext main.pdf - | python3 -c "
import sys
text = sys.stdin.read()
pages = text.split('\f')
for i, page in enumerate(pages):
    if 'Ethics Statement' in page or 'Reproducibility' in page:
        print(f'Conclusion ends on page {i+1}')
    if any(w in page for w in ['References', 'Bibliography']):
        lines = [l for l in page.split('\n') if l.strip()]
        for l in lines[:3]:
            if 'References' in l or 'Bibliography' in l:
                print(f'References start on page {i+1}')
                break
"
```

If Conclusion ends mid-page and References start on the same page, the main body is that page number (e.g., if both are on page 9, main body = ~8.5 pages, which is fine for a 9-page limit since it leaves room for the References header).

If over limit, apply the ordered remediation in [`../shared-references/page-shrink-heuristic.md`](../shared-references/page-shrink-heuristic.md). Don't paraphrase the steps here — the shared doc owns the protocol so all skills cut in the same order. **Before applying any step, read `<paper-dir>/PAPER_PREFERENCES.md`** (if present) and check `## Hard don'ts` — a bullet like "Do not move Theorem 1 to appendix" overrides the corresponding heuristic step. When the next-best heuristic step conflicts with a hard don't, halt and surface to the user per the failure-mode section. Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md). Report the overflow as:

> "Main body is X pages (limit: MAX_PAGES). Apply shared-references/page-shrink-heuristic.md — start at step 1 (compress conclusion) and stop as soon as the count drops to ≤ MAX_PAGES."

If after step 5 the paper still overflows, surface `verdict: BLOCKED, reason_code: page_shrink_failed_under_constraints` to the user per the failure-mode section of the shared doc.

### Step 6.5: Stale File Detection

Check for orphaned section files not referenced by `main.tex`:

```bash
# Find all .tex files in sections/ and check which are \input'ed by main.tex
for f in paper/sections/*.tex; do
    base=$(basename "$f")
    if ! grep -q "$base" paper/main.tex; then
        echo "WARNING: $f is not referenced by main.tex — consider removing"
    fi
done
```

This prevents confusion from leftover files when section structure changes (e.g., old `5_conclusion.tex` left behind after restructuring to 7 sections).

### Step 7: Submission Readiness

For conference submission, additional checks:

- [ ] **Anonymous**: no author names, affiliations, or self-citations that reveal identity
- [ ] **Page limit**: main body within MAX_PAGES (to end of Conclusion)
- [ ] **Font embedding**: all fonts embedded in PDF
  ```bash
  pdffonts main.pdf | grep -v "yes"  # should return nothing (or only header)
  ```
- [ ] **No supplementary mixed in**: appendix clearly after `\newpage\appendix`
- [ ] **File size**: reasonable (< 50MB for most venues, < 10MB preferred)
- [ ] **No `[VERIFY]` markers**: search the PDF text for leftover markers

**Packaging the source for arXiv?** Do not assemble the tarball by hand — resolve
`tools/pack_arxiv.sh` through the same chain as Step 2 and run it. It discovers the real dependency
set from `main.fls` (what LaTeX actually opened), dereferences symlinks (arXiv silently drops them),
keeps the `.bbl`, and proves the package stands alone via a clean-room recompile. See
`/camera-ready-prep` Step 8.

### Step 8: Output Summary

```markdown
## Compilation Report

- **Status**: SUCCESS / FAILED
- **PDF**: paper/main.pdf
- **Pages**: X (main body to Conclusion) + Y (references) + Z (appendix)
- **Within page limit**: YES/NO (MAX_PAGES = N)
- **Errors fixed**: [list of auto-fixed issues]
- **Warnings remaining**: [list of non-critical warnings]
- **Undefined references**: 0
- **Undefined citations**: 0

### Next Steps
- [ ] Visual inspection of PDF
- [ ] Run `/paper-write` to fix any content issues
- [ ] Submit to [venue] via OpenReview / CMT / HotCRP
```

## Key Rules

- **Never delete the user's source files** — only modify to fix errors
- **Keep compile.log** — useful for debugging
- **Don't suppress warnings** — report them, let the user decide
- **If LaTeX is not installed**, provide clear installation instructions rather than failing silently
- **Font embedding is critical** — some venues reject PDFs with non-embedded fonts
- **Page count rules differ by venue** — ML conferences: main body to Conclusion (refs excluded). **IEEE venues: total pages including references.**

## Common Venue Requirements

| Venue | Style File | Citation | Page Limit | Refs in limit? | Submission |
|-------|-----------|----------|------------|----------------|------------|
| ICLR 2026 | `iclr2026_conference.sty` | `natbib` (`\citep`/`\citet`) | 9 pages (to Conclusion end) | No | OpenReview |
| NeurIPS 2025 | `neurips_2025.sty` | `natbib` (`\citep`/`\citet`) | 9 pages (to Conclusion end) | No | OpenReview |
| ICML 2025 | `icml2025.sty` | `natbib` (`\citep`/`\citet`) | 8 pages (to Conclusion end) | No | OpenReview |
| IEEE Journal | `IEEEtran.cls` [journal] | `cite` (`\cite{}`, numeric) | ~12-14 pages (Transactions) / ~4-5 (Letters) | **Yes** | IEEE Author Portal / ScholarOne |
| IEEE Conference | `IEEEtran.cls` [conference] | `cite` (`\cite{}`, numeric) | 5-8 pages (varies by conf) | **Yes** | EDAS / IEEE Author Portal |

---
name: camera-ready-prep
description: >-
  Prepare a conference/journal paper for camera-ready / final submission after an
  accept-or-revise decision. Use this whenever the user has an acceptance decision,
  a decision/review folder, or reviewer comments and wants to (1) turn the reviews
  into an actionable revision checklist, (2) de-anonymize and order authors for the
  camera-ready, (3) fix figure/formatting issues reviewers flagged, (4) make the PDF
  pass the submission system's compliance checks (Type 3 font rejection, page limits,
  embedded fonts), (5) produce the plain-text abstract the submission form needs, and
  (6) build a self-contained, symlink-free arXiv source package from the LaTeX project.
  Trigger on: "camera ready", "camera-ready", "final version", "process the decision",
  "decision folder", "reviewer comments/审稿意见", "submit to IROS/ICRA/RA-L/RSS/CoRL",
  "PaperCept/RAS submission", "处理审稿意见", "准备终稿/相机就绪版", "去匿名/添加作者",
  "Type 3 字体", "提交摘要", "开源链接", "打包 arXiv", "arXiv 投稿/提交", "submit to arXiv",
  "package for arXiv", "arXiv tarball/zip", "投预印本" — even if the user only hands over a
  decision folder and a paper directory without naming the full workflow. Generated documents
  default to Chinese and are written into the decision folder.
---

# Camera-Ready Preparation

Help an author go from an acceptance decision to a clean, compliant, submittable
camera-ready package. This skill does two kinds of work: **analysis** (read the
decision, produce a revision checklist) and **action** (edit the paper: authors,
figures, formatting, PDF compliance, abstract). Lead with the analysis so the user
sees the full picture, then act on the parts they approve.

## What the user provides

- **Paper directory** — the LaTeX project root (e.g., contains `root.tex`, `Sections/`, `Images/`).
- **Decision folder** — reviewer comments, AE/meta-review, similarity (iThenticate/CrossCheck) report, etc.
- **Author info** — the final author order, who are co-first and who are co-corresponding, plus a source of affiliations + emails (often an `authors.json`). The user may give this incrementally ("add X as the third from last").
- **Target venue** — e.g., IROS/ICRA/RA-L. If unstated, infer it from the decision text (the submission system, conference name, PIN URL all hint at it).

## Output conventions (defaults)

- **Language: Chinese (中文)** for all generated documents, unless the user asks otherwise.
- **Location: the decision folder.** Write `审稿修改清单.md` and `提交摘要_纯文本.md` there. Paper edits happen in the paper directory.
- **Faithfulness over completeness.** Never invent experimental numbers, results, or claims to satisfy a reviewer. If a request needs data you don't have, say so and route it to the right checklist bucket (see below). This is the single most important rule — a camera-ready that fabricates is worse than one that honestly defers.
- **Recompile and verify after every paper edit.** Don't trust that an edit is correct; rebuild the PDF and check the rendered result.

## Shared helpers (resolve once, before Step 5 or Step 8)

Two shared-runtime helpers back this skill. Resolve them with the standard chain
(see [`../shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2)
— never hardcode `tools/…`, and never hand-roll their logic:

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
resolve_helper() {   # $1 = helper filename -> echoes path, or empty
  local h p=".aris/tools/$1"
  [ -f "$p" ] || p="tools/$1"
  [ -f "$p" ] || { [ -n "${ARIS_REPO:-}" ] && p="$ARIS_REPO/tools/$1"; }
  [ -f "$p" ] && printf '%s' "$p"
}
FONT_FLATTENER="$(resolve_helper flatten_pdf_fonts.sh)"   # Step 5
ARXIV_PACKER="$(resolve_helper pack_arxiv.sh)"            # Step 8
```

**Failure policy — degrade, don't block.** `$FONT_FLATTENER` unresolved → you can still *audit* with
`pdffonts <file>.pdf | grep -i "Type 3"`, but do **not** hand-roll the flatten step; a bare
`gs -dNoOutputFonts` pass can silently leave a Type 3 font behind, and the helper's whole point is
that it refuses to overwrite when that happens. Report the broken install instead (repair:
`bash tools/install_aris.sh`). `$ARXIV_PACKER` unresolved → tell the user the arXiv package cannot be
built safely and stop that step; do **not** improvise a `zip` of the paper directory (it will carry
symlinks and miss the `.bbl`). Neither failure affects Steps 1–4, 6, 7.

## Workflow

Steps 2–8 are independent; do whichever the user asks for. Step 1 always comes first.
**Step 5 (PDF compliance) is reactive** — run it only when the submission system flags a problem
or the user explicitly asks, never as part of the default pass. **Step 8 (arXiv packaging) is
on-request** — a camera-ready and an arXiv preprint are separate deliverables.

### 1. Identify the venue and load its requirements

Look in `references/` for a file matching the venue. `references/ras-papercept.md` covers
the IEEE RAS / PaperCept family (IROS, ICRA, RA-L, CASE …). Read it — it has the font,
page-limit, and abstract rules you'll need in later steps.

If no reference matches the venue, **research the venue's Author's Kit / Call for Papers
and create a new `references/<venue>.md`** in the same shape, so the library grows over
time. Submission rules (page limits especially) change year to year — sanity-check against
the current CFP rather than trusting memory.

### 2. Build the revision checklist  ← core deliverable

Read every file in the decision folder. Merge the reviewers' and editor's asks by **theme**
(not by reviewer), noting the source (R1/R2/AE) and the section/figure each maps to.

Write the checklist using `assets/checklist_template.md`. The defining feature is the final
**Checklist, categorized by what you can actually do right now**:

- **✅ 现在就能直接改** — text/format only, and the supporting information already exists in the
  paper. These are writing tasks you can execute immediately (e.g., explain a design choice,
  add a loss equation when the method already says "follows ACT" and the hyperparameters are
  in a table, merge duplicate citations, fix a float/paragraph nit).
- **⚠️ 需新实验/新数据/新图** — cannot be done without running something new. The most you can
  do now is add an honest limitation / future-work sentence.
- **❓ 需作者确认或外部资源** — needs an implementation detail only the authors know, or an
  external resource (the iThenticate online report behind a login, an open-source link, etc.).

Why this split: it lets the user see in one glance what you can knock out now versus what
needs them, which prevents both fabrication and pointless back-and-forth. When in doubt about
whether the paper already contains the supporting material, **read the relevant section before
categorizing** — the difference between ✅ and ⚠️ is usually "is the information already here?"

If the abstract or body promises a code/data release, add **"提供开源链接"** to the ❓ bucket and
link it to Step 7.

### 3. De-anonymize and order authors (camera-ready)

Replace the anonymous `\author{...}` block with the real author list. Conventions that keep
this correct and consistent:

- **Order exactly as the user specifies**, including relative positions ("倒数第三" = third from
  last). Recount from the end after each insertion to confirm.
- **Number affiliations by order of first appearance** ($^{1}$, $^{2}$, …).
- **Co-first authors share one mark** (e.g., `*`), **co-corresponding share another** (e.g., `\dag`).
  Add a `\thanks{*Equal contribution; \dag Corresponding Author.}` footnote.
- **Group emails by shared domain** following the project's house style
  (e.g., `\{ghz23,jyf23,chenzx24\}@mails.tsinghua.edu.cn`).
- **Pull every name/affiliation/email from the provided source** (e.g., `authors.json`) and verify
  each email maps to the right person. Watch for near-duplicate names (e.g., "Lei Han" vs "Lei Hao").

After editing, **recompile and read the author line back from the PDF** (`pdftotext -f 1 -l 1`)
to confirm marks, affiliation numbers, and emails render correctly.

### 4. Apply the directly-fixable review items (the ✅ bucket)

Work through the ✅ items. Patterns that came up repeatedly:

- **Duplicate / mergeable references**: confirm the entries are truly the same work, point all
  citations at one key, delete the duplicate from the `.bib`, and recompile so numbering updates
  automatically (don't hand-edit the `.bbl`).
- **Figure/text inconsistency** (text references something not in the figure): fix whichever is
  wrong. Usually the text, since regenerating a rendered figure needs its source. You can also
  enrich a caption to document subpanels the text refers to.
- **Floating/standalone-paragraph nits**: merge the orphan sentence into the adjacent paragraph
  as a lead-in, or restructure so it isn't a lonely line.
- **Length**: a substantive addition (e.g., a new paragraph + equation) can push the paper over
  the page limit. Check page count after; if it grows, tell the user and offer a trim or to comment
  the addition out (`% ...`) with a marker so it's easy to restore later.

### 5. PDF compliance pass (reactive — not part of the default flow)

**Do not run the font check by default.** Most PDFs are fine, the problem only surfaces at upload,
and outlining a figure is a change you don't want to make unless it's actually needed. Trigger this
step only when the submission system rejects the PDF (e.g., "This document has Type 3 fonts on page 6")
or the user explicitly asks for a compliance check.

- **Type 3 fonts** (auto-rejected by IEEE/PaperCept): audit and fix with the shared helper
  `tools/flatten_pdf_fonts.sh`, resolved as `$FONT_FLATTENER` above.

  ```bash
  bash "$FONT_FLATTENER" --check <main>.pdf          # audit only, exit 1 if Type 3 present
  bash "$FONT_FLATTENER" --check Images/*.pdf        # locate the offending figure (batch)
  bash "$FONT_FLATTENER" <figure>.pdf                # flatten in place, keeps <figure>.orig.pdf
  ```

  The usual culprit is a matplotlib-exported figure (matplotlib defaults to Type 3). Flattening
  converts the figure's text to vector outlines — no font objects, no quality loss, bounding box
  preserved. The helper refuses to overwrite if a Type 3 font survives the pass, so a silent
  no-op cannot slip through. Then recompile and re-run `--check` until it reports 0 Type 3.
  (Long-term source fix: regenerate with `matplotlib.rcParams['pdf.fonttype'] = 42`.)
- **Embedded fonts / paper size**: per the venue reference, likewise only when flagged.

Page count is different — it's a natural consequence of editing, so check it after substantive
additions in Step 4, not here.

### 6. Abstract for the submission form

**Gate — only produce this once the open-source link status is settled.** If the paper promises a
code/data release and the link is not yet decided, do **not** create `提交摘要_纯文本.md` at all — not
even a draft or placeholder. A half-finished abstract that still says "released upon acceptance" or
carries a TODO link is dangerous precisely because it looks ready to paste into the submission form,
so the file must not exist until the question is resolved (link provided, or explicitly declined —
see Step 7). If the paper makes no open-source promise, there is nothing to wait on; proceed.

The submission system's abstract box is **not** LaTeX. Convert the paper's abstract to the venue's
plain-text rules (see the reference; for RAS/PaperCept: plain text, only `<b> <i> <sub> <sup>`
recognized, excess truncated). Transformations:

- `\url{X}` → bare `X`; strip `\cite{}`, `\label{}`, comments.
- Math/markup → allowed tags: `$F_{ext}$` → `F<sub>ext</sub>`, `$x^2$` → `x<sup>2</sup>`,
  `\textbf{}` → `<b>`, `\emph{}`/`\textit{}` → `<i>`. If the abstract has no math/markup, the
  result is just clean prose with no tags.

Save to `提交摘要_纯文本.md` using `assets/abstract_plaintext_template.md` — include the ready-to-paste
text, the character + word count (so the user can judge truncation), and a note on which tags (if any)
were used. Verify the count with `wc -c`/`wc -w` rather than estimating.

### 7. Open-source link handling (state machine)

If the paper promises a code/data release, the camera-ready should not still say "released upon
acceptance". Treat the link as a small state machine:

- **Promised but link not yet decided** → keep "提供开源链接" open in the checklist (❓ bucket), and do
  **not** create `提交摘要_纯文本.md` at all — no draft, no placeholder. The submission abstract is
  withheld entirely until the link is settled.
- **User provides a link** → put it in the abstract (`\url{...}`), recompile, and **now** save the
  final compliant plain-text abstract to `提交摘要_纯文本.md`.
- **User explicitly declines / no link** → use a neutral phrasing (or remove the sentence), note the
  decision, and **now** save the final abstract md.

The submission abstract md is created **only** once the link question is resolved one way or the other
(provided or explicitly declined). Until then, no abstract file — and no draft — is produced.

### 8. arXiv preprint package (on request)

Posting the accepted version to arXiv is a separate deliverable from the camera-ready. **Never
assemble the archive by hand** (`zip -r paper.zip paper/` is wrong three different ways) — use the
canonical packer resolved above:

```bash
bash "$ARXIV_PACKER" --paper <paper-dir> --main <main-basename>
```

It exists because arXiv re-compiles your source on its own machines, so the package must be
self-contained. The script builds once to refresh `main.fls`, reads the recorder file to learn
**exactly which files LaTeX opened** (rather than grepping `\input`/`\includegraphics`), adds the
`.bib`/`.bst` that bibtex needs but `.fls` never lists, copies everything into a clean staging dir
with `cp -L` so no symlink survives (arXiv silently drops symlinks and you get a broken build), then
**recompiles the staged copy in isolation** and fails loudly if it does not stand alone. It also
warns on `.eps`/`.ps` figures that pdfLaTeX cannot embed.

Notes for the user:
- **Keep the `.bbl`.** The packer ships it deliberately. On arXiv's "Review Files" screen the `.bbl`
  is auto-suggested for deletion — uncheck it. It is the exact bibliography that passed the
  clean-room build; deleting it makes the reference list depend on arXiv re-running bibtex.
  The `.bib` ships too, which is what their "a .bib file is preferred" note is really asking for.
- Upload the resulting archive only — delete any previously uploaded PDF first (arXiv rejects
  TeX-produced PDFs).
- Useful flags: `--targz` (instead of the default `.zip`), `--out <file>`, `--keep-staging`
  (inspect what was collected), `--no-verify` (skip the clean-room recompile — not recommended).

## Files in this skill

- `assets/checklist_template.md` — the revision-checklist template (with the categorized Checklist).
- `assets/abstract_plaintext_template.md` — the submission-form abstract template.
- `references/ras-papercept.md` — IROS/ICRA/RA-L/CASE (PaperCept) requirements. Add siblings for other venues.

Shared-runtime helpers this skill invokes (resolved, not vendored): `tools/flatten_pdf_fonts.sh`
(Step 5), `tools/pack_arxiv.sh` (Step 8). See [`../../tools/README.md`](../../tools/README.md).

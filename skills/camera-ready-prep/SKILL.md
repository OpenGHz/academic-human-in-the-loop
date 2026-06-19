---
name: camera-ready-prep
description: >-
  Prepare a conference/journal paper for camera-ready / final submission after an
  accept-or-revise decision. Use this whenever the user has an acceptance decision,
  a decision/review folder, or reviewer comments and wants to (1) turn the reviews
  into an actionable revision checklist, (2) de-anonymize and order authors for the
  camera-ready, (3) fix figure/formatting issues reviewers flagged, (4) make the PDF
  pass the submission system's compliance checks (Type 3 font rejection, page limits,
  embedded fonts), and (5) produce the plain-text abstract the submission form needs.
  Trigger on: "camera ready", "camera-ready", "final version", "process the decision",
  "decision folder", "reviewer comments/审稿意见", "submit to IROS/ICRA/RA-L/RSS/CoRL",
  "PaperCept/RAS submission", "处理审稿意见", "准备终稿/相机就绪版", "去匿名/添加作者",
  "Type 3 字体", "提交摘要", "开源链接" — even if the user only hands over a decision
  folder and a paper directory without naming the full workflow. Generated documents
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

## Workflow

Steps 2–7 are independent; do whichever the user asks for. Step 1 always comes first.
**Step 5 (PDF compliance) is reactive** — run it only when the submission system flags a problem
or the user explicitly asks, never as part of the default pass.

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

- **Type 3 fonts** (auto-rejected by IEEE/PaperCept): run `scripts/check_pdf_fonts.sh <main>.pdf`.
  If any are found, locate the offending figure by running the same script on each figure PDF
  (`scripts/check_pdf_fonts.sh Images/*.pdf`). The usual culprit is a matplotlib-exported figure
  (matplotlib defaults to Type 3). Fix it with `scripts/outline_fonts.sh <figure>.pdf`, which uses
  Ghostscript `-dNoOutputFonts` to convert the figure's text to vector outlines — no font objects,
  no quality loss, bounding box preserved — and backs up the original. Then recompile and re-run
  the check until it reports 0 Type 3. (Long-term source fix: regenerate with
  `matplotlib.rcParams['pdf.fonttype'] = 42`.)
- **Embedded fonts / paper size**: per the venue reference, likewise only when flagged.

Page count is different — it's a natural consequence of editing, so check it after substantive
additions in Step 4, not here.

### 6. Abstract for the submission form

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

- **Promised but link not yet decided** → keep "提供开源链接" open in the checklist (❓ bucket). Do not
  finalize the abstract md yet.
- **User provides a link** → put it in the abstract (`\url{...}`), recompile, and **save the final
  compliant plain-text abstract** to `提交摘要_纯文本.md`.
- **User explicitly declines / no link** → use a neutral phrasing (or remove the sentence), note the
  decision, and **save the final abstract md** anyway.

The trigger for producing the *final* submission-ready abstract md is that the link question has been
resolved one way or the other. Until then it stays pending.

## Files in this skill

- `assets/checklist_template.md` — the revision-checklist template (with the categorized Checklist).
- `assets/abstract_plaintext_template.md` — the submission-form abstract template.
- `references/ras-papercept.md` — IROS/ICRA/RA-L/CASE (PaperCept) requirements. Add siblings for other venues.
- `scripts/check_pdf_fonts.sh` — list fonts in a PDF, flag Type 3 (exit 1 if any).
- `scripts/outline_fonts.sh` — outline a PDF's fonts via Ghostscript to remove Type 3 (backs up original).

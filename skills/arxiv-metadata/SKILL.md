---
name: arxiv-metadata
description: "Extract arXiv submission metadata from a finished paper and emit copy-paste-ready values for every field on the arXiv submission form: Title, Author(s), Abstract, Comments, Report-no, Journal-ref, DOI, ACM-class, MSC-class, plus a suggested primary category. Enforces arXiv's actual rules from info.arxiv.org/help/prep.html: metadata fields are ASCII-only (Unicode must become TeX accent commands, NOT the reverse), abstracts over 1920 characters are rejected outright, custom macros must be spelled out, no all-caps, no 'et al.', affiliations go in parentheses with the numbered format, ACM-class is cs-archive-only and MSC-class is math-archive-only. Detects anonymized submissions and refuses to invent an author list (arXiv refuses anonymous submissions). Use when user says \"arxiv metadata\", \"提交 arxiv\", \"arxiv 信息\", \"投 arxiv\", \"fill arxiv form\", \"arxiv submission info\", \"准备 arxiv 提交\", or is about to upload a paper to arXiv."
argument-hint: "[paper-directory]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob
---

# arXiv Metadata Extractor

Extract arXiv submission metadata from the paper at: **$ARGUMENTS**

## Context

The arXiv submission form asks for 9 metadata fields plus a category. Most can be derived mechanically from the LaTeX source and the compiled PDF, but arXiv's field rules are stricter and less intuitive than they look, and violating them costs a re-submission cycle:

- **All metadata fields are ASCII-only.** The usual instinct — "clean up the LaTeX by converting `\'e` to `é`" — is exactly backwards.
- **Abstracts over 1920 characters are rejected**, not truncated.
- Custom macros render literally; arXiv has no access to your preamble.
- Affiliations are *allowed* in the Authors field, but only in a specific parenthesized format.

This skill reads the paper once and emits a single `ARXIV_METADATA.md` with a copy-paste block per form field, in form order, plus a warnings section and an audit trail of every transformation applied.

**Authority:** all rules below come from [arXiv's official submission-prep guide](https://info.arxiv.org/help/prep.html). Where this skill states a hard limit or a "do not", it is quoting arXiv policy, not a house style preference.

**Scope:** metadata only. This skill does not upload anything, does not build the submission tarball, and does not modify the paper. Its only write is `ARXIV_METADATA.md`.

Sibling skill: [`../arxiv/SKILL.md`](../arxiv/SKILL.md) searches and **downloads** papers *from* arXiv. This skill prepares a paper *for* arXiv. No overlap.

## Constants

- **PAPER_DIR** — directory containing `main.tex` and the compiled `main.pdf`. Default `paper/`. Override by passing it as `$ARGUMENTS`.
- **OUTPUT_MD = `ARXIV_METADATA.md`** — written into `PAPER_DIR`.
- **ABSTRACT_HARD_LIMIT = 1920** — characters. arXiv's own wording: *"abstracts longer than 1920 characters will not be accepted"*. This is a **hard gate**, not a warning — over the limit, the field is marked `BLOCKED` and the user is told how much to cut.
- **EMAIL_WRAP_WIDTH = 80** — arXiv wraps the abstract to 80 characters for the email announcement. Affects only how deliberate line breaks behave (see Step 4).

## Cross-cutting rule: metadata fields are ASCII-only

arXiv: *"Our metadata fields only accept ASCII input."* This governs Title, Authors, and Abstract simultaneously, so resolve it once before touching any field.

**The conversion direction is Unicode → TeX, not TeX → Unicode.** A LaTeX source that already contains `\'e` or `\"o` is *already correct* for arXiv. Leave it alone. What needs fixing is Unicode that crept in — usually from a PDF copy-paste.

| Found in source | Do | Result |
|---|---|---|
| `\'e`, `\"o`, `\v{S}`, `{\ss}` | **keep as-is** | arXiv renders é, ö, Š, ß |
| Literal `é`, `ö`, `Š`, `ß` | convert to TeX accent form | `\'e`, `\"o`, `\v{S}`, `{\ss}` |
| Curly quotes `“ ”` `‘ ’` | convert to ASCII `"` `'` | most common "Bad character" cause |
| Em/en dash `—` `–` | convert to ASCII `-` or `--` | arXiv names these as frequent offenders |
| Ligature glyphs `ﬁ` `ﬂ` | retype as `fi` `fl` | pasted from PDF as single glyphs |
| Ellipsis `…` | retype as `...` | |
| Non-breaking space, thin space | retype as a plain space | |

The TeX accent subset arXiv accepts *"only accepts characters from ISO Latin 1"* — a name outside Latin-1 (e.g. most CJK) cannot be entered as an accent command. Use the Latin transliteration the author publishes under.

**Detection sweep** — run this before assembling any field, and put every hit in the warnings section:

```bash
# Find non-ASCII bytes in the fields we care about, with line numbers
grep -nP '[^\x00-\x7F]' "$PAPER_DIR/main.tex" 2>/dev/null
grep -rnP '[^\x00-\x7F]' "$PAPER_DIR"/sections/*.tex 2>/dev/null | grep -iE 'abstract|title|author'
```

arXiv's own advice when a character is unidentifiable: *"If you can't figure it out, type it out."*

## Workflow

### Step 1: Locate the source files

```bash
PAPER_DIR="${1:-paper}"

[ -f "$PAPER_DIR/main.tex" ] || { echo "ERROR: $PAPER_DIR/main.tex not found." >&2; exit 1; }
[ -f "$PAPER_DIR/main.pdf" ] || echo "WARNING: main.pdf missing — page count unavailable. Run /paper-compile first." >&2

# Where the abstract lives: inline in main.tex, or in a section file
grep -rln 'begin{abstract}' "$PAPER_DIR"/main.tex "$PAPER_DIR"/sections/*.tex 2>/dev/null
```

Read `main.tex` in full (preamble macros, `\title`, `\author`, package options) plus whichever file holds the abstract.

### Step 2: Title

Extract from `\title{...}`. Then apply:

| Rule | Source |
|---|---|
| **No all-caps** — *"Do not use all uppercase letters."* | arXiv |
| **No Unicode** — *"Do not use unicode characters."* Convert per the ASCII table above. | arXiv |
| **Spell out obscure macros** — arXiv's own example: write `Nonlinear Sigma Models`, not `\nlsm` | arXiv |
| **Keep inline math** — MathJax is supported | arXiv |
| **Keep TeX accent commands** — permitted in this field | arXiv |
| Strip `\\`, `\newline` | single-line field |
| Strip `\thanks{...}`, `\footnote{...}` | not part of the title |
| `\textbf{X}` / `\emph{X}` / `\textit{X}` / `\texttt{X}` → `X` | font commands not processed |
| `~` → plain space | |

If the title cites another arXiv paper, use the linkable identifier form `arXiv:YYMM.NNNNN` (or `arXiv:arch-ive/YYMMNNN` for old-style) so arXiv auto-links it.

Preserve the paper's own capitalization otherwise — do not re-title-case.

### Step 3: Author(s)

**First, check for anonymization.** Robotics/ML venues default to double-blind, so a submission-ready `main.tex` frequently has no real author list:

```bash
grep -nE '\\author\{[^}]*[Aa]nonymous' "$PAPER_DIR/main.tex"
grep -nE '\\usepackage\{(corl|neurips|icml|iclr)' "$PAPER_DIR/main.tex"   # no [final] → anonymous
grep -nE '\\usepackage\[(final|preprint)\]' "$PAPER_DIR/main.tex"          # → de-anonymized
```

If anonymous or absent: **stop and ask the user for the real author list.** Do NOT infer it from `git log`, `.bib` self-citations, or file ownership. Two reasons: a wrong author list on arXiv is public and awkward to correct, and arXiv **refuses anonymous submissions** as a matter of policy — misrepresenting identity or affiliation risks *"immediate and permanent suspension."* Emit:

```
*Author(s): ⚠️ BLOCKED — paper is in anonymous mode (line NN). Provide the real author list.
```

and continue with the remaining fields.

When a real author list exists:

State the head count and institution count in one line above the field, so the user can
eyeball it against the paper's author block before pasting — a dropped author is easy to
miss in a long comma-separated string, and the field forbids "et al." shortcuts.

**Name format** — *"Names must be given in the order: Firstname Lastname or Firstname Middlename Lastname"*

- Separate with a comma **or** the word `and`. arXiv's example: `E. L. Grossman, T. Zhou, E. Ben-Naim`
- **Include every author** — *"Include the names of all authors instead of truncating the list with et al."*
- Initials are fine: *"First names and middle names may be abbreviated with just an initial."* Each initial gets a period then a space (`E. L. Grossman`, not `E.L.Grossman`)
- **No all-caps names**
- **Strip** honorifics (`Dr.`, `Professor`) and degree suffixes (`MD`, `PhD`, `MSc`, `BSc`)
- **Keep** unseparated generational suffixes (`Bill Gates Jr`) and particles as written (`John von Neumann`)
- *"Do not enter a name that contains a comma or the word `and'"* — these are the field's separators
- **Roles may not appear here.** *"Roles — such as `editor`, or `appendix author` — may not be indicated within the Authors field"* → move to Comments
- **Do not list AI language tools as authors** (arXiv policy)

**Affiliations are allowed** — this is where most people over-strip. *"Affiliations must be placed within parentheses."* Full mailing addresses are not allowed: at most city and country, never street or postal code. For shared institutions, arXiv's numbered format:

```
Author One (1), Author Two (1 and 2), Author Three (2) ((1) Institution One, (2) Institution Two)
```

So: strip LaTeX affiliation *markup* (`$^{1}$`, `\textsuperscript{2}`, `*`, `†`, `‡`, `\thanks{}`, `\affiliation{}`, `\And`/`\AND`), then optionally re-express the affiliations in arXiv's parenthesized form. Ask the user whether to include affiliations — both including and omitting them are valid.

**Collaborations**, if applicable, have three accepted patterns:
- `ABCD Collaboration: Author One, Author Two`
- `Author One, Author Two, for the ABCD Collaboration`
- `Author One, Author Two (the ABCD Collaboration)` — note this form does not link to a collaboration search

Warn (do not block) if a cleaned name still contains a digit, `@`, or a stray symbol — a marker survived the strip.

### Step 4: Abstract

Extract everything between `\begin{abstract}` and `\end{abstract}`. **Omit the literal word "Abstract"** — arXiv adds its own heading.

**Hard length gate** — check this first, because it can invalidate all other work on the field:

```bash
# Character count of the cleaned abstract. arXiv rejects > 1920.
printf '%s' "$CLEANED_ABSTRACT" | wc -m
```

Over 1920 → mark the field `BLOCKED`, report the actual count and the overage (`2104 chars — cut 184`). Do not silently truncate; cutting an abstract is an authorial decision. Offer to hand it to `/paper-writing-polish-loop` or `/paper-write` for a principled trim.

**Must remove** (these render literally or are explicitly unprocessed):

| Pattern | Action | Why |
|---|---|---|
| `\cite{}`, `\citep{}`, `\citet{}` | delete, repair surrounding grammar | no bibliography in the metadata field |
| `\ref{}`, `\cref{}`, `\autoref{}` | delete, or inline the literal number | no cross-ref resolution |
| `\label{}` | delete | |
| `\footnote{}` | delete, or inline if load-bearing | |
| `%` comments | delete to end of line | |
| `\%`, `\&`, `\_`, `\#`, `\$` **outside** `$...$` | → plain `%`, `&`, `_`, `#`, `$` | the abstract field is plain text, not a TeX document; the backslash survives verbatim (a literal `69-88\%` is what readers see) |
| `\em`, `\it`, `\textbf{}`, `\emph{}`, `\textit{}`, `\texttt{}` | → contents | arXiv: font commands *"will not be processed"* |
| `~`, `\,`, `\ ` (backslash-space) | → plain space | arXiv names these spacing TeX-isms explicitly |
| `\\`, `\newline`, `\par` | → plain space | see line-break rules below |
| Custom preamble macros | **expand inline** | arXiv has no preamble |

**Must keep:**
- Inline math `$...$` — *"Some TeX commands are supported via MathJax"*
- TeX accent commands — permitted in this field
- Escapes **inside** `$...$` (MathJax processes them there) — e.g. `$50\%$` is fine, but prefer moving the percent outside the math

**On `\%` specifically:** the abstract field is not compiled as a LaTeX document, so an escape that is mandatory in the paper source becomes a defect here. Only the parts wrapped in `$...$` reach MathJax; everything else is delivered as-is, backslash included. Unescape all of them — `16--30\%` → `16-30%`. This is the same class of error as shipping a literal `\ourmethod`: correct in the source, wrong in the field.

**Line breaks and whitespace** — arXiv's mechanism is unusual:
- The abstract is wrapped to 80 characters for the email announcement.
- Carriage returns are *"discarded unless they are followed by leading white spaces"*. So a bare newline vanishes; a newline **followed by indentation** forces a real break.
- *"Do not start lines with whitespace (spaces, tabs, etc.)"* — except deliberately, to block auto-wrapping (e.g. for a small table of contents).
- Practical guidance: emit **one single paragraph with no leading whitespace on any line**. That is what a normal paper abstract wants.

**Custom-macro sweep.** The step most people skip, and the most common arXiv metadata defect. List every macro the preamble defines, then check the abstract for each:

```bash
# Macro names defined in the preamble (and math_commands.tex if present)
grep -hoE '\\(newcommand|renewcommand|def|DeclareMathOperator)\*?\{?\\([A-Za-z]+)' \
  "$PAPER_DIR"/main.tex "$PAPER_DIR"/math_commands.tex 2>/dev/null \
  | grep -oE '\\[A-Za-z]+$' | sort -u
```

Expand every hit inline. If a macro appears in the abstract and cannot be expanded (depends on a package), flag it — never ship a literal `\ourmethod` to arXiv. This mirrors arXiv's own title guidance to spell out `\nlsm` as "Nonlinear Sigma Models".

**Cross-references** to other arXiv papers: use `arXiv:YYMM.NNNNN` so arXiv auto-links.

### Step 5: Comments

Optional but strongly recommended — arXiv says it *should* state *"number of pages and number of figures"*, and it is the correct home for venue status.

**Page count** — arXiv convention is the whole submission:

```bash
pdfinfo "$PAPER_DIR/main.pdf" | grep Pages
```

If the appendix is large, the common phrasing splits it: `9 pages main text, 22 pages total`.

**Figure and table counts:**

```bash
grep -rhcE '\\begin\{figure\*?\}' "$PAPER_DIR"/main.tex "$PAPER_DIR"/sections/*.tex 2>/dev/null | awk '{s+=$1} END {print s}'
grep -rhcE '\\begin\{table\*?\}' "$PAPER_DIR"/main.tex "$PAPER_DIR"/sections/*.tex 2>/dev/null | awk '{s+=$1} END {print s}'
```

**Venue status** — read it, do not assume:
- Style package (`corl_2026`, `neurips_2025`, `icml2025`, `IEEEtran`) names the target venue.
- `NARRATIVE_REPORT.md` `## Target Venue` or `PAPER_PLAN.md` if present.
- Phrasing by actual status: `Accepted at CoRL 2026` (only if genuinely accepted) / `Submitted to CoRL 2026` / `Under review` / `Preprint`.
- **Never write "Accepted" without the user's explicit confirmation.** A false acceptance claim is a real problem, and arXiv notes these details *are not editable after announcement*.

**Also belongs here:**
- Author roles arXiv bars from the Authors field: `Appendix by Jane Smith`, `Editor: ...`
- Project page / code URLs. arXiv converts URLs to "this http URL" links, and requires that you *"add a space to separate any periods or text following a URL from the URL itself"* — so write `https://example.github.io/proj .` not `https://example.github.io/proj.`

```bash
grep -rhoE 'https?://[A-Za-z0-9./_%#?=&+-]+' "$PAPER_DIR"/main.tex "$PAPER_DIR"/sections/*.tex 2>/dev/null \
  | grep -viE 'arxiv\.org|doi\.org|github\.io/latex|ctan' | sort -u
```

If the paper is anonymous, a project URL is probably an anonymized placeholder — flag rather than publish it.

**Prohibited here:** *"Do not put copyright statements in the comments, put them on the front page of the article."* Nothing in Comments may contradict the license granted.

**On replacements:** the field *"is not cumulative"* — a v2 comment must re-state page count and prior details, plus describe what changed.

Example assembled Comments:

```
8 pages main text, 22 pages total, 6 figures, 4 tables. Submitted to CoRL 2026. Project page: https://example.github.io/proj
```

### Step 6: Report-no, Journal-ref, DOI

Emit these explicitly, with the reason when blank, so the user does not wonder whether the skill skipped them.

**Report-no** — only an institution's locally assigned publication number. arXiv: *"Do not put any other information in this field."* Format example: `EFI-94-11`. Almost always blank for conference submissions. Grep near the title for `report` / `technical report`.

**Journal-ref** — *"only for a full bibliographic reference if the article has already appeared in a journal or a proceedings."*
- Must *"Indicate the volume number, year, and page number (or page range)."*
- Multiple references separated by *"a semicolon and a space"*: `J.Hasty Results 1 (2008) 1-9; Erratum: J.Hasty Results 2 (2008) 1-2`
- *"Do not put URLs into this field, as they will not be converted into links."*
- A pending submission is **not** a journal reference — that goes in Comments. A journal ref can be added later via arXiv's jref facility.

**DOI** — only a DOI resolving to another version (e.g. the published journal version).
- *"Do not add the arXiv assigned DOI to this field"* — arXiv assigns and registers its own.
- Multiple DOIs *"separate[d] ... with a space"*.
- Nothing else belongs in the field.

### Step 7: ACM-class, MSC-class, primary category

**These two are archive-gated** — a detail worth getting right, because offering the wrong one wastes the user's time:

| Field | Available in | Format |
|---|---|---|
| **ACM-class** | **cs archive only** | ACM Computing Classification System codes, *"Separate multiple classifications by a semicolon and a space."* arXiv's example: `F.2.2; I.2.7` |
| **MSC-class** | **math archive only** | Mathematics Subject Classification codes, comma-separated, with `(Primary)` / `(Secondary)` keywords in parentheses. arXiv's example: `14J60 (Primary) 14F05, 14J26 (Secondary)`. `(Primary)` is optional if there is only one. |

So for a `cs.RO` robotics paper: fill **ACM-class**, leave **MSC-class** blank (unavailable outside the math archive).

**ACM-class suggestions** for this repo's typical papers — pick 1-3 by actual topic:

| Code | Area |
|---|---|
| `I.2.9` | Robotics |
| `I.2.6` | Learning (machine learning) |
| `I.2.10` | Vision and Scene Understanding |
| `I.2.8` | Problem Solving, Control Methods, Search |
| `I.4` | Image Processing and Computer Vision |
| `I.5.4` | Pattern Recognition — Applications |

**Primary category** — the next step of the submission flow, not on this form page:

| Category | When |
|---|---|
| `cs.RO` | robotics is the core contribution → primary for robot-learning papers |
| `cs.LG` | the method is the contribution, robots are the testbed |
| `cs.CV` | perception / vision is the core |
| `cs.AI` | general AI framing |
| `cs.SY` / `eess.SY` | control-theoretic |

For a CoRL-style paper: `cs.RO` primary, cross-list `cs.LG` (plus `cs.CV` if perception-heavy).

### Step 8: Write `ARXIV_METADATA.md`

Write to `<PAPER_DIR>/ARXIV_METADATA.md`, field order matching the form:

````markdown
# arXiv Submission Metadata

Source: `<PAPER_DIR>` | Generated: <ISO-8601 date>
Rules: https://info.arxiv.org/help/prep.html
Status: <READY | BLOCKED: <reason> | WARNINGS: N>

---

## *Title

```
<cleaned title, single line, ASCII-only, not all-caps>
```

## *Author(s)

<N> authors across <M> institutions, all listed in full (arXiv forbids truncating
with "et al."). Order follows the paper's author block.

```
<Firstname Lastname, F. M. Lastname, Firstname Lastname>
```

<if affiliations included, show arXiv's parenthesized form>
<if blocked: ⚠️ BLOCKED — anonymous mode detected at main.tex:NN. arXiv refuses
anonymous submissions. Provide the real author list.>

## *Abstract

```
<de-LaTeXed, ASCII-only, single paragraph, no leading whitespace>
```

Length: <N> / 1920 characters <— ⚠️ BLOCKED: over hard limit, cut <N-1920> if applicable>

## Comments

```
<N pages main text, M pages total, F figures, T tables. <venue status>. Project page: <url> .>
```

## Report-no

```
(blank — no institutional report number found)
```

## Journal-ref

```
(blank — not yet published; pending submissions belong in Comments)
```

## DOI

```
(blank — no publisher DOI yet; arXiv assigns its own, which must not go here)
```

## ACM-class

```
I.2.9; I.2.6
```

## MSC-class

```
(N/A — math archive only; this is a cs submission)
```

---

## Not on this form page, but next in the flow

- **Primary category:** `cs.RO`
- **Cross-list:** `cs.LG`
- **License:** arXiv's default perpetual non-exclusive license is the safe pick unless your venue requires CC BY.

---

## Warnings

<numbered; omit the section if empty>

1. Non-ASCII character at sections/0_abstract.tex:12 — curly quote `“` → convert to `"`.
2. Abstract contains unexpanded macro `\ourmethod` (sections/0_abstract.tex:8) — expand before pasting.
3. Venue status inferred as "Submitted to CoRL 2026" from `\usepackage{corl_2026}`. Confirm before submitting — do not claim acceptance if not accepted.
4. Affiliations found in source but omitted from the Authors field. Say the word to re-add them in arXiv's parenthesized format.

## Transformations applied

<audit trail, so the user can verify nothing was lost>

- Abstract: removed 4 `\citep{}` calls; repaired grammar at 2 sites.
- Abstract: expanded `\ourmethod` → `TraceFormer`.
- Abstract: converted 2 em-dashes to `-`, 6 curly quotes to ASCII (arXiv is ASCII-only).
- Authors: stripped 3 affiliation superscripts and 1 `\thanks{}`.
- Title: converted `é` → `\'e` (Unicode is not accepted; TeX accent form is).
````

### Step 9: Report to the user

Print a short summary, not the whole file:

```
📋 arXiv metadata extracted → <PAPER_DIR>/ARXIV_METADATA.md

  Title:     <first 60 chars>…
  Authors:   <N> authors   |   ⚠️ BLOCKED (anonymous) if applicable
  Abstract:  <N>/1920 chars, <M> transformations   |   ⚠️ BLOCKED (over limit) if applicable
  Comments:  <the assembled string>
  ACM-class: <codes>
  Category:  cs.RO (primary), cs.LG (cross-list)

  Warnings: <N>  — see the file.
```

If a field is blocked, ask the blocking question inline so the user can resolve it in one turn.

## Key Rules

- **ASCII-only, and the direction is Unicode → TeX.** `\'e` in the source is already correct; leave it. A literal `é` is what needs converting. Getting this backwards is the single easiest way to produce a "Bad character(s) in field" rejection.
- **1920 characters is a hard gate.** arXiv: *"abstracts longer than 1920 characters will not be accepted."* Block, report the overage, and let the user decide the cut. Never silently truncate.
- **Never invent an author list.** If the paper is anonymized, block and ask. Do not infer from `git log`, `.bib` self-citations, or filesystem ownership. arXiv refuses anonymous submissions and treats identity misrepresentation as grounds for permanent suspension.
- **Never claim acceptance.** Infer venue *targeting* from the style package; the words "Accepted at" require the user's explicit confirmation. Default to `Submitted to X` or `Preprint`. arXiv notes Comments is not editable after announcement.
- **Expand every custom macro.** arXiv has no preamble. A literal `\ourmethod` in a published abstract is the most common arXiv metadata defect.
- **Unescape `\%` (and `\&`, `\_`, `\#`) outside math.** The abstract field is plain text, not a compiled document — only `$...$` reaches MathJax. `69-88\%` ships the backslash to the reader. Same failure mode as an unexpanded macro: correct in the paper source, wrong in the field.
- **Affiliations are allowed, not banned.** Strip the LaTeX *markup*, then offer arXiv's parenthesized numbered format. Do not silently drop affiliation information the author put in the paper.
- **Respect the archive gating.** ACM-class exists only in the cs archive; MSC-class only in math. Mark the unavailable one `N/A` with the reason, not blank.
- **Read-only on the paper.** The only file written is `ARXIV_METADATA.md`. If the abstract needs a source fix, report it as a warning and let the user or `/paper-write` do it.
- **Emit every field explicitly**, with the reason when blank or N/A. A field that silently disappears looks like a bug.
- **Audit trail for every transformation**, so the user can confirm no meaning was lost in the de-LaTeXing.

## Output

```
<PAPER_DIR>/
└── ARXIV_METADATA.md    # copy-paste block per form field + warnings + transformation audit
```

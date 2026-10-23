---
name: paper-figure
description: "Generate publication-quality figures and tables from experiment results. Use when user says \"画图\", \"作图\", \"generate figures\", \"paper figures\", or needs plots for a paper."
argument-hint: "[figure-plan-or-data-path]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex, mcp__codex__codex-reply, mcp__antigravity__antigravity, mcp__antigravity__antigravity-reply, mcp__grok__grok, mcp__grok__grok-reply, mcp__claude-review__review, mcp__claude-review__review_reply, mcp__claude-review__review_start, mcp__claude-review__review_reply_start, mcp__claude-review__review_status
---

# Paper Figure: Publication-Quality Plots from Experiment Data

> **Before each reviewer slot**, follow [Selectable Reviewers](../shared-references/reviewer-backends.md):
> resolve invocation → `.aris/reviewer.json` → Claude Code default (Codex MCP)
> with `reviewer_route.py` through the canonical helper resolver, preserving this
> slot's tier, fresh contexts, source/image inputs and deterministic gates.
> Codex examples/pins below apply only to `backend=codex`; other routes use their
> own first-call/reply contract. Save the route and actual returned identity;
> unavailable selections are `REVIEW_UNAVAILABLE`. Classify acceptance from actual
> families/completion/scope. Forward invocation reviewer/model/effort overrides
> to reviewer-bearing children. Generation workers are unchanged.


Generate all figures and tables for a paper based on: **$ARGUMENTS**

## Scope: What This Skill Can and Cannot Do

| Category | Can auto-generate? | Examples |
|----------|-------------------|----------|
| **Data-driven plots** | ✅ Yes | Line plots (training curves), bar charts (method comparison), scatter plots, heatmaps, box/violin plots |
| **Comparison tables** | ✅ Yes | LaTeX tables comparing prior bounds, method features, ablation results |
| **Multi-panel figures** | ✅ Yes | Subfigure grids combining multiple plots (e.g., 3×3 dataset × method) |
| **Architecture/pipeline diagrams** | ❌ No — manual | Model architecture, data flow diagrams, system overviews. At best can generate a rough TikZ skeleton, but **expect to draw these yourself** using tools like draw.io, Figma, or TikZ |
| **Generated image grids** | ❌ No — manual | Grids of generated samples (e.g., GAN/diffusion outputs). These come from running your model, not from this skill |
| **Photographs / screenshots** | ❌ No — manual | Real-world images, UI screenshots, qualitative examples |

**In practice:** For a typical ML paper, this skill handles ~60% of figures (all data plots + tables). The remaining ~40% (hero figure, architecture diagram, qualitative results) need to be created manually and placed in `figures/` before running `/paper-write`. The skill will detect these as "existing figures" and preserve them.

## Constants

- **STYLE = `publication`** — Visual style preset. Options: `publication` (default, clean for print), `poster` (larger fonts), `slide` (bold colors)
- **DPI = 300** — Output resolution
- **FORMAT = `pdf`** — Output format. Options: `pdf` (vector, best for LaTeX), `png` (raster fallback)
- **COLOR_PALETTE = `tab10`** — Default matplotlib color cycle. Options: `tab10`, `Set2`, `colorblind` (deuteranopia-safe)
- **FONT_SIZE = 10** — Base font size (matches typical conference body text)
- **FIG_DIR = `figures/`** — Output directory for generated figures
- **REVIEWER_MODEL = `gpt-6-astra`** — Model used via Codex MCP for figure quality review.
- **PREVIEW = `true`** — After the snippets are written, build `figures/preview.pdf`: a figures-and-tables-only document in the venue's real page layout, so the user (and the reviewer in Step 7) sees every figure and table at printed size with its caption. Override with `— no-preview`.

## Inputs

1. **PAPER_PLAN.md** — figure plan table (from `/paper-plan`)
2. **Experiment data** — JSON files, CSV files, or screen logs in `figures/` or project root
3. **Existing figures** — any manually created figures to preserve
4. **`<paper-dir>/PAPER_PREFERENCES.md`** (if present) — read for figure-relevant standing orders. Bullets in `## Notation` may fix terminology that goes into axis labels and legends; bullets in `## Hard don'ts` may forbid specific figure changes (e.g., "do not change the color of method A's curve — reserved for the ablation panel"). Spec: [`../shared-references/paper-preferences.md`](../shared-references/paper-preferences.md). Missing file → treat as empty.
5. **`idea-stage/TITLE.md`** (if present, from `/title-decider`) — canonical title and **Terminology rulings**; authoritative. Use the ruled terms verbatim in captions, table titles, legends and axis labels; never introduce a synonym for a ruled term. If a new term gets settled while you work, add it to the rulings (see `/title-decider`, Downstream contract) instead of only using it locally.

If no PAPER_PLAN.md exists, scan for data files and ask the user which figures to generate.

## Workflow

### Step 1: Read Figure Plan

Parse the Figure Plan table from PAPER_PLAN.md:

```markdown
| ID | Type | Description | Data Source | Priority |
|----|------|-------------|-------------|----------|
| Fig 1 | Architecture | ... | manual | HIGH |
| Fig 2 | Line plot | ... | figures/exp.json | HIGH |
```

Identify:
- Which figures can be auto-generated from data
- Which need manual creation (architecture diagrams, etc.)
- Which are comparison tables (generate as LaTeX)

### Step 2: Set Up Plotting Environment

Create a shared style configuration script:

```python
# paper_plot_style.py — shared across all figure scripts
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({
    'font.size': FONT_SIZE,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'axes.labelsize': FONT_SIZE,
    'axes.titlesize': FONT_SIZE + 1,
    'xtick.labelsize': FONT_SIZE - 1,
    'ytick.labelsize': FONT_SIZE - 1,
    'legend.fontsize': FONT_SIZE - 1,
    'figure.dpi': DPI,
    'savefig.dpi': DPI,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'axes.grid': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'text.usetex': False,  # set True if LaTeX is available
    'mathtext.fontset': 'stix',
})

# Color palette
COLORS = plt.cm.tab10.colors  # or Set2, or colorblind-safe

def save_fig(fig, name, fmt=FORMAT):
    """Save figure to FIG_DIR with consistent naming."""
    fig.savefig(f'{FIG_DIR}/{name}.{fmt}')
    print(f'Saved: {FIG_DIR}/{name}.{fmt}')
```

### Step 3: Auto-Select Figure Type

Use this decision tree for data-driven figures (inspired by Imbad0202/academic-research-skills):

| Data Pattern | Recommended Type | Size |
|-------------|-----------------|------|
| X=time/steps, Y=metric | Line plot | 0.48\textwidth |
| Methods × 1 metric | Bar chart | 0.48\textwidth |
| Methods × multiple metrics | Grouped bar / radar | 0.95\textwidth |
| Two continuous variables | Scatter plot | 0.48\textwidth |
| Matrix / grid values | Heatmap | 0.48\textwidth |
| Distribution comparison | Box/violin plot | 0.48\textwidth |
| Multi-dataset results | Multi-panel (subfigure) | 0.95\textwidth |
| Prior work comparison | LaTeX table | — |

**DEDUP GATE (mandatory before generating any figure):**

Before generating a figure, check whether a LaTeX table already exists (or is planned) for the same dataset. If yes, do NOT generate the figure — the table is sufficient. A single dataset must appear in exactly ONE of {figure, table} in the main body.

- **Generate a table (not a figure)** when: exact fractions matter, few conditions (≤5×5), downstream tables reference these numbers, or per-condition annotations are needed.
- **Generate a figure (not a table)** when: the visual pattern (trend, shape, non-monotonicity) IS the claim and cannot be conveyed by a table alone.
- **Never generate both** for the same data at the same granularity. If the paper plan lists both a figure and a table for the same dataset, flag the conflict and pick one.

### Step 4: Generate Each Figure

For each figure in the plan, create a standalone Python script:

**Line plots** (training curves, scaling):
```python
# gen_fig2_training_curves.py
from paper_plot_style import *
import json

with open('figures/exp_results.json') as f:
    data = json.load(f)

fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))
ax.plot(data['steps'], data['fac_loss'], label='Factorized', color=COLORS[0])
ax.plot(data['steps'], data['crf_loss'], label='CRF-LR', color=COLORS[1])
ax.set_xlabel('Training Steps')
ax.set_ylabel('Cross-Entropy Loss')
ax.legend(frameon=False)
save_fig(fig, 'fig2_training_curves')
```

**Bar charts** (comparison, ablation):
```python
fig, ax = plt.subplots(1, 1, figsize=(5, 3))
methods = ['Baseline', 'Method A', 'Method B', 'Ours']
values = [82.3, 85.1, 86.7, 89.2]
bars = ax.bar(methods, values, color=[COLORS[i] for i in range(len(methods))])
ax.set_ylabel('Accuracy (%)')
# Add value labels on bars
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{val:.1f}', ha='center', va='bottom', fontsize=FONT_SIZE-1)
save_fig(fig, 'fig3_comparison')
```

**Comparison tables** (LaTeX, for theory papers):
```latex
\begin{table}[t]
\centering
\caption{Comparison of estimation error bounds. $n$: sample size, $D$: ambient dim, $d$: latent dim, $K$: subspaces, $n_k$: modes.}
\label{tab:bounds}
\begin{tabular}{lccc}
\toprule
Method & Rate & Depends on $D$? & Multi-modal? \\
\midrule
\citet{MinimaxOkoAS23} & $n^{-s'/D}$ & Yes (curse) & No \\
\citet{ScoreMatchingdistributionrecovery} & $n^{-2/d}$ & No & No \\
\textbf{Ours} & $\sqrt{\sum n_k d_k / n}$ & No & Yes \\
\bottomrule
\end{tabular}
\end{table}
```

**Architecture/pipeline diagrams** (MANUAL — outside this skill's scope):
- These require manual creation using draw.io, Figma, Keynote, or TikZ
- This skill can generate a rough TikZ skeleton as a starting point, but **do not expect publication-quality results**
- If the figure already exists in `figures/`, preserve it and generate only the LaTeX `\includegraphics` snippet
- Flag as `[MANUAL]` in the figure plan and `latex_includes.tex`
- **Converting a hand-drawn SVG to PDF**: use `tools/svg_to_pdf.py` (resolve via `.aris/tools/` →
  `tools/` → `$ARIS_REPO/tools/`), not `rsvg-convert`/Inkscape — draw.io puts its text in
  `<foreignObject>`, which those two drop silently, giving you a diagram with blank labels.
  See `/figure-spec` Step 3.

### Step 5: Run All Scripts

```bash
# Run all figure generation scripts
for script in gen_fig*.py; do
    python "$script"
done
```

Verify all output files exist and are non-empty. Then **render-then-verify**:
re-open each RENDERED PDF/PNG (not the script) and self-check — no clipped
labels, no legend covering data, every number/label readable at final print
size. This self-check happens BEFORE the Step 7 review, so the reviewer's
budget goes to substance, not to catching clipped axes.

### Step 6: Generate LaTeX Include Snippets

For each figure, output the LaTeX code to include it:

```latex
% === Fig 2: Training Curves ===
\begin{figure}[t]
    \centering
    \includegraphics[width=0.48\textwidth]{figures/fig2_training_curves.pdf}
    \caption{Training curves comparing factorized and CRF-LR denoising.}
    \label{fig:training_curves}
\end{figure}
```

Save all snippets to `figures/latex_includes.tex` for easy copy-paste into the paper.

### Step 6.5: Build the Figures-Only Preview PDF (default; skip with `— no-preview`)

Render every figure and table, with its caption, in the venue's real page layout and nothing else. Printed size is where clipping, unreadable fonts, oversized tables and caption overflow actually show; a figure PDF viewed on its own hides them.

1. **Write `figures/preview.tex`.** Take the preamble (everything before `\begin{document}`) of the venue template `/paper-write` will use, from `../paper-write/templates/` (`IEEE_CONF` and RA-L → `ieee_conference.tex`, which already carries the RAS margin overrides; `ICLR` → `iclr2026.tex`; and so on). Copy any style or class file it needs next to `preview.tex` only if LaTeX cannot find it otherwise. Add the packages and macro files the snippets need (e.g. `booktabs`, the `caption` setup, generated macro files). The body is a title (`<working title>: figures and tables (draft preview)`), one line saying what the document is, and `\input{figures/latex_includes.tex}`, so the preview always shows exactly the snippets the paper will use. Drop bibliography commands and author blocks; keep the venue's anonymity.
2. **Build from the project root, auxiliary files outside the repository:**
   ```bash
   OUT=$(mktemp -d)
   for pass in 1 2; do   # second pass resolves cross-references between captions
     pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$OUT" figures/preview.tex \
       > "$OUT/build.txt" 2>&1 || { echo "preview build failed: see $OUT/preview.log"; break; }
   done
   [ -s "$OUT/preview.pdf" ] && cp "$OUT/preview.pdf" figures/preview.pdf
   ```
   Paths inside the snippets (`figures/...`) resolve because the build runs from the project root. If `pdflatex` is not installed, skip the preview with a warning; do not fail the skill.
3. **Check the build.** No `Overfull \hbox` from a float, cleared by restructuring the table rather than squeezing it (Key Rules, table width); no undefined references (captions may cite each other); `pdffonts figures/preview.pdf` shows every font embedded and none of type Type 3; each `Requested size` line in the log matches the figure's natural size when the figure was made at its printed width (a large rescale changes the printed font size). Fix the cause and rebuild.
4. **Look at the pages.** Rasterize them (`pdftoppm -r 110 -png figures/preview.pdf "$OUT/page"`) and do the render-then-verify check of Step 5 on these pages at printed size: clipped labels, overlaps, legend placement, font sizes, table width, caption length. In two-column layouts a full-width float cannot appear on the page where it is defined, so page 1 normally holds only the title; that is expected.
5. **Report the path** (`figures/preview.pdf`) to the user at the end of the run, and rebuild the preview whenever a figure, table or caption changes in this skill. If the snippets contain placeholder or not-yet-measured data, the preview is a draft: keep the markers visible and say so.

### Step 7: Figure Quality Review with REVIEWER_MODEL

Send figure descriptions and captions to GPT-6-Astra for review. When the preview exists and the selected backend can read images (for `codex exec`, attach the page renders with `-i`), give the reviewer the rendered preview pages as well, so it judges what will actually print:

> Resolve this reviewer slot first; the following is the `backend=codex` example.

```
mcp__codex__codex:
  model: gpt-6-astra
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Review these figure/table plans for a [VENUE] submission.

    For each figure:
    1. Is the caption informative and self-contained?
    2. Does the figure type match the data being shown?
    3. Is the comparison fair and clear?
    4. Any missing baselines or ablations?
    5. Would a different visualization be more effective?

    [list all figures with captions and descriptions]
```

### Step 8: Quality Checklist

The checklist is PARTITIONED (pattern from Anthropic's Claude Science
`figure-style` skill, Apache-2.0): **correctness rules always bind** — they are
about whether the figure tells the truth, have no aesthetic content, and no
style choice may override them; **guidance rules are defaults** — they produce
a clean result, but a deliberate, stated alternative may override them.

**Correctness — always binds, verify against the DATA before the render:**

- [ ] **Excluded data never enters summaries** — a row excluded/flagged in the
      source either disappears entirely or is drawn visibly distinct (open /
      hatched marker, named in the key); it never feeds a mean/CI plotted
      alongside included rows
- [ ] **Captions and any claim-like title text are tested against EVERY plotted
      row** — if one category contradicts the claim, qualify it ("on 3 of 4
      benchmarks") or downgrade to a description; a figure that overclaims is
      wrong even if it renders beautifully
- [ ] **Comparable conditions only** — arms measured under different N / budget
      / protocol are not drawn as visual peers; separate them or mark the
      difference in the caption
- [ ] **State n and what was held fixed** — every panel with a summary mark
      says n and the unit of replication (panel or caption)
- [ ] **Captions, table titles and legends use the paper's terms** — the ones in
      `idea-stage/TITLE.md` Terminology rulings, one per concept; no synonym for the
      compared options or for what was held fixed ("the same network" reads as
      shared weights; "labels" in a caption reads as the plot's text labels);
      ruled terms written in full ("action representation", not "representation");
      "trained policies", not "checkpoints" or "model weights"
- [ ] **A caption describes what is plotted, nothing else** — counts per cell, what
      each mark is, how the compared arms differ; a clause that reconciles this figure
      with another table ("four of the six models of Table I"), or a result from a
      condition the figure does not show, goes in the text; when the caption says how
      one arm runs, it says how the other runs, shared part first
- [ ] **Render-then-verify** — the Step-5 self-check on the RENDERED PDF/PNG
      (not the script) actually happened: no clipped labels, no legend covering
      data, every number/label readable at final print size

**Guidance — strong defaults (from pedrohcgs/claude-code-my-workflow), a
deliberate stated alternative may override — EXCEPT items that Key Rules below
make hard (vector-PDF output and no-titles-inside-figures are Key Rules: treat
those two as binding, not overridable):**

- [ ] Font size readable at printed paper size (not too small)
- [ ] Colors distinguishable in grayscale (print-friendly)
- [ ] **Tables have a short caption and nothing below** — no note paragraph or footnote; caveats are in the text plan, an extra result is its own row group (Key Rules)
- [ ] **Grouped tables put the groups in a first column** — no spanning header rows, indented sub-rows or "same" rows between the data rows (Key Rules)
- [ ] **No protocol-history labels in captions, table titles, footnotes or legends** — no registered / follow-up / post hoc / original protocol / stage names; name each condition by what it is (e.g. "selected execution: chosen on tuning scenes, evaluated on fresh scenes") and say how an option picked on the test data was picked
- [ ] **No title inside figures** — titles go only in LaTeX `\caption{}` (from pedrohcgs)
- [ ] Legend does not overlap data
- [ ] Axis labels have units where applicable
- [ ] Axis labels are publication-quality (not variable names like `emp_rate`)
- [ ] Figure width fits single column (0.48\textwidth) or full width (0.95\textwidth)
- [ ] PDF output is vector (not rasterized text)
- [ ] No matplotlib default title (remove `plt.title` for publications)
- [ ] Serif font matches paper body text (Times / Computer Modern)
- [ ] Colorblind-accessible (if using colorblind palette)

## Output

```
figures/
├── paper_plot_style.py          # shared style config
├── gen_fig1_architecture.py     # per-figure scripts
├── gen_fig2_training_curves.py
├── gen_fig3_comparison.py
├── fig1_architecture.pdf        # generated figures
├── fig2_training_curves.pdf
├── fig3_comparison.pdf
├── latex_includes.tex           # LaTeX snippets for all figures
├── TABLE_*.tex                  # standalone table LaTeX files
├── TABLE_*_facts.tex            # macros for numbers the text needs (no note paragraphs under tables)
├── preview.tex                  # figures-and-tables-only document (Step 6.5)
└── preview.pdf                  # rendered preview at printed size
```

## Key Rules

- **Every figure must be reproducible** — save the generation script alongside the output
- **Do NOT hardcode data** — always read from JSON/CSV files
- **Use vector format (PDF)** for all plots — PNG only as fallback
- **No decorative elements** — no background colors, no 3D effects, no chart junk
- **Consistent style across all figures** — same fonts, colors, line widths
- **Colorblind-safe** — verify with https://davidmathlogic.com/colorblind/ if needed
- **One script per figure** — easy to re-run individual figures when data changes
- **No titles inside figures** — captions are in LaTeX only
- **Comparison tables count as figures** — generate them as standalone .tex files
- **Always build the preview** — every run ends with an up-to-date `figures/preview.pdf` (Step 6.5) unless the user passed `— no-preview`
- **Short table captions, no note paragraph below a table** — the caption (above the table in IEEE style) says only what a reader needs to read the table: metric and units, default conditions, what bold and symbols mean. No footnotes below the table either: everything a reader needs to read the table is in the caption. An extra result that qualifies one row (a number with its interval, e.g. the same comparison against a stronger baseline picked a different way) goes into the table as its own row group, placed right after the row it qualifies and defined in one caption clause; that also shows both sides' values, which a footnote usually omits. Protocol details, sample counts, caveats and definitions go into the paper text, not under the table: list each one with its target section in `PAPER_PLAN.md` for `/paper-write`, and write their numbers as macros (e.g. `figures/TABLE_<name>_facts.tex`) so the text never copies them by hand. This also applies when a reviewer asks for a caveat to "accompany" a table. Paragraph-length table notes are uncommon in robotics venues (RA-L, ICRA, IROS, CoRL) and cost space
- **Grouped tables: groups in their own first column** — when rows fall into groups (conditions, tasks, protocols), put each group's label in a first column that spans its rows (`\multirow{<rows>}{*}{<label>}`; the preamble then needs `multirow`), separate groups with `\midrule`, and keep every data row flat and self-contained. Do not put spanning header rows (`\multicolumn{..}{l}{\emph{<group>}}`) between data rows, and no indented sub-rows (`\quad ...`), back-reference rows ("same, 200 steps") or header rows with empty cells: group headers mixed in with data rows read as clutter. Anything those headers carried that applies to several groups (e.g. registered vs follow-up) goes into one caption sentence, with the groups ordered so that one sentence can state it. A label may have no more lines than its group has rows; shorten it rather than let it overflow. In a table placed in one text column whose group column is what makes it too wide, the group column may be dropped: separate the blocks with `\midrule` and name them in one caption sentence ("Top: ...; middle: ...").
- **Table width: restructure before squeezing** — a table must fit its target column (or the text width for `table*`) with template-default or venue-approved spacing and a readable table font. When it does not, first shorten labels, move shared words into the caption, span a long label over an empty number column, or drop/merge a column while preserving the table's meaning (a group column only as the grouped-tables rule allows); use full width only where the venue permits. Do not use extreme `\tabcolsep` or font reductions, or `\resizebox`, merely to hide an overfull box. Check the rendered width (Step 6.5), not only the log

## Figure Type Reference

| Type | When to Use | Typical Size |
|------|------------|--------------|
| Line plot | Training curves, scaling trends | 0.48\textwidth |
| Bar chart | Method comparison, ablation | 0.48\textwidth |
| Grouped bar | Multi-metric comparison | 0.95\textwidth |
| Scatter plot | Correlation analysis | 0.48\textwidth |
| Heatmap | Attention, confusion matrix | 0.48\textwidth |
| Box/violin | Distribution comparison | 0.48\textwidth |
| Architecture | System overview | 0.95\textwidth |
| Multi-panel | Combined results (subfigures) | 0.95\textwidth |
| Comparison table | Prior bounds vs. ours (theory) | full width |

## Acknowledgements

Design pattern (type × style matrix) inspired by [baoyu-skills](https://github.com/jimliu/baoyu-skills). Publication style defaults and figure rules from [pedrohcgs/claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow). Visualization decision tree from [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills).

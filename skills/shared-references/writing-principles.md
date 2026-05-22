# Orchestra-Adapted Writing Principles

Use this reference when `paper-plan` needs help shaping the paper's story or when `paper-write` needs stronger drafting and revision guidance.

This is the expanded English counterpart to the detailed Chinese version. It is not a new workflow phase. Its purpose is to provide a stronger writing model on top of the existing `insleep` pipeline.

## Contents

- [When to Read](#when-to-read)
- [The Narrative Principle](#the-narrative-principle)
- [Time Allocation and Reviewer Reading Order](#time-allocation-and-reviewer-reading-order)
- [How to Write the Abstract](#how-to-write-the-abstract)
- [Introduction Structure](#introduction-structure)
- [Sentence-Level Clarity](#sentence-level-clarity)
- [Micro-Level Writing Tactics](#micro-level-writing-tactics)
- [Word Choice and Precision](#word-choice-and-precision)
- [Implementation Identifiers Stay Out of the Main Body](#implementation-identifiers-stay-out-of-the-main-body)
- [Method-Level Claims Stay Above the Experimental Choices](#method-level-claims-stay-above-the-experimental-choices)
- [Mathematical Writing](#mathematical-writing)
- [Figure Design](#figure-design)
- [Common Mistakes](#common-mistakes)
- [Pre-Submission Checklist](#pre-submission-checklist)

## When to Read

- Read before locking the framing of the paper.
- Read before drafting the Abstract and Introduction.
- Read when Related Work feels like a literature dump.
- Read when the prose feels generic, templated, or overly AI-shaped.
- Read when the structure looks fine on paper but the draft still feels unconvincing.

## The Narrative Principle

### Neel Nanda's Core View

A paper should be a **short, rigorous, evidence-backed technical story**, not a pile of experiments.

By the end of the Introduction, the reader should clearly understand:

- **The What**: the 1-3 specific claims the paper makes,
- **The Why**: the evidence that supports those claims,
- **The So What**: why the community should care.

### Andrej Karpathy's Complement

A strong paper “sells” **one thing** that was previously absent or non-obvious. The full paper should be organized around that single contribution.

### Practical Rules

- If the core contribution cannot be stated in one sentence, the framing has not converged.
- Every section should serve the same story instead of launching a second one.
- Experiments, related work, and discussion are there to support the main claim, not to operate as independent mini-papers.

### One-Sentence Contribution Test

If you cannot write something like the following, the framing is still too loose:

- “We prove that X converges under assumption Y.”
- “We show that method A improves B by 15% on benchmark C.”
- “We identify failure mode D and propose mechanism E that removes it.”

If the one-sentence contribution is hard to write, the usual causes are:

- the contribution is still too vague,
- the evidence is not yet tightly coupled to the claims,
- or the paper does not yet know what story it is telling.

## Time Allocation and Reviewer Reading Order

### Where Effort Should Go

A useful rule of thumb is to spend roughly the same amount of time on:

1. the Abstract,
2. the Introduction,
3. the Figures,
4. everything else combined.

This is not an exaggeration. Many reviewers form a preliminary judgment before they read the full methods section carefully.

### Common Reviewer Reading Order

Most reviewers encounter the paper in this order:

1. Title
2. Abstract
3. Introduction
4. Figures, especially Figure 1
5. The rest

### Writing Implications

- Put disproportionate effort into the title, abstract, introduction, and hero figure.
- Do not bury the main contribution after Section 3.
- Make the value of the paper legible before the reader reaches the full method.
- If the first two pages are unclear, later brilliance may never be seen.

## How to Write the Abstract

### Sebastian Farquhar's Five-Sentence Formula

Prefer a compact five-part abstract:

1. What you achieved
2. Why the problem is important and difficult
3. How you approached it
4. What evidence supports the claim
5. What number, result, or guarantee the reader should remember

### What a Good Abstract Should Do

- Enter the paper's specific contribution in the first one or two sentences.
- Include at least one explicit quantitative result.
- Be understandable without the main text.
- Avoid undefined acronyms.
- Avoid depending on citations to explain itself.

### A Good Abstract Sketch

```text
We prove that X converges linearly under assumption Y.
This addresses a long-standing question about why optimization remains stable in an apparently non-convex setting.
Our analysis reduces the training dynamics to Z, which yields a tractable theoretical structure.
We validate the prediction on datasets A and B and observe close agreement between theory and experiment.
Compared with prior methods, we reduce error by 15% and provide the first convergence guarantee in this setting.
```

### Openings to Delete

If the first sentence could fit almost any ML paper, delete it.

For example:

- “Large language models have achieved remarkable success...”
- “In recent years, deep learning has...”
- “Neural networks have revolutionized...”

The problem is not just that these openings sound stale. They carry **too little information** to help a reviewer judge the paper's specific contribution.

## Introduction Structure

### Basic Requirements

In two-column conference papers, the Introduction is usually best at about 1-1.5 pages.

It should satisfy the following:

- the method should start appearing by page 2-3 at the latest,
- the Introduction should include 2-4 contribution bullets,
- the central story should already make sense before technical detail arrives.

### Recommended Structure

1. **Opening hook**
   - What problem does the paper address?
   - Why does it matter now?

2. **Background / challenge**
   - Why is the problem hard?
   - What has prior work tried, and why is it insufficient?

3. **Approach overview**
   - What does this paper do differently?
   - What is the key insight?

4. **Contribution bullets**
   - 2-4 items
   - specific and falsifiable
   - ideally no longer than 1-2 lines each

5. **Results preview**
   - surface the strongest result early
   - tell the reader what is worth remembering

6. **Optional roadmap**
   - briefly describe the remaining sections

### Contribution Bullets: Good vs Bad

Good:

- We prove that X converges in O(n log n) under assumption Y.
- We introduce architecture Z, which reduces memory by 40%.
- We improve method A by 15% on benchmark C.

Bad:

- We study problem X.
- We perform extensive experiments.
- We make several contributions to the field.

The problem with the “bad” bullets is not grammar. It is that a reviewer cannot cleanly agree, disagree, or challenge them.

### Hard Cap: At Most Four Bullets

The 2-4 bound is not a soft suggestion. If you find yourself writing a fifth bullet, **stop and merge**. Five bullets almost always means one of:

- two bullets describe the same evidence type and should be merged (e.g. "headline metric on benchmark X" + "ablation that explains why" → one "empirical evidence" bullet);
- one bullet describes the benchmark / dataset rather than the contribution; fold it into §Experiments and let the bullets describe what you *did with* the benchmark;
- one bullet describes an implementation detail (a baseline you also tried, a setup choice) that belongs in §Setup or appendix, not in the framing.

If you cannot drop or merge to four, the paper is probably trying to claim too many things. The reviewer will pick the weakest bullet and reject on it. Better four claims you can defend than five with a weak one in the mix.

## Sentence-Level Clarity

### The Core Insight from Gopen and Swan

Readers have strong structural expectations about prose. If you repeatedly violate those expectations, readers spend effort decoding the sentence instead of understanding the idea.

### Seven Key Principles

#### 1. Keep Subject and Verb Close

Weak:

```text
The model, which was trained on 100M tokens and then fine-tuned with several domain-specific modifications, achieves strong results.
```

Strong:

```text
The model achieves strong results after training on 100M tokens and fine-tuning with domain-specific modifications.
```

#### 2. Put Important Information Near the End

Weak:

```text
Accuracy improves by 15% when using attention.
```

Strong:

```text
When using attention, accuracy improves by 15%.
```

#### 3. Put Context at the Start

Weak:

```text
A new attention mechanism is introduced to solve the alignment problem.
```

Strong:

```text
To address the alignment problem, we introduce a new attention mechanism.
```

#### 4. Move from Old to New

Readers track arguments more easily when the sentence begins with what is already familiar and ends with what is newly important.

#### 5. One Unit, One Function

- A paragraph should ideally do one main job.
- If a sentence is carrying two layers of logic at once, it probably wants to become two sentences.

#### 6. Put Actions in Verbs

Weak:

```text
We performed an analysis of the results.
```

Strong:

```text
We analyzed the results.
```

#### 7. Set the Stage Before New Material

Before presenting an equation, theorem, or experimental result, tell the reader why it matters.

### Fast Revision Questions

When revising a paragraph, ask:

- Is the subject separated from the verb by too much material?
- Does the sentence begin with context?
- Does the sentence end on the point that matters most?
- Is this paragraph trying to do two jobs at once?

## Micro-Level Writing Tactics

### Reduce Ambiguous Pronouns

When `this`, `it`, or `these` could be unclear, replace them with a specific noun.

Weak:

```text
This shows the method is robust.
```

Strong:

```text
These ablation results show that the method is robust to label noise.
```

### Move Verbs Earlier

Readers parse sentences faster when the main verb arrives early.

### Remove Low-Information Fillers

These words can usually be deleted:

- actually
- very
- really
- quite
- basically
- essentially
- Importantly,
- Notably,
- It is worth noting that

### Paragraph Shape

A useful paragraph skeleton is:

- first sentence: the point,
- middle: support,
- last sentence: reinforcement or transition.

Do not bury the key sentence in the middle.

## Word Choice and Precision

### Zachary Lipton Style: Remove Needless Hedging

Unless uncertainty is genuine, avoid overusing:

- may
- can
- might
- potentially

Excessive hedging often reads less like rigor and more like self-doubt.

### Replace Vague Terms with Specific Ones

| Vague Term | Better Alternative |
|-----------|--------------------|
| performance | accuracy / F1 / latency / throughput |
| improves | increases by X% / reduces by Y |
| large | 1B parameters / 100M tokens |
| fast | 3x faster / 50ms latency |
| good results | 92% accuracy / 0.85 F1 |

### Terminology Consistency

Do not rename the same concept across the paper.

For example, avoid mixing:

- model / network / architecture
- training / learning / optimization
- sample / instance / example

Choose the best term and keep it stable.

### Vocabulary Signaling

Some verbs make the work sound like a loose combination of existing pieces:

- combine
- modify
- extend
- expand

Stronger alternatives are often:

- develop
- propose
- introduce
- characterize

This is not about mechanical substitution. It is about how wording changes a reviewer's intuition about whether the work is a real contribution.

## Implementation Identifiers Stay Out of the Main Body

The main body is read by reviewers who do not have your codebase open. Code-shaped identifiers — variable names, CLI flags, environment-specific file paths, project-internal proper nouns, internal metric keys — leak implementation context into a venue that expects conceptual language. They cost the reviewer attention, they age badly (a renamed flag invalidates the prose), and they signal that the framing has not converged from "thing I built" to "thing the field should know about." Push all such identifiers to the appendix, supplementary code release, or footnote, and substitute the conceptual term in the main body.

### What Counts as a Code-Shaped Identifier

The discipline applies to all of:

- **Variable, parameter, and column names** as they appear in source code — including ones the reader is meant to read literally (e.g. fields of a struct, columns of a data frame, attribute access). Write the conceptual quantity instead.
- **Command-line flags and shell invocations** — any token that begins with `-` or `--`, any `script.py arg1 arg2` form, anything that reads like a recipe to re-run a job.
- **Configuration / metric keys** — dotted accessors and dictionary-key strings used inside the codebase to look something up (logging keys, JSON paths into result files, config-namespace identifiers). Rename to the human concept.
- **Project-internal identifiers and dataset slugs** — internal task / dataset / experiment codenames, snapshot tags, and any branch / build identifiers that only mean something inside the team.
- **File paths and module names** — repository-relative paths, package or module references, and config filenames. Reviewers cannot resolve these.
- **Model / framework / API switches as literal flags** — model name plus the literal flag that selected it. The reader needs the model name; the flag is appendix material.

### The Substitution Pattern

For each offending token, ask: *what concept does this stand for, in language a reader who has never seen my codebase would understand?* Substitute the concept in the main body; preserve the literal token in the appendix, methods reproducibility section, or supplementary code release. The literal token is not deleted — it is **relocated** to the audience that needs it.

| Offender | Main-body replacement | Where the literal token belongs |
|----------|----------------------|---------------------------------|
| `state_vector[i].angle_deg` | "the relevant angular component of the state vector" | Appendix table: column-to-concept mapping |
| `--max_envs 7 --max_chains 3` | "capped at seven environments and three chains per group" | Appendix: evaluation protocol / reproducibility |
| `--platform $P --model $M --reasoning $R` | "$M at the chosen reasoning level" | Appendix: exact invocation |
| `metrics.group.accuracy` | "group accuracy" (or whatever the metric is conceptually) | Appendix: metric definition + source key |
| `prompt_template.json` | "the task-keyed prompt template" | Appendix: code release path |
| `benchmark_suite: task_v3` | "the v3 release of the benchmark suite" | Appendix: dataset identifiers |
| `--test_fraction 0.2` | "a 20\% held-out split" | Appendix: split protocol |
| `scripts/run_gated_eval.py` | "the gated-evaluation driver" | Appendix / supplementary code release |
| `experiments/E0X-some-baselines/results.md` | "the baseline results file" | Footnote / supplementary materials index |

### The Appendix Is Where the Literal Token Lives

A short appendix paragraph titled something like "Notation, identifiers, and reproducibility" can host:

- a small **concept-to-identifier table** mapping each concept named in the main body to the literal column / flag / file path,
- the **exact command-line invocation(s)** used to produce the headline numbers,
- the **dataset slugs**, **config filenames**, and **internal task codenames**.

The reviewer who wants to reproduce reaches the appendix; the reviewer who wants to evaluate the claim never has to.

### Exceptions

Three narrow cases where a literal identifier may stay in the main body:

1. **The identifier *is* the concept.** Common-knowledge symbols (`ReLU`, `softmax`, `argmax`, standard dataset names like `ImageNet` / `COCO`) carry meaning across the field. Keep them.
2. **The paper's contribution is precisely a name or a key.** If you are proposing a new metric, the metric's name belongs in the main body.
3. **A short, locally-defined symbol used once for clarity.** If you spell out the concept and then introduce a notation in parentheses (e.g. "the target end-effector pitch, denoted $\theta_p$"), the notation can be used freely afterwards. This is not the same as importing a code identifier — it is defining a paper-internal symbol.

### Figures, Schematics, and In-Image Text Are Part of the Main Body

The discipline above applies to every visible artifact, not just to prose. A reviewer who sees a literal `config_field.subkey` inside Figure 1 has been handed the same code-shaped identifier the main-body prose was supposed to suppress, and the figure is harder to undo because it is rendered, not typeset. Audit and rewrite the in-figure text the same way:

- **Schematic boxes, arrow labels, and legends** — anything inside the figure that the reader can read — must use the conceptual term, not the code identifier. The concept name inside the box, not the JSON path; the human metric ("accuracy ≥ 0.85") on the gate arrow, not the dotted metric key; the evidence concept on the input arrow, not the column-name list.
- **Heatmap / table column headers and row labels** — substitute the concept (a short conceptual label is fine; a literal column accessor is not). Numeric cells stay as numbers.
- **Source-of-truth pointers rendered inside the figure** (`rule from <path>::<key>` style annotations) belong in the caption or appendix, not in the figure itself.
- **Caption copy** — captions are read with the figure, so the same substitution rules apply: no flag tokens, no dotted accessors, no project-internal slugs.

When the literal identifier is essential for reproducibility — e.g. the exact column being read — put it in the appendix's concept-to-identifier table, then reference the concept in the figure and let the appendix carry the literal token.

For Matplotlib / TikZ / draw.io figures the practical workflow is: (a) keep the source file alongside the rendered PDF in `figures/`, (b) edit the source to replace literal identifiers with conceptual labels, (c) re-render. For Codex-generated illustrations, the same edit happens in the regeneration prompt — explicitly enumerate the conceptual labels the figure should use and forbid the code identifiers.

### How to Audit a Draft

A quick mechanical pass on the LaTeX sources:

- grep the draft for `\texttt{...--...}` and any `--word` patterns — every hit is a command-line flag candidate for relocation,
- grep for `\texttt{...}` blocks containing `.` (dotted accessors), `/` (paths), `_` followed by lowercase (likely a code identifier), and underscores between words — each is a candidate,
- grep for filename suffixes (`.py`, `.json`, `.zarr`, `.csv`, `.md`) in the main body — relocate the path, keep the concept,
- read the offending sentence aloud: if it sounds like a README, rewrite it as prose.

And a parallel pass on the figures themselves (the part grep cannot see):

- open every figure PDF / PNG referenced from the main body and read every visible text label — schematic boxes, arrows, legends, axis titles, in-image annotations, footers,
- for each label, ask the same substitution question as for prose: would a reviewer who has never seen the codebase parse this? If not, edit the figure source and re-render,
- check the figure captions in the same pass — captions are prose and inherit every prose rule,
- if the figure was rendered from a notebook or a generation prompt, fix the source so the next regeneration does not reintroduce the identifiers.

A sentence the reader cannot parse without your codebase is a sentence the reader will skip. A figure label the reader cannot parse without your codebase is a figure the reader will mistrust.

## Method-Level Claims Stay Above the Experimental Choices

A method-level claim states *what the paper is contributing*. An experimental choice records *how the contribution was tested*. When the two are confused — when the abstract, introduction, or method-claim is bound to a specific model name (`$MODEL_NAME` / `$VENDOR-$VERSION`), a specific hyperparameter (`K=$k`, threshold = `$T`), or a specific dataset tag (`$dataset_v3`, `setting=$s`) — the contribution reads as if it only works with that exact recipe. Reviewers cannot tell whether the method generalizes; the framing has not separated "the thing we built" from "the way we happened to evaluate it."

A useful self-check: when you read your abstract aloud, can you swap a specific model name for "a sufficiently capable model of that class," or a literal hyperparameter `$K=k_0$` for "a small `$K`," without changing the claim? If yes, the conceptual phrasing is already available — the specific value is appendix or experimental-setup material, not framing. If no, the claim is over-bound to the recipe and should be relaxed.

This is a separate discipline from the implementation-identifier rule above. That rule prevented things like `--some_flag` and `config_file.json` from leaking into the main body. This rule prevents *legitimately-named* concepts — the model, the gate, the cap — from being repeated in their specific form (`$MODEL`, `K=$k`, `n=$N`) across every framing sentence. The literal value is fine; the *repetition* and the *placement in claim sentences* is what makes the contribution look brittle.

### What to Promote to Conceptual Phrasing

- **Specific model names** in abstract / intro / method-claim → "a frozen base $CLASS-of-model", "a recent frontier model", or the model family. The model name belongs in §Experiments / §Setup ("we instantiate the frozen base model with `$MODEL` at the chosen reasoning level").
- **Specific hyperparameter values** (`K=$k`, gate threshold `= $T`, `n=$N` per group) → "a small `$K`", "a held-out accuracy gate", "an evaluation cap". The literal numbers belong in §Setup.
- **Dataset version stamps and difficulty tags** (`"the $v setting"`, `"$dataset_v3 split"`) → the task / dataset name alone, or a difficulty descriptor. Version tags belong in the appendix.
- **Tooling / framework / library choices** (specific library names + versions) → the role the tool plays, not the tool itself. Names go in the supplementary code release.
- **Random seeds, batch sizes, learning rates, GPU counts** → §Implementation Details / appendix.

### Where the Specific Values Belong

One Experimental Setup paragraph collects every concrete choice in one place:

> "We instantiate the frozen base model with `$MODEL` at the chosen reasoning level; the held-out gate passes after `K=$k` consecutive training groups each clear accuracy `≥ $T`; evaluation is capped at `$E` environments × `$C` chains per group on a `$f` held-out split."

Everywhere else in the paper, write about the method, not the recipe. Repeating the recipe values across abstract, intro, and method-claim makes the contribution sound like a specific tuning rather than a general technique.

### The Substitution Pattern

| Claim that over-binds to the recipe | Conceptual rewrite | Where the specific value lives |
|---|---|---|
| "`$MODEL` with our discovered prompt lifts accuracy from `$x` to `$y`." | "A frozen base model with the discovered prompt lifts accuracy from `$x` to `$y`." | §Setup: model choice |
| "Our `K=$k` gated iteration discovers..." | "Our held-out-gated iteration discovers..." (define `$K` once in §Setup) | §Setup: `$K` value |
| "Our `K=$k` train + held-out aggregates of `$a`, `$b`, `$c`..." | "Our train + held-out aggregates of `$a`, `$b`, `$c`..." | §Setup: `$K` and split definition |
| "Trained on `$dataset_v3` data..." | "Trained on the `$task` task (the regime where the prior fails)..." | §Setup / appendix: dataset tag |
| "We use `$MODEL` at `$reasoning_level` throughout." | "We use a frozen frontier model throughout (`$MODEL` at `$reasoning_level` — §Setup)." | §Setup: model + reasoning level |
| "`$task`'s `$MODEL` row hits `$x`..." | "The `$task` reference saturates at `$x` under the frozen base model..." | §Setup / appendix: model row label |

### Where the Specific Values Are Welcome

The discipline only applies *outside* the experimental setup. Inside §Setup / §Implementation Details / §Experiments, the specific values are exactly what the reader is reading that section for. The same holds for ablation captions that explicitly contrast values (`"$K=k_1$ vs. $K=k_2$"`, `"$MODEL_A vs. $MODEL_B"`). Don't strip names from sections that exist to talk about names.

### Reviewer-Side Test

For each method-level claim, ask: *would the contribution still be interesting if the specific value changed?* If yes, abstract over the value. If no, the contribution is the recipe itself, and the paper should declare that explicitly — naming the specific value as the contribution rather than smuggling it into the framing.

### Exceptions

A model / parameter / dataset tag may legitimately appear in the main body in three narrow cases:

1. **The contribution is about the specific artifact.** A paper whose contribution is "we evaluate `$MODEL` on `$BENCHMARK`" needs `$MODEL` in the framing.
2. **The value is the headline result.** A specific number that is *the* result stays — the headline metric is not a recipe knob.
3. **The framing claim is about robustness across a value.** "`$K=k_1$` vs. `$K=k_2$` ablation shows the method is insensitive to `$K`" legitimately uses both because the contrast is the point.

### How to Audit a Draft

A few mechanical passes:

- Count appearances of every specific model name across abstract + introduction + method (not §Setup / §Experiments). More than two is a sign the framing is leaning on the model name; rewrite each occurrence to "the frozen base model" / equivalent and leave one definition pointer to §Setup.
- Count appearances of every literal hyperparameter (`K=$k`, threshold values, evaluation caps) in claim sentences. Promote each repeat to its conceptual name; leave one literal mention in §Setup.
- Read each method-claim sentence and substitute a different model name / value in your head. If the sentence breaks, the claim is over-bound — and is probably less general than the paper means to imply.

## Mathematical Writing

### Core Principle

The goal of mathematical writing is not to sound sophisticated. It is to let the reader **follow** the argument.

Prefer the following:

1. state assumptions formally before the theorem,
2. pair proofs and derivations with intuition,
3. keep notation consistent,
4. define symbols at first use.

### Recommended Notation Habits

```latex
% Scalars: lowercase italic
$x$, $y$, $\alpha$, $\beta$

% Vectors: lowercase bold
$\mathbf{x}$, $\mathbf{v}$

% Matrices: uppercase bold
$\mathbf{W}$, $\mathbf{X}$

% Sets: uppercase calligraphic
$\mathcal{X}$, $\mathcal{D}$

% Named functions: roman
$\mathrm{softmax}$, $\mathrm{ReLU}$
```

### Common Mathematical Writing Mistakes

- presenting equations without telling the reader why they matter,
- introducing assumptions too late,
- reusing symbols with different meanings across sections,
- moving all proof intuition to the appendix and leaving only bare statements in the main text.

For theory papers especially, **intuition and rigor** should coexist.

## Figure Design

### Why Figure 1 Matters

Figure 1 is often one of the first artifacts a reviewer studies after the abstract.

It should usually do at least one of the following:

- explain the core system or method idea,
- show the strongest comparison that justifies the paper,
- or provide the simplest visual summary of the main claim.

### Design Principles

1. **Figure 1 is crucial**
2. **captions should be self-contained**
3. **do not place a decorative title inside the figure**
4. **plots should use vector graphics whenever possible**

### Accessibility

Account for color-vision deficiency.

Do:

- use colorblind-safe palettes,
- avoid red-green pairings,
- make sure the figure still works in grayscale,
- use line styles and markers in addition to color.

### Caption Rules

- A reader should understand the point of the figure from the caption alone.
- State what is being compared.
- State what the reader should notice.
- Do not make the caption depend on the surrounding paragraph for essential meaning.

## Common Mistakes

### Structural Mistakes

| Mistake | Fix |
|--------|-----|
| Introduction longer than 1.5 pages | Move background to Related Work |
| Method buried too late | Front-load the contribution and compress the intro |
| Missing contribution bullets | Add 2-4 concrete claims |
| Experiments not tied to claims | State what each experiment tests |

### Writing Mistakes

| Mistake | Fix |
|--------|-----|
| Generic abstract opening | Start from the paper's actual contribution |
| Inconsistent terminology | Keep one name per concept |
| Too much passive voice | Prefer active constructions |
| Hedging everywhere | Keep hedging only where uncertainty is real |
| Code identifiers, CLI flags, file paths, internal slugs in the main body | Substitute the concept; relocate the literal token to an appendix table |

### Figure Mistakes

| Mistake | Fix |
|--------|-----|
| Raster plots | Use PDF / EPS or other vector output |
| Red-green color schemes | Switch to colorblind-safe palettes |
| Titles inside figures | Move the title into the caption |
| Captions that require the main text | Rewrite them to be self-contained |
| Code identifiers, file paths, or CLI flags rendered inside the figure (schematic boxes, axis labels, in-image annotations) | Edit the figure source, rename labels to conceptual terms, re-render; relocate the literal token to an appendix table |

### Citation Mistakes

| Mistake | Fix |
|--------|-----|
| Related Work as paper-by-paper summary | Reorganize by method family or research question |
| Missing important references | Proactively expand the search |
| AI-generated citations | Use a verification workflow |
| Inconsistent key or style format | Normalize the bibliography |

## Pre-Submission Checklist

### Narrative

- [ ] The contribution can be stated in one sentence.
- [ ] The Introduction makes the What / Why / So What clear.
- [ ] Every major experiment supports a clear claim.

### Structure

- [ ] The abstract follows the five-sentence formula.
- [ ] The Introduction stays within about 1-1.5 pages.
- [ ] The method starts by page 2-3.
- [ ] There are 2-4 concrete contribution bullets.
- [ ] Limitations are clearly stated.

### Writing

- [ ] Terminology is consistent.
- [ ] There are no generic field-background openings.
- [ ] Unnecessary hedging has been removed.
- [ ] All key figures have self-contained captions.
- [ ] No code identifiers, CLI flags, file paths, dotted metric keys, or internal dataset slugs remain in the main body; literal tokens live in an appendix table.
- [ ] Every figure has been opened and visually inspected: no schematic box, arrow label, axis title, or in-image annotation contains a code-shaped identifier; figure captions follow the same rule.
- [ ] No method-level claim is bound to a specific model name, hyperparameter value, or dataset tag outside §Setup / §Experiments; the recipe is defined once and referenced conceptually elsewhere.
- [ ] The Introduction has exactly 2-4 contribution bullets — not five. Bullets that describe an experiment or a benchmark have been folded into §Experiments / §Setup.

### Technical

- [ ] Citations are verified.
- [ ] Error bars and statistical reporting are clear.
- [ ] Compute resources are documented.
- [ ] Code / data availability is stated.

## Final Sentence

**A paper is not just a written record of experiments. It is a technical conclusion organized into a story that a reviewer is willing to believe.**

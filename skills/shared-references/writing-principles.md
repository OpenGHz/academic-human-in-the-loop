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
- [Acronyms and Domain Shorthand: Expand at First Use](#acronyms-and-domain-shorthand-expand-at-first-use)
- [Implementation Identifiers Stay Out of the Main Body](#implementation-identifiers-stay-out-of-the-main-body)
- [Method-Level Claims Stay Above the Experimental Choices](#method-level-claims-stay-above-the-experimental-choices)
- [The Paper Is Not a Tech Report](#the-paper-is-not-a-tech-report)
- [Hide Weaknesses: Limitations Are Framework-Level, Not Experiment-Defect Lists](#hide-weaknesses-limitations-are-framework-level-not-experiment-defect-lists)
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
- **Use zero em-dashes (`—` / `---`).** The body of the paper allows up to two; the abstract allows none. See [Punctuation: Cap the Em-Dash](#punctuation-cap-the-em-dash) for the reasoning and the grep check.

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

### Punctuation: Cap the Em-Dash

**Hard cap: at most two em-dashes (`—`) in the entire main body, and ZERO in the abstract.** Em-dashes are aesthetically tempting and grammatically permissive, so drafts accumulate them quickly: a parenthetical mid-clause, an emphatic appositive, a trailing afterthought, a clause break that "feels right." A reader who hits the third em-dash starts noticing the punctuation instead of the content, and the prose acquires a recognizable AI-shaped rhythm. The abstract gets a stricter rule because it is read first, often in isolation (search results, OpenReview tiles, social previews), so any AI-tell there does disproportionate damage to first impression.

The cap forces a real edit. For each em-dash, pick the right replacement based on what the em-dash was doing:

| What the em-dash was doing | Replacement |
|---|---|
| Parenthetical aside (`X — which is Y — Z`) | Commas, or split into two sentences |
| Strong appositive (`the result — a 15% lift — confirms ...`) | Comma, colon, or a separate sentence |
| Clause break / shift in direction | Semicolon, period, or `, and` / `, but` |
| Trailing emphasis / afterthought | Colon, or just delete the dash and let the sentence end |
| List-item gloss (`item — explanation`) | Colon, or restructure the list with explicit bullets |

After the substitution pass, count em-dashes in **two separate buckets**: (a) the abstract — must be exactly **0**; (b) main body — must be **≤ 2**. If either bucket fails, keep editing. The same body cap applies to figure captions and table notes — captions are prose. Final-check skills (`/paper-write` Step 8, `/paper-compile` Step 5, `/auto-paper-improvement-loop` Step 8) should grep the abstract explicitly:

```bash
# Extract abstract block and count em-dashes — must be 0.
awk '/\\begin\{abstract\}/,/\\end\{abstract\}/' paper/sections/*.tex paper/main.tex \
  | grep -oE "—|---" | wc -l
```

A non-zero count is a `BLOCKED` gate, not a warning: surface the offending sentences to the user before declaring write complete.

This rule does *not* target hyphens (`-`, in compounds like `state-of-the-art`) or en-dashes (`–`, in numeric ranges like `5–10`). Only the long em-dash (`—`) is capped. **Note**: LaTeX `---` renders as an em-dash; the grep above catches both the Unicode `—` and the LaTeX `---` source form.

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

## Acronyms and Domain Shorthand: Expand at First Use

Every acronym, initialism, or domain-internal shorthand must be expanded at its first occurrence in the paper, with the expansion in full first and the abbreviation following in parentheses. The expansion belongs at the *first* mention regardless of where that mention falls (Abstract, Introduction, Method, figure caption, table label). After that point the short form is fine. The rule applies even when the abbreviation feels universal inside the subfield: reviewers cross disciplines, and "obvious" varies.

### What Counts as Needing Expansion

- **Field acronyms** common in ML, vision, NLP, robotics, etc. — even ones that feel ubiquitous (`LLM`, `VLM`, `VLA`, `MLLM`, `VQA`, `RL`, `CNN`, `RNN`, `MLP`, `BLEU`, `IoU`, `mAP`). Expand once.
- **Direction / orientation shorthand** specific to a domain (`CCW`, `CW`, `LHS`/`RHS`, `NE`/`SW`). Expand the first time it appears in prose; figure-internal one-letter labels can stay short *if* the caption defines them.
- **Method and benchmark abbreviations** used in the paper's own framing (`SOTA`, `OOD`, `IID`, `KL`, `ELBO`). Expand once.
- **Internal compound shorthand** the paper introduces itself ("the procedural-QA chain", "the chain-prompt prior") — define the phrase explicitly the first time, then reuse.
- **Greek-letter or symbol shorthand** when it stands for a named quantity (`$\Delta$ accuracy`, `$\theta_p$`). Spell out what the symbol refers to at first use.

### What Does Not Need Expansion

- Universal symbols and math notation (`$x$`, `$f(\cdot)$`, `=`, `\arg\max`).
- Standard units and SI prefixes (`ms`, `Hz`, `cm`, `GB`).
- Dataset / model names that are themselves the proper noun (`ImageNet`, `COCO`, `MS-MARCO`, `Llama`, `GPT-4`) — these are names, not abbreviations of expandable phrases.
- Common-English abbreviations (`e.g.`, `i.e.`, `etc.`, `vs.`).

### The Substitution Pattern

| First-use form to fix | Correct first-use form |
|---|---|
| "a frozen VLM does X" | "a frozen vision-language model (VLM) does X" |
| "trained VLA stacks" | "trained vision-language-action (VLA) stacks" |
| "VQA-style construction" | "visual-question-answering (VQA) construction" |
| "MLLM planning" | "multimodal large language model (MLLM) planning" |
| "[CCW, pull]" (no prior definition) | "counter-clockwise (CCW) ... [CCW, pull]" (define on first prose mention; reuse after) |
| "$+0.47$ $\Delta$ chain accuracy" (no $\Delta$ definition) | "an increase ($\Delta$) of $+0.47$ in chain accuracy" |

### Where Expansion Belongs

- **Abstract**: expand the abbreviation that the abstract *uses*. Do not expand abbreviations the abstract does not need; that's noise.
- **Introduction**: expand every abbreviation the intro uses, even if the abstract already expanded it (the reader may skim the abstract). Reviewers who jump straight to the intro should not face an undefined token.
- **Method / Experiments**: if a new abbreviation is introduced here (e.g. an evaluation metric), expand it on its first appearance in this section.
- **Figure captions and table notes**: captions are read independently of body text. Expand the first time an abbreviation appears *in a caption*, or define it in the caption with a one-line gloss. Do not assume the reader read the body first.
- **Figure-internal labels** (axis tick labels, schematic boxes, legend entries) can stay short *only* when the caption defines them on the same page. A bare `CCW` on a chart with no caption gloss is a defect.

### Exceptions (Rare)

- The abbreviation is part of a proper-noun benchmark or model name (`BERT`, `T5`, `GPT-N`). The abbreviation *is* the name; do not invent a fake expansion.
- The abbreviation has multiple competing expansions in the field and the paper deliberately stays neutral. In that case, footnote the choice and proceed.

### How to Audit a Draft

A two-pass check:

1. **Mechanical grep.** Search the main body and figure files for runs of `[A-Z]{2,}` (two or more consecutive capitals). For each hit, locate the *first* occurrence in document reading order (abstract → intro → method → results → ablations → limitations → conclusion → captions → tables); verify the expansion is present. Hits that are part of a proper-noun model/dataset name or a standard unit are exempt.
- A LaTeX-aware command: `grep -nE '\b[A-Z]{2,}\b' sections/*.tex figures/*.tex` and walk down the list.
1. **Read aloud the first page.** Anything that sounds like an acronym you would need to recall from earlier ("VLA," "MLLM," "CCW") and is not expanded inline is a defect to fix.

Maintain the expansion discipline incrementally: every time you introduce a new abbreviation in a draft, add the expansion at first use *immediately*. Acronym drift accumulates faster than any audit pass can catch.

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

## The Paper Is Not a Tech Report

A paper presents a contribution; a tech report or project status document presents *the state of a body of work* (what has run, what has not, what was tried and dropped, what is queued for next quarter). The two have different readers and different success criteria. A reviewer reads a paper to evaluate a contribution against the field, not to track the team's experimental backlog. When status-report content leaks into the main body, the reviewer reads it as either an admission of incompleteness or a confession of unfocus — both push the paper toward rejection. Strip status-report content out, keep paper content in.

### What Counts as Status-Report Content

Move the following out of the main body — to the appendix only when the reproducibility audience genuinely needs it, otherwise delete entirely:

- **Rerun queues and deferred work.** "Baseline X was not re-run on split Y" / "future revisions should run Z" / "matched W baselines are the next most important experiment" / "we plan to compare against V in the next revision." None of this is information the reviewer is meant to grade; all of it tells the reviewer the paper is not yet finished. If a comparison is missing, either (a) the missing comparison is genuinely out-of-scope and the framing should make that scope explicit, or (b) the comparison is in-scope and the paper is not ready to submit.
- **Why-we-chose-these-tasks rationale.** A paragraph explaining the selection process — "we considered tasks A, B, C, then narrowed to X, Y, Z because of constraint Q" — is project journal, not paper content. The paper presents the tasks that *are* in the contribution; the selection narrative belongs in a tech report or a methods supplement.
- **Intermediate-attempt narrative.** "We first tried approach P, found it failed because of R, then moved to S which also failed, finally arrived at T." The dropped attempts are not part of the contribution; presenting them invites the reviewer to grade the dropped attempts. Lead with T; let the discarded P / S live in an internal log, not in §Method.
- **Deprecated experimental rows / superseded results.** Once an experimental row is dropped from the contribution (whether because the protocol changed, the row was flawed, or it was superseded by a stronger version), it stays dropped. The paper does not present the dropped row "for completeness" and does not footnote it as deprecated. A footnote that says "deprecated row $K$ shows $X$" tells the reviewer there *was* a row $K$ that someone (you) judged unfit to present, and now invites them to ask why.
- **Internal milestone language.** "Round-2 prompt template", "v3 of the protocol", "the post-Q4 evaluation cap." Version stamps make sense in a changelog, not in a method section. Pick the version that is in the contribution and present it as *the* method.
- **Pipeline status flags.** "This experiment is in progress" / "raw data archives are not yet local for $TASK$" / "the cluster scheduler is being migrated." Operational state is invisible to the reviewer and should stay that way.
- **"Saturated reference" or "excluded from headline" callouts.** If a task or row is excluded from the headline, it is not in the headline; it should not be footnoted into the headline by another route. Including a row only to footnote it as "saturated" or "excluded" reintroduces the dropped content in a way the reviewer has to parse.

### The Boundary Test

For each paragraph in the main body, ask: *if a reviewer reads only this paragraph, does it describe the contribution, or the project that produced the contribution?* If it describes the project — what has been done, what is left, what was tried and abandoned, what the queue looks like — it does not belong in the main body. Either delete it, or relocate the genuinely reproducibility-relevant part (an exact invocation, a split definition, a code-release pointer) to an appendix where the reproducibility audience can find it.

### What This Rule Does *Not* Mean

This rule does not forbid honest scope statements, and it does not forbid an appendix. It targets a specific failure mode where status content leaks into framing prose. The following are still allowed:

- **Scope declarations in framing.** "This paper targets $X$; head-to-head numbers against the $Y$ family are out of scope." That is a framing statement about what the contribution is *about*, not an admission that the comparison was queued and dropped.
- **Reproducibility appendices.** Exact invocations, dataset slugs, split definitions, evaluation caps, model identifiers — these live in an appendix that the reproducibility audience opens. The main body should not duplicate them.
- **A single Limitations section.** See the next principle for what belongs in Limitations and what does not.

### The Substitution Pattern

| Status-report sentence | Paper substitute | Where the literal info goes |
|---|---|---|
| "Held-out no-prompt baselines were not re-run; future revisions should rerun them." | (Delete. If the held-out result is weaker without the baseline, either compute it or rescope the claim.) | Internal status log, not the paper |
| "Matched $TASK$ baselines are the most important next experiment." | (Delete. The framing should already say what is in scope.) | Internal status log, not the paper |
| "We first tried approach $P$, then $S$, before arriving at $T$." | "We $T$." | Tech report / methods supplement |
| "Deprecated row $K$ falls to $X$, entirely on chain $C$ (Appendix~$Z$)." | (Delete the row and the footnote. If the deprecation argument is itself the point, the surviving row should carry it without naming the deprecated one.) | Internal experimental log |
| "Task $W$ saturates at $X$ and is excluded from the headline." | (Delete the row entirely. If it is excluded from the headline, it is not in the paper.) | Internal log; explicit scope statement in §Setup if the absence matters |
| "Round-2 of the prompt template tightened the gate." | "The prompt template uses a held-out training-group gate at $T$." | (No relocation; pick the in-paper version and present it once) |
| "Raw $DATASET$ archives are not yet local, so $BASELINE$ is deferred." | (Delete. Either run the baseline or scope it out explicitly.) | Status log |

### How to Audit a Draft

- Grep the body for status verbs: "not re-run", "deferred", "future revision", "next experiment", "is in progress", "to be done", "we plan to", "remains to be", "yet to". Each hit is a candidate.
- Grep the body for deprecation markers: "deprecated", "superseded", "legacy", "row $K$" / "old setting", "earlier version". Each hit is a candidate.
- Grep the body for selection narrative: "we first tried", "we initially", "we considered", "we narrowed". Each hit is a candidate.
- Read every footnote in the main body. Footnotes that introduce a row only to flag it as excluded / saturated / deprecated should be deleted along with the row.

A paper presents the contribution that exists. The contribution that does not yet exist is not part of the paper.

## Hide Weaknesses: Limitations Are Framework-Level, Not Experiment-Defect Lists

Most venues require a Limitations section. The required section is not a confession booth. Its purpose is to delimit the scope of the contribution — to tell the reviewer what claim the paper is making and what claim it is *not* making — so that the reviewer evaluates the contribution at its actual scope, not at an inflated one. A well-written Limitations section makes the contribution easier to accept, not easier to reject. A poorly written one enumerates every defect the authors are aware of and hands the reviewer a ready-made list of rejection reasons.

The discipline is sometimes phrased as *藏拙*: hide what you cannot defend; foreground what you can. This is not dishonest framing. The reviewer is grading the contribution against the field's standard scope, not against the team's internal punch list. A scope declaration that says "this paper targets the narrow problem of $X$" is honest; an enumeration that says "we ran into defect $D_1$ on experiment $E_1$, defect $D_2$ on experiment $E_2$, and need to rerun $E_3$" is needlessly self-damaging and is not what the section is for.

### What Belongs in Limitations

Only two categories belong here:

1. **Framework-intrinsic scope boundaries.** Constraints baked into the assumptions of the approach itself: what task structures the method assumes, what labels it requires at training time, what input modalities it depends on, what kind of generalization claim is in scope vs. out of scope. Examples (phrased as scope declarations, not defects): "the method assumes the procedural answer is readable from a one-line rule over the available signal class," "the training-time loop assumes ground-truth chain labels," "the contribution is demonstrated on a single robot embodiment and is not claimed to be platform-agnostic."

2. **Whole-paper baseline coverage scoped as framing, not as defect.** If the contribution does *not* present head-to-head numbers against a competing family, state that as part of the scope of the contribution ("we contrast against same-backbone no-iteration rows; head-to-head numbers against the $Y$ family of methods are not the scope of this paper"). This frames the absence as a deliberate scope choice, not as an experimental task the team failed to complete.

### What Does Not Belong in Limitations

- **Per-experiment defects.** "Held-out no-prompt baseline on $g_2$ was not re-run." "Cabinet bottle held-out columns are iteration accuracies, not $\Delta$s." These are operational details. If the defect is real and material, fix it before submitting. If it is real but not material, do not mention it. If it is not real, do not mention it.
- **Rerun queues.** "Future revisions should rerun $X$." Future revisions are not the reviewer's concern.
- **"Most important next experiment" language.** This is roadmap, not limitation. It tells the reviewer that the experiment that *would* have closed the case is not in the paper.
- **Internal admissions of incompleteness.** "Raw trajectory archives for $TASK$ are not local." "$BASELINE$ reproductions are deferred." Operational state.
- **Cost / scale apologetics outside of framing.** "Our method requires $N$ rounds of iteration, which is expensive." Either the cost is in scope (state it once as a framing constraint with the actual number) or it is not (do not preemptively raise it).

### The Reframe Pattern

For each draft limitation, ask: *is this a scope of the framework, or is it a defect of an experiment in this paper?*

| Draft sentence (defect-shaped) | Reframed (scope-shaped) | What changed |
|---|---|---|
| "Baseline $B$ was not re-run on split $S$; the held-out column is iteration accuracy, not $\Delta$." | (Either delete, or fold into §Setup: "Headline $\Delta$s are reported on training groups; held-out columns report iteration accuracy alone.") | Status fact moved to setup, no longer named as limitation |
| "Head-to-head numbers against the $Y$ family are not run." | "The contribution contrasts against same-backbone no-iteration rows; positioning against the $Y$ family of methods is outside the scope of this paper." | Defect reframed as scope of the contribution |
| "We did not evaluate on $PLATFORM_2$." | "The contribution is demonstrated on a single embodiment; cross-platform transfer is a question we do not claim to answer here." | Defect reframed as scope of the generalization claim |
| "Matched $TASK$ baselines are the most important next experiments." | (Delete. If the matched baseline is genuinely missing in scope, address in scope statement above; if it is missing operationally, do not write the paper around it.) | Roadmap content removed entirely |
| "Our method needs ground-truth chain labels in Stage 1; this is expensive and a limitation." | "The contribution is a supervised rule-discovery procedure: it requires ground-truth labels during training and is not claimed to apply in the label-free regime." | Cost-of-recipe reframed as framework scope |
| "Cabinet held-out is only 15 episodes; this is small." | (Either remove and let the reader read $n$ in the table, or fold into §Setup. Calling out sample sizes in Limitations invites the reviewer to demand more.) | Operational detail moved to setup |

### Sentence-Level Forbidden Phrases

These phrasings are almost always a sign that the section has drifted toward tech-report territory; rewrite or delete:

- "$X$ was not re-run."
- "Future revisions should ..."
- "The most important next experiment is ..."
- "We plan to ..." / "is deferred until ..."
- "$X$ remains to be evaluated."
- "Deprecated row $K$ ..."
- "$\dots$ this is small / weak / partial / not yet $\dots$"

A Limitations section written entirely in scope-declaration sentences will tend not to use any of these.

### Length and Tone

A Limitations section at a conference venue is typically short — a single paragraph or two, on the order of 5-10 sentences. If it grows past that, it is almost certainly enumerating defects. Tone: factual and scope-oriented, not apologetic. "The contribution targets $X$" is the right shape; "we acknowledge that we did not $Y$" is the wrong shape.

### How to Audit a Draft

- Read the draft Limitations section aloud. If any sentence sounds like a project-status update — anything a reviewer could quote in the rejection writeup as "the authors themselves acknowledge that $X$ is missing" — rewrite or remove it.
- Grep for the forbidden phrases above.
- For each remaining sentence, classify it as (a) framework-scope declaration, (b) whole-paper coverage scope, or (c) other. Anything in (c) should be either reframed into (a)/(b) or removed.
- Cross-check against the rest of the paper: if a section earlier in the body admits a defect (e.g., "matched baselines were not re-run on the held-out groups"), that admission is now hosted in the wrong place and should be deleted there too — operational facts go in §Setup, scope goes in §Limitations, neither belong in §Results prose.

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
| Em-dashes (`—`) scattered through the prose (more than two in the whole main body) | Replace with comma, colon, semicolon, or split sentence — see [Punctuation: Cap the Em-Dash](#punctuation-cap-the-em-dash) |
| Status-report content in main body (deferred work, rerun queues, deprecated rows, why-we-chose-these-tasks narrative) | Delete from main body; relocate genuine reproducibility info to appendix — see [The Paper Is Not a Tech Report](#the-paper-is-not-a-tech-report) |
| Limitations section enumerates per-experiment defects ("$X$ was not re-run", "matched $Y$ baselines are the next experiment") | Reframe as framework-scope declarations and whole-paper coverage scope — see [Hide Weaknesses](#hide-weaknesses-limitations-are-framework-level-not-experiment-defect-lists) |

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
- [ ] The Introduction has 2-4 contribution bullets, not five. Bullets that describe an experiment or a benchmark have been folded into §Experiments / §Setup.
- [ ] At most two em-dashes (`—`) in the entire main body (figure captions and table notes included). Hyphens and en-dashes are not counted.
- [ ] Every acronym, initialism, and domain-shorthand token (e.g. `VLM`, `VLA`, `VQA`, `MLLM`, `LLM`, `CCW`, `CW`, `SOTA`, `OOD`) is expanded at its first occurrence in the paper (and at first occurrence in figure captions, which are read independently). Proper-noun model/dataset names are exempt.
- [ ] No status-report content in the main body: no "$X$ was not re-run", no "future revisions should ...", no "the next most important experiment is ...", no "deprecated row $K$" footnotes, no "we first tried $P$ then $S$" selection narrative. Operational details live in §Setup or appendix; the contribution that does not yet exist is not in the paper.
- [ ] Limitations section contains only (a) framework-intrinsic scope declarations (what the method assumes, what regime it targets, what generalization claim is in scope) and (b) whole-paper baseline coverage scoped as framing — *not* per-experiment defects, rerun queues, or "most important next experiment" language. Length is roughly 1-2 short paragraphs.

### Technical

- [ ] Citations are verified.
- [ ] Error bars and statistical reporting are clear.
- [ ] Compute resources are documented.
- [ ] Code / data availability is stated.

## Final Sentence

**A paper is not just a written record of experiments. It is a technical conclusion organized into a story that a reviewer is willing to believe.**

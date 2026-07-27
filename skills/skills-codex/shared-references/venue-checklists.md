# Venue Checklists for ICLR, NeurIPS, ICML, and CoRL

Use this reference near the end of `paper-plan` and during the final checks in `paper-write`.

## When to Read

- Read once when setting the target venue.
- Read again before locking the outline.
- Read again during final submission-readiness checks.

## Universal Requirements

Across these venues, the following are usually expected:

- anonymous submission unless preparing a camera-ready version,
- references and appendices outside the main page budget,
- enough experimental detail for reproduction,
- honest limitations and scope boundaries,
- clear mapping from claims to evidence.

## NeurIPS

Planning implications:

- The paper checklist is mandatory.
- Claims in the Abstract and Introduction must align with the actual evidence.
- The paper should discuss limitations honestly.
- Reproducibility details, hyperparameters, data access, and compute usage should be documented.
- Statistical reporting should specify error bars, number of runs, and how uncertainty is computed.

Final-check implications:

- Confirm the paper checklist is complete.
- Ensure limitations, reproducibility details, and compute reporting exist somewhere appropriate.
- Verify theory papers include assumptions and full proofs in the main paper or appendix.

## ICML

Planning implications:

- The paper must budget space for an ICML-style Broader Impact statement.
- Reproducibility expectations are strong: data splits, hyperparameters, search ranges, and compute should be documented.
- Statistical reporting should state whether uncertainty uses standard deviation, standard error, or confidence intervals.

Final-check implications:

- Ensure the Broader Impact statement is present in the expected location.
- Confirm anonymization is strict: no author names, acknowledgments, grant IDs, or self-identifying repository links.
- Verify experimental details are detailed enough for replication.

## ICLR

Planning implications:

- Reproducibility and ethics statements are often recommended even if not always mandatory.
- If LLMs materially contributed to ideation or writing to the point of authorship-like contribution, plan a disclosure section or appendix note.
- Keep the story front-loaded because ICLR reviewers often judge quickly from the early pages.

Final-check implications:

- Decide whether LLM disclosure is required for this project.
- Confirm the paper includes enough reproducibility guidance, code/data availability information, and limitations discussion.
- Check that the contribution is already clear by the end of the Introduction.

## CoRL (Conference on Robot Learning, PMLR)

Planning implications:

- Use `\documentclass{article}` with `\usepackage{corl_2026}` (anonymous initial submission, double-blind by default). For camera-ready use `[final]`; for arXiv preprint use `[preprint]`.
- Citation style is `natbib` (`\citep{}` / `\citet{}`). Bibliography style is auto-set to `corlabbrvnat` by the package — do NOT add a manual `\bibliographystyle{}`.
- Abstract is **strictly 4-6 sentences in a single paragraph**. Gross violations are corrected at camera-ready.
- `\keywords{...}` with 2-3 keywords is **mandatory**, placed immediately after the abstract.
- **Page budget (initial submission): 8 pages main text.** Acknowledgments, References, and Appendix do NOT count. Camera-ready gets one extra page (9 pages main text) to accommodate review feedback.
- **`\section{Limitations}` is MANDATORY** and counts toward the 8-page limit. It must explicitly cover limiting assumptions, failure modes, and how these could be addressed in future work. Reviewers may reject papers that omit it.
- The Appendix is optional but, when present, should be at the end of the camera-ready PDF — NOT a separate supplementary file. Reviewers are not obligated to read the Appendix; put load-bearing claims in the main paper.
- CoRL strongly encourages **enough detail in main paper + appendix to let future researchers reproduce the work** — hyperparameters, data, hardware setup, training procedure all explicit.
- CoRL reviewers strongly prefer **real-robot experiments** or rigorous sim-to-real validation; sim-only work has a high bar and should justify the sim setup. Plan a multi-task or generalization story rather than single-task SOTA.
- **Video supplementary is critical at CoRL** — reviewers expect demonstration videos. Plan a 2-3 minute video early in the writing phase, not as an afterthought.

Final-check implications:

- Verify abstract is 4-6 sentences and a single paragraph.
- Verify `\keywords{}` is present and has 2-3 entries.
- **Verify `\section{Limitations}` exists in the main paper and is substantive (not a sentence).**
- Confirm no manual `\bibliographystyle{}` is set (the corl_2026 package handles it).
- Verify all citations use `\citep` / `\citet`, not `\cite`.
- Initial submission: `corl_2026` loaded WITHOUT `[final]` / `[preprint]` (anonymous); page count of main text (Title through end of Conclusion or Limitations, whichever is last) ≤ 8.
- Camera-ready: switch to `\usepackage[final]{corl_2026}`; **author list is NOT anonymous**; page count of main text ≤ 9; Appendix (if any) placed at end of the camera-ready PDF, not a separate file.
- Camera-ready footer on page 1 must read: `10th Conference on Robot Learning (CoRL 2026), Austin, Texas, USA.` — this is inserted automatically by `\usepackage[final]{corl_2026}`. Verify it appears in the compiled PDF.
- Confirm video / supplementary materials are referenced in the paper and prepared.
- Verify hardware experiments (or sim justification) are discussed with enough detail to reproduce.
- Confirm at least one task-generalization or cross-scene result is reported.

## IROS / ICRA preferences (robotics IEEE_CONF)

IROS and ICRA are submitted through PaperPlaza, whose automated check enforces a stricter page geometry than the generic IEEE conference baseline. The official RAS Author's Kit ships `ieeeconf.cls` (with `root.tex`), **not** `IEEEtran` — the two are not interchangeable, because their text blocks differ in width. If you build on `\documentclass[conference]{IEEEtran}` anyway (which the `ieee_conference.tex` template does), you MUST override its margins; see the first bullet. Beyond geometry, reviewers and the proceedings editors have a few robotics-specific conventions worth respecting:

- **Margins are checked automatically, and are the most common silent failure.** On US Letter, PaperPlaza requires **≥ 0.75in (54pt) left, right and bottom margins on every page**, and **≥ 1in (72pt) at the top of page 1** (0.75in top on the rest). `ieeeconf.cls` satisfies this by fixing `\textwidth` at 7.0in. **Stock `IEEEtran[conference]` does not**: it lays out a 7.16in text block (0.68in sides) and starts the title at 0.75in, so *every* paper overruns by ~5pt per side and ~17pt at the top of page 1. When using IEEEtran, put this before `\documentclass` (CLASSINPUT overrides only take effect there) and the `\renewcommand` after it:
  ```latex
  \newcommand{\CLASSINPUTinnersidemargin}{56pt}
  \newcommand{\CLASSINPUToutersidemargin}{56pt}
  \newcommand{\CLASSINPUTtoptextmargin}{61pt}    % page-top floats sit ~5pt higher
  \newcommand{\CLASSINPUTbottomtextmargin}{56pt}
  \documentclass[conference]{IEEEtran}
  \renewcommand{\IEEEtitletopspaceextra}{11pt}   % clear the 1in first-page top
  ```
  Two traps worth knowing. First, this failure is **invisible to overfull-hbox checks**: the text block itself is misplaced, so every line is legally set inside a wrong frame and the log stays clean at zero overfulls. Verify by measuring rendered ink instead — `gs -dQUIET -dBATCH -dNOPAUSE -sDEVICE=bbox main.pdf` prints one `%%HiResBoundingBox: x0 y0 x1 y1` per page, from which left = `x0`, right = `612-x1`, top = `792-y1`, bottom = `y0`. Second, a float at the top of a page starts ~5pt *above* where the body text starts, so a table-topped page can overrun the top margin even when all body pages pass; that is why the top margin above is 61pt rather than 56pt. Leave ~2pt of slack rather than landing exactly on 54pt.

- **No standalone Limitations section.** Fold limitations and future-work discussion into the final paragraph(s) of the `Conclusion` section. A separate `\section{Limitations}` is unusual in this community and will read as ML-conference-flavored rather than robotics-flavored.
- **No separate Results section.** Fold results (tables, quantitative comparisons, ablations, qualitative analysis) into the `Experiments` section as subsections (e.g., `\subsection{Setup}` then `\subsection{Main Results}` then `\subsection{Ablations}` then `\subsection{Qualitative Analysis}`). A standalone `\section{Results}` after `\section{Experiments}` reads as ML-flavored and wastes header lines that count against the tight 6-page IROS/ICRA budget.
- **Captions are sentence case, not ALL-CAPS.** Figure captions in `IEEEtran` are already sentence case. **Table captions are NOT** — `IEEEtran.cls` applies `\scshape` to table caption text, which renders as ALL-CAPS in standard Computer Modern / Times fonts (this is the published IEEE style but does NOT match IROS/ICRA proceedings practice). To match what IROS/ICRA papers actually look like, add the following preamble override:
  ```latex
  \usepackage{caption}
  \captionsetup[table]{font=footnotesize, labelfont=normalfont, textfont=normalfont}
  ```
  This forces table captions to render in sentence case like figure captions. Do NOT use `\MakeUppercase` / `\uppercase` / `caption=upper`.
- Page limit is typically 6 pages of content + up to 2 pages of references (8 pages total) — check the current year's CFP.
- Multimedia attachments (video) are encouraged and submitted via PaperPlaza alongside the PDF.
- **Keywords must be picked from the IEEE RAS controlled vocabulary.** PaperPlaza requires authors to select from a fixed keyword tree (~300 terms across 30 categories). The `\begin{IEEEkeywords}` block in the PDF should mirror the PaperPlaza selection so the area chair routes the paper correctly. See [`icra-keywords.md`](icra-keywords.md) for the full vocabulary and selection heuristics; run `/pick-keywords` to auto-select 3–5 terms from an abstract.
- Hardware experiments, real-robot validation, and a clear problem-setup figure are strongly weighted by reviewers.
- **`\pdfminorversion=4` is required for ICRA PDF upload.** ICRA's submission portal explicitly warns: if you upload a self-generated PDF built by pdfLaTeX, you must add `\pdfminorversion=4` in the preamble (as the very first line, before `\documentclass`), otherwise the generated PDF will be corrupt as far as the portal is concerned. IROS shares the IEEE PDF eXpress toolchain and benefits from the same setting. Add it unconditionally when targeting IROS/ICRA:
  ```latex
  \pdfminorversion=4
  \documentclass[conference]{IEEEtran}
  ```
- Citation style is `\cite{}` (numeric, via `cite` package); do not use `\citep` / `\citet`.
- Not anonymous: include full author information.
- **AI-content disclosure in Acknowledgments (ICRA policy).** If AI systems generated any text, figures, images, or code in the paper, disclose it in the `\section*{Acknowledgments}` (or `\section*{Acknowledgment}`) section. Grammar/editing polish by AI does NOT require disclosure — only *generated content*. Example wording: "Portions of the [text / figures / code] were generated with the assistance of [system name]; all content was reviewed and verified by the authors." Do NOT bury the disclosure in the appendix, a footnote, or a paragraph before the acknowledgments — reviewers/PC look for it inside the acknowledgments section specifically. The acknowledgments section itself does not count against the page limit at IROS/ICRA (it sits between the last content section and references).

## Minimal Submission Checklist

Before submission, verify:

- the venue-specific required sections are present,
- the page budget is satisfied for the main body,
- the contribution bullets do not overclaim,
- citations, figures, tables, and references are internally consistent,
- the PDF is anonymized and ready for reviewer consumption.

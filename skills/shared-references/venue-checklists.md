# Venue Checklists for ICLR, NeurIPS, ICML, CoRL, and IEEE

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
- **Video supplementary is critical at CoRL** — reviewers expect demonstration videos. Plan a 2-3 minute video early in the writing phase, not as an afterthought. Use `/paper-video` to assemble + gate-check the video (250 MB / 180 s hard limits, h264 + faststart enforced).

Final-check implications:

- Verify abstract is 4-6 sentences and a single paragraph.
- Verify `\keywords{}` is present and has 2-3 entries.
- **Verify `\section{Limitations}` exists in the main paper and is substantive (not a sentence).**
- Confirm no manual `\bibliographystyle{}` is set (the corl_2026 package handles it).
- Verify all citations use `\citep` / `\citet`, not `\cite`.
- Initial submission: `corl_2026` loaded WITHOUT `[final]` / `[preprint]` (anonymous); page count of main text (Title through end of Conclusion or Limitations, whichever is last) ≤ 8.
- Camera-ready: switch to `\usepackage[final]{corl_2026}`; **author list is NOT anonymous**; page count of main text ≤ 9; Appendix (if any) placed at end of the camera-ready PDF, not a separate file.
- Camera-ready footer on page 1 must read: `10th Conference on Robot Learning (CoRL 2026), Austin, Texas, USA.` — this is inserted automatically by `\usepackage[final]{corl_2026}`. Verify it appears in the compiled PDF.
- Confirm video / supplementary materials are referenced in the paper and prepared. If a video is produced via `/paper-video`, attach the `submission/video/verify.json` artifact (ok=true is the gate).
- Verify hardware experiments (or sim justification) are discussed with enough detail to reproduce.
- Confirm at least one task-generalization or cross-scene result is reported.

## IEEE Journal (Transactions / Letters)

Planning implications:

- IEEE journals are typically **not anonymous** — include full author names, affiliations, and IEEE membership status from submission.
- Use `\documentclass[journal]{IEEEtran}` with `\cite{}` (numeric citations via `cite` package). Do NOT use `natbib`.
- References **count toward the page limit**. IEEE Transactions typically allow 12-14 pages total; IEEE Letters (e.g., WCL, CL, SPL) typically allow 4-5 pages total. Check the specific journal's author guidelines.
- Include an `\begin{IEEEkeywords}` block immediately after the abstract.
- The bibliography style must be `IEEEtran.bst` (produces numeric `[1]` style citations).
- IEEE journals may require a biosketch (`\begin{IEEEbiography}`) for each author in the camera-ready version.
- Some IEEE journals require a cover letter addressing how the paper differs from conference versions (if applicable).

Final-check implications:

- Confirm author names and IEEE membership grades are correct (Member, Senior Member, Fellow).
- Verify the total page count including references is within the journal's limit.
- Check that all figures meet IEEE quality requirements: 300 dpi minimum, proper axis labels, readable when printed in grayscale.
- Ensure the paper uses two-column IEEE format throughout (the `[journal]` option handles this).
- Verify no `\citep` or `\citet` commands are present — IEEE uses `\cite{}` only.
- Check that `\bibliographystyle{IEEEtran}` is used.

## IEEE Conference (ICC, GLOBECOM, INFOCOM, ICASSP, etc.)

Planning implications:

- Most IEEE conferences are **not anonymous** (except some like IEEE S&P). Include full author information.
- Use `\documentclass[conference]{IEEEtran}` with `\cite{}` (numeric citations).
- References **count toward the page limit**. Typical limit: 5-6 pages (e.g., ICC, GLOBECOM), some allow up to 8 pages (e.g., INFOCOM). Extra pages may incur additional charges.
- Include `\begin{IEEEkeywords}` after the abstract.
- Conference papers do NOT include author biographies.
- Some IEEE conferences accept 2-page extended abstracts — confirm the paper category before planning.

Final-check implications:

- Verify total page count including references fits within the conference limit.
- Check that figures are readable at the two-column conference format size.
- Ensure `\bibliographystyle{IEEEtran}` is used.
- Verify no `\citep` or `\citet` commands are present.
- Confirm the correct `\documentclass` option (`[conference]`, not `[journal]`).
- Some conferences require IEEE copyright notice — check submission portal for specific requirements.

## Minimal Submission Checklist

Before submission, verify:

- the venue-specific required sections are present,
- the page budget is satisfied for the main body,
- the contribution bullets do not overclaim,
- citations, figures, tables, and references are internally consistent,
- the PDF is anonymized and ready for reviewer consumption.

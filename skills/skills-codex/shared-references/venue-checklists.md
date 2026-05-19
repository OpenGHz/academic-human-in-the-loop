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
- Page budget: typically 8-9 pages main body (excluding references and appendix) for initial submission; check the current year's CFP for the exact limit. References and appendix do NOT count toward the page limit (like NeurIPS/ICML).
- CoRL reviewers strongly prefer **real-robot experiments** or rigorous sim-to-real validation; sim-only work has a high bar and should justify the sim setup. Plan a multi-task or generalization story rather than single-task SOTA.
- **Video supplementary is critical at CoRL** — reviewers expect demonstration videos. Plan a 2-3 minute video early in the writing phase, not as an afterthought.
- Plan an explicit failure-mode / limitations section; CoRL reviewers weight honest limitations highly.

Final-check implications:

- Verify abstract is 4-6 sentences and a single paragraph.
- Verify `\keywords{}` is present and has 2-3 entries.
- Confirm no manual `\bibliographystyle{}` is set (the corl_2026 package handles it).
- Verify all citations use `\citep` / `\citet`, not `\cite`.
- For initial submission, confirm `corl_2026` is loaded WITHOUT `[final]` / `[preprint]` (anonymous).
- Confirm video / supplementary materials are referenced in the paper and prepared.
- Verify hardware experiments (or sim justification) are discussed with enough detail to reproduce.
- Confirm at least one task-generalization or cross-scene result is reported.

## Minimal Submission Checklist

Before submission, verify:

- the venue-specific required sections are present,
- the page budget is satisfied for the main body,
- the contribution bullets do not overclaim,
- citations, figures, tables, and references are internally consistent,
- the PDF is anonymized and ready for reviewer consumption.

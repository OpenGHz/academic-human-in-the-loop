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

- **DESK-REJECT GATE — robotics focus is mandatory.** CoRL's CFP explicitly states: *"submissions should focus on a core robotics problem and demonstrate the relevance of proposed models, algorithms, datasets, and benchmarks to robotics. Submissions without a robotics focus will be returned without review."* This is a desk-reject filter applied before peer review — not a reviewer preference. The paper must (a) be motivated by a core robotics problem, and (b) explicitly demonstrate why the proposed method / dataset / benchmark matters *for robotics specifically*. Generic ML with a robot demo bolted on at the end does not pass this gate. **If the planned contribution is not clearly robotics-grounded, switch venues at plan time — do not try to repackage during writing.** Paper-plan should surface this risk early (e.g., as a `BLOCKED` precondition).
- Use `\documentclass{article}` with `\usepackage{corl_2026}` (anonymous initial submission, double-blind by default). For camera-ready use `[final]`; for arXiv preprint use `[preprint]`.
- Citation style is `natbib` (`\citep{}` / `\citet{}`). Bibliography style is auto-set to `corlabbrvnat` by the package — do NOT add a manual `\bibliographystyle{}`.
- Abstract is **strictly 4-6 sentences in a single paragraph**. Gross violations are corrected at camera-ready.
- `\keywords{...}` with 2-3 keywords is **mandatory**, placed immediately after the abstract.
- **Page budget (initial submission): 8 pages main text.** Acknowledgments, References, and Appendix do NOT count. Camera-ready gets one extra page (9 pages main text) to accommodate review feedback.
- **`\section{Limitations}` is MANDATORY** and counts toward the 8-page limit. The CFP requires it to "explicitly describe limiting assumptions, failure modes, and other limitations of the results and experiments and how these might be addressed in the future." A single sentence does not satisfy this — plan a substantive paragraph (or two) addressing each axis explicitly. Reviewers may reject papers that omit it.
- The Appendix is optional but, when present, should be at the end of the camera-ready PDF — NOT a separate supplementary file. Reviewers are not obligated to read the Appendix; put load-bearing claims in the main paper.
- CoRL strongly encourages **enough detail in main paper + appendix to let future researchers reproduce the work** — hyperparameters, data, hardware setup, training procedure all explicit.
- CoRL reviewers strongly prefer **real-robot experiments** or rigorous sim-to-real validation; sim-only work has a high bar and should justify the sim setup. Plan a multi-task or generalization story rather than single-task SOTA. (Note: this is the *experimental* form of the robotics-focus gate above — passing both gates is required.)
- **Video supplementary is critical at CoRL** — reviewers expect demonstration videos. Plan a 2-3 minute video early in the writing phase, not as an afterthought. Use `/paper-video` to assemble + gate-check the video (250 MB / 180 s hard limits, h264 + faststart enforced).

Final-check implications:

- **Verify robotics-focus gate.** Confirm the paper's Title, Abstract, and Introduction all frame the contribution as a robotics problem (not "general method, applied to a robot"). The relevance of the proposed method / dataset / benchmark to robotics must be explicit in §1, not buried in §5. If the Abstract could be retitled for a non-robotics ML venue with no content changes, the gate is at risk — flag for the user before submission.
- Verify abstract is 4-6 sentences and a single paragraph.
- Verify `\keywords{}` is present and has 2-3 entries.
- **Verify `\section{Limitations}` exists in the main paper and is substantive** — must explicitly cover limiting **assumptions**, **failure modes**, and **future mitigations** (the three axes the CFP names). A one-sentence Limitations section fails this gate; flag it as `BLOCKED` rather than warning.
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
- References **count toward the page limit**. IEEE Transactions typically allow 12-14 pages total; IEEE Letters (e.g., WCL, CL, SPL) typically allow 4-5 pages total. Check the specific journal's author guidelines. **RA-L differs:** it allows up to 8 pages (6 free + 2 paid; ARIS targets ≤ 8 by default), is reviewed double-anonymous, and is first submitted in conference format. See the RA-L section below.
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

- Most IEEE conferences are **not anonymous** (except some like IEEE S&P, and the RAS conferences ICRA and IROS — see IROS / ICRA below). Include full author information.
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

### IROS / ICRA preferences (robotics IEEE_CONF)

IROS and ICRA are submitted through PaperPlaza, whose automated check enforces a stricter page geometry than the generic IEEE conference baseline above. The official RAS Author's Kit ships `ieeeconf.cls` (with `root.tex`), **not** `IEEEtran` — the two are not interchangeable, because their text blocks differ in width. If you build on `\documentclass[conference]{IEEEtran}` anyway (which the `ieee_conference.tex` template does), you MUST override its margins; see the first bullet. Beyond geometry, reviewers and the proceedings editors have a few robotics-specific conventions:

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
- **`\pdfminorversion=4` is required for ICRA PDF upload.** ICRA's submission portal explicitly warns: if you upload a self-generated PDF built by pdfLaTeX, you must add `\pdfminorversion=4` in the preamble (as the very first line, before `\documentclass`), otherwise the generated PDF will be corrupt as far as the portal is concerned. IROS shares the IEEE PDF eXpress toolchain and benefits from the same setting. Add it unconditionally when targeting IROS/ICRA:
  ```latex
  \pdfminorversion=4
  \documentclass[conference]{IEEEtran}
  ```
- Page limit is typically 6 pages of content + up to 2 pages of references (8 pages total) — check the current year's CFP.
- Multimedia attachments (video) are encouraged and submitted via PaperPlaza alongside the PDF.
- **Keywords must be picked from the IEEE RAS controlled vocabulary.** PaperPlaza requires authors to select from a fixed keyword tree (~300 terms across 30 categories). The `\begin{IEEEkeywords}` block in the PDF should mirror the PaperPlaza selection so the area chair routes the paper correctly. See [`icra-keywords.md`](icra-keywords.md) for the full vocabulary and selection heuristics; run `/pick-keywords` to auto-select 3–5 terms from an abstract.
- Hardware experiments, real-robot validation, and a clear problem-setup figure are strongly weighted by reviewers.
- **ICRA and IROS are double-anonymous.** The ICRA 2027 CFP says: "ICRA applies the double anonymous review process as defined by RAS", and IROS uses double-anonymous review as well. Follow the RAS rules listed in the RA-L section below: no names or affiliations, no acknowledgments or funding until acceptance, neutral self-citations, and no identifying links, logos or faces.
- **AI-content disclosure in Acknowledgments (ICRA policy).** If AI systems generated any text, figures, images, or code in the paper, disclose it in the `\section*{Acknowledgments}` (or `\section*{Acknowledgment}`) section. Grammar/editing polish by AI does NOT require disclosure — only *generated content*. Example wording: "Portions of the [text / figures / code] were generated with the assistance of [system name]; all content was reviewed and verified by the authors." Do NOT bury the disclosure in the appendix, a footnote, or a paragraph before the acknowledgments — reviewers/PC look for it inside the acknowledgments section specifically. The acknowledgments section itself does not count against the page limit at IROS/ICRA (it sits between the last content section and references).

## RA-L (IEEE Robotics and Automation Letters)

Checked 2026-10-14 against the RAS pages: RA-L *Information for Authors*, *FAQ* and *Final Submission Checklist*; *Rules for the Double-Anonymous Review Process*; *Guidelines for Generative AI Usage*; and the ICRA 2027 Call for Papers. RAS revises these, so re-check them before submitting.

RA-L is a journal, but the version you submit for review is formatted as a RAS **conference** manuscript. The generic "IEEE Journal" section above does not apply until after acceptance.

Planning implications:

- **Two formats for one paper.** For the initial submission, use `\documentclass[letterpaper, 10 pt, conference]{ieeeconf}`. RA-L says: "For compatibility reasons, the first submission to the Letters will be formatted as a RAS conference manuscript." In ARIS, start from `ieee_conference.tex` (`IEEE_CONF`), **not** `ieee_journal.tex`. That template is `IEEEtran` with overrides that reproduce `ieeeconf`'s page geometry (see IROS / ICRA above), and RA-L is uploaded through the same PaperPlaza system (`ras.papercept.net/journals/ral`). PaperPlaza checks the uploaded PDF, not which class produced it. If you want no risk at all, use the official `ieeeconf.zip` linked from RA-L's page. Only after acceptance do you switch to `\documentclass[letterpaper, 10 pt, journal, twoside]{ieeetran}` (see Camera-ready below).
- **Page budget: up to 8 pages by default, everything included.** RA-L says: "Letters are six pages long in two-column IEEE format ... with up to two extra pages allowed at a charge ($175 per extra page)". It also says: "These page limits include everything needed for publication, e.g., figures, tables, and any appendices", so references are not exempt. PaperPlaza rejects files longer than 8 pages. **Default to `MAX_PAGES = 8`**: any length up to 8 pages is acceptable. Do not cut the paper to 6 (or 7) pages on your own to avoid the charge; tighten to 6 or 7 only when the user explicitly asks for it. If the paper runs past 6 pages, note the $175-per-page charge once in the report, but do not shrink the paper because of it. This budget differs from the 4–5 pages typical of communications Letters mentioned in the IEEE Journal section.
- **Double-anonymous review.** RAS has applied this to its fully sponsored journals since 2025-01-01, and a violation can lead to a desk rejection. It overrides "IEEE journals are typically not anonymous" above, so set `ANONYMOUS = true` for RA-L until acceptance. Rules:
  - Do not include a cover page. RA-L says: "Please leave space for an author byline, but do not include the author information." Fill the byline with a placeholder such as `Anonymous Authors`, not invisible text, so reviewers can see that the authors are withheld on purpose.
  - Do not put names or affiliations anywhere, including the supplementary material and the PDF metadata. Watch out for `\hypersetup{pdfauthor=...}`.
  - Include acknowledgments to people or funding agencies only after acceptance.
  - Cite your own work in neutral wording ("In previous work [x]"), never "In our earlier work".
  - Remove lab names and logos from figures and videos, and blur people's faces.
  - Hide individual robot names unless the robot is widely known.
  - Do not link to anything that reveals identity, such as YouTube, GitHub or lab pages.
  - Posting on arXiv is allowed. Reviewers are told not to search for it.
- **Keywords.** Put 2–5 keywords just beneath the abstract. The first two must come from the predefined RA-L set, which you select in PaperPlaza. Do not assume the RA-L set matches the conference list in [`icra-keywords.md`](icra-keywords.md). The ICRA 2027 rule of exactly 3 keywords, one per tier, does not apply to RA-L.
- **Only videos as extra material.** The RA-L FAQ says: "Multimedia materials (i.e. videos) are the only extra material allowed." Do not submit a supplementary PDF, and do not plan an appendix that would push the paper past 8 pages. Each submission may include only one video, packed in a single zip archive of at most 50 MB. The video falls under the anonymity rules too. You may post datasets online and cite them by URL, as long as the URL does not reveal identity during review.
- **No deadlines; presenting at a conference is a transfer after acceptance.** RA-L has no submission deadlines. It guarantees a final decision within 6 months and averages 4. The FAQ advises submitting at least 4 months before a conference's transfer deadline. For ICRA 2027, PaperPlaza transfers RA-L papers directly, and the transfer deadline is **31 December 2026**. Transferred papers appear in RA-L on Xplore, not in the conference proceedings. RAS marks the older "RA-L + conference option" scheme, where a paper rejected by RA-L could still become a conference paper, as outdated after IROS 2022. Do not plan around it.
- **Review timeline.** The first decision comes within about 3 months, and a revision is due within 30 days of it. Submit only a stable version: RA-L says "Incremental updates are typically not allowed." When resubmitting a rejected paper, give the previous submission number in PaperPlaza. Also upload one PDF made of the authors' response followed by the revised paper with the changes highlighted.
- **Extending a conference paper.** RA-L may accept an extension of an IEEE conference paper under the "evolutionary paradigm". It notes, however, that this is "difficult" for Letters, because a Letter is about as long as a conference paper.
- **arXiv statement.** The preprint must carry: "This work has been submitted to the IEEE for possible publication. Copyright may be transferred without notice, after which this version may no longer be accessible." After acceptance, add the IEEE copyright notice. After publication, replace the preprint with the DOI citation, or with the accepted version plus the copyright notice and a link to Xplore.
- **Generative AI (RAS policy).**
  - Disclose AI-generated text, figures, images or code in the acknowledgments section. Using AI for editing and grammar does not need disclosure.
  - AI-generated illustrative figures must name the tool and give the prompt **in the caption**.
  - AI cannot be listed as an author.
  - These rules collide with the rule above that acknowledgments appear only after acceptance, and neither RAS page says how to resolve that at review time. Our working reading, which is not stated by RAS: at submission, keep an `Acknowledgment` section that contains only the AI disclosure, and add people and funding after acceptance.

Final-check implications (initial submission):

- The document class is `ieeeconf`, or `IEEEtran[conference]` with the margin overrides. The paper size is US Letter, and the bbox margin check in `paper-compile` passes.
- The paper is at most 8 pages including references, or at most the 6 or 7 pages the user explicitly asked for. Pages 7–8 incur the $175-per-page charge: report it, do not cut for it.
- Nothing identifies the authors:
  - the byline is empty;
  - `pdfinfo main.pdf` shows no Author field;
  - the acknowledgments contain no people or funding, and no grant numbers appear in footnotes;
  - self-citations use neutral wording;
  - no GitHub, YouTube or lab URLs appear;
  - figures and the video have no logos, and faces are blurred.
- 2–5 keywords appear beneath the abstract, and the first two are from the RA-L set.
- All fonts are embedded and none are Type 3 (see `camera-ready-prep/references/ras-papercept.md`).

Camera-ready (after acceptance):

- Reformat to `\documentclass[letterpaper, 10 pt, journal, twoside]{ieeetran}`. RA-L's Information for Authors links an official sample (`RA-L-Template-YY.tex` / `.pdf`); start from it rather than from `ieee_journal.tex`.
- Fill in the parts that only exist after acceptance:
  - the running header `IEEE ROBOTICS AND AUTOMATION LETTERS. PREPRINT VERSION. ACCEPTED MONTH, YEAR`;
  - a first-page footnote containing "Manuscript received: ...; Revised: ...; Accepted: ..." and "This paper was recommended for publication by Editor ... upon evaluation of the Associate Editor and Reviewers' comments.", followed by the funding, the affiliations and e-mails, and "Digital Object Identifier (DOI): see top of this page."
- Re-check the page count after converting. The journal class lays text out differently from `ieeeconf`, so the 8-page cap must hold in the final format, not only in the submitted one.
- **Do not include author biographies or photos.** Letters exclude them, unlike Transactions, so drop any `IEEEbiography` blocks.
- Restore the authors and their IEEE membership status, the acknowledgments and the funding.
- Size limits: the PDF must be at most 5 MB, the zipped sources at most 10 MB, and the zipped multimedia at most 50 MB.
- Complete the IEEE electronic copyright form before the final submission. Final files are due within **14 days** of acceptance, and pages 7–8 are billed at $175 each.

## Minimal Submission Checklist

Before submission, verify:

- the venue-specific required sections are present,
- the page budget is satisfied for the main body,
- the contribution bullets do not overclaim,
- citations, figures, tables, and references are internally consistent,
- the PDF is anonymized and ready for reviewer consumption.

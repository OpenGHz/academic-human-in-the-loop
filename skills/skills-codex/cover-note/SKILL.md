---
name: cover-note
description: "Draft the cover note (cover letter) a submission form asks for: plain text for the editor saying what the submission is, why it fits the venue, and the declarations the editor needs. Venue-aware, with the RA-L / PaperPlaza rules on file. Use when user says \"cover note\", \"cover letter\", \"投稿信\", \"给编辑的信\", or pastes a form's cover-note prompt, at initial submission, revision, resubmission or final version."
argument-hint: "[paper-dir] [— venue: <venue>] [— stage: initial|revision|resubmission|final]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebFetch
---

# Cover Note: The Submission Message to the Editor

Draft a cover note for: **$ARGUMENTS**

The editor reads the cover note apart from the paper, and the abstract already reports what the paper found. The note carries only what the editor needs and can get neither from the paper nor from another field of the form: what the submission is, why it suits this venue, and the declarations. A note limited to that is brief, which is what the form asks for.

## Constants

- **OUTPUT = `paper/COVER_NOTE.md`**: written next to the paper; override with `— output: <path>`.
- **MAX_WORDS = 150**: body of the note, without salutation and sign-off.

## Inputs

1. **Paper**: the directory in `$ARGUMENTS`, else `paper/`. Read the title (`\title{...}`), the abstract and the acknowledgment. If `idea-stage/TITLE.md` exists (from `/title-decider`), its terminology rulings bind the note as well.
2. **Venue**: `— venue:` > the `## Target Venue` section of `PAPER_PLAN.md` > ask the user.
3. **Stage**: `— stage:` > a decision letter or reviews in the conversation or project (`revision`, `resubmission`, or `final` after acceptance) > `initial`.
4. **Form text**: the field's prompt, when the user pasted it (RA-L: "Please enter a brief cover note. This is not transmitted to the other editorial staff or to the reviewers."). It names the reader.

## Workflow

### Step 1: Pin the reader and the venue's requirements

Read the venue's section of [`../shared-references/venue-checklists.md`](../shared-references/venue-checklists.md) and its **Cover note** entry. If the venue has no section or no such entry, fetch its author-information and submission-procedure pages with WebFetch and quote what they require of the note at this stage. If the form text the user pasted contradicts the entry, the form wins; tell the user the entry is stale.

Done when you can name who reads the note and can list every item the venue requires in it at this stage, each with its source, or can state that the sources require none.

The reader decides the anonymity of the note:

- **Editor-only** (the form says reviewers do not receive it): names may appear, but sign `The authors` unless the user asks for names. Anything reviewers must weigh belongs in the paper.
- **Shared with reviewers or the whole editorial board** of a double-anonymous venue: no names, affiliations or identifying links anywhere in the note.

### Step 2: Collect the declarations

Give each candidate a status: shown by the paper, required by the venue, or awaiting the user's confirmation.

- **Originality and no concurrent submission.** A paper under review at a conference counts as concurrent.
- **Earlier versions**: a conference paper, or a previously rejected submission and its number. When the venue has a field for it or requires citing it in the paper (RA-L does both), that is where it is declared; the note mentions it in one clause.
- **AI use**: when the acknowledgment discloses generative-AI use, one sentence saying so. IEEE requires the disclosure in the acknowledgment, not in the note; the sentence spares the editor a surprise.
- **Requests the editor must act on**: reviewers to exclude for a conflict of interest when the form has no field for them; a request to deviate from the venue's review model.
- **Revision or resubmission**: the previous submission number and the response file that answers the reviews.
- **Final version**: the changes made for the final version, when the venue asks for them.

Each sentence of the note passes one test: the editor needs it, and neither the paper nor another form field carries it. Findings and numbers live in the abstract; preprints that the venue's rules allow without notice, keywords and suggested reviewers live in their own fields or nowhere.

### Step 3: Draft

Plain text in the venue's language (English for IEEE), shaped for pasting into a web form: straight quotes, no Markdown, no LaTeX.

```text
Dear <reader from Step 1>,

We submit "<title>" for consideration in <venue>.

<One sentence: the kind of contribution (method, system, benchmark, negative result with its explanation, ...) and its core claim, in the abstract's terms and no stronger. One sentence: which of the venue's readers it serves.>

<The declarations from Step 2, one sentence each.>

Sincerely,
The authors
```

- Keep the body within MAX_WORDS, and keep numbers out of the second paragraph.
- For a revision or resubmission, the first paragraph names the previous submission ("a revised version of RA-L submission <number>, ...") and points to the response file; the point-by-point response stays in that file.
- When the user trims the draft, edit OUTPUT and show the whole note again.

### Step 4: Write and report

Write OUTPUT:

````markdown
# <Venue> Cover Note

For the <system> "<field>" field at <stage>. <Who reads it, quoting the form or the venue page.>

Before pasting:
- <each declaration awaiting confirmation>
- <each placeholder left in the note>

```text
<the note>
```
````

Report to the user in their language: the note, the before-pasting list, and any venue requirement from Step 1 that belongs in the paper or in another field rather than the note. The skill writes only OUTPUT.

## References

- [`../shared-references/venue-checklists.md`](../shared-references/venue-checklists.md): per-venue rules; the RA-L section has the cover-note entry.
- [`../camera-ready-prep/SKILL.md`](../camera-ready-prep/SKILL.md): the rest of the final-version preparation after acceptance.

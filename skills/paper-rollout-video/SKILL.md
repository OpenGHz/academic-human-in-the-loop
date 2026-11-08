---
name: paper-rollout-video
description: "Build a paper's supplementary video from simulated policy rollouts: shots picked by fixed rules from the evaluation files, bare panels rendered from checkpoints, pages composed in code with every on-screen number read from the paper source, a one-command rebuild from committed panels, Codex cross-review and the /paper-video gate. Use when the footage must be rendered from trained policies in simulation (robot learning, world models, sim2sim) rather than cut from recordings, or when user says \"用仿真结果做补充视频\", \"rollout video\", \"render the policy videos for the paper\". For editing existing recordings use /paper-video."
argument-hint: "[paper-dir] [— venue: RAL|CORL|ICRA|RSS|GENERIC] [— max-mb: N] [— max-seconds: N] [— runs: <dir>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex, mcp__codex__codex-reply
---

# Paper Rollout Video

Build a supplementary video from simulated rollouts for: **$ARGUMENTS**

Every frame comes from a trained policy rolled out in simulation, every number on screen from
the paper's source, and one command rebuilds the video. The deliverable is the MP4 *and* that
reproducible build: a compose script, the raw panels with their shot plan, and a byte-for-byte
`--panels` rebuild. `/paper-video` supplies the final size, duration and anonymity gate.

## Constants

- **FRAME** = 1920x1080, 25 fps, H.264 + AAC with `+faststart`; comparison pages put two
  960x540 panels side by side between a title band and a caption band.
- **LIMITS** = the venue's video size and duration caps. Take them from the user or the venue's
  author instructions; record them before Step 1.
- **STYLE** (defaults the user can override) = black background with white text; a soft
  synthesized soundtrack; few words per page, with motion (growing bars, curves drawn over
  time, diagrams built step by step) carrying the point instead of text cards.
- **REVIEWER** = `gpt-6-astra` at `xhigh`, read-only, one thread for the whole job.

## Workflow

### Step 1: Plan the pages and confirm

Read the abstract, the experiments section, the figure data and the macro files the numbers
come from (for example `*_facts.tex`). Propose the pages as a table (page, what moves on
screen, source of every number, seconds). Four decisions frame the job: the page list, the
branch that receives the code, where the final MP4 lives (desktop, server, repository via Git
LFS), and the frame size; take them from the arguments and defaults, and ask the user only for
those still open. A proven page order: the title over the tracking clips, training curves, a
guide page, one side-by-side comparison per motion or task type, a mechanism diagram, a
failure case, the key quantitative result, a one-sentence takeaway.

Done when the user has approved the page list and all four decisions are recorded.

### Step 2: Pick the shots by fixed rules

Selection is a rule applied to the evaluation files; appearance plays no part:

- **Seed**: per method, the seed with the median aggregate return.
- **Clip per type**: the clip whose (method − baseline) return difference is closest to the
  median difference over all clips; ties go to the first name.
- **Failure shot**: among the clips the run failed in evaluation, the one whose return is
  closest to that run's mean return; when the run failed on none, drop the failure page.
- **Window**: the one free choice, the seconds inside a clip, picked to show motion; the video
  says so.

Write `<raw>/plan.json`: every shot (run, checkpoint, clip, window, label) plus the per-clip
numbers the captions need. Done when `plan.json` exists and each rule fits in one sentence for
the guide page.

### Step 3: Render the panels

On the GPU machine, render one bare panel per shot: no text burned in, since all text is drawn
in Step 4. Write a provenance sidecar next to each panel (checkpoint, clip, window, label,
backend, renderer md5) and reuse a panel when its sidecar still matches.

- GPU simulators are not bit-reproducible: the same checkpoint can fail at another time, or
  not at all, on another run. Render the failure shot as a fresh rollout, record its outcome
  and failure time in a sidecar, take the window from it, and caption only what the rollout
  shown does.
- Render headless with the simulator's offscreen backend (MuJoCo: `MUJOCO_GL=egl`); a SOCKS
  proxy in the environment can break asset downloads.
- Run long renders detached (`nohup`, `screen`) and stop them by process group: a `pkill -f`
  pattern also matches the ssh command that launched it.

Done when every shot in `plan.json` has a panel and a matching sidecar.

### Step 4: Compose in code

Write the compose script as a list of page builders (`page(t) -> frame`) so one page can be
rendered as a still. PIL draws the frames at 2x and downsamples for antialiasing; imageio-ffmpeg
encodes; numpy synthesizes the soundtrack, so the video carries no third-party audio.

- **Sourced numbers**: read every number from the paper's macros, the figure data or
  `plan.json`; abort when a quoted phrase or the title no longer appears in the paper.
- **Manifest**: record every drawn string to `<output>.text.json` for the anonymity scan.
- **Font**: bundle an OFL font (Inter, for example) with its license, so frames match on every
  machine and μ, Δ and subscripts render.
- **One command**: a build script runs render then compose; `--panels` composes from the
  committed panels with no GPU and no runs.

Done when the script builds the full video from `plan.json` and the panels.

### Step 5: Lay out and word every page

Apply each rule to every page:

- **Title page**: the paper's title alone.
- **Guide page**: what all rollout pages share, said once (simulated robot, real time, what the
  overlay or ghost shows, the checkpoint, the selection rules, simulator non-repeatability).
  Later pages carry only what differs: the motion, its time window, the bars.
- **Grid**: the heading at the same height on every page, at most one footnote line, one
  sentence per line in lists, last lines of two words or more, every element clear of every
  other.
- **Names**: readable and sourced: `walk1_subject1` becomes "LAFAN1: Walk 1, subject 1".
  Keep the field's technical terms (seed, iteration, return, rollout, the paper's own
  vocabulary); a less "engineering" look means readable identifiers, not paraphrase.
- **One statistic per row**: a bar shows one quantity and its label names it ("Full-clip
  evaluation return", "Mean return of 3 seeds at iteration N"). A number on screen is one the
  paper reports or one the label pins down exactly; a one-seed count belongs on its own row,
  never under a multi-seed mean.

Done when every page passes every rule.

### Step 6: Preview stills, then compose

A full compose takes minutes, so render one still per page first, each at its busiest moment
(all text and bars visible), and look at every still for overlap, wrapping, lone words and
alignment. Measure a line with the font before rewording it to fit. Then compose the video and
pull a few frames from the MP4 to confirm the stills carried over.

Done when every page's still is clean and the composed MP4 shows the same pages.

### Step 7: Cross-review with Codex

Pass file paths, never summaries: the compose script, `plan.json`, the paper directory, the
stills directory and the text manifest. The reviewer can propose code changes, so append the
scope-limits block from
[`review-scope-limits.md`](../shared-references/review-scope-limits.md) verbatim to the prompt.

```
mcp__codex__codex:
  model: gpt-6-astra
  config: {"model_reasoning_effort": "xhigh"}
  sandbox: read-only
  prompt: |
    Review the supplementary video generator <script> (read-only).
    Paper source: <paper-dir>. Shot plan: <raw>/plan.json.
    Stills of every page: <stills-dir>; every on-screen string: <output>.text.json.
    Check (a) every on-screen string and number against the paper and plan.json,
    (b) information a reviewer needs that is missing, (c) wording: concise, no
    overclaim, anonymity kept, the paper's terms, (d) bugs in the script.
    Reply as MUST-FIX / SHOULD-FIX / NIT, each with the exact string or line and a
    concrete replacement; reply PASS when nothing must be fixed.
    [the SCOPE LIMITS block, verbatim]
```

Fix, then continue the same thread with `mcp__codex__codex-reply` until it replies PASS. When
the user asks for wording changes, first show a table (current text, proposed text, its
meaning in the user's language, the reason) with the reviewer's findings folded in, and apply
only what the user approves.

Done when the reviewer's last reply is PASS on the current script.

### Step 8: Gate

Resolve `$VIDEO_HELPER` (`paper_video.py`) with the resolver in
[`/paper-video`](../paper-video/SKILL.md), then:

```bash
python3 "$VIDEO_HELPER" verify --video <output>.mp4 --mode submission --venue GENERIC \
  --max-mb <LIMITS size> --max-seconds <LIMITS duration> --manifest <output>.text.json \
  --anon-blocklist '(?i)<authors|labs|repositories|usernames|hostnames>' --json-out verify.json
```

Done when `verify.json` reports `ok: true` with no violations and a clean anonymity scan.

### Step 9: Make it reproducible and deliver

Commit everything `--panels` reads: the build, render and compose scripts, the font with its
license, the paper files the numbers come from, the figure data, and through Git LFS the raw
panels with `plan.json` and the sidecars. In a fresh checkout with the LFS objects pulled,
run `--panels` with no GPU and no run directories, and compare its md5 with the MP4 you
deliver. Put the final MP4 where Step 1 said (in the repository only through Git LFS), with a
dated desktop copy when the user wants one, and report duration, size, md5, the gate result
and what changed since the last version.

Done when the fresh-checkout `--panels` rebuild has the same md5 as the delivered MP4.

## Outputs

```
<raw>/plan.json, <raw>/<shot>.mp4, <raw>/<shot>.shot.json    # shot plan, bare panels, provenance
<output>.mp4, <output>.text.json, verify.json                 # video, on-screen strings, gate result
tools/<build script> [--panels]                               # one-command rebuild
```

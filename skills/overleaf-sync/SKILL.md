---
name: overleaf-sync
description: "Two-way sync between a local paper directory and an Overleaf project, so ARIS audit/edit workflows stay on the local copy while collaborators edit in the Overleaf web UI. Use when user says \"同步 overleaf\", \"overleaf sync\", \"推送到 overleaf\", \"connect overleaf\", \"Overleaf 桥接\", \"pull overleaf\", \"push overleaf\", or wants to bridge their ARIS paper directory with an Overleaf project."
argument-hint: "[setup <project-id> | pull | push | status]"
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write
---

# Overleaf Sync

Bridge a local paper directory with an Overleaf project so that:

- **You** can keep editing in the Overleaf web UI (or share editing access with collaborators)
- **ARIS** can read your changes, run audits (`/paper-claim-audit`, `/citation-audit`, `/auto-paper-improvement-loop`), and push fixes back

This uses the official **Overleaf Git bridge** (Premium feature). The agent **never sees your authentication token** — you do the one-time auth manually so the token lives in macOS Keychain, not in chat history or `.git/config`.

## When to Use This Skill

- You want to use Overleaf as the editing surface (better collaboration, shared with team) but still run ARIS pipelines locally
- You want to take an existing local ARIS paper and push it to Overleaf for a co-author to edit
- A collaborator made changes in Overleaf and you want to pull + diff them before continuing local work

## Constants

- **CLONE_DIR_DEFAULT** = `paper-overleaf` (sibling of existing `paper/`, NOT inside `paper/`)
- **CREDENTIAL_HELPER** = `osxkeychain` (macOS) / `manager` (Windows) / `cache` (Linux fallback)
- **TOKEN_HANDLING** = **NEVER write token to disk, env var, or chat**. User pastes it once into the terminal credential prompt; the OS keychain stores it from then on.

## Architecture

```
┌─────────────────┐       git pull/push      ┌─────────────────┐
│  Local paper/   │ ◄─── rsync ──── ►       │ paper-overleaf/ │ ◄──► Overleaf web
│  (ARIS audits)  │                          │ (git bridge)    │     (collaborators)
└─────────────────┘                          └─────────────────┘
```

The `paper-overleaf/` directory is a **git clone of the Overleaf project**. The `paper/` directory is the working copy where ARIS skills run. They are kept in sync via `rsync`.

**Single-source-of-truth rule**: at any given time, treat *one* of them as authoritative for active editing. Switch directions explicitly with `pull` or `push`, and run a `status` check before either to surface unexpected divergence.

## Shared helper — resolve once, before any sub-command

`status`, `pull`, `push`, `sync-figures`, and `audit` are already implemented by the shared-runtime
helper `overleaf_sync.sh`. **Call it instead of retyping the `git`/`rsync` recipes below** — those
recipes are documentation of what the helper does (and the fallback if it does not resolve), not a
second implementation to maintain. Resolve it with the standard chain (see
[`../shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2):

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
OVERLEAF_SYNC=".aris/tools/overleaf_sync.sh"
[ -f "$OVERLEAF_SYNC" ] || OVERLEAF_SYNC="tools/overleaf_sync.sh"
[ -f "$OVERLEAF_SYNC" ] || { [ -n "${ARIS_REPO:-}" ] && OVERLEAF_SYNC="$ARIS_REPO/tools/overleaf_sync.sh"; }
[ -f "$OVERLEAF_SYNC" ] || OVERLEAF_SYNC=""
```

**Failure policy: fall back, don't block.** If `$OVERLEAF_SYNC` is empty, run the inline recipes in
each sub-command below — same effect, fewer guardrails.

Path resolution inside the helper: `--paper`/`--clone` flags → `$OVERLEAF_PAPER_DIR`/`$OVERLEAF_CLONE_DIR`
→ `PAPER_DIR=`/`CLONE_DIR=` in `.overleaf-sync.conf` → `./paper` and `./paper-overleaf`. It carries the
canonical rsync exclude list (`.git`, `.aris`, LaTeX intermediates, `main.pdf`, `raw_data`, …) — one
place to fix when the list changes, which is exactly why the inline `--exclude` chains should not be
copied around.

## Sub-commands

### `setup <project-id>` — one-time

Sets up the bridge for a new Overleaf project. **The user runs this in their own terminal, never through the agent.** The skill ships with a hardened setup script that:

1. Refuses to run unless stdin/stdout are a TTY (won't run inside an agent harness)
2. Reads the token from a hidden prompt (no chat history, no shell history)
3. Strips the token from the remote URL immediately after cloning
4. Primes the OS keychain so subsequent agent operations are auth-free
5. **Auto-installs a `pre-commit` hook in `paper-overleaf/.git/hooks/` that refuses to commit any blob containing the token pattern `olp_[A-Za-z0-9]{20,}`** — a hard technical block, not a behavioral rule

The agent's only role here is to print the user instruction:

```
Run this in your own terminal (NOT through me):

    bash <ARIS_REPO>/tools/overleaf_setup.sh <project-id-or-url>

When it finishes, tell me "setup done" and I'll verify.
```

After the user reports "setup done", the agent verifies (token-free):

```bash
cd paper-overleaf
git remote -v                    # must show URL WITHOUT token
git config --get credential.helper
git fetch && git log --oneline -3   # must succeed without prompting
ls .git/hooks/pre-commit         # must exist
bash <ARIS_REPO>/tools/overleaf_audit.sh .   # must report "Audit clean"
```

If `paper-overleaf/` exists but is empty (new Overleaf project), the agent then mirrors local `paper/` into it (see `push` workflow).

### `pull` — before each editing session

```bash
bash "$OVERLEAF_SYNC" pull
```

It runs `git pull --ff-only`, prints the `BEFORE..AFTER` diffstat, and refuses to auto-merge into
`paper/` — on a non-fast-forward it prints the two `git log` inspection commands and exits 1 rather
than merging. Fallback (helper unresolved):

```bash
cd paper-overleaf && git pull --ff-only

# Show what changed since last pull
LAST=$(git rev-parse HEAD@{1})
git diff --stat $LAST..HEAD
git diff $LAST..HEAD -- 'sec/*.tex'        # detailed view for prose changes
```

**Diff protocol — DO NOT blindly merge into local `paper/`.** Overleaf edits frequently include:

- **Half-finished sentences** (collaborator clicked save mid-thought)
- **Typos** that aren't in canonical references (`Lrage` for `Large`)
- **Commented-out blocks** that may be intentional or may be a stash
- **Number changes** that should re-trigger `/paper-claim-audit`
- **Cite key changes** that should re-trigger `/citation-audit`

For each diff hunk, decide one of:

| Hunk character | Action |
|----------------|--------|
| Clean editorial improvement | Sync into `paper/`, no audit needed |
| Numerical / claim change | Sync, then re-run `/paper-claim-audit` |
| New `\cite{...}` | Sync, then re-run `/citation-audit` |
| Half-sentence / obvious typo | Flag to user, do NOT auto-sync |
| New section / restructure | Stop, ask user before syncing |

After deciding per-hunk:

```bash
# Sync only the files the user approved into local paper/
rsync -av paper-overleaf/sec/0.abstract.tex paper/sec/0.abstract.tex
# (or use Edit tool for surgical changes that skip half-sentences)
```

### `push` — after local editing

Use after ARIS skills have edited `paper/` and you want collaborators on Overleaf to see the changes.

```bash
bash "$OVERLEAF_SYNC" push                       # phase 1: stage + show the diff
bash "$OVERLEAF_SYNC" push --yes -m "<message>"  # phase 2: after the user approves
```

The helper does all four steps (`pull --ff-only` → `rsync` → `git add -A` + `--cached --stat` review
→ commit + push) and satisfies the confirmation gate by construction: its `confirm` prompt reads
stdin, so under an agent harness phase 1 always ends in "Cancelled. Changes are STAGED but not
committed." **Show that diffstat to the user, wait for approval, then re-run with `--yes`.** Never
pass `--yes` on the first call. Re-running is safe — the rsync is idempotent.

Two behaviors worth knowing: it distinguishes a network failure from a real divergence (and tells the
user the proxy export line instead of "remote diverged"), and it stages *before* the review so new
untracked files show up in the stat. It rsyncs **without** `--delete` unless `OVERLEAF_SYNC_DELETE=1`
— deleting files on a shared Overleaf project is opt-in.

Fallback (helper unresolved):

```bash
# 1. Always pull first to surface remote drift
cd paper-overleaf && git pull --ff-only

# 2. If pull was a no-op, sync local paper → paper-overleaf
rsync -av --delete \
  --exclude='.git' --exclude='.DS_Store' \
  --exclude='*.aux' --exclude='*.log' --exclude='*.bbl' --exclude='*.blg' \
  --exclude='*.fls' --exclude='*.fdb_latexmk' --exclude='*.out' \
  --exclude='*.synctex.gz' --exclude='*.toc' \
  paper/ paper-overleaf/

# 3. Show what would be pushed
git status --short
git diff --stat

# 4. Commit + push
git add -A
git commit -m "<descriptive message — what ARIS changed and why>"
git push
```

**Commit message protocol**: include the ARIS skill that produced the change so collaborators on Overleaf understand provenance. Examples:

- `paper-write: regenerated sec/3.assurance after audit cascade refactor`
- `citation-audit: fix 14 metadata entries (madaan2023, lee2024, ...)`
- `paper-claim-audit: correct sec/5 numbers vs results/run_2026_04_19.json`

**Confirmation gate**: `push` writes to a shared resource. ALWAYS show the user `git diff --stat` (and a representative hunk for prose changes) before running `git push`. Wait for explicit confirmation unless the user said `auto: true` upfront.

### `status` — diagnostic

```bash
bash "$OVERLEAF_SYNC" status
```

It prints both divergence axes (remote-vs-clone commit counts, `paper/`-vs-`paper-overleaf/` as an
`rsync -n` dry run using the canonical excludes) and ends with the verdict from the table below, so
there is no need to reproduce the `diff -rq | grep -v ...` pipeline by hand. Fallback:

```bash
cd paper-overleaf
git fetch
echo "=== Remote-vs-local divergence ==="
git log --oneline HEAD..origin/master    # remote ahead
git log --oneline origin/master..HEAD    # local ahead
echo "=== paper/ vs paper-overleaf/ divergence ==="
diff -rq --brief paper/ paper-overleaf/ 2>/dev/null \
  | grep -v "Only in paper/.*\.\(aux\|log\|out\|fls\|fdb_latexmk\|bbl\|blg\|synctex\|toc\)" \
  | grep -v "Only in paper-overleaf/.git" \
  | grep -v "DS_Store"
```

Three-way state assessment:

| Remote ahead? | paper/ vs paper-overleaf/ differ? | Meaning | Recommended action |
|:-------------:|:---------------------------------:|---------|--------------------|
| No  | No  | Clean       | Nothing to do |
| Yes | No  | Overleaf has new edits | Run `pull`, then re-run status |
| No  | Yes | Local ARIS edits unsynced | Run `push` |
| Yes | Yes | Diverged — needs merge | Stop, surface to user, do NOT auto-resolve |

### `sync-figures` — figures only

```bash
bash "$OVERLEAF_SYNC" sync-figures
```

Pushes `paper/figures/` → `paper-overleaf/figures/` alone (allow-list: `.pdf .png .svg .jpg .jpeg
.tex .json`; `__pycache__` and `.figures-prep` excluded), then stages and commits after confirmation
— **no push**. Use it when only the figures changed and a full `push` would drag in unrelated prose
edits still in progress.

### `audit` — token leak scan

```bash
bash "$OVERLEAF_SYNC" audit
```

Thin alias for `overleaf_audit.sh <clone-dir>` — same scan as the `setup` verification step, run
against the resolved clone directory. Cheap; run it whenever the remote URL or credential config
may have been touched.

## Conflict Resolution

If `git pull --ff-only` fails because of true divergence:

1. **Do not** run `git pull` (which would auto-merge).
2. **Do not** run `git reset --hard` or `git push --force` (destructive).
3. Show the user `git log origin/master ^HEAD` (their Overleaf commits) and `git log HEAD ^origin/master` (local ARIS commits).
4. Ask the user which side to take per file, or to manually merge in Overleaf and then re-pull.

## Token Security — Defense in Depth

Behavioral rules alone are not enough — the next agent reading this skill might forget them. The skill therefore relies on **technical guards** that hold even if the agent misbehaves:

| Layer | Guard | Where enforced |
|-------|-------|---------------|
| 1. Setup | `overleaf_setup.sh` refuses to run without an interactive TTY (agents don't have one) | `tools/overleaf_setup.sh` |
| 2. Input | Token is read by `read -s` (hidden prompt, no shell history, never enters chat) | `tools/overleaf_setup.sh` |
| 3. Storage | Token goes straight into OS keychain via `git credential approve`; remote URL is stripped to a token-free form | `tools/overleaf_setup.sh` |
| 4. Commits | `paper-overleaf/.git/hooks/pre-commit` greps staged content for `olp_[A-Za-z0-9]{20,}` and aborts | auto-installed by setup script |
| 5. Audit | `overleaf_audit.sh` scans working tree, remote URLs, git history, credential files | `tools/overleaf_audit.sh` |

Behavioral rules (still apply, but secondary):

- **Never** ask the user to paste a token into chat. If they do anyway: (a) acknowledge it, (b) tell them to revoke it at https://www.overleaf.com/user/settings, (c) recover via keychain if already primed.
- **Never** write a token to a file (`.env`, `.netrc`, `tools/*.sh`, etc.) committed to any repo.
- **Never** include a token in a `git remote -v` URL — strip it after clone.
- On `401 Unauthorized` from push/pull, tell the user the keychain entry expired and to re-run `overleaf_setup.sh`. Do **not** ask for a fresh token.

## Mutual-Exclusion Rule

The single biggest source of pain in two-way sync is **simultaneous editing on both sides**.

- If the user is in an active Overleaf editing session, ARIS skills should **read-only** access `paper/` until the user runs `/overleaf-sync pull`.
- If ARIS is in the middle of `/auto-paper-improvement-loop` or `/paper-write`, the user should pause Overleaf editing until the loop finishes and `/overleaf-sync push` is run.

When in doubt, run `status` first.

## Output Contract

- `paper-overleaf/` directory at repo root, git clone of Overleaf project (origin URL has NO token)
- `paper/` directory unchanged in role — still the ARIS working copy
- Each `pull`/`push` operation: a one-line summary back to the user (commits pulled / pushed, file count, link to Overleaf project URL)

## See Also

- `/paper-claim-audit` — re-run after pulling Overleaf changes that touch numbers
- `/citation-audit` — re-run after pulling Overleaf changes that add/edit `\cite{...}`
- `/paper-compile` — local LaTeX build; Overleaf compiles independently in the cloud
- Overleaf Git bridge docs: https://www.overleaf.com/learn/how-to/Using_Git_and_GitHub

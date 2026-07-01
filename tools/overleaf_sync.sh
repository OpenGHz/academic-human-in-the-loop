#!/usr/bin/env bash
# overleaf_sync.sh — wrapper for the /overleaf-sync sub-commands.
#
# Reads paths from (in order of precedence):
#   1. CLI flags --paper / --clone
#   2. env vars OVERLEAF_PAPER_DIR / OVERLEAF_CLONE_DIR
#   3. $REPO_ROOT/.overleaf-sync.conf  (PAPER_DIR=..., CLONE_DIR=...)
#   4. fallback ./paper and ./paper-overleaf
#
# Usage: bash tools/overleaf_sync.sh <subcommand> [flags]

set -euo pipefail

# ---------- 1. Resolve paths --------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONF="$REPO_ROOT/.overleaf-sync.conf"

PAPER_DIR=""
CLONE_DIR=""

if [[ -f "$CONF" ]]; then
  # shellcheck disable=SC1090
  source "$CONF"
fi
PAPER_DIR="${OVERLEAF_PAPER_DIR:-${PAPER_DIR:-}}"
CLONE_DIR="${OVERLEAF_CLONE_DIR:-${CLONE_DIR:-}}"

# ---------- 2. Parse sub-command + flags --------------------------------
SUBCMD="${1:-}"
[[ $# -gt 0 ]] && shift

# Allow --help / -h as the first arg.
if [[ "$SUBCMD" == "--help" || "$SUBCMD" == "-h" ]]; then
  SUBCMD=""
  SHOW_HELP_EARLY=1
fi

AUTO_YES=0
COMMIT_MSG=""
SHOW_HELP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --paper)    PAPER_DIR="$2"; shift 2 ;;
    --clone)    CLONE_DIR="$2"; shift 2 ;;
    --yes|-y)   AUTO_YES=1; shift ;;
    --message|-m) COMMIT_MSG="$2"; shift 2 ;;
    --help|-h)  SHOW_HELP=1; shift ;;
    *)          echo "Unknown flag: $1" >&2; SHOW_HELP=1; shift ;;
  esac
done

PAPER_DIR="${PAPER_DIR:-./paper}"
CLONE_DIR="${CLONE_DIR:-./paper-overleaf}"

# Resolve to absolute paths if they exist
[[ -d "$PAPER_DIR" ]] && PAPER_DIR="$(cd "$PAPER_DIR" && pwd)"
[[ -d "$CLONE_DIR" ]] && CLONE_DIR="$(cd "$CLONE_DIR" && pwd)"

usage() {
  cat <<EOF
Usage: bash tools/overleaf_sync.sh <subcommand> [flags]

Subcommands:
  status         Three-way diagnostic: remote-vs-clone, clone-vs-paper.
                 Read-only. Always safe to run.
  pull           git pull --ff-only on the clone; show what changed but
                 do NOT auto-merge into paper/. User reviews each hunk.
  push           Mirror paper/ → paper-overleaf/ (figures symlink resolved
                 via rsync -L), show diff, confirm, commit, push.
  sync-figures   Only copy figure-shaped files (pdf/png/svg/jpg/jpeg + .tex
                 + .json) from paper/figures/ into the clone. Stages and
                 commits locally; does not push (run 'push' after).
  audit          Run tools/overleaf_audit.sh on the clone.

Flags:
  --paper PATH       Override paper directory.
  --clone PATH       Override clone directory.
  --yes, -y          Skip confirmation prompts (push only).
  --message, -m MSG  Commit message for push (default is a generic stamp).
  --help, -h         This message.

Environment variables (alternatives to flags):
  OVERLEAF_PAPER_DIR        Same as --paper
  OVERLEAF_CLONE_DIR        Same as --clone
  OVERLEAF_SYNC_DELETE=1    Make push use rsync --delete (DANGEROUS:
                            collaborator-only files in clone get wiped).
  OVERLEAF_SYNC_COMMIT_MSG  Same as --message

Configuration file:
  $CONF
  Variables: PAPER_DIR, CLONE_DIR

Resolved paths:
  PAPER_DIR = $PAPER_DIR
  CLONE_DIR = $CLONE_DIR
EOF
}

if [[ "$SHOW_HELP" -eq 1 || "${SHOW_HELP_EARLY:-0}" -eq 1 || -z "$SUBCMD" ]]; then
  usage; exit 0
fi

if [[ ! -d "$CLONE_DIR/.git" ]]; then
  echo "ERROR: '$CLONE_DIR' is not a git repository." >&2
  echo "  Run tools/overleaf_setup.sh first, or fix --clone path." >&2
  exit 2
fi

# ---------- 3. Shared helpers -------------------------------------------
EXCLUDES=(
  --exclude='.git'         --exclude='.aris'      --exclude='.figures-prep'
  --exclude='.DS_Store'    --exclude='__pycache__'
  --exclude='*.aux'        --exclude='*.log'      --exclude='*.bbl'
  --exclude='*.blg'        --exclude='*.fls'      --exclude='*.fdb_latexmk'
  --exclude='*.out'        --exclude='*.synctex.gz'  --exclude='*.toc'
  --exclude='main.pdf'     --exclude='main_round*.pdf' --exclude='main_post_*.pdf'
  --exclude='raw_data'     --exclude='*.bkp'      --exclude='.$*'
)

confirm() {
  if [[ "$AUTO_YES" -eq 1 ]]; then
    echo "  [--yes] auto-confirmed"
    return 0
  fi
  printf "%s [y/N]: " "$1"
  read -r REPLY
  [[ "$REPLY" =~ ^[Yy]$ ]]
}

remote_branch() {
  git -C "$CLONE_DIR" rev-parse --abbrev-ref --symbolic-full-name '@{u}' \
    2>/dev/null || echo 'origin/master'
}

# ---------- 4. Sub-commands ---------------------------------------------
cmd_status() {
  echo "=== PAPER_DIR: $PAPER_DIR"
  echo "=== CLONE_DIR: $CLONE_DIR"
  echo
  echo "=== Remote vs clone ==="
  git -C "$CLONE_DIR" fetch --quiet
  REMOTE="$(remote_branch)"
  REMOTE_AHEAD="$(git -C "$CLONE_DIR" rev-list --count "HEAD..$REMOTE" 2>/dev/null || echo 0)"
  LOCAL_AHEAD="$(git -C "$CLONE_DIR" rev-list --count "$REMOTE..HEAD" 2>/dev/null || echo 0)"
  echo "  remote ahead: $REMOTE_AHEAD commit(s)"
  echo "  local  ahead: $LOCAL_AHEAD commit(s)"
  [[ "$REMOTE_AHEAD" -gt 0 ]] && \
    git -C "$CLONE_DIR" log --oneline "HEAD..$REMOTE" | sed 's/^/    /'
  [[ "$LOCAL_AHEAD" -gt 0 ]] && \
    git -C "$CLONE_DIR" log --oneline "$REMOTE..HEAD" | sed 's/^/    /'

  echo
  echo "=== paper/ vs paper-overleaf/ (rsync dry-run) ==="
  RSYNC_DIFF="$(rsync -aLvn --delete "${EXCLUDES[@]}" \
                "$PAPER_DIR/" "$CLONE_DIR/" 2>/dev/null \
                | grep -Ev '^(sending incremental|sent |total |^$)' \
                | grep -v '/$' || true)"
  if [[ -n "$RSYNC_DIFF" ]]; then
    printf '%s\n' "$RSYNC_DIFF" | head -50
    PUSH_PENDING=1
  else
    echo "  (in sync)"
    PUSH_PENDING=0
  fi

  echo
  echo "=== Verdict ==="
  if [[ "$REMOTE_AHEAD" -eq 0 && "$LOCAL_AHEAD" -eq 0 && "$PUSH_PENDING" -eq 0 ]]; then
    echo "✅ Clean — paper/, paper-overleaf/, Overleaf all in sync."
  elif [[ "$REMOTE_AHEAD" -gt 0 && "$PUSH_PENDING" -eq 0 ]]; then
    echo "ℹ️  Overleaf has new commits. Run: bash tools/overleaf_sync.sh pull"
  elif [[ "$REMOTE_AHEAD" -eq 0 && "$PUSH_PENDING" -eq 1 ]]; then
    echo "ℹ️  Local paper/ has unsynced changes. Run: bash tools/overleaf_sync.sh push"
  elif [[ "$REMOTE_AHEAD" -gt 0 && "$PUSH_PENDING" -eq 1 ]]; then
    echo "⚠️  Both sides changed. Pull first, review, then push."
  fi
}

cmd_pull() {
  echo "=== git pull --ff-only ==="
  cd "$CLONE_DIR"
  BEFORE="$(git rev-parse HEAD)"
  if ! git pull --ff-only; then
    cat >&2 <<EOF

⚠️  pull --ff-only failed — likely true divergence.

  Inspect both sides before doing anything destructive:
    git -C "$CLONE_DIR" log HEAD..$(remote_branch)   # remote commits
    git -C "$CLONE_DIR" log $(remote_branch)..HEAD   # local commits

  Do NOT run plain 'git pull' (auto-merge) or 'git reset --hard'.
  Either reconcile in Overleaf web UI then re-pull, or hand-merge per file.
EOF
    exit 1
  fi
  AFTER="$(git rev-parse HEAD)"
  if [[ "$BEFORE" == "$AFTER" ]]; then
    echo "  (already up to date)"
    return 0
  fi
  echo
  echo "=== Changes pulled ($BEFORE..$AFTER) ==="
  git diff --stat "$BEFORE..$AFTER"
  echo
  cat <<EOF
Per skill protocol, changes are now in paper-overleaf/ ONLY.
DO NOT auto-merge into paper/. Inspect each hunk and Edit paper/ surgically.

  git -C "$CLONE_DIR" diff $BEFORE..$AFTER -- 'sections/*.tex'

Decide per hunk:
  Clean editorial improvement → sync to paper/
  Number change              → sync + re-run /paper-claim-audit
  New \\cite{...}             → sync + re-run /citation-audit
  Half-sentence / typo       → flag, do NOT auto-sync
EOF
}

cmd_sync_figures() {
  echo "=== Syncing paper/figures/ → paper-overleaf/figures/ ==="
  mkdir -p "$CLONE_DIR/figures"
  rsync -aL \
        --include='*/' \
        --include='*.pdf' --include='*.png' --include='*.svg' \
        --include='*.jpg' --include='*.jpeg' \
        --include='*.tex' --include='*.json' \
        --exclude='__pycache__' --exclude='.figures-prep' \
        --exclude='*' \
        "$PAPER_DIR/figures/" "$CLONE_DIR/figures/"

  cd "$CLONE_DIR"
  if [[ -z "$(git status --porcelain figures/)" ]]; then
    echo "  (no figure changes)"
    return 0
  fi
  echo
  git status --short figures/
  echo
  if ! confirm "Stage and commit (no push yet)?"; then
    echo "  Cancelled. Unstaged changes remain in $CLONE_DIR/figures/."
    return 0
  fi
  git add figures/
  MSG="${COMMIT_MSG:-overleaf-sync: refresh figures from local paper/}"
  git commit -m "$MSG"
  echo
  echo "✅ Committed. Run 'push' to publish, or 'git -C \"$CLONE_DIR\" push' directly."
}

cmd_push() {
  cd "$CLONE_DIR"

  echo "=== Step 1/4: pull --ff-only (surface remote drift) ==="
  PULL_OUT="$(git pull --ff-only 2>&1)" && PULL_RC=0 || PULL_RC=$?
  printf '%s\n' "$PULL_OUT"
  if [[ "$PULL_RC" -ne 0 ]]; then
    if printf '%s' "$PULL_OUT" | grep -qiE 'gnutls|handshake|could not resolve|connection (refused|timed out|reset)|failed to connect|unable to access|network'; then
      cat >&2 <<EOF
⚠️  Cannot push: network error reaching git.overleaf.com (not a divergence).
  Set the local proxy and retry:
    export {HTTP_PROXY,HTTPS_PROXY,ALL_PROXY,http_proxy,https_proxy,all_proxy}=http://127.0.0.1:7890
EOF
    else
      echo "⚠️  Cannot push: remote diverged. Run 'pull' first." >&2
    fi
    exit 1
  fi

  echo
  echo "=== Step 2/4: rsync paper/ → paper-overleaf/ ==="
  if [[ "${OVERLEAF_SYNC_DELETE:-0}" -eq 1 ]]; then
    echo "  [OVERLEAF_SYNC_DELETE=1] using rsync --delete"
    rsync -aL --delete "${EXCLUDES[@]}" "$PAPER_DIR/" "$CLONE_DIR/" | tail -30
  else
    rsync -aL "${EXCLUDES[@]}" "$PAPER_DIR/" "$CLONE_DIR/" | tail -30
  fi

  echo
  echo "=== Step 3/4: review ==="
  # Stage first so NEW (untracked) files appear in the stat — git diff on an
  # unstaged tree hides untracked files entirely, making review look empty.
  git add -A
  if git diff --cached --quiet; then
    echo "  (nothing to push)"
    return 0
  fi
  # --no-pager: never drop into `less` for the review (the 'q-to-quit' trap).
  git --no-pager diff --cached --stat
  echo
  if ! confirm "Commit and push to Overleaf?"; then
    echo
    echo "Cancelled. Changes are STAGED but not committed."
    echo "To unstage:  git -C \"$CLONE_DIR\" restore --staged ."
    return 1
  fi

  echo
  echo "=== Step 4/4: commit + push ==="
  MSG="${COMMIT_MSG:-${OVERLEAF_SYNC_COMMIT_MSG:-overleaf-sync: push local paper/ to Overleaf}}"
  git commit -m "$MSG"
  git push
  echo
  echo "✅ Pushed. $(git rev-parse --short HEAD) is now on Overleaf."
}

cmd_audit() {
  bash "$SCRIPT_DIR/overleaf_audit.sh" "$CLONE_DIR"
}

# ---------- 5. Dispatch -------------------------------------------------
case "$SUBCMD" in
  status)        cmd_status ;;
  pull)          cmd_pull ;;
  push)          cmd_push ;;
  sync-figures)  cmd_sync_figures ;;
  audit)         cmd_audit ;;
  *)
    echo "Unknown subcommand: '$SUBCMD'" >&2
    echo
    usage
    exit 2
    ;;
esac

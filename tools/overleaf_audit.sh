#!/usr/bin/env bash
# overleaf_audit.sh — scan a paper-overleaf clone for accidentally-committed
# Overleaf tokens, leaked URLs, or stray credential files.
#
# Exit codes:
#   0 — Audit clean
#   1 — Finding(s) require attention
#   2 — Bad invocation / not a git repo
#
# Usage: bash tools/overleaf_audit.sh <path-to-paper-overleaf>

set -euo pipefail

DIR="${1:-paper-overleaf}"
if [[ ! -d "$DIR/.git" ]]; then
  echo "ERROR: '$DIR' is not a git repository." >&2
  exit 2
fi

cd "$DIR"

PATTERN='olp_[A-Za-z0-9_-]{20,}'
FINDINGS=0

note() { printf '  ⚠️  %s\n' "$1"; FINDINGS=$((FINDINGS + 1)); }
ok()   { printf '  ✅ %s\n' "$1"; }

echo "Auditing $(pwd) ..."

# 1. Working tree -------------------------------------------------------
if grep -r -E "$PATTERN" --binary-files=without-match \
      --exclude-dir=.git . >/dev/null 2>&1; then
  note "Working tree contains an Overleaf-token-shaped string. Inspect:"
  grep -r -n -E "$PATTERN" --binary-files=without-match \
       --exclude-dir=.git . | head -10 || true
else
  ok "Working tree clean of olp_ tokens."
fi

# 2. Remote URL ---------------------------------------------------------
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo '')"
if [[ "$REMOTE_URL" == *"olp_"* ]]; then
  note "origin URL contains an Overleaf token."
elif [[ "$REMOTE_URL" == *"@git.overleaf.com"* ]]; then
  note "origin URL contains credential material (user@host form)."
else
  ok "origin URL is token-free: $REMOTE_URL"
fi

# 3. Git history --------------------------------------------------------
if git log --all -p -G"$PATTERN" 2>/dev/null \
   | grep -E "$PATTERN" >/dev/null 2>&1; then
  note "Git history contains an olp_ token. Rotate the token in Overleaf and rewrite history with git-filter-repo before pushing."
else
  ok "Git history clean of olp_ tokens."
fi

# 4. Plaintext credential files ----------------------------------------
LEAK=0
for f in "$HOME/.netrc" "$HOME/.git-credentials" \
         "$HOME/.config/git/credentials"; do
  if [[ -f "$f" ]] && grep -q "git.overleaf.com" "$f" 2>/dev/null \
                  && grep -q "olp_" "$f" 2>/dev/null; then
    note "$f stores the Overleaf token in plaintext."
    LEAK=1
  fi
done
[[ $LEAK -eq 0 ]] && ok "No plaintext credential files found."

# 5. Pre-commit hook ---------------------------------------------------
if [[ -x .git/hooks/pre-commit ]] && grep -q "olp_" .git/hooks/pre-commit 2>/dev/null; then
  ok "Pre-commit hook installed and screens for olp_ tokens."
else
  note "Pre-commit hook missing or does not screen for tokens. Re-run overleaf_setup.sh."
fi

echo
if [[ $FINDINGS -eq 0 ]]; then
  echo "✅ Audit clean"
  exit 0
else
  echo "⚠️  Audit found $FINDINGS finding(s) — see above."
  exit 1
fi

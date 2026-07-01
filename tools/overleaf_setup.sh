#!/usr/bin/env bash
# overleaf_setup.sh — one-time bridge between a local paper directory and an
# Overleaf project via the Overleaf Git bridge (Premium feature).
#
# SECURITY MODEL:
#   - Refuses to run unless stdin/stdout are a TTY (agents have no TTY).
#   - Reads the token via stty -echo (hidden, no shell history, no chat).
#   - Pipes the token directly into `git credential approve`; the OS keychain
#     stores it from then on.
#   - Strips any credential material from the remote URL after clone.
#   - Installs a pre-commit hook that refuses to commit blobs matching the
#     token pattern olp_[A-Za-z0-9_-]{20,}.
#   - Token is unset from shell memory before exit.
#
# Usage:
#   bash tools/overleaf_setup.sh <project-id-or-url> [clone-dir]
#
# Example:
#   bash tools/overleaf_setup.sh https://www.overleaf.com/project/64aa...e9 \
#       research/ideas/new/exploratory-trace-procedural-reasoning/paper-overleaf

set -euo pipefail

# --- 1. TTY guard --------------------------------------------------------
if [[ ! -t 0 || ! -t 1 ]]; then
  echo "ERROR: overleaf_setup.sh requires an interactive terminal." >&2
  echo "  Run this directly in your shell, not through an agent or pipe." >&2
  exit 2
fi

# --- 2. Arg parsing ------------------------------------------------------
if [[ $# -lt 1 ]]; then
  cat >&2 <<EOF
Usage: bash $0 <project-id-or-url> [clone-dir]

  project-id-or-url   Overleaf project ID (24-hex) or full URL
                      (https://www.overleaf.com/project/<id>)
  clone-dir           Optional target directory
                      (default: ./paper-overleaf)
EOF
  exit 2
fi

INPUT="$1"
CLONE_DIR="${2:-paper-overleaf}"

PROJECT_ID="$(printf '%s' "$INPUT" | sed -E 's#^https?://www\.overleaf\.com/project/##; s#/$##')"
if [[ ! "$PROJECT_ID" =~ ^[a-f0-9]{24}$ ]]; then
  echo "ERROR: '$INPUT' is not a valid Overleaf project ID or URL." >&2
  echo "  Expected a 24-character hex ID or" >&2
  echo "  https://www.overleaf.com/project/<24-hex>" >&2
  exit 2
fi

REMOTE_URL="https://git.overleaf.com/${PROJECT_ID}"

if [[ -e "$CLONE_DIR" && -n "$(ls -A "$CLONE_DIR" 2>/dev/null || true)" ]]; then
  echo "ERROR: '$CLONE_DIR' already exists and is non-empty." >&2
  echo "  Move it aside or pick a different clone-dir." >&2
  exit 2
fi

# --- 3. Credential helper selection -------------------------------------
PLATFORM="$(uname -s)"
HELPER=""
case "$PLATFORM" in
  Darwin)
    HELPER="osxkeychain"
    ;;
  Linux)
    if git credential-libsecret </dev/null >/dev/null 2>&1; then
      HELPER="libsecret"
    elif command -v secret-tool >/dev/null 2>&1; then
      cat <<NOTE
NOTE: secret-tool is installed but git-credential-libsecret is not.
      For best security, install it:
        sudo apt install libsecret-1-0 libsecret-1-dev
        sudo make -C /usr/share/doc/git/contrib/credential/libsecret
      Falling back to in-memory cache (8h timeout).
NOTE
      HELPER="cache --timeout=28800"
    else
      cat <<NOTE
NOTE: No system keychain detected. Falling back to in-memory cache (8h).
      Token will need to be re-pasted after 8h of idle.
NOTE
      HELPER="cache --timeout=28800"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    HELPER="manager"
    ;;
  *)
    echo "ERROR: Unsupported platform: $PLATFORM" >&2
    exit 2
    ;;
esac

# --- 4. Token prompt (hidden, never written to disk/chat) ----------------
cat <<EOF

═══════════════════════════════════════════════════════════════════════
 Overleaf Git Authentication Token
═══════════════════════════════════════════════════════════════════════
 Generate at:
   https://www.overleaf.com/user/settings  →  Git Integration  →
   "Create authentication token"

 The token starts with 'olp_'. It will be:
   - read into memory only (no echo, no shell history)
   - handed to git credential helper '${HELPER%% *}'
   - never stored in any file in this repo
   - unset from memory when this script exits
═══════════════════════════════════════════════════════════════════════

EOF

printf "Paste Overleaf Git token (input hidden): "
stty -echo 2>/dev/null || true
trap 'stty echo 2>/dev/null || true' EXIT
IFS= read -r TOKEN
stty echo 2>/dev/null || true
trap - EXIT
printf "\n"

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: empty token, aborting." >&2
  exit 2
fi
if [[ ! "$TOKEN" =~ ^olp_[A-Za-z0-9_-]{20,}$ ]]; then
  echo "ERROR: token does not match expected 'olp_...' format." >&2
  echo "  Length: ${#TOKEN} characters. Aborting without using token." >&2
  unset TOKEN
  exit 2
fi

# --- 5. Configure credential helper -------------------------------------
git config --global "credential.helper" "$HELPER"

{
  printf 'protocol=https\n'
  printf 'host=git.overleaf.com\n'
  printf 'username=git\n'
  printf 'password=%s\n' "$TOKEN"
  printf '\n'
} | git credential approve

# --- 6. Clone --------------------------------------------------------
echo
echo "Cloning Overleaf project into '$CLONE_DIR' ..."
if ! git clone "$REMOTE_URL" "$CLONE_DIR"; then
  echo "ERROR: clone failed. Common causes:" >&2
  echo "  - Project ID wrong, or this token cannot access this project" >&2
  echo "  - Token revoked / expired" >&2
  echo "  - Network blocked (try setting HTTPS_PROXY=http://127.0.0.1:7890)" >&2
  unset TOKEN
  exit 3
fi

# Verify remote URL contains no credential material.
cd "$CLONE_DIR"
CURRENT_URL="$(git remote get-url origin)"
if [[ "$CURRENT_URL" == *"olp_"* || "$CURRENT_URL" == *"@"* ]]; then
  git remote set-url origin "$REMOTE_URL"
  echo "INFO: stripped credentials from origin URL."
fi

# --- 7. Pre-commit hook (defense layer 4) -------------------------------
HOOK=".git/hooks/pre-commit"
cat > "$HOOK" <<'HOOK_EOF'
#!/usr/bin/env bash
# Installed by overleaf_setup.sh.
# Refuses to commit any blob containing an Overleaf access token.
# DO NOT REMOVE — last-line technical guard against publishing the token.

set -e
PATTERN='olp_[A-Za-z0-9_-]{20,}'

if git diff --cached -U0 | grep -E "$PATTERN" >/dev/null 2>&1; then
  echo "═══════════════════════════════════════════════════════════════════" >&2
  echo " pre-commit BLOCKED: staged content contains an Overleaf token." >&2
  echo "═══════════════════════════════════════════════════════════════════" >&2
  echo "" >&2
  echo "A blob matching '$PATTERN' was found in staged changes." >&2
  echo "Committing this would publish the token to the Overleaf project." >&2
  echo "" >&2
  echo "What to do:" >&2
  echo "  1. Revoke the token at https://www.overleaf.com/user/settings" >&2
  echo "  2. Unstage:  git reset HEAD <file>" >&2
  echo "  3. Remove the token from the file content" >&2
  echo "  4. Re-run overleaf_setup.sh to prime a fresh token" >&2
  exit 1
fi
HOOK_EOF
chmod +x "$HOOK"

cd - >/dev/null

# --- 8. Memory cleanup --------------------------------------------------
unset TOKEN

# --- 9. Summary ---------------------------------------------------------
cat <<EOF

═══════════════════════════════════════════════════════════════════════
 ✅ Setup complete
═══════════════════════════════════════════════════════════════════════
 Clone:       $CLONE_DIR
 Remote:      $REMOTE_URL  (no token in URL)
 Helper:      $HELPER
 Pre-commit:  $CLONE_DIR/.git/hooks/pre-commit

 Next:
   1. Tell the agent: "setup done"
   2. The agent will verify (token-free) and run an initial mirror of
      your local paper/ into paper-overleaf/.
═══════════════════════════════════════════════════════════════════════
EOF

#!/usr/bin/env bash
# build_paper.sh — recompile a local LaTeX paper into a PDF via latexmk.
#
# Usage:
#   bash tools/build_paper.sh [--paper <dir>] [--main <basename>] [--clean]
#                             [--clean-only] [--open] [-q|--quiet] [-h|--help]
#
# Paper directory resolution (highest precedence first):
#   1. --paper <dir>
#   2. env var  OVERLEAF_PAPER_DIR  (or PAPER_DIR)
#   3. PAPER_DIR=... in .overleaf-sync.conf, searched by walking up from the
#      current working directory to filesystem root; falls back to
#      $REPO_ROOT/.overleaf-sync.conf (repo root of this script) if no
#      per-project config is found.
#   4. ./paper — the "paper" folder under the current directory, if it exists
# If none of the above resolve to an existing directory, the script exits with
# a non-zero status and prints the resolution chain that was tried.

set -euo pipefail

# ---------- paths -------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Look for .overleaf-sync.conf by walking up from $PWD; fall back to the
# script's own repo root for backwards compatibility.
find_conf() {
  local dir="$PWD"
  while [[ "$dir" != "/" && -n "$dir" ]]; do
    if [[ -f "$dir/.overleaf-sync.conf" ]]; then
      printf '%s' "$dir/.overleaf-sync.conf"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  # Root as final step.
  if [[ -f "/.overleaf-sync.conf" ]]; then
    printf '%s' "/.overleaf-sync.conf"
    return 0
  fi
  # Fall back to the script's own repo root.
  if [[ -f "$REPO_ROOT/.overleaf-sync.conf" ]]; then
    printf '%s' "$REPO_ROOT/.overleaf-sync.conf"
    return 0
  fi
  return 1
}
CONF="$(find_conf || true)"

PAPER_DIR_CLI=""
PAPER_DIR_SRC=""   # diagnostics: "flag" | "env (OVERLEAF_PAPER_DIR)" | "env (PAPER_DIR)" | ".overleaf-sync.conf"

# Capture inherited env values BEFORE we touch our own PAPER_DIR var below.
PAPER_DIR_INHERITED="${PAPER_DIR:-}"
OVERLEAF_PAPER_DIR_INHERITED="${OVERLEAF_PAPER_DIR:-}"

MAIN="main"
DO_CLEAN=0        # --clean: scrub intermediates BEFORE the build
CLEAN_ONLY=0      # --clean-only: scrub and exit
KEEP_AUX=0        # --keep-aux: skip the default AFTER-build scrub
DO_OPEN=0
QUIET=0

# ---------- pretty output ----------------------------------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[1;31m'; C_GRN=$'\033[1;32m'; C_YEL=$'\033[1;33m'
  C_BLU=$'\033[1;34m'; C_DIM=$'\033[2m';    C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_DIM=""; C_RST=""
fi
say()  { printf '%s\n' "$*"; }
info() { printf '%s[build]%s %s\n' "$C_BLU" "$C_RST" "$*"; }
ok()   { printf '%s[ ok ]%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s[warn]%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s[fail]%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }

usage() {
  local conf_line
  if [[ -n "$CONF" ]]; then
    conf_line="currently resolving to: $CONF"
  else
    conf_line="currently: no config file located"
  fi
  cat <<EOF
build_paper.sh — recompile a local LaTeX paper into a PDF via latexmk.

Paper directory resolution (highest precedence first):
  1. --paper <dir>
  2. env  OVERLEAF_PAPER_DIR (or PAPER_DIR)
  3. PAPER_DIR=... in .overleaf-sync.conf, searched by walking up from \$PWD
     (falls back to ${REPO_ROOT}/.overleaf-sync.conf if no per-project file found)
     $conf_line
  4. ./paper (the "paper" folder under \$PWD), if it exists

If none resolve to an existing directory, the script exits non-zero.

Options:
  --paper <dir>     Override paper source directory
  --main <name>     Main TeX basename without .tex (default: main)
  --clean           Remove intermediate artifacts BEFORE building
  --clean-only      Clean intermediates and exit (no build)
  --keep-aux        Skip the default AFTER-build scrub (keep .aux/.log/.bbl/...)
  --open            Open the resulting PDF after a successful build
  -q, --quiet       Suppress latexmk stdout (errors still printed)
  -h, --help        Show this help

By default, after a successful build the script removes intermediate artifacts
(.aux .log .out .bbl .blg .fdb_latexmk .fls .synctex.gz ...) and keeps only
$MAIN.pdf in the paper directory. Pass --keep-aux to preserve them, e.g. when
debugging a LaTeX error against the .log file.

Examples:
  bash tools/build_paper.sh
  bash tools/build_paper.sh --clean
  bash tools/build_paper.sh --keep-aux
  bash tools/build_paper.sh --paper path/to/other_paper --main draft
EOF
}

# ---------- flag parsing -----------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --paper)      PAPER_DIR_CLI="$2"; shift 2 ;;
    --main)       MAIN="$2";          shift 2 ;;
    --clean)      DO_CLEAN=1;         shift ;;
    --clean-only) CLEAN_ONLY=1;       DO_CLEAN=1; shift ;;
    --keep-aux)   KEEP_AUX=1;         shift ;;
    --open)       DO_OPEN=1;          shift ;;
    -q|--quiet)   QUIET=1;            shift ;;
    -h|--help)    usage; exit 0 ;;
    *) err "Unknown flag: $1"; usage; exit 2 ;;
  esac
done

# ---------- resolve paper directory ------------------------------------
# 1. CLI flag wins.
# 2. Then env (OVERLEAF_PAPER_DIR or PAPER_DIR), captured before this block.
# 3. Then PAPER_DIR= entry in .overleaf-sync.conf.
# 4. Finally ./paper, but only if that directory actually exists — so an
#    unconfigured run in an unrelated cwd still aborts with a clear error.
PAPER_DIR=""

if [[ -n "$PAPER_DIR_CLI" ]]; then
  PAPER_DIR="$PAPER_DIR_CLI"
  PAPER_DIR_SRC="flag"
elif [[ -n "$OVERLEAF_PAPER_DIR_INHERITED" ]]; then
  PAPER_DIR="$OVERLEAF_PAPER_DIR_INHERITED"
  PAPER_DIR_SRC="env (OVERLEAF_PAPER_DIR)"
elif [[ -n "$PAPER_DIR_INHERITED" ]]; then
  PAPER_DIR="$PAPER_DIR_INHERITED"
  PAPER_DIR_SRC="env (PAPER_DIR)"
elif [[ -n "$CONF" && -f "$CONF" ]]; then
  # Source the conf in a subshell so its variables can't pollute ours,
  # then echo just PAPER_DIR back out.
  CONF_PAPER_DIR="$(
    # shellcheck disable=SC1090
    ( set +u; source "$CONF" >/dev/null 2>&1; printf '%s' "${PAPER_DIR:-}" )
  )"
  if [[ -n "$CONF_PAPER_DIR" ]]; then
    PAPER_DIR="$CONF_PAPER_DIR"
    PAPER_DIR_SRC=".overleaf-sync.conf ($CONF)"
  fi
fi

if [[ -z "$PAPER_DIR" && -d "$PWD/paper" ]]; then
  PAPER_DIR="$PWD/paper"
  PAPER_DIR_SRC="default (./paper)"
fi

if [[ -z "$PAPER_DIR" ]]; then
  err "Could not resolve a paper directory."
  say "" >&2
  say "Tried (in order):" >&2
  say "  1. --paper <dir>           : not provided" >&2
  say "  2. OVERLEAF_PAPER_DIR env  : empty" >&2
  say "  3. PAPER_DIR env           : empty" >&2
  if [[ -n "$CONF" && -f "$CONF" ]]; then
    say "  4. PAPER_DIR in $CONF" >&2
    say "                             : present but empty" >&2
  else
    say "  4. .overleaf-sync.conf (walking up from \$PWD, plus $REPO_ROOT)" >&2
    say "                             : not found" >&2
  fi
  say "  5. ./paper ($PWD/paper)" >&2
  say "                             : does not exist" >&2
  say "" >&2
  say "Set one of the above, e.g.:" >&2
  say "  bash tools/build_paper.sh --paper /path/to/paper" >&2
  say "  echo 'PAPER_DIR=\"/path/to/paper\"' >> \$PWD/.overleaf-sync.conf" >&2
  exit 1
fi

if [[ ! -d "$PAPER_DIR" ]]; then
  err "Paper directory not found: $PAPER_DIR  (source: $PAPER_DIR_SRC)"
  exit 1
fi
PAPER_DIR="$(cd "$PAPER_DIR" && pwd)"
info "Paper dir   : $PAPER_DIR  ${C_DIM}(source: $PAPER_DIR_SRC)${C_RST}"

TEX_FILE="$PAPER_DIR/$MAIN.tex"
if [[ ! -f "$TEX_FILE" ]]; then
  err "Main TeX file not found: $TEX_FILE"
  exit 1
fi

if ! command -v latexmk >/dev/null 2>&1; then
  err "latexmk not found in PATH. Install TeX Live (or add it to PATH) first."
  exit 1
fi

# ---------- clean helper ------------------------------------------------
# Scrub intermediate LaTeX artifacts from $PAPER_DIR, KEEPING $MAIN.pdf.
# Used both for the pre-build --clean step and the default post-build sweep.
scrub_intermediates() {
  local label="${1:-Cleaning}"
  info "${label} intermediates in $PAPER_DIR (keeping $MAIN.pdf)…"
  # latexmk -c removes most generated files but keeps the PDF (and .bbl).
  ( cd "$PAPER_DIR" && latexmk -c "$MAIN.tex" >/dev/null 2>&1 || true )
  # Drop the rest latexmk -c is intentionally conservative about, plus the
  # synctex(busy) temp file latexmk leaves when interrupted, plus biber side-files.
  for ext in bbl synctex.gz fdb_latexmk fls run.xml bcf; do
    rm -f -- "$PAPER_DIR/$MAIN.$ext"
  done
  rm -f -- "$PAPER_DIR/$MAIN.synctex(busy)"
  ok "Cleaned."
}

# ---------- pre-build clean --------------------------------------------
if [[ $DO_CLEAN -eq 1 ]]; then
  scrub_intermediates "Pre-build cleaning"
  [[ $CLEAN_ONLY -eq 1 ]] && exit 0
fi

# ---------- build -------------------------------------------------------
info "Building $TEX_FILE → $MAIN.pdf"
LOG_FILE="$PAPER_DIR/$MAIN.log"

LATEXMK_FLAGS=( -pdf -interaction=nonstopmode -halt-on-error -file-line-error )
BUILD_RC=0
if [[ $QUIET -eq 1 ]]; then
  ( cd "$PAPER_DIR" && latexmk "${LATEXMK_FLAGS[@]}" "$MAIN.tex" ) >/dev/null 2>&1 || BUILD_RC=$?
else
  ( cd "$PAPER_DIR" && latexmk "${LATEXMK_FLAGS[@]}" "$MAIN.tex" ) || BUILD_RC=$?
fi

if [[ $BUILD_RC -ne 0 ]]; then
  err "latexmk exited with status $BUILD_RC."
  if [[ -f "$LOG_FILE" ]]; then
    say ""
    say "${C_RED}── error summary from $MAIN.log ──${C_RST}"
    # Surface the lines that almost always pinpoint the cause.
    grep -nE \
      -e '^!' \
      -e '^l\.[0-9]+' \
      -e '! LaTeX Error' \
      -e '! Undefined control sequence' \
      -e '! Package .* Error' \
      -e 'Emergency stop' \
      -e 'Undefined reference' \
      -e 'Citation .* undefined' \
      -e 'Missing .* inserted' \
      "$LOG_FILE" | head -n 40 | while IFS= read -r line; do
        printf '%s%s%s\n' "$C_RED" "$line" "$C_RST"
      done
    say ""
    say "${C_DIM}Full log: $LOG_FILE${C_RST}"
  fi
  exit "$BUILD_RC"
fi

PDF_FILE="$PAPER_DIR/$MAIN.pdf"
if [[ ! -f "$PDF_FILE" ]]; then
  err "Build reported success but $PDF_FILE is missing."
  exit 1
fi

ok "Built $PDF_FILE"

# ---------- post-build sanity checks -----------------------------------
say ""
say "${C_BLU}── post-build checks ──${C_RST}"

# Page count via pdfinfo (fall back gracefully if missing).
if command -v pdfinfo >/dev/null 2>&1; then
  PAGES="$(pdfinfo "$PDF_FILE" 2>/dev/null | awk -F': *' '/^Pages/ {print $2; exit}')"
  if [[ -n "${PAGES:-}" ]]; then
    say "pages       : $PAGES"
  else
    warn "pdfinfo ran but did not report a page count."
  fi
else
  warn "pdfinfo not installed; skipping page count."
fi

# em-dash audit on main-body section files (NOT the appendix).
SECTIONS_DIR="$PAPER_DIR/sections"
if [[ -d "$SECTIONS_DIR" ]]; then
  # Main-body section files only — appendix is intentionally excluded.
  shopt -s nullglob
  body_files=( "$SECTIONS_DIR"/[0-9]_*.tex )
  shopt -u nullglob
  if [[ ${#body_files[@]} -gt 0 ]]; then
    em_total=0
    for f in "${body_files[@]}"; do
      n="$(grep -c -- '—' "$f" 2>/dev/null || true)"
      n="${n:-0}"
      em_total=$(( em_total + n ))
    done
    if [[ $em_total -eq 0 ]]; then
      say "em-dashes   : 0 in main-body section files"
    else
      say "em-dashes   : ${C_YEL}$em_total${C_RST} in main-body section files (check writing-principles cap)"
      for f in "${body_files[@]}"; do
        n="$(grep -c -- '—' "$f" 2>/dev/null || true)"
        [[ "${n:-0}" -gt 0 ]] && printf '              %s : %s\n' "${f#$PAPER_DIR/}" "$n"
      done
    fi
  fi
fi

# ---------- post-build scrub (default ON; opt out with --keep-aux) ------
if [[ $KEEP_AUX -eq 0 ]]; then
  say ""
  scrub_intermediates "Post-build cleaning"
else
  say ""
  info "Keeping intermediate artifacts (--keep-aux)."
fi

# ---------- optional open ----------------------------------------------
if [[ $DO_OPEN -eq 1 ]]; then
  if command -v xdg-open >/dev/null 2>&1; then
    ( xdg-open "$PDF_FILE" >/dev/null 2>&1 & )
    info "Opened $PDF_FILE via xdg-open."
  elif command -v open >/dev/null 2>&1; then
    ( open "$PDF_FILE" >/dev/null 2>&1 & )
    info "Opened $PDF_FILE."
  else
    warn "No xdg-open / open found; cannot launch viewer."
  fi
fi

ok "Done."

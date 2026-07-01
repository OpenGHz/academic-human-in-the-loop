#!/usr/bin/env bash
# pack_arxiv.sh — build a flattened, symlink-free arXiv submission tarball from
# a local LaTeX paper, with a clean-room compile to prove it stands alone.
#
# Usage:
#   bash tools/pack_arxiv.sh [--paper <dir>] [--main <basename>]
#                            [--out <file>] [--targz] [--no-verify]
#                            [--keep-staging] [-q|--quiet] [-h|--help]
#
# Why this exists: arXiv rejects TeX-produced PDFs and re-compiles your source
# on its own machines. A submission therefore must (a) carry every custom .sty
# / .bst / figure / .bbl it needs, (b) contain NO symlinks (arXiv ignores the
# target), and (c) ship only pdfLaTeX-compatible figures. This script discovers
# the real dependency set from the recorder file ($MAIN.fls) that LaTeX itself
# writes — i.e. exactly the files it opened — rather than grepping \input /
# \includegraphics by hand, then dereferences symlinks into a clean staging dir
# and tars it.
#
# Paper directory resolution (highest precedence first):
#   1. --paper <dir>
#   2. env  OVERLEAF_PAPER_DIR  (or PAPER_DIR)
#   3. PAPER_DIR=... in $REPO_ROOT/.overleaf-sync.conf

set -euo pipefail

# ---------- paths -------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONF="$REPO_ROOT/.overleaf-sync.conf"

PAPER_DIR_CLI=""
PAPER_DIR_SRC=""

# Capture inherited env BEFORE we touch our own PAPER_DIR var below.
PAPER_DIR_INHERITED="${PAPER_DIR:-}"
OVERLEAF_PAPER_DIR_INHERITED="${OVERLEAF_PAPER_DIR:-}"

MAIN="main"
OUT_CLI=""
FORMAT="zip"      # default; switch with --targz
DO_VERIFY=1
KEEP_STAGING=0
QUIET=0

# ---------- pretty output ----------------------------------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[1;31m'; C_GRN=$'\033[1;32m'; C_YEL=$'\033[1;33m'
  C_BLU=$'\033[1;34m'; C_DIM=$'\033[2m';    C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_DIM=""; C_RST=""
fi
say()  { printf '%s\n' "$*"; }
info() { printf '%s[pack]%s %s\n' "$C_BLU" "$C_RST" "$*"; }
ok()   { printf '%s[ ok ]%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s[warn]%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s[fail]%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }

usage() {
  cat <<EOF
pack_arxiv.sh — build a flattened, symlink-free arXiv submission tarball.

Paper directory resolution (highest precedence first):
  1. --paper <dir>
  2. env  OVERLEAF_PAPER_DIR (or PAPER_DIR)
  3. PAPER_DIR=... in $CONF

Options:
  --paper <dir>     Override paper source directory
  --main <name>     Main TeX basename without .tex (default: main)
  --out <file>      Output archive path
                    (default: <paper>/arxiv_<main>.<zip|tar.gz>)
  --targz           Produce a .tar.gz instead of the default .zip
  --zip             Produce a .zip (the default; kept for explicitness)
  --no-verify       Skip the clean-room recompile of the staged package
  --keep-staging    Keep the temporary staging directory (for inspection)
  -q, --quiet       Suppress build stdout (errors still printed)
  -h, --help        Show this help

What it does:
  1. Builds the paper once (latexmk) to refresh $MAIN.fls and $MAIN.bbl.
  2. Reads $MAIN.fls to collect every local file LaTeX actually opened
     (.tex .sty .bbl figures …), dropping system TeX files and rebuildable
     intermediates (.aux .log .out .fls …; .bbl is kept).
  3. Adds bibliography side-files bibtex needs but .fls never lists:
     the .bib from \\bibliography{...} and the .bst from $MAIN.blg.
  4. Copies all of it into a clean staging dir, DEREFERENCING symlinks
     (arXiv ignores symlinks) and preserving the directory layout.
  5. Unless --no-verify, recompiles the staged copy in isolation
     (pdflatex → bibtex → pdflatex × 2) and fails if it does not build.
  6. Archives the staging dir to the output file.

Examples:
  bash tools/pack_arxiv.sh
  bash tools/pack_arxiv.sh --paper path/to/paper --main draft --targz
  bash tools/pack_arxiv.sh --out /tmp/submission.tar.gz
EOF
}

# ---------- flag parsing -----------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --paper)        PAPER_DIR_CLI="$2"; shift 2 ;;
    --main)         MAIN="$2";          shift 2 ;;
    --out)          OUT_CLI="$2";       shift 2 ;;
    --zip)          FORMAT="zip";       shift ;;
    --targz|--tar)  FORMAT="tar.gz";    shift ;;
    --no-verify)    DO_VERIFY=0;        shift ;;
    --keep-staging) KEEP_STAGING=1;     shift ;;
    -q|--quiet)     QUIET=1;            shift ;;
    -h|--help)      usage; exit 0 ;;
    *) err "Unknown flag: $1"; usage; exit 2 ;;
  esac
done

# ---------- resolve paper directory ------------------------------------
PAPER_DIR=""
if [[ -n "$PAPER_DIR_CLI" ]]; then
  PAPER_DIR="$PAPER_DIR_CLI";                       PAPER_DIR_SRC="flag"
elif [[ -n "$OVERLEAF_PAPER_DIR_INHERITED" ]]; then
  PAPER_DIR="$OVERLEAF_PAPER_DIR_INHERITED";        PAPER_DIR_SRC="env (OVERLEAF_PAPER_DIR)"
elif [[ -n "$PAPER_DIR_INHERITED" ]]; then
  PAPER_DIR="$PAPER_DIR_INHERITED";                 PAPER_DIR_SRC="env (PAPER_DIR)"
elif [[ -f "$CONF" ]]; then
  CONF_PAPER_DIR="$(
    # shellcheck disable=SC1090
    ( set +u; source "$CONF" >/dev/null 2>&1; printf '%s' "${PAPER_DIR:-}" )
  )"
  if [[ -n "$CONF_PAPER_DIR" ]]; then
    PAPER_DIR="$CONF_PAPER_DIR";                    PAPER_DIR_SRC=".overleaf-sync.conf"
  fi
fi

if [[ -z "$PAPER_DIR" ]]; then
  err "Could not resolve a paper directory."
  say "" >&2
  say "Tried: --paper, OVERLEAF_PAPER_DIR, PAPER_DIR, PAPER_DIR in $CONF" >&2
  say "e.g.:  bash tools/pack_arxiv.sh --paper /path/to/paper" >&2
  exit 1
fi
if [[ ! -d "$PAPER_DIR" ]]; then
  err "Paper directory not found: $PAPER_DIR  (source: $PAPER_DIR_SRC)"
  exit 1
fi
PAPER_DIR="$(cd "$PAPER_DIR" && pwd -P)"   # -P: resolve to the real path
info "Paper dir   : $PAPER_DIR  ${C_DIM}(source: $PAPER_DIR_SRC)${C_RST}"

TEX_FILE="$PAPER_DIR/$MAIN.tex"
[[ -f "$TEX_FILE" ]] || { err "Main TeX file not found: $TEX_FILE"; exit 1; }

for bin in latexmk pdflatex bibtex; do
  command -v "$bin" >/dev/null 2>&1 || { err "$bin not found in PATH. Install TeX Live first."; exit 1; }
done

# ---------- 1. build once to refresh .fls and .bbl ---------------------
info "Building $MAIN.tex to refresh recorder (.fls) and bibliography (.bbl)…"
BUILD_RC=0
if [[ $QUIET -eq 1 ]]; then
  ( cd "$PAPER_DIR" && latexmk -pdf -recorder -interaction=nonstopmode -halt-on-error "$MAIN.tex" ) >/dev/null 2>&1 || BUILD_RC=$?
else
  ( cd "$PAPER_DIR" && latexmk -pdf -recorder -interaction=nonstopmode -halt-on-error "$MAIN.tex" ) || BUILD_RC=$?
fi
[[ $BUILD_RC -eq 0 ]] || { err "Source paper failed to build (latexmk rc=$BUILD_RC). Fix it before packaging."; exit "$BUILD_RC"; }

FLS="$PAPER_DIR/$MAIN.fls"
[[ -f "$FLS" ]] || { err "No $MAIN.fls produced; cannot discover dependencies."; exit 1; }
ok "Source builds; recorder file present."

# ---------- 2. collect dependencies from the recorder file -------------
# .fls lists every file LaTeX opened as 'INPUT <path>'. We keep local files
# only and drop rebuildable intermediates. Extensions we never ship (the .bbl
# is deliberately NOT in this list — arXiv reuses it):
DROP_EXT_RE='\.(aux|log|out|fls|fdb_latexmk|blg|synctex\.gz|run\.xml|bcf|toc|lof|lot|nav|snm|vrb|spl|brf|idx|ind|ilg|pdf)$'
# Note: the MAIN .pdf is recorded as OUTPUT (not INPUT) so it never enters the
# list; figure PDFs are INPUT and must survive — so .pdf is dropped ONLY for the
# main output, handled by the OUTPUT/INPUT split, while the regex above would
# also strip figure PDFs. Guard that below by exempting INPUT .pdf figures.

declare -A SEEN=()
FILES=()
add_file() {
  local rel="$1"
  [[ -n "$rel" && -z "${SEEN[$rel]:-}" ]] || return 0
  SEEN[$rel]=1
  FILES+=("$rel")
}

while IFS= read -r line; do
  [[ "$line" == INPUT\ * ]] || continue
  path="${line#INPUT }"
  path="${path#./}"
  # Absolute paths: keep only those inside the paper dir (e.g. the main .tex),
  # relativized; everything else (/usr, /texlive, …) is a system file → skip.
  if [[ "$path" == /* ]]; then
    if [[ "$path" == "$PAPER_DIR"/* ]]; then
      path="${path#$PAPER_DIR/}"
    else
      continue
    fi
  fi
  # Skip rebuildable intermediates, but never drop a figure PDF (INPUT .pdf
  # that is not the main output).
  if [[ "$path" =~ $DROP_EXT_RE ]]; then
    if [[ "$path" == *.pdf && "$path" != "$MAIN.pdf" ]]; then
      :   # a figure PDF — keep it
    else
      continue
    fi
  fi
  [[ -e "$PAPER_DIR/$path" ]] || { warn "recorder lists missing file: $path (skipped)"; continue; }
  add_file "$path"
done < "$FLS"

# ---------- 3. add bibliography side-files (.bib/.bst) ------------------
# bibtex reads these, so they never appear in the LaTeX .fls.
if [[ -f "$PAPER_DIR/$MAIN.bbl" ]]; then add_file "$MAIN.bbl"; fi
# .bib targets from every \bibliography{a,b,...} across the staged .tex inputs.
while IFS= read -r bibarg; do
  IFS=',' read -ra parts <<< "$bibarg"
  for b in "${parts[@]}"; do
    b="${b// /}"; [[ -n "$b" ]] || continue
    [[ "$b" == *.bib ]] || b="$b.bib"
    [[ -f "$PAPER_DIR/$b" ]] && add_file "$b"
  done
done < <(grep -rhoE '\\bibliography\{[^}]*\}' "$PAPER_DIR" 2>/dev/null | sed -E 's/\\bibliography\{([^}]*)\}/\1/')
# .bst named in the build log (covers \bibliographystyle set inside a .sty too).
if [[ -f "$PAPER_DIR/$MAIN.blg" ]]; then
  bst="$(grep -aoE 'style file: .*\.bst' "$PAPER_DIR/$MAIN.blg" | head -1 | sed -E 's/.*style file: //')"
  [[ -n "${bst:-}" && -f "$PAPER_DIR/$bst" ]] && add_file "$bst"
fi

[[ ${#FILES[@]} -gt 0 ]] || { err "No files collected; aborting."; exit 1; }
info "Collected ${#FILES[@]} source files for the package."

# ---------- 4. stage into a clean, symlink-free directory ---------------
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/arxiv_${MAIN}.XXXXXX")"
cleanup() { [[ $KEEP_STAGING -eq 0 ]] && rm -rf "$STAGING"; }
trap cleanup EXIT

for rel in "${FILES[@]}"; do
  mkdir -p "$STAGING/$(dirname "$rel")"
  # -L dereferences symlinks so the real bytes land in the package.
  cp -L "$PAPER_DIR/$rel" "$STAGING/$rel"
done

# Hard guarantee: no symlinks survived into the package.
if find "$STAGING" -type l | grep -q .; then
  err "Symlinks remain in staging dir — arXiv would drop them:"; find "$STAGING" -type l >&2; exit 1
fi

# Figure-format sanity (pdfLaTeX wants pdf/png/jpg; .eps/.ps break it).
badfigs="$(find "$STAGING" -type f \( -iname '*.eps' -o -iname '*.ps' \) || true)"
if [[ -n "$badfigs" ]]; then
  warn "Found .eps/.ps figures — pdfLaTeX cannot embed these. Convert to PDF/PNG:"
  say "$badfigs" >&2
fi

# ---------- 5. clean-room verify ---------------------------------------
if [[ $DO_VERIFY -eq 1 ]]; then
  info "Verifying: clean-room recompile of the staged package…"
  V_RC=0
  (
    cd "$STAGING"
    pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >v1.log 2>&1
    bibtex "$MAIN"                                               >vb.log 2>&1 || true
    pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >v2.log 2>&1
    pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >v3.log 2>&1
  ) || V_RC=$?
  if [[ $V_RC -ne 0 || ! -f "$STAGING/$MAIN.pdf" ]]; then
    err "Staged package did NOT compile standalone (something is missing)."
    [[ -f "$STAGING/v3.log" ]] && grep -nE '^!|Undefined control|LaTeX Error|not found|Emergency' "$STAGING/v3.log" | head -20 >&2
    KEEP_STAGING=1; warn "Staging kept for inspection: $STAGING"
    exit 1
  fi
  pages="$(pdfinfo "$STAGING/$MAIN.pdf" 2>/dev/null | awk -F': *' '/^Pages/{print $2; exit}')"
  undef="$(grep -c 'Citation .* undefined\|LaTeX Warning: Reference .* undefined' "$STAGING/v3.log" 2>/dev/null || true)"
  ok "Clean-room build succeeded (${pages:-?} pages)."
  [[ "${undef:-0}" -gt 0 ]] && warn "$undef undefined citation/reference warning(s) in the staged build."
  # Strip the verify by-products so they don't ship.
  ( cd "$STAGING" && rm -f v1.log vb.log v2.log v3.log "$MAIN".{aux,log,out,blg,pdf} && find . -name '*.aux' -delete )
fi

# ---------- 6. archive --------------------------------------------------
if [[ -n "$OUT_CLI" ]]; then
  OUT="$OUT_CLI"
else
  if [[ "$FORMAT" == "zip" ]]; then OUT="$PAPER_DIR/arxiv_${MAIN}.zip"; else OUT="$PAPER_DIR/arxiv_${MAIN}.tar.gz"; fi
fi
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"

if [[ "$FORMAT" == "zip" ]]; then
  command -v zip >/dev/null 2>&1 || { err "zip not found; install it or drop --zip for tar.gz."; exit 1; }
  ( cd "$STAGING" && zip -qr "$OUT" . )
else
  tar czf "$OUT" -C "$STAGING" .
fi

ok "Wrote $(du -h "$OUT" | cut -f1)  →  $OUT"
say ""
say "${C_BLU}── package contents ──${C_RST}"
if [[ "$FORMAT" == "zip" ]]; then unzip -l "$OUT" | awk 'NR>3 && $4!="" {print "  "$4}' | grep -v '^\s*$' | sort; else tar tzf "$OUT" | sed 's#^\./##' | grep -v '^$' | sort | sed 's/^/  /'; fi
say ""
ok "Done. Upload this file to arXiv (delete any previously uploaded PDF first)."

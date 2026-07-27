#!/usr/bin/env bash
# flatten_pdf_fonts.sh — flatten a PDF's text to vector outlines so the file
# carries NO embedded fonts, eliminating Type 3 (bitmap) fonts that make
# IEEE PDF eXpress / arXiv reject a submission ("This document has a Type 3
# font on page N").
#
# Typical trigger: a draw.io / Inkscape / matplotlib figure exports a Type 3
# font that ends up embedded in the final paper PDF. Flatten the *figure* PDF
# (then recompile the paper) — the text becomes vector paths, so it stays
# crisp and scalable but no longer counts as a font.
#
# Usage:
#   bash tools/flatten_pdf_fonts.sh <file.pdf> [<file2.pdf> ...]  # flatten in place (+ .orig.pdf backup)
#   bash tools/flatten_pdf_fonts.sh -o out.pdf <in.pdf>           # write to a new file (single input)
#   bash tools/flatten_pdf_fonts.sh --check <file.pdf> ...        # audit only: report Type 3 fonts, no writes
#   bash tools/flatten_pdf_fonts.sh --no-backup <file.pdf>        # flatten in place, skip the backup
#
# Options:
#   --check          Report each PDF's Type 3 fonts and exit non-zero if any are
#                    found. Modifies nothing — use as a pre-submission gate.
#   -o, --output F   Write the result to F instead of editing in place.
#                    Valid only with a single input file.
#   --no-backup      When editing in place, do NOT keep a <name>.orig.pdf backup.
#   -q, --quiet      Print less.
#   -h, --help       Show this help.
#
# Exit codes:
#   0 — success (flatten completed, or --check found no Type 3 fonts)
#   1 — a Type 3 font survived flattening, or --check found Type 3 fonts,
#       or one or more files failed
#   2 — bad invocation or a missing dependency (ghostscript)
#
# Requires: ghostscript (gs).
# Optional: pdffonts (poppler-utils) for the before/after Type 3 audit; without
#           it the audit is skipped and --check cannot run.

set -euo pipefail

# ---------- pretty output ----------------------------------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[1;31m'; C_GRN=$'\033[1;32m'; C_YEL=$'\033[1;33m'
  C_BLU=$'\033[1;34m'; C_DIM=$'\033[2m';    C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_DIM=""; C_RST=""
fi
QUIET=0
info() { [[ $QUIET -eq 1 ]] || printf '%s[flatten]%s %s\n' "$C_BLU" "$C_RST" "$*"; }
ok()   { [[ $QUIET -eq 1 ]] || printf '%s[  ok  ]%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s[ warn ]%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s[ fail ]%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }

usage() { sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# ---------- argument parsing -------------------------------------------
CHECK=0
NO_BACKUP=0
OUTPUT=""
FILES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)          CHECK=1; shift ;;
    --no-backup)      NO_BACKUP=1; shift ;;
    -o|--output)      OUTPUT="${2:-}"; [[ -n "$OUTPUT" ]] || { err "-o/--output needs an argument"; exit 2; }; shift 2 ;;
    -q|--quiet)       QUIET=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    --)               shift; while [[ $# -gt 0 ]]; do FILES+=("$1"); shift; done ;;
    -*)               err "unknown option: $1"; usage >&2; exit 2 ;;
    *)                FILES+=("$1"); shift ;;
  esac
done

if [[ ${#FILES[@]} -eq 0 ]]; then
  err "no input PDF given."
  usage >&2
  exit 2
fi
if [[ -n "$OUTPUT" && ${#FILES[@]} -ne 1 ]]; then
  err "-o/--output is only valid with a single input file (got ${#FILES[@]})."
  exit 2
fi
if [[ -n "$OUTPUT" && $CHECK -eq 1 ]]; then
  err "-o/--output cannot be combined with --check."
  exit 2
fi

# ---------- dependency probe -------------------------------------------
HAVE_PDFFONTS=0
command -v pdffonts >/dev/null 2>&1 && HAVE_PDFFONTS=1

if [[ $CHECK -eq 0 ]] && ! command -v gs >/dev/null 2>&1; then
  err "ghostscript (gs) not found — install it, e.g. 'sudo apt install ghostscript'."
  exit 2
fi
if [[ $CHECK -eq 1 && $HAVE_PDFFONTS -eq 0 ]]; then
  err "--check needs pdffonts — install poppler-utils, e.g. 'sudo apt install poppler-utils'."
  exit 2
fi

# ---------- helpers -----------------------------------------------------
# Count Type 3 font rows reported by pdffonts (echoes 0 when none / unavailable).
count_type3() {
  [[ $HAVE_PDFFONTS -eq 1 ]] || { printf '0'; return; }
  local n
  n="$(pdffonts "$1" 2>/dev/null | grep -c 'Type 3' || true)"
  printf '%s' "${n:-0}"
}

# Print the offending Type 3 font rows (with the pdffonts header) for context.
show_type3() {
  [[ $HAVE_PDFFONTS -eq 1 ]] || return 0
  pdffonts "$1" 2>/dev/null | awk 'NR<=2 || /Type 3/'
}

# Flatten $in -> $out via Ghostscript, converting all text to outlines.
# CompatibilityLevel 1.4 matches the paper's \pdfminorversion=4 requirement.
flatten_one() {
  local in="$1" out="$2"
  local dir tmp
  dir="$(cd "$(dirname "$out")" && pwd)"
  tmp="$(mktemp "$dir/.flatten_pdf.XXXXXX")"
  # shellcheck disable=SC2064
  trap "rm -f '$tmp'" RETURN

  if ! gs -q -dNOPAUSE -dBATCH -dNoOutputFonts -sDEVICE=pdfwrite \
          -dCompatibilityLevel=1.4 -o "$tmp" "$in" 2>/tmp/flatten_pdf_gs.$$.log; then
    err "$in: ghostscript failed — see /tmp/flatten_pdf_gs.$$.log"
    return 1
  fi

  local after; after="$(count_type3 "$tmp")"
  if [[ "$after" != "0" ]]; then
    err "$in: $after Type 3 font(s) survived flattening — not overwriting."
    return 1
  fi

  mv -f "$tmp" "$out"
  return 0
}

# ---------- run ---------------------------------------------------------
STATUS=0

if [[ $CHECK -eq 1 ]]; then
  # -------- audit-only mode --------
  for f in "${FILES[@]}"; do
    if [[ ! -f "$f" ]]; then err "not found: $f"; STATUS=1; continue; fi
    n="$(count_type3 "$f")"
    if [[ "$n" != "0" ]]; then
      err "$f: $n Type 3 font(s) — will be rejected by IEEE PDF eXpress / arXiv."
      show_type3 "$f"
      STATUS=1
    else
      ok "$f: no Type 3 fonts."
    fi
  done
  [[ $STATUS -eq 0 ]] && info "All checked PDFs are Type 3-free."
  exit $STATUS
fi

# -------- flatten mode --------
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then err "not found: $f"; STATUS=1; continue; fi

  before="$(count_type3 "$f")"
  dest="${OUTPUT:-$f}"

  # Back up the original when editing in place (unless it's already been kept).
  if [[ -z "$OUTPUT" && $NO_BACKUP -eq 0 ]]; then
    backup="${f%.pdf}.orig.pdf"
    if [[ -e "$backup" ]]; then
      warn "$f: backup already exists, keeping it: $backup"
    else
      cp -p "$f" "$backup"
      info "$f: backup -> $backup"
    fi
  fi

  if flatten_one "$f" "$dest"; then
    if [[ $HAVE_PDFFONTS -eq 1 ]]; then
      ok "$f -> $dest  (Type 3: $before -> 0; all text outlined)"
    else
      ok "$f -> $dest  (text outlined; install pdffonts to verify)"
    fi
  else
    STATUS=1
  fi
done

exit $STATUS

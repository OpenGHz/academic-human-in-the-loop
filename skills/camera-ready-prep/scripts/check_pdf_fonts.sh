#!/usr/bin/env bash
# List fonts in one or more PDFs and flag Type 3 fonts, which IEEE / PaperCept
# submission systems reject. Exit status is 1 if any file contains Type 3 fonts,
# so it can gate a compile/upload step.
#
# Usage:
#   check_pdf_fonts.sh <main>.pdf                 # check the compiled paper
#   check_pdf_fonts.sh Images/*.pdf              # locate the offending figure
#
# Requires: pdffonts (poppler-utils).
set -uo pipefail

command -v pdffonts >/dev/null 2>&1 || {
  echo "ERROR: pdffonts not found (install poppler-utils)" >&2; exit 2; }
[ "$#" -ge 1 ] || {
  echo "usage: check_pdf_fonts.sh <file.pdf> [more.pdf ...]" >&2; exit 2; }

bad=0
for pdf in "$@"; do
  if [ ! -f "$pdf" ]; then
    echo "skip (not found): $pdf"; continue
  fi
  n=$(pdffonts "$pdf" 2>/dev/null | grep -c "Type 3")
  if [ "$n" -gt 0 ]; then
    echo "✗ $pdf — $n Type 3 font(s):"
    pdffonts "$pdf" 2>/dev/null | awk 'NR<=2 || /Type 3/'
    echo
    bad=1
  else
    echo "✓ $pdf — no Type 3"
  fi
done

exit $bad

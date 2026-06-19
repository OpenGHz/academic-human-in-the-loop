#!/usr/bin/env bash
# Outline all fonts in a PDF (render text as vector paths) using Ghostscript's
# -dNoOutputFonts. This removes Type 3 (and any non-embedded) font objects while
# keeping the figure fully vector — no rasterization, bounding box preserved.
# Ideal for matplotlib-exported figure PDFs that embed Type 3 fonts.
#
# Usage:
#   outline_fonts.sh <in.pdf>            # replace in place; backup -> <in>.orig.pdf
#   outline_fonts.sh <in.pdf> <out.pdf>  # write to out.pdf, leave in.pdf untouched
#
# Requires: gs (ghostscript); pdffonts (poppler-utils) for verification.
set -uo pipefail

command -v gs >/dev/null 2>&1 || { echo "ERROR: ghostscript (gs) not found" >&2; exit 2; }
in="${1:-}"
[ -n "$in" ] || { echo "usage: outline_fonts.sh <in.pdf> [out.pdf]" >&2; exit 2; }
[ -f "$in" ] || { echo "ERROR: not found: $in" >&2; exit 2; }
out="${2:-}"

tmp="$(dirname "$in")/.outline_tmp_$$.pdf"
gs -q -dNOPAUSE -dBATCH -dNoOutputFonts -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.4 -o "$tmp" "$in"

# Verify no fonts remain (font table should be empty -> nothing past the header).
if command -v pdffonts >/dev/null 2>&1; then
  if pdffonts "$tmp" 2>/dev/null | awk 'NR>2 && NF {found=1} END{exit !found}'; then
    echo "WARNING: fonts still present after outlining:" >&2
    pdffonts "$tmp" >&2
  fi
fi

if [ -n "$out" ]; then
  mv "$tmp" "$out"
  echo "wrote $out (source $in unchanged)"
else
  cp "$in" "${in%.pdf}.orig.pdf"
  mv "$tmp" "$in"
  echo "replaced $in  (backup: ${in%.pdf}.orig.pdf)"
fi

#!/usr/bin/env bash
# render_slides_video.sh — regenerate the narrated slides MP4 after editing
# TALK_SCRIPT.md (or, with --rebuild-pdf, main.tex). Thin wrapper around the
# /paper-slides-render helper (paper_slides_render.py `render` + `verify`).
#
# Usage:
#   bash tools/render_slides_video.sh [options]
#
# Slides directory resolution (highest precedence first):
#   1. --slides <dir>                         (used as-is)
#   2. --paper <dir>                          -> <dir>/slides
#   3. env OVERLEAF_PAPER_DIR or PAPER_DIR    -> <env>/slides
#   4. PAPER_DIR=... in <repo>/.overleaf-sync.conf -> <conf>/slides
# The slides dir must contain main.pdf and TALK_SCRIPT.md.
#
# Options:
#   --paper <dir>        Paper dir; slides taken as <dir>/slides
#   --slides <dir>       Slides dir directly (overrides --paper)
#   --max-seconds N      Duration cap; halts BEFORE compose if projected over (default: 180)
#   --no-cap             Disable the duration cap
#   --rate <+N%|-N%>     edge-tts speed delta, e.g. +2% (keeps wording, helps fit the cap)
#   --allow-over-cap     Render even if projected total exceeds --max-seconds
#   --with-subtitles     Burn subtitles (default source: script)
#   --subtitle-source <s>  script (default; exact narration text, no whisper) | whisper (ASR)
#   --voice <name>       edge-tts voice (default: en-US-AvaNeural)
#   --resolution <WxH>   Output resolution (default: 1920x1080)
#   --fps <N>            Output fps (default: 30)
#   --rebuild-pdf        Recompile main.pdf via latexmk first (use when you edited main.tex)
#   --no-verify          Skip the post-render verify gate
#   --no-proxy-retry     Do not retry TTS through the local proxy on a network failure
#   -h, --help           Show this help
#
# Exit codes: 0 ok · 2 bad invocation / inputs missing · 3 latexmk/ffmpeg failed
#             4 projected duration over --max-seconds (nothing composed)
#
# Only the slides whose narration text changed are re-synthesized (content-hash
# cached); the rest reuse cached audio + rasterized PNGs.

set -euo pipefail

PROXY="http://127.0.0.1:7890"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONF="$REPO_ROOT/.overleaf-sync.conf"

# Capture any env override before we touch these names.
ENV_PAPER="${OVERLEAF_PAPER_DIR:-${PAPER_DIR:-}}"

# Defaults.
PAPER_FLAG=""
SLIDES_DIR=""
MAX_SECONDS="180"
RATE=""
ALLOW_OVER=0
SUBTITLES=0
SUBTITLE_SOURCE="script"   # script = exact narration text timed from audio (no whisper); or "whisper"
VOICE="en-US-AvaNeural"
RESOLUTION="1920x1080"
FPS="30"
REBUILD_PDF=0
DO_VERIFY=1
PROXY_RETRY=1

usage() { sed -n '2,42p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --paper)          PAPER_FLAG="${2:?--paper needs a dir}"; shift 2;;
    --slides)         SLIDES_DIR="${2:?--slides needs a dir}"; shift 2;;
    --max-seconds)    MAX_SECONDS="${2:?--max-seconds needs a number}"; shift 2;;
    --no-cap)         MAX_SECONDS=""; shift;;
    --rate)           RATE="${2:?--rate needs e.g. +2%}"; shift 2;;
    --allow-over-cap) ALLOW_OVER=1; shift;;
    --with-subtitles) SUBTITLES=1; shift;;
    --subtitle-source) SUBTITLE_SOURCE="${2:?--subtitle-source needs whisper|script}"; SUBTITLES=1; shift 2;;
    --voice)          VOICE="${2:?--voice needs a name}"; shift 2;;
    --resolution)     RESOLUTION="${2:?--resolution needs WxH}"; shift 2;;
    --fps)            FPS="${2:?--fps needs a number}"; shift 2;;
    --rebuild-pdf)    REBUILD_PDF=1; shift;;
    --no-verify)      DO_VERIFY=0; shift;;
    --no-proxy-retry) PROXY_RETRY=0; shift;;
    -h|--help)        usage; exit 0;;
    *) echo "ERROR: unknown argument: $1" >&2; echo "Run with --help." >&2; exit 2;;
  esac
done

# ---- Resolve slides dir -------------------------------------------------------
read_conf_paper() {
  [ -f "$CONF" ] || return 1
  ( set +u +e; PAPER_DIR=""; . "$CONF" >/dev/null 2>&1; printf '%s' "$PAPER_DIR" )
}

if [ -z "$SLIDES_DIR" ]; then
  paper="$PAPER_FLAG"
  [ -z "$paper" ] && paper="$ENV_PAPER"
  [ -z "$paper" ] && paper="$(read_conf_paper || true)"
  if [ -z "$paper" ]; then
    echo "ERROR: could not resolve a paper dir." >&2
    echo "       Tried: --paper / --slides, \$OVERLEAF_PAPER_DIR or \$PAPER_DIR, PAPER_DIR= in $CONF" >&2
    exit 2
  fi
  SLIDES_DIR="$paper/slides"
fi
SLIDES_DIR="${SLIDES_DIR%/}"

# ---- Resolve the render helper (mirrors SKILL §2 resolver) --------------------
HELPER=""
if [ -n "${CLAUDE_SKILL_DIR:-}" ] && [ -f "$CLAUDE_SKILL_DIR/scripts/paper_slides_render.py" ]; then
  HELPER="$CLAUDE_SKILL_DIR/scripts/paper_slides_render.py"
fi
if [ -z "$HELPER" ]; then
  for cand in \
    "$REPO_ROOT/.claude/skills/paper-slides-render/scripts/paper_slides_render.py" \
    "$REPO_ROOT/.aris/tools/paper_slides_render.py" \
    "$REPO_ROOT/tools/paper_slides_render.py"; do
    [ -f "$cand" ] && HELPER="$cand" && break
  done
fi
[ -n "$HELPER" ] && [ -f "$HELPER" ] || { echo "ERROR: paper_slides_render.py not found." >&2; exit 2; }

# ---- Optional: rebuild main.pdf (only needed if main.tex changed) -------------
if [ "$REBUILD_PDF" = 1 ]; then
  command -v latexmk >/dev/null 2>&1 || { echo "ERROR: latexmk not on PATH." >&2; exit 3; }
  echo "→ rebuilding main.pdf via latexmk …"
  latexmk -cd -pdf -interaction=nonstopmode -halt-on-error "$SLIDES_DIR/main.tex" >/dev/null 2>&1 \
    || { echo "ERROR: latexmk failed (see $SLIDES_DIR/main.log)." >&2; exit 3; }
fi

# ---- Preflight inputs ---------------------------------------------------------
[ -f "$SLIDES_DIR/main.pdf" ]       || { echo "ERROR: $SLIDES_DIR/main.pdf not found (try --rebuild-pdf or --paper)." >&2; exit 2; }
[ -f "$SLIDES_DIR/TALK_SCRIPT.md" ] || { echo "ERROR: $SLIDES_DIR/TALK_SCRIPT.md not found." >&2; exit 2; }
mkdir -p "$SLIDES_DIR/render"
RENDER_JSON="$SLIDES_DIR/render/render.json"
VERIFY_JSON="$SLIDES_DIR/render/verify.json"
OUT_MP4="$SLIDES_DIR/render/presentation.mp4"

echo "→ slides:  $SLIDES_DIR"
echo "→ helper:  $HELPER"
echo "→ cap:     ${MAX_SECONDS:-(none)}${RATE:+   rate: $RATE}"

# ---- Build + run the render ---------------------------------------------------
args=( render
  --slides-pdf  "$SLIDES_DIR/main.pdf"
  --talk-script "$SLIDES_DIR/TALK_SCRIPT.md"
  --output      "$OUT_MP4"
  --workspace   "$SLIDES_DIR"
  --voice       "$VOICE"
  --resolution  "$RESOLUTION"
  --fps         "$FPS"
  --json-out    "$RENDER_JSON" )
[ -n "$MAX_SECONDS" ] && args+=( --max-seconds "$MAX_SECONDS" )
[ -n "$RATE" ]        && args+=( --rate "$RATE" )
[ "$ALLOW_OVER" = 1 ] && args+=( --allow-over-cap )
[ "$SUBTITLES" = 1 ]  && args+=( --with-subtitles --subtitle-source "$SUBTITLE_SOURCE" )

# Silence the helper's own stdout/stderr; this script formats all output itself
# and reads details back from $RENDER_JSON (written via --json-out) on failure.
do_render() { set +e; python3 "$HELPER" "${args[@]}" >/dev/null 2>&1; local r=$?; set -e; return $r; }

echo "→ rendering (only changed slides re-synthesize) …"
do_render && rc=0 || rc=$?

# Exit 1 is often a transient network drop during TTS; retry once via the proxy.
if [ "$rc" = 1 ] && [ "$PROXY_RETRY" = 1 ] && [ -z "${ALL_PROXY:-}" ]; then
  echo "→ render exit 1; retrying TTS through local proxy ($PROXY) …" >&2
  export HTTP_PROXY="$PROXY" HTTPS_PROXY="$PROXY" ALL_PROXY="$PROXY" \
         http_proxy="$PROXY" https_proxy="$PROXY" all_proxy="$PROXY"
  do_render && rc=0 || rc=$?
fi

# ---- Handle outcome -----------------------------------------------------------
if [ "$rc" = 4 ]; then
  python3 - "$RENDER_JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"\n⛔ Over duration cap: projected {d.get('projected_seconds')}s "
      f"> cap {d.get('cap_seconds')}s (over by {d.get('over_by_seconds')}s). Nothing was composed.")
print("   Fix with one of:")
print("     • shorten the longest slide's narration, then re-run")
print("     • re-run with  --rate +2%        (keeps wording, speeds narration)")
print("     • re-run with  --allow-over-cap  (render at the over-cap length)")
PY
  exit 4
fi
if [ "$rc" != 0 ]; then
  echo "" >&2
  echo "ERROR: render failed (exit $rc). Details:" >&2
  python3 -c "import json;d=json.load(open('$RENDER_JSON'));print('  '+str(d.get('error') or d.get('tts_errors') or d))" 2>/dev/null || true
  exit "$rc"
fi

TOTAL=$(python3 -c "import json;print(json.load(open('$RENDER_JSON'))['totals']['actual_seconds'])" 2>/dev/null || echo '?')
SIZE=$(python3 -c "import json;print(json.load(open('$RENDER_JSON'))['totals']['size_mb'])" 2>/dev/null || echo '?')
echo "✅ rendered: $OUT_MP4  (${TOTAL}s, ${SIZE} MB)"

# ---- Verify -------------------------------------------------------------------
if [ "$DO_VERIFY" = 1 ]; then
  set +e
  python3 "$HELPER" verify --video "$OUT_MP4" --talk-script "$SLIDES_DIR/TALK_SCRIPT.md" --json-out "$VERIFY_JSON" >/dev/null 2>&1
  set -e
  VOK=$(python3 -c "import json;print(json.load(open('$VERIFY_JSON'))['ok'])" 2>/dev/null || echo False)
  if [ "$VOK" = "True" ]; then
    echo "✅ verify ok"
  else
    echo "⚠️  verify failed:" >&2
    python3 -c "import json;[print('   - '+str(v)) for v in json.load(open('$VERIFY_JSON')).get('violations',[])]" 2>/dev/null || true
    exit 2
  fi
fi

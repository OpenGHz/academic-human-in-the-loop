set -ex

# Restore git-ignored content (third_party/, .aris/, .vscode/, .claude/, global skills).
# Run from the project root, e.g. after cloning, to recreate the local-only setup.
ARIS_ROOT="$1"
if [ -z "$ARIS_ROOT" ]; then
  # If this script lives inside the AHIL repo itself (install_aris.sh sits next
  # to it), use that checkout directly instead of looking for / cloning one.
  SELF_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  if [ -f "$SELF_ROOT/tools/install_aris.sh" ]; then
    ARIS_ROOT="$SELF_ROOT"
  else
    ARIS_ROOT="$HOME/academic-human-in-the-loop"
    if [ ! -d "$ARIS_ROOT" ]; then
      read -r -p "No ARIS root provided. Clone academic-human-in-the-loop into $ARIS_ROOT? [y/N] " reply
      case "$reply" in
        [Yy]*)
          git clone https://github.com/OpenGHz/academic-human-in-the-loop.git "$ARIS_ROOT"
          ;;
        *)
          echo "Aborted. Pass the ARIS root dir as the first argument." >&2
          exit 1
          ;;
      esac
    fi
  fi
fi

mkdir -p third_party

bash "$ARIS_ROOT/tools/install_aris.sh"

mkdir -p .vscode
if [ ! -f .vscode/settings.json ]; then
  cat > .vscode/settings.json <<'EOF'
{
  "github.copilot.chat.commitMessageGeneration.instructions": [
    {
      "text": "Always generate git commit messages in English only. Keep them concise, in the imperative mood, and specific. Do not include Chinese or other non-English text."
    }
  ]
}
EOF
fi

mkdir -p .claude
if [ ! -f .claude/settings.json ]; then
  cat > .claude/settings.json <<'EOF'
{
  "extraKnownMarketplaces": {
    "rse-plugins": {
      "source": {
        "source": "github",
        "repo": "uw-ssec/rse-plugins"
      }
    }
  },
  "enabledPlugins": {
    "scientific-python-development@rse-plugins": true
  }
}
EOF
fi
# for non-claude users
npx skills add uw-ssec/rse-plugins/plugins/scientific-python-development/skills --all

npx skills add OpenGHz/cfgable@python-config-style -g -y -a universal

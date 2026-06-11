set -ex

# Reuse install_ahil.sh to restore git-ignored content (third_party/, .aris/,
# .vscode/, .claude/, global skills). It resolves/clones the ARIS root from "$1".
bash "$(dirname "$0")/install_ahil.sh" "$1"

cat > .gitignore <<'EOF'
third_party/
.aris/
.claude/
init_aris_project.sh
.vscode/
papers/
EOF

git init

git add . && git commit -m "Add .gitignore to exclude specific directories and files"

python3 .aris/tools/research_wiki.py init research-wiki/

git add . && git commit -m "Add research wiki"

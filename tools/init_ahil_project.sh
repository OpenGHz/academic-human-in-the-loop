set -ex

# Reuse install_ahil.sh to restore git-ignored content (third_party/, .aris/,
# .vscode/, .claude/, global skills). It resolves/clones the ARIS root from "$1".
bash "$(dirname "$0")/install_ahil.sh" "$1"

cat > .gitignore <<'EOF'
third_party/
.aris/
.claude/
.vscode/
paper/raw_data/
papers/
# LaTeX build intermediates (latexmk / pdflatex / bibtex)
*.aux
*.bbl
*.blg
*.fdb_latexmk
*.fls
*.log
*.out
*.synctex.gz
*.toc
*.lof
*.lot
*.nav
*.snm
*.vrb
*.bcf
*.run.xml
*.idx
*.ind
*.ilg
*.xdv
*.dvi
compile.log
# Middleman intermediates
*.json
*.txt
*.png
*.svg
*.bkp
EOF

git init

git add . && git commit -m "Add .gitignore to exclude specific directories and files"

python3 .aris/tools/research_wiki.py init research-wiki/

git add . && git commit -m "Add research wiki"

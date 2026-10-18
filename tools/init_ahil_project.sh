set -ex

# 只追加 .gitignore 里还没有的条目，不覆盖已有内容
touch .gitignore
# 已有文件末尾没有换行时先补一个，避免追加的第一行和原最后一行粘在一起
[ -n "$(tail -c1 .gitignore)" ] && echo >> .gitignore
while IFS= read -r line; do
  [ -z "$line" ] && continue
  grep -qxF -- "$line" .gitignore || echo "$line" >> .gitignore
done <<'EOF'
third_party/
.aris/
.claude/
.vscode/
paper/raw_data/
/papers/
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

# arxiv.org submission files
*.zip
EOF

python3 .aris/tools/research_wiki.py init research-wiki/

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
# LaTeX build intermediates (latexmk / pdflatex / bibtex); these extensions are LaTeX-only
*.aux
*.bbl
*.blg
*.fdb_latexmk
*.fls
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
*.bkp
# .log, .out, .json, .txt, .png and .svg are also experiment evidence (train.log, eval.log,
# readout JSON, text logs), so they are ignored only inside the paper directory.
/paper/**/*.log
/paper/**/*.out
/paper/**/*.json
/paper/**/*.txt
/paper/**/*.png
/paper/**/*.svg

# arxiv.org submission packages
/*.zip
/paper/**/*.zip

EOF

python3 .aris/tools/research_wiki.py init research-wiki/

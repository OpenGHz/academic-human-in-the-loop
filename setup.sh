set -ex

# setup codex reviewer
npm install -g @openai/codex
claude mcp add codex -s user -- codex mcp-server

# setup latex
sudo apt install texlive-full latexmk poppler-utils -y
latexmk --version && pdfinfo -v

# setup script for codex-image2 mcp server
mkdir -p ~/.claude/mcp-servers/codex-image2
cp mcp-servers/codex-image2/server.py ~/.claude/mcp-servers/codex-image2/server.py
chmod +x ~/.claude/mcp-servers/codex-image2/server.py

claude mcp add codex-image2 -s user -- python3 ~/.claude/mcp-servers/codex-image2/server.py

# setup target project
cd ~/your-paper-project
bash ~/path/to/your/aris_repo/tools/install_aris.sh

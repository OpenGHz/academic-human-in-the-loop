# `tools/` — shared-runtime helpers

Every executable in this directory is a **shared implementation** that one or more skills call.
This file is the map: what exists, what it does, and which skill owns the intent.

## Read this before writing a new script

The failure mode this index exists to prevent is an agent re-implementing something that already
lives here — a hand-rolled `latexmk` line, a `zip -r paper.zip paper/`, a bespoke `rsync --exclude`
chain. **Check this table first.** If a tool covers the intent, call it; if it *almost* covers the
intent, extend it rather than forking it.

Two rules that follow from that:

- **Never hardcode `python3 tools/foo.py` in a SKILL.md.** Resolve the path through the chain in
  [`../AGENT_GUIDE.md`](../AGENT_GUIDE.md) (§ Helper Resolution) — formally specified in
  [`../skills/shared-references/integration-contract.md`](../skills/shared-references/integration-contract.md) §2.
  Installed skills run from a symlink farm where `tools/` is not at a fixed relative path.
- **A tool nobody names is a tool nobody uses.** Agents discover helpers through SKILL.md bodies,
  not through this file — nothing loads `tools/README.md` into context automatically. When you add a
  script here, add the invocation to the SKILL.md that owns the intent *in the same change*, and add
  the row below. A tool with no owner in the "Owner skill" column is dead weight until wired up.

## Paper production

| Tool | Owner skill | What it does |
|------|-------------|--------------|
| `build_paper.sh` | `/paper-compile` | latexmk wrapper: paper-dir resolution, error-summary extraction from `.log`, page count + em-dash audit, post-build intermediate scrub (`--keep-aux` to keep `.log` for diagnosis). |
| `pack_arxiv.sh` | `/camera-ready-prep` §8, `/paper-compile` §7 | Builds a self-contained arXiv source archive. Reads `main.fls` to learn what LaTeX *actually* opened, adds `.bib`/`.bst`, dereferences symlinks (arXiv drops them), keeps the `.bbl`, then recompiles the staged copy in isolation to prove it stands alone. |
| `flatten_pdf_fonts.sh` | `/camera-ready-prep` §5 | Audits (`--check`) and removes Type 3 fonts by outlining text via Ghostscript. Refuses to overwrite if a Type 3 font survives. Sole implementation — the skill-local `check_pdf_fonts.sh` / `outline_fonts.sh` duplicates were deleted in favor of this. |
| `extract_paper_style.py` | `/paper-plan`, `/paper-write`, `/paper-writing` | Extracts a skeleton-only style profile from a reference paper (structure, not content). |
| `render_slides_video.sh` | `/paper-slides-render` | Re-renders the narrated slides MP4 after a `TALK_SCRIPT.md` edit; only changed slides re-synthesize. Enforces the same duration cap (exit 4) as the skill. |
| `paper_illustration_image2.py` | `/paper-illustration-image2` | Legacy entry point; forwards to the canonical helper. |

## Figures

| Tool | Owner skill | What it does |
|------|-------------|--------------|
| `figure_renderer.py` | `/figure-spec` | FigureSpec JSON → SVG (`render` / `validate` / `schema`). Legacy entry point forwarding to the canonical helper. |
| `svg_to_pdf.py` | `/figure-spec` §3, `/paper-figure` | SVG → tightly-cropped single-page PDF via headless Chromium. Use for draw.io exports, whose `<foreignObject>` text `rsvg-convert` and Inkscape silently drop. Needs `playwright install chromium`. |

## Overleaf bridge

| Tool | Owner skill | What it does |
|------|-------------|--------------|
| `overleaf_setup.sh` | `/overleaf-sync setup` | One-time git-bridge setup. Refuses to run without a TTY (agents can't), reads the token via `read -s`, strips it from the remote URL, installs a token-blocking `pre-commit` hook. **The user runs this, not the agent.** |
| `overleaf_sync.sh` | `/overleaf-sync` | The `status` / `pull` / `push` / `sync-figures` / `audit` sub-commands. Owns the canonical rsync exclude list; stages before review so new files show in the diffstat; distinguishes a network failure from a real divergence. |
| `overleaf_audit.sh` | `/overleaf-sync` | Scans a clone for a leaked token: working tree, remote URLs, git history, credential files. |

## Literature and search

| Tool | Owner skill | What it does |
|------|-------------|--------------|
| `arxiv_fetch.py` | `/arxiv`, `/research-lit` | Search and download arXiv papers. |
| `openalex_fetch.py` | `/openalex`, `/research-lit` | OpenAlex API client. |
| `semantic_scholar_fetch.py` | `/semantic-scholar`, `/research-lit` | Semantic Scholar fetch. |
| `exa_search.py` | `/exa-search`, `/research-lit` | AI-powered web search via Exa. |
| `deepxiv_fetch.py` | `/deepxiv`, `/research-lit` | Adapter around the installed `deepxiv` CLI. |
| `verify_papers.py` | `/research-lit`, `/novelty-check`, `/idea-creator` | Pre-search existence check — catches hallucinated references before they enter the pipeline. |
| `research_wiki.py` | `/research-wiki` (+ ~15 consumers) | Research-wiki read/write utilities. The most widely shared helper in the repo. |
| `verify_wiki_coverage.sh` | `/research-wiki` | Coverage diagnostic — explicitly **not** a gate. |
| `capture_filter.py` | `/research-wiki`, `/meta-optimize` | Anti-self-poisoning filter on what gets written into ARIS memory. |

## Audits and integrity

| Tool | Owner skill | What it does |
|------|-------------|--------------|
| `verify_paper_audits.sh` | `/paper-claim-audit`, `/citation-audit`, `/proof-checker`, … | External verifier for the mandatory paper audits. |
| `refresh_audit_hashes.py` | `/paper-claim-audit`, `/citation-audit`, `/proof-checker`, `/kill-argument` | Batched SHA-256 refresh across the four audit ledgers. |
| `evidence_check.py` | `/result-to-claim` | Deterministic evidence pre-check for claim audits. |
| `forensics_gate.py` | `/integrity-forensics`, `/paper-writing` | Typed policy gate + append-only obligations ledger. |
| `provenance.py` | `/meta-apply`, `/meta-optimize` | Provenance-as-authorization for auto-authored artifacts. |
| `threat_scan.py` | `/idea-creator` (Codex mirror) | Prompt-injection / exfiltration scanner. |
| `save_trace.sh` | ~20 audit + review skills | Saves a reviewer MCP call trace to `.aris/traces/`. |

## Run orchestration

| Tool | Owner skill | What it does |
|------|-------------|--------------|
| `run_state.py` | `/research-pipeline` | Resumable run state for multi-phase workflows. |
| `iteration_log.py` | `/research-pipeline`, `/idea-discovery` | Overnight-loop stall detection → forced structural pivot. |
| `watchdog.py` | `/training-check`, `/research-pipeline` | Server-side unified monitoring daemon. |
| `experiment_queue/` | `/experiment-queue` | `queue_manager.py`, `build_manifest.py` (legacy entry points → canonical helpers). |
| `meta_opt/` | `/meta-optimize` | `check_ready.sh`, `log_event.sh`, `trigger_eval.py` — measures whether a skill's `description` actually fires. |

## Install / update (no skill owner — run by hand)

| Tool | What it does |
|------|--------------|
| `install_aris.sh` / `install_aris.ps1` | Project-local ARIS install (flat per-skill symlinks). Referenced by ~25 SKILL.md files as the repair step when a helper fails to resolve. |
| `smart_update.sh` / `smart_update.ps1` | Update installed skills without clobbering local edits. |
| `install_aris_codex.sh`, `smart_update_codex.sh` | Same, for the Codex-native skill mirror (`skills-codex/`). |
| `install_aris_copilot.sh`, `smart_update_copilot.sh` | Same, for GitHub Copilot CLI. |
| `skill_picker.py` | Interactive checkbox picker for a selective install. |

## Project bootstrap (AHIL-specific, no skill owner)

These restore local-only content that is deliberately git-ignored. They are project setup, not part
of any research workflow — an agent should not reach for them unless the user is setting up a clone.

| Tool | What it does |
|------|--------------|
| `install_ahil.sh` | Restores git-ignored content (`third_party/`, `.aris/`, `.vscode/`, `.claude/`, global skills). Resolves or clones the ARIS root from `$1`. |
| `init_ahil_project.sh` | Calls `install_ahil.sh`, then writes the standard `.gitignore` for a new AHIL project. |
| `install_ahil_ei.sh` | Clones the embodied-intelligence dependency (`lerobot`) into `third_party/ei_ws/`. |

## Repo maintenance (no skill owner — CI and authoring aids)

| Tool | What it does |
|------|--------------|
| `lint_skills_helpers.sh` | Advisory lint for hardcoded `tools/<helper>` references in SKILL.md files — i.e. resolution-chain violations. |
| `check_skills_inventory.py` | Checks skill-inventory drift across mainline, the Codex mirror, and the docs. |
| `convert_skills_to_llm_chat.py` | Converts Codex-native skills to llm-chat MCP compatible versions. |
| `generate_codex_claude_review_overrides.py` | Generates Claude-review overrides for upstream Codex-native skills. |
| `skill-groups.tsv` | Skill grouping table consumed by the installers. |
</content>

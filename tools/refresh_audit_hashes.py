#!/usr/bin/env python3
"""
refresh_audit_hashes.py — batched SHA-256 hash refresh across the four ARIS
mandatory paper-audit JSONs (PROOF_AUDIT.json, PAPER_CLAIM_AUDIT.json,
CITATION_AUDIT.json, KILL_ARGUMENT.json).

================================================================
CONTRACT
================================================================

Purpose
-------
After a writing-level edit pass on a paper (e.g. tightening a paragraph,
re-pluralizing a phrase, fixing a citation context — anything that does
NOT change which claims are made, which citations exist, or whether any
theorem environment is added/removed), the paper's `.tex` / `.pdf` files
move on disk but the audited_input_hashes recorded in the four audit
JSONs go stale. `verify_paper_audits.sh` then reports STALE and the
submission-level enforcement fails.

The mechanical fix is to recompute SHA-256 for each touched file and
overwrite the matching `"path/to/file": "sha256:..."` line in every
audit JSON that references it. Doing this with one Edit per (file ×
JSON) pair is O(N×M) tool calls — wasteful when one Bash invocation
of this helper can do the entire grid in O(1).

What this script does
---------------------
1. Reads the paper directory.
2. For each requested file (paper-relative path), computes SHA-256.
3. For each of the four audit JSONs that exist in the paper directory,
   regex-replaces the hex segment after `"<path>": "sha256:` with the
   new hash. The JSON is NOT parsed and re-dumped — formatting,
   indentation, key ordering, and any surrounding `hash_refresh_note_*`
   narrative blocks are preserved byte-for-byte except for the 64-char
   hex segment(s) that changed.

What this script does NOT do
----------------------------
- Does NOT add `hash_refresh_note_*` narrative blocks. Those are
  human-written prose that says WHY the refresh happened (e.g. "fifth
  user-directed writing-level pass; zero citation additions; per-point
  verdicts unchanged"). Add the note via a separate Edit on whichever
  one or two JSONs need it.
- Does NOT re-run the audit. Hash refresh is only valid when the
  underlying audit verdict is structurally invariant under the edit
  (no new claims / citations / theorems). If the edit could change the
  audit outcome, re-run the audit skill instead.
- Does NOT touch `main.tex`, `references.bib`, `math_commands.tex`, or
  any file not explicitly listed on the command line. The caller is
  responsible for telling the helper exactly which files moved.
- Does NOT compile the paper. Caller must run latexmk first so that
  `main.pdf` is up-to-date before the script hashes it.
- Does NOT call `verify_paper_audits.sh`. Caller should run that
  afterwards as the final gate.

Usage
-----
    python3 tools/refresh_audit_hashes.py <paper-dir> <file1> [<file2> ...]

Examples
--------
    # After a §0/§1/§7 writing pass + recompile:
    python3 tools/refresh_audit_hashes.py path/to/paper \\
        sections/0_abstract.tex \\
        sections/1_introduction.tex \\
        sections/7_conclusion.tex \\
        main.pdf

    # After a §3/§4 polish:
    python3 tools/refresh_audit_hashes.py path/to/paper \\
        sections/3_method.tex sections/4_main_results.tex main.pdf

Exit codes
----------
    0  All requested files hashed; matching keys updated in every audit
       JSON that referenced them. Stdout prints a per-(file × JSON) grid
       so the caller can verify coverage.
    1  Paper directory missing, or a requested file does not exist on disk.
    2  Bad command-line arguments.
    3  A requested file exists on disk but is referenced by NONE of the
       four audit JSONs. This is almost always a typo in the file list
       (e.g. `section/` instead of `sections/`) — the caller should fix
       the path rather than silently accept a no-op.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys
from typing import Iterable

AUDIT_JSONS = (
    "PROOF_AUDIT.json",
    "PAPER_CLAIM_AUDIT.json",
    "CITATION_AUDIT.json",
    "KILL_ARGUMENT.json",
)
SHA256_HEX_RE = r"[0-9a-f]{64}"


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_in_json(text: str, paper_rel: str, new_hex: str) -> tuple[str, int]:
    pattern = re.compile(
        r'("' + re.escape(paper_rel) + r'":\s*"sha256:)' + SHA256_HEX_RE
    )
    matches = pattern.findall(text)
    if not matches:
        return text, 0
    new_text = pattern.sub(lambda m: m.group(1) + new_hex, text)
    return new_text, len(matches)


def refresh(paper_dir: pathlib.Path, files: Iterable[str]) -> int:
    if not paper_dir.is_dir():
        print(f"error: paper dir not found: {paper_dir}", file=sys.stderr)
        return 1

    file_hashes: dict[str, str] = {}
    for rel in files:
        target = paper_dir / rel
        if not target.is_file():
            print(f"error: file not found: {target}", file=sys.stderr)
            return 1
        file_hashes[rel] = sha256_of(target)

    grid: dict[str, dict[str, int]] = {rel: {} for rel in file_hashes}
    untouched_files: list[str] = []

    for jname in AUDIT_JSONS:
        jpath = paper_dir / jname
        if not jpath.is_file():
            continue
        text = jpath.read_text()
        changed = False
        for rel, new_hex in file_hashes.items():
            text, n = replace_in_json(text, rel, new_hex)
            grid[rel][jname] = n
            if n > 0:
                changed = True
        if changed:
            jpath.write_text(text)

    for rel, per_json in grid.items():
        if sum(per_json.values()) == 0:
            untouched_files.append(rel)

    width = max(len(rel) for rel in file_hashes) if file_hashes else 0
    header = f"{'file':<{width}}  " + "  ".join(
        j.replace(".json", "").replace("_AUDIT", "")[:12] for j in AUDIT_JSONS
    )
    print(header)
    print("-" * len(header))
    for rel in file_hashes:
        per_json = grid[rel]
        row = f"{rel:<{width}}  " + "  ".join(
            f"{per_json.get(j, 0):>12d}" for j in AUDIT_JSONS
        )
        print(row)

    if untouched_files:
        print(
            "\nerror: the following files were hashed but are referenced by "
            "NONE of the four audit JSONs (likely a typo in the file list):",
            file=sys.stderr,
        )
        for rel in untouched_files:
            print(f"  - {rel}", file=sys.stderr)
        return 3

    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: python3 tools/refresh_audit_hashes.py <paper-dir> "
            "<file1> [<file2> ...]",
            file=sys.stderr,
        )
        return 2
    paper_dir = pathlib.Path(argv[1]).resolve()
    files = argv[2:]
    return refresh(paper_dir, files)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

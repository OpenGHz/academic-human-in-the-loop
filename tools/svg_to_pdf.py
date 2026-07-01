#!/usr/bin/env python3
"""Convert an SVG to a tightly-cropped single-page PDF via Playwright/Chromium.

Designed for SVGs exported from draw.io / diagrams.net, whose text labels live
inside <foreignObject> (HTML). Inkscape 0.92 silently drops those; librsvg's
support is limited. Chromium renders them faithfully.

Usage:
    python3 tools/svg_to_pdf.py <input.svg> [output.pdf] [--pad PX]

If <output.pdf> is omitted, writes alongside the SVG with the same stem.
--pad adds a few CSS pixels around the SVG box so content doesn't spill to
page 2 (default 2).

Requires: playwright with chromium installed
    pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def convert(svg_path: Path, pdf_path: Path, pad_px: float = 2.0) -> None:
    from playwright.sync_api import sync_playwright

    svg = svg_path.read_text(encoding="utf-8")
    html = (
        "<!doctype html><html><head><meta charset=utf-8>"
        "<style>html,body{margin:0;padding:0;background:#fff} svg{display:block}</style>"
        f"</head><body>{svg}</body></html>"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        box = page.evaluate(
            "() => { const s = document.querySelector('svg');"
            " const r = s.getBoundingClientRect();"
            " return {w: r.width, h: r.height}; }"
        )
        w_in = (box["w"] + pad_px) / 96.0
        h_in = (box["h"] + pad_px) / 96.0
        page.pdf(
            path=str(pdf_path),
            width=f"{w_in}in",
            height=f"{h_in}in",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("svg", type=Path, help="Input SVG path")
    ap.add_argument("pdf", type=Path, nargs="?", help="Output PDF path (default: alongside SVG)")
    ap.add_argument("--pad", type=float, default=2.0, help="CSS-px padding to avoid page overflow (default 2)")
    args = ap.parse_args()

    if not args.svg.is_file():
        print(f"ERROR: SVG not found: {args.svg}", file=sys.stderr)
        return 2

    pdf_path = args.pdf if args.pdf is not None else args.svg.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        convert(args.svg, pdf_path, pad_px=args.pad)
    except ImportError:
        print(
            "ERROR: playwright is not installed.\n"
            "  pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 3
    except Exception as e:
        print(f"ERROR: conversion failed: {e}", file=sys.stderr)
        return 4

    size = pdf_path.stat().st_size
    print(f"OK  {pdf_path}  ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

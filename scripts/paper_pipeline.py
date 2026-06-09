"""One-shot pipeline for paper processing (agent-native).

This script ties together the non-LLM parts of the workflow:
1. Parse the PDF into structured JSON.
2. (Agent analyzes the paper JSON — not handled by this script)
3. Write the final Markdown note from an analysis JSON.

The agent should run this script twice:
- First with just the PDF to get the parsed JSON.
- Then with --analysis to render the final note.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

_SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from scripts.obsidian_writer import write_obsidian_note
from scripts.pdf_parser import parse_paper_pdf


VAULT_DIR = Path(os.getenv("PAPER_VAULT_DIR", "./output"))


def build_arg_parser() -> argparse.ArgumentParser:
    """Create command-line arguments for the pipeline."""
    parser = argparse.ArgumentParser(
        description="Parse a paper PDF and/or render a Markdown note from analysis JSON"
    )
    parser.add_argument("pdf", type=Path, help="Input paper PDF file")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Working output directory for intermediate files")
    parser.add_argument(
        "--vault",
        type=Path,
        default=VAULT_DIR,
        help="Target folder where the final note should be written",
    )
    parser.add_argument("--name", type=str, default=None, help="Optional note filename without extension")
    parser.add_argument(
        "--analysis", type=Path, default=None,
        help="Path to analysis JSON (agent output). If provided, skips parsing and renders note directly.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the paper pipeline."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Step 1: parse the raw PDF into a structured JSON file.
    paper_data = parse_paper_pdf(args.pdf, args.out)
    paper_json_path = Path(paper_data.json_path)

    if not args.analysis:
        stem = args.pdf.stem
        print(f"\nPDF parsed -> {paper_json_path}")
        print(f"Next: agent analyzes and saves to {paper_json_path.parent / f'{stem}.analysis.json'}")
        print(f"Then: python scripts/paper_pipeline.py \"{args.pdf}\" --analysis \"{paper_json_path.parent / f'{stem}.analysis.json'}\"")
        return 0

    # Step 2: render the final Markdown note from analysis JSON.
    analysis_json_path = Path(args.analysis)
    if not analysis_json_path.exists():
        print(f"Error: analysis JSON not found: {analysis_json_path}")
        return 1

    note = write_obsidian_note(analysis_json_path, args.vault, args.name)
    print(json.dumps({"analysis_json": str(analysis_json_path), "note": str(note.path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

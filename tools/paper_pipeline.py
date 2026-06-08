"""One-shot pipeline for paper processing.

This script ties together the full workflow:
1. Parse the PDF into structured JSON.
2. Analyze the parsed JSON with DeepSeek.
3. Write the final Obsidian note.

The goal is to give you a single command entry point so you do not need to run
three separate scripts manually every time.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.llm_analyzer import analyze_paper, load_paper_json
from tools.obsidian_writer import write_obsidian_note
from tools.pdf_parser import parse_paper_pdf


def build_arg_parser() -> argparse.ArgumentParser:
    """Create command-line arguments for the end-to-end pipeline."""
    parser = argparse.ArgumentParser(description="Parse a paper PDF, analyze it, and write an Obsidian note")
    parser.add_argument("pdf", type=Path, help="Input paper PDF file")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Working output directory for intermediate files")
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path(r"C:\Users\14870\Documents\Obsidian Vault\琅嬛记\02_Research\21_论文阅读笔记"),
        help="Obsidian vault folder where the final note should be written",
    )
    parser.add_argument("--name", type=str, default=None, help="Optional note filename without extension")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the full paper pipeline."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Step 1: parse the raw PDF into a structured JSON file.
    paper_data = parse_paper_pdf(args.pdf, args.out)

    # Step 2: load the parser output again and send it to the LLM analyzer.
    paper_json = load_paper_json(paper_data.json_path or args.out / args.pdf.stem / f"{args.pdf.stem}.json")
    analysis = analyze_paper(paper_json)

    # Step 3: persist the full analysis JSON (including new fields like title, authors, year, etc.)
    analysis_json_path = Path(paper_data.json_path or args.out / args.pdf.stem / f"{args.pdf.stem}.json")
    analysis_output_path = analysis_json_path.with_suffix(".analysis.json")
    analysis_output_path.write_text(
        json.dumps(
            {
                "paper": analysis.paper,
                "title": analysis.title,
                "authors": analysis.authors,
                "year": analysis.year,
                "journal": analysis.journal,
                "abstract": paper_json.get("abstract", ""),
                "summary": analysis.summary,
                "problem": analysis.problem,
                "method": analysis.method,
                "result": analysis.result,
                "architecture": analysis.architecture,
                "innovations": analysis.innovations,
                "experiments": analysis.experiments,
                "thoughts": analysis.thoughts,
                "figure_notes": analysis.figure_notes,
                "limitations": analysis.limitations,
                "topics": analysis.topics,
                "aliases": analysis.aliases,
                "related_papers": analysis.related_papers,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Step 4: write the final Obsidian markdown note into your vault.
    note = write_obsidian_note(analysis_output_path, args.vault, args.name)
    print(json.dumps({"analysis_json": str(analysis_output_path), "note": str(note.path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""One-command pipeline: PDF -> structured JSON + Markdown note.

Usage:
    # Parse PDF only (agent analyzes later)
    python scripts/process_paper.py "paper.pdf"

    # Parse + render (with existing analysis JSON)
    python scripts/process_paper.py "paper.pdf" --analysis ./output/paper/paper.analysis.json --name "2025 TiMi"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

# Load .env if present (for local Obsidian paths etc.)
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

# Allow running as `python scripts/process_paper.py` from skill root
_SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

# -- defaults (override via .env or environment variables) --
VAULT_DIR = Path(os.getenv("PAPER_VAULT_DIR", "./output"))
ATTACHMENTS_DIR = Path(os.getenv("PAPER_ATTACHMENTS_DIR", "./output/attachments"))
OUTPUT_DIR = Path(os.getenv("PAPER_OUTPUT_DIR", "./output"))


def parse_paper(
    pdf_path: str | Path,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path:
    """Parse a PDF and return the path to the generated paper JSON."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"[1/2] Parsing PDF: {pdf_path.name}")
    from scripts.pdf_parser import parse_paper_pdf

    extraction = parse_paper_pdf(pdf_path, output_dir)
    paper_json_path = Path(extraction.json_path)
    print(f"      -> {paper_json_path}")
    return paper_json_path


def render_note(
    analysis_json_path: str | Path,
    vault_dir: str | Path = VAULT_DIR,
    attachments_dir: str | Path = ATTACHMENTS_DIR,
    note_name: str | None = None,
) -> Path:
    """Render a Markdown note from an existing analysis JSON."""
    analysis_json_path = Path(analysis_json_path)
    if not analysis_json_path.exists():
        raise FileNotFoundError(f"Analysis JSON not found: {analysis_json_path}")

    print(f"[2/2] Rendering Markdown note...")
    from scripts.obsidian_writer import write_obsidian_note

    images_dir = analysis_json_path.parent / "images" / "png"

    note = write_obsidian_note(
        analysis_json_path=analysis_json_path,
        vault_dir=vault_dir,
        note_name=note_name,
        images_dir=images_dir if images_dir.is_dir() else None,
        attachments_dir=attachments_dir,
    )
    print(f"      -> {note.path}")
    print(f"\nDone: {note.title}")
    return note.path


def process_paper(
    pdf_path: str | Path,
    vault_dir: str | Path = VAULT_DIR,
    attachments_dir: str | Path = ATTACHMENTS_DIR,
    output_dir: str | Path = OUTPUT_DIR,
    note_name: str | None = None,
    analysis_json_path: str | Path | None = None,
) -> Path | None:
    """Run the pipeline. If analysis_json is provided, render note; otherwise just parse PDF."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir = Path(output_dir)
    stem = pdf_path.stem

    # Step 1: Parse PDF
    paper_json_path = parse_paper(pdf_path, output_dir)

    # Step 2: Render note if analysis JSON is provided
    if analysis_json_path:
        return render_note(
            analysis_json_path=analysis_json_path,
            vault_dir=vault_dir,
            attachments_dir=attachments_dir,
            note_name=note_name,
        )

    print(f"\nPDF parsed. Next steps:")
    print(f"  1. Agent analyzes: {paper_json_path}")
    print(f"  2. Save analysis as: {paper_json_path.parent / f'{stem}.analysis.json'}")
    print(f"  3. Render note: python scripts/process_paper.py \"{pdf_path}\" --analysis \"{paper_json_path.parent / f'{stem}.analysis.json'}\"")
    return None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PDF -> structured JSON + Markdown note"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--name", type=str, default=None, help="Note filename (without .md)")
    parser.add_argument("--vault", type=Path, default=VAULT_DIR, help="Target directory for the note")
    parser.add_argument("--attachments", type=Path, default=ATTACHMENTS_DIR, help="Attachments directory")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Output directory for parsed data")
    parser.add_argument(
        "--analysis", type=Path, default=None,
        help="Path to analysis JSON (agent output). If provided, renders note directly.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = build_arg_parser().parse_args(argv)
    try:
        process_paper(
            pdf_path=args.pdf,
            vault_dir=args.vault,
            attachments_dir=args.attachments,
            output_dir=args.output,
            note_name=args.name,
            analysis_json_path=args.analysis,
        )
        return 0
    except Exception as e:
        print(f"\nFailed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

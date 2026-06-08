"""One-command pipeline: PDF → Obsidian note.

Usage:
    python tools/process_paper.py "path/to/paper.pdf"
    python tools/process_paper.py "path/to/paper.pdf" --name "2025 TiMi"

Steps:
    1. Parse PDF → output/<stem>/<stem>.json + images
    2. LLM analysis → output/<stem>/<stem>.analysis.json
    3. Render to Obsidian vault with images
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

# Allow running as `python tools/process_paper.py` from project root
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ── defaults ──────────────────────────────────────────────────────────────
VAULT_DIR = r"C:\Users\14870\Documents\Obsidian Vault\琅嬛记\02_Research\21_论文阅读笔记"
ATTACHMENTS_DIR = r"C:\Users\14870\Documents\Obsidian Vault\琅嬛记\99_Templates\Attachments"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def process_paper(
    pdf_path: str | Path,
    vault_dir: str | Path = VAULT_DIR,
    attachments_dir: str | Path = ATTACHMENTS_DIR,
    output_dir: str | Path = OUTPUT_DIR,
    note_name: str | None = None,
) -> Path:
    """Run the full pipeline and return the path to the generated note."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir = Path(output_dir)
    stem = pdf_path.stem

    # ── Step 1: Parse PDF ──
    print(f"[1/3] 解析 PDF: {pdf_path.name}")
    from tools.pdf_parser import parse_paper_pdf
    extraction = parse_paper_pdf(pdf_path, output_dir)
    paper_json_path = Path(extraction.json_path)
    print(f"      → {paper_json_path}")

    # ── Step 2: LLM Analysis ──
    print(f"[2/3] LLM 分析中...")
    from tools.llm_analyzer import load_paper_json, analyze_paper
    import json

    paper_json = load_paper_json(paper_json_path)
    result = analyze_paper(paper_json)

    analysis_path = paper_json_path.parent / f"{stem}.analysis.json"
    payload = {
        "paper": result.paper,
        "title": result.title,
        "authors": result.authors,
        "year": result.year,
        "journal": result.journal,
        "abstract": result.abstract,
        "summary": result.summary,
        "tldr": result.tldr,
        "problem": result.problem,
        "method": result.method,
        "result": result.result,
        "architecture": result.architecture,
        "innovations": result.innovations,
        "experiments": result.experiments,
        "thoughts": result.thoughts,
        "figure_notes": result.figure_notes,
        "limitations": result.limitations,
        "topics": result.topics,
        "aliases": result.aliases,
        "related_papers": result.related_papers,
    }
    analysis_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"      → {analysis_path}")

    # ── Step 3: Render to Obsidian ──
    print(f"[3/3] 渲染笔记到 Obsidian...")
    from tools.obsidian_writer import write_obsidian_note

    images_dir = paper_json_path.parent / "images" / "png"
    note = write_obsidian_note(
        analysis_json_path=analysis_path,
        vault_dir=vault_dir,
        note_name=note_name,
        images_dir=images_dir if images_dir.is_dir() else None,
        attachments_dir=attachments_dir,
    )
    print(f"      → {note.path}")
    print(f"\n✅ 完成: {note.title}")
    return note.path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PDF → Obsidian note (one command pipeline)"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--name", type=str, default=None, help="Note filename (without .md)")
    parser.add_argument("--vault", type=Path, default=Path(VAULT_DIR), help="Obsidian vault dir")
    parser.add_argument("--attachments", type=Path, default=Path(ATTACHMENTS_DIR), help="Attachments dir")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Output dir for parsed data")
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
        )
        return 0
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

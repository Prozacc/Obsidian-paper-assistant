"""Analyze parsed paper JSON with an OpenAI-compatible LLM API.

The expected workflow is:
1. Run ``tools/pdf_parser.py`` to create ``output/<paper>/<paper>.json``.
2. Run this script on that JSON file.
3. Save a cleaner, note-friendly analysis JSON for downstream use.

The default endpoint is DeepSeek's OpenAI-compatible API. Provide credentials
through environment variables instead of hard-coding secrets:

    $env:DEEPSEEK_API_KEY="..."
    $env:DEEPSEEK_MODEL="deepseek-chat"
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass
class AnalysisResult:
    """Structured LLM analysis for a paper."""

    paper: str
    summary: str
    contributions: list[str]
    method: str
    experiments: str
    figure_notes: list[str]
    limitations: list[str]


def load_paper_json(path: str | Path) -> dict[str, Any]:
    """Load the raw paper JSON produced by ``pdf_parser.py``."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_prompt(paper_json: dict[str, Any]) -> str:
    """Build a strict JSON-only analysis prompt."""
    title = paper_json.get("title", "")
    abstract = paper_json.get("abstract", "")
    sections = paper_json.get("sections", [])
    references = paper_json.get("references", [])
    images = paper_json.get("images", [])

    return (
        "You are a research assistant skilled at reading papers and creating "
        "structured notes.\n\n"
        "Based on the parsed paper JSON below, output strict JSON only. "
        "Do not include markdown, comments, or code fences.\n\n"
        "The JSON object must contain these keys:\n"
        "- summary: 3-5 sentence overall summary.\n"
        "- contributions: list of main contributions.\n"
        "- method: structured explanation of the core method and modules.\n"
        "- experiments: datasets, baselines, metrics, and main findings.\n"
        "- figure_notes: list of figure/table notes.\n"
        "- limitations: list of possible limitations. Use an empty list if unknown.\n\n"
        "Do not invent facts. If information is missing, use an empty string or "
        "empty list as appropriate.\n\n"
        f"Title:\n{title}\n\n"
        f"Abstract:\n{abstract}\n\n"
        f"Sections:\n{json.dumps(sections, ensure_ascii=False, indent=2)}\n\n"
        "References, first 20:\n"
        f"{json.dumps(references[:20], ensure_ascii=False, indent=2)}\n\n"
        f"Images:\n{json.dumps(images, ensure_ascii=False, indent=2)}\n"
    )


def call_llm(prompt: str) -> str:
    """Call an OpenAI-compatible chat completion API."""
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI")
    except Exception as exc:
        raise RuntimeError("Missing dependency: install it with `pip install openai`.") from exc

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY environment variable.")

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a paper analysis assistant that outputs strict JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or "{}"


def analyze_paper(paper_json: dict[str, Any]) -> AnalysisResult:
    """Analyze parsed paper JSON with an LLM."""
    prompt = build_prompt(paper_json)
    raw = call_llm(prompt)
    data = json.loads(raw)
    return AnalysisResult(
        paper=str(paper_json.get("pdf", "")),
        summary=str(data.get("summary", "")),
        contributions=list(data.get("contributions", [])),
        method=str(data.get("method", "")),
        experiments=str(data.get("experiments", "")),
        figure_notes=list(data.get("figure_notes", [])),
        limitations=list(data.get("limitations", [])),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze parsed paper JSON with an LLM")
    parser.add_argument("input", type=Path, help="Input JSON from tools/pdf_parser.py")
    parser.add_argument("--out", type=Path, default=None, help="Optional output JSON path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    paper_json = load_paper_json(args.input)
    result = analyze_paper(paper_json)
    payload = {
        "paper": result.paper,
        "summary": result.summary,
        "contributions": result.contributions,
        "method": result.method,
        "experiments": result.experiments,
        "figure_notes": result.figure_notes,
        "limitations": result.limitations,
    }

    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

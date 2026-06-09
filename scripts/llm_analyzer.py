"""Paper analysis prompt template and result utilities for agent-native workflows.

This module provides:
- ``build_prompt()``: builds the analysis prompt for the agent to use.
- ``AnalysisResult``: dataclass defining the expected output schema.
- ``save_analysis()``: validates and saves agent-produced analysis JSON.
- ``parse_llm_json()``: robust JSON parsing for LLM-style output.

Expected agent workflow:
1. Run ``scripts/pdf_parser.py`` to create ``output/<paper>/<paper>.json``.
2. Agent reads that JSON, calls ``build_prompt()`` to get the analysis prompt.
3. Agent produces structured JSON analysis (as the LLM itself).
4. Save the result with ``save_analysis()`` or pass to ``obsidian_writer.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


_SKILL_ROOT = Path(__file__).resolve().parent.parent
STYLE_GUIDE_PATH = _SKILL_ROOT / "references" / "style-guide.md"

_PAPER_LANG = os.environ.get("PAPER_LANG", "zh").lower()
if _PAPER_LANG not in ("zh", "en"):
    _PAPER_LANG = "zh"


@dataclass
class AnalysisResult:
    """Structured analysis result for a paper."""

    paper: str
    title: str
    authors: list[str]
    year: str
    journal: str
    abstract: str
    summary: str
    tldr: str
    problem: str
    method: str
    result: str
    architecture: str
    innovations: list[str]
    experiments: str
    thoughts: str
    figure_notes: list[str]
    limitations: list[str]
    topics: list[str]
    aliases: list[str]
    related_papers: list[str]


def load_paper_json(path: str | Path) -> dict[str, Any]:
    """Load the raw paper JSON produced by ``pdf_parser.py``."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_style_guide() -> str:
    """Load the style guide from references/style-guide.md."""
    if STYLE_GUIDE_PATH.exists():
        return STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    return ""


def _clean_authors(raw_authors: list[str]) -> list[str]:
    """Filter out obvious non-author tokens from PDF parser noise."""
    blacklist = {
        "university", "school", "institute", "college", "laboratory",
        "lab", "email", "department", "center", "centre", "corporation",
        "inc.", "ltd.", "org", "google", "microsoft", "amazon", "apple",
        "facebook", "meta", "nvidia", "intel", "ibm", "alibaba", "tencent",
        "baidu", "huawei", "siemens", "bosch", "philips",
        "china", "usa", "canada", "uk", "germany", "france", "japan",
        "shanghai", "beijing", "shenzhen", "hangzhou", "toronto",
        "co.,", "ltd", "inc", "corp", "gmbh", "ag", "bv", "plc",
    }
    cleaned: list[str] = []
    seen: set[str] = set()
    for a in raw_authors:
        a = a.strip().strip("†‡*•").rstrip(",")
        if not a or len(a) < 3 or len(a) > 40:
            continue
        lower = a.lower()
        if any(tok in lower for tok in blacklist):
            continue
        # simple name heuristic
        if not re.match(r"^[A-Za-z\s\-\.']+$", a):
            continue
        if len(a.split()) > 5:
            continue
        if lower in seen:
            continue
        seen.add(lower)
        cleaned.append(a)
    return cleaned


def build_prompt(paper_json: dict[str, Any]) -> str:
    """Build a strict JSON-only analysis prompt tailored to the user's note style.

    The agent should use this prompt to guide its analysis of the paper content.
    """
    title = paper_json.get("title", "")
    abstract = paper_json.get("abstract", "")
    sections = paper_json.get("sections", [])
    references = paper_json.get("references", [])
    images = paper_json.get("images", [])

    # Build caption text so the agent can reason about figures WITHOUT seeing the image.
    image_descriptions: list[str] = []
    for img in images:
        caption = img.get("caption", "")
        label = img.get("figure_label", "")
        if caption or label:
            image_descriptions.append(f"{label or 'Figure'}: {caption or 'No caption'}")

    # Truncate sections to avoid token explosion while keeping key sections.
    key_sections = []
    for sec in sections:
        heading = sec.get("heading", "")
        text = sec.get("text", "")
        if any(k in heading.lower() for k in (
            "abstract", "introduction", "method", "model", "architecture",
            "experiment", "result", "evaluation", "conclusion",
        )):
            key_sections.append({"heading": heading, "text": text[:3000]})
        else:
            key_sections.append({"heading": heading, "text": text[:1500]})

    style_guide = _load_style_guide()

    if _PAPER_LANG == "en":
        return _build_prompt_en(title, abstract, key_sections, references, image_descriptions)
    return _build_prompt_zh(title, abstract, key_sections, references, image_descriptions, style_guide)


def _build_prompt_en(
    title: str,
    abstract: str,
    key_sections: list[dict[str, str]],
    references: list[str],
    image_descriptions: list[str],
) -> str:
    """English prompt template for paper analysis."""
    return (
        "You are a senior deep learning researcher skilled at reading academic papers "
        "and producing high-quality structured reading notes.\n"
        "Based on the parsed paper content below, output strictly valid JSON "
        "(no markdown code blocks, no comments).\n\n"

        "【Important: Figure/Table Notes】\n"
        "- You do NOT have access to the actual images. Use only the captions provided.\n"
        "- figure_notes: select the 3-5 most important figures/tables, 1-2 sentences each.\n"
        "- DO NOT include any file paths or image links (no ![...](...) syntax).\n"
        "- In architecture and experiments, reference figures by number "
        "(e.g. \"as shown in Figure 3\"). The system will auto-embed matching images.\n\n"

        "【Field Requirements】\n\n"
        "1. summary: Output the paper's original English abstract verbatim.\n\n"
        "2. tldr: ONE sentence only. No bold, no expansion, no line breaks.\n\n"
        "3. problem / method / result: Each starts with `- **Problem:**` etc., "
        "followed by 2-4 short sub-bullets (1-2 lines each). No deep nesting.\n\n"
        "4. architecture: Most important section. Structure as:\n"
        "   - `### 1. Overall Architecture`: 3-5 step data flow + input/output shapes.\n"
        "   - `### 2. Module X`, `### 3. Module Y`... detail each core module.\n"
        "   - Include key formulas (LaTeX $...$). Use > [!question] callouts for tricky concepts.\n"
        "   - Conclude with Loss Function and optimization strategy.\n\n"
        "5. innovations: List 3-4 items, 1 sentence each, highlighting key differences.\n\n"
        "6. experiments: Concise, markdown list:\n"
        "   - Datasets (name only, one sentence)\n"
        "   - Baselines (name only, one sentence)\n"
        "   - Key findings (2-3 bullet points with critical numbers)\n"
        "   - Do NOT include ablation details or experimental setup.\n\n"
        "7. thoughts: Keep brief, 1-2 points, use first person (\"I think...\"). Can be empty.\n\n"
        "8. figure_notes: Core information per figure, based on captions and text.\n\n"
        "9. limitations: Author-stated or inferrable limitations. Empty list if none.\n\n"
        "10. Metadata: topics (3-5), aliases (paper short name), related_papers (3-8 classic papers).\n\n"

        "Required JSON fields (empty string/list OK, but don't omit keys):\n"
        "title, authors, year, journal, abstract, summary, tldr, problem, method, result, "
        "architecture, innovations, experiments, thoughts, figure_notes, limitations, "
        "topics, aliases, related_papers\n\n"

        "---\n\n"
        f"Paper Title: {title}\n\n"
        f"Abstract:\n{abstract}\n\n"
        f"Sections:\n{json.dumps(key_sections, ensure_ascii=False, indent=2)}\n\n"
        "Figure Captions (for reference only, images not needed):\n"
        f"{chr(10).join(image_descriptions[:30]) or 'None'}\n\n"
        "First 10 References (for domain context):\n"
        f"{json.dumps(references[:10], ensure_ascii=False, indent=2)}"
    )


def _build_prompt_zh(
    title: str,
    abstract: str,
    key_sections: list[dict[str, str]],
    references: list[str],
    image_descriptions: list[str],
    style_guide: str,
) -> str:
    """Chinese prompt template for paper analysis."""
    return (
        "你是一位资深深度学习研究者，擅长阅读学术论文并整理高质量阅读笔记。\n"
        "请基于下面提供的论文解析内容，输出严格 JSON（不要 markdown 代码块，不要注释）。\n\n"

        "【重要：风格要求】\n"
        "你必须严格按照下面的风格指南来写笔记。风格指南中包含规则和真实笔记范例，\n"
        "你的输出必须在语言风格、格式、深度上与范例保持一致。\n\n"
        f"{style_guide}\n\n"

        "【关于图片/表格的重要说明】\n"
        "- 你**不需要**、也**无法**看到论文中的图片本身。\n"
        "- 我已经提供了每张图片的 Caption。\n"
        "- figure_notes 字段：只选最重要的 3-5 张图/表，每条 1-2 句话概括核心信息。\n"
        "  不要列出所有图片，只选对理解论文最关键的几张（如整体架构图、核心实验对比图）。\n"
        "- **绝对不要在输出中包含任何文件路径或图片链接**（不要写 ![...](...) 格式），\n"
        "  路径在笔记中会爆红。\n"
        "- 但在 architecture 和 experiments 中，**应该用文字引用图号**（如\"如图4所示\"、\"Figure 5 展示\"），\n"
        "  系统会自动根据图号插入对应图片。对关键架构图和实验结果图，务必要引用。\n\n"

        "【各字段要求（简要版，详细风格见上方指南）】\n\n"

        "1. summary：直接输出论文的**英文摘要原文**，不要自己缩写改写。\n\n"

        "2. tldr（一句话总结）：**只写一句话**，不加粗、不展开、不换行。\n"
        "   用一句话概括论文解决了什么问题、用了什么方法、效果如何。\n\n"

        "3. problem / method / result：每个字段用 `- **Problem:**` 等开头，\n"
        "   然后跟 2-4 个简短的 sub-bullets（每个 bullet 1-2 行），**不要层层嵌套**。\n"
        "   - problem：简要说明问题和现有方法的缺陷。\n"
        "   - method：分模块概述，每个模块一句话。\n"
        "   - result：2-3 条核心结论，含关键数字。\n\n"

        "4. architecture：**笔记最核心的部分**，按以下结构组织：\n"
        "   - `### 1. 整体思路`：3-5 步数据流 + 输入输出形状。\n"
        "   - `### 2. XXX模块`、`### 3. YYY模块`... 逐一详解每个核心模块。\n"
        "   - 每个模块要写**充分的解释性文字**，像在给同学讲解这个模块为什么这样设计、\n"
        "     它解决了什么问题、和已有方法有什么区别。不要只列公式，要解释公式的含义。\n"
        "   - 包含关键公式（LaTeX $...$），对难理解的概念用 > [!question] callout 解释。\n"
        "   - 最后说明 Loss Function 和优化策略。\n"
        "   - 不需要单独的\"关键创新点\"小节，创新点融入各模块描述中。\n\n"

        "5. innovations：列表形式，3-4 条，每条 1 句话，突出核心区别。\n\n"

        "6. experiments：**简洁**，用 markdown 列表：\n"
        "   - 数据集（一句话列出名称即可）\n"
        "   - Baseline（一句话列出名称即可）\n"
        "   - 主要结论（2-3 条核心结论，每条一行）\n"
        "   - **不要写消融实验细节、不要写实验设置**，只抓核心结论。\n\n"

        "7. thoughts：**尽量简洁**，1-2 点即可，也可以留空。\n"
        "   - 如果写，要有个人视角（用\"我\"），点到为止。\n\n"

        "7. figure_notes：基于 caption 和正文，列出每张图的核心信息。\n\n"

        "8. limitations：论文自述或可推断的局限，如无则空列表。\n\n"

        "9. 元数据：topics（3-5个）、aliases（论文简称）、related_papers（3-8个经典论文）。\n\n"

        "JSON 必须包含以下字段（value 为空字符串或空列表均可，但不要省略 key）：\n"
        "title, authors, year, journal, abstract, summary, tldr, problem, method, result, "
        "architecture, innovations, experiments, thoughts, figure_notes, limitations, "
        "topics, aliases, related_papers\n\n"

        "---\n\n"
        f"论文标题: {title}\n\n"
        f"摘要:\n{abstract}\n\n"
        f"章节内容:\n{json.dumps(key_sections, ensure_ascii=False, indent=2)}\n\n"
        "图片 Caption（供参考，无需看图本身）:\n"
        f"{chr(10).join(image_descriptions[:30]) or '无'}\n\n"
        "参考文献前 10 条（供推断领域背景）:\n"
        f"{json.dumps(references[:10], ensure_ascii=False, indent=2)}"
    )


def _sanitize_json_text(text: str) -> str:
    """修复 LLM 输出中常见的非法转义，尽量把文本变成可解析 JSON。"""
    # 1. 处理一般非法转义（保留合法转义：\" \\ \/ \b \f \n \r \t）
    text = re.sub(r'\\(?![\\"/bfnrtu])', r'\\\\', text)
    # 2. 处理 \u 后面不紧跟 4 位十六进制数字的情况（如 Windows 路径 C:\users）
    text = re.sub(r'\\u(?![0-9a-fA-F]{4})', r'\\\\u', text)
    return text


def parse_llm_json(raw: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM/agent response.

    Models sometimes wrap the object in a fenced code block or add a short
    preface. We also sanitize invalid backslash escapes because some model
    outputs may contain raw path-like strings or accidental single backslashes
    that break ``json.loads``.
    """
    text = raw.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    candidates = [text]
    object_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if object_match:
        candidates.append(object_match.group(0))

    last_error: Exception | None = None
    for candidate in candidates:
        for variant in (candidate, _sanitize_json_text(candidate)):
            try:
                parsed = json.loads(variant)
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError("LLM response must be a JSON object.")
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                continue

    raise last_error or ValueError("Unable to parse LLM response as JSON.")


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value] if value else []
    return [str(value)]


def _as_single_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return str(value)


def clean_analysis(data: dict[str, Any], paper_json: dict[str, Any]) -> AnalysisResult:
    """Clean and normalize a raw analysis dict into an AnalysisResult.

    This is useful when the agent produces analysis JSON that needs
    validation and normalization before saving.
    """
    # Prefer agent-corrected authors/year/journal over noisy PDF extraction
    llm_authors = _as_str_list(data.get("authors"))
    raw_authors = _clean_authors(paper_json.get("authors", []))
    authors = llm_authors if llm_authors else raw_authors

    return AnalysisResult(
        paper=str(paper_json.get("pdf", "")),
        title=str(data.get("title", paper_json.get("title", ""))),
        authors=authors,
        year=str(data.get("year", "")),
        journal=str(data.get("journal", "")),
        abstract=_as_single_str(data.get("abstract")) or str(paper_json.get("abstract", "")),
        summary=_as_single_str(data.get("summary")),
        tldr=_as_single_str(data.get("tldr")),
        problem=_as_single_str(data.get("problem")),
        method=_as_single_str(data.get("method")),
        result=_as_single_str(data.get("result")),
        architecture=_as_single_str(data.get("architecture")),
        innovations=_as_str_list(data.get("innovations")),
        experiments=_as_single_str(data.get("experiments")),
        thoughts=_as_single_str(data.get("thoughts")),
        figure_notes=_as_str_list(data.get("figure_notes")),
        limitations=_as_str_list(data.get("limitations")),
        topics=_as_str_list(data.get("topics")),
        aliases=_as_str_list(data.get("aliases")),
        related_papers=_as_str_list(data.get("related_papers")),
    )


def save_analysis(
    analysis: AnalysisResult,
    output_path: str | Path,
) -> Path:
    """Save an AnalysisResult to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "paper": analysis.paper,
        "title": analysis.title,
        "authors": analysis.authors,
        "year": analysis.year,
        "journal": analysis.journal,
        "abstract": analysis.abstract,
        "summary": analysis.summary,
        "tldr": analysis.tldr,
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
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean and normalize agent-produced analysis JSON"
    )
    parser.add_argument("input", type=Path, help="Raw analysis JSON (agent output)")
    parser.add_argument(
        "--paper-json", type=Path, default=None,
        help="Original paper JSON from pdf_parser (for author/title fallback)",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output path for cleaned JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: clean and normalize a raw analysis JSON file."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    raw_data = json.loads(Path(args.input).read_text(encoding="utf-8"))

    # If paper-json is provided, use it for fallback data; otherwise use raw_data itself
    paper_json = raw_data
    if args.paper_json and args.paper_json.exists():
        paper_json = json.loads(args.paper_json.read_text(encoding="utf-8"))

    result = clean_analysis(raw_data, paper_json)

    output = json.dumps(
        {
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
        },
        ensure_ascii=False,
        indent=2,
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

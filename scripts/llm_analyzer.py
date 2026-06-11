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

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "【MANDATORY RULES — Violating any of these will get the note rejected】\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "1. summary: MUST output the paper's original English abstract verbatim. "
        "If abstract is missing, write \"Abstract not available\". Do NOT paraphrase.\n\n"

        "2. tldr: ONE sentence only. No bold, no line breaks, max 80 words.\n\n"

        "3. problem: Start with `- **Problem:**`, then 2-4 short sub-bullets. "
        "Each bullet at most 2 lines. NO long paragraphs, NO deep nesting.\n\n"

        "4. method: Start with `- **Method:**`, then 3-4 module overviews, ONE sentence each.\n\n"

        "5. result: Start with `- **Result:**`, then 2-3 qualitative conclusions.\n"
        "   - NO specific numbers (MSE, MAE, accuracy, improvement %, etc.)\n"
        "   - NO \"as shown in Table X\" / \"see Figure X\" / \"in Table X\" / \"in Figure X\" — NO figure/table references at all\n"
        "   - Example (correct): \"The model achieves strong performance across multiple benchmarks, validating the proposed approach.\"\n\n"

        "6. architecture: **THE MOST IMPORTANT section — must be longer than problem + method + result + experiments combined.**\n"
        "   If you cannot achieve this length, your analysis is not deep enough.\n\n"
        "   Structure:\n"
        "   ### 1. Overall Architecture\n"
        "   - One-sentence core insight, then 3-5 step data flow with tensor shapes.\n\n"
        "   ### 2. Module X, ### 3. Module Y... (expand each module in depth)\n\n"
        "   Each module MUST follow this rhythm:\n"
        "   - Opening sentence: the module's core idea / fundamental problem it solves.\n"
        "   - Use bold sub-headings (`**Sub-component**`), NEVER `####`.\n"
        "   - Each sub-part: problem context -> method -> formula -> symbol explanation -> "
        "wrap up with \"This step can be understood as...\"\n"
        "   - Formulas embedded in narrative; NEVER stack naked formulas.\n"
        "   - End each module with a **Key Insights** paragraph (1-3 insights).\n"
        "   - Conclude with Loss Function and optimization strategy.\n\n"
        "   **ABSOLUTELY FORBIDDEN (any of these will get rejected):**\n"
        "   - One-liner descriptions (\"TMoE uses text as router input\") — each sub-part needs 2-3 full sentences minimum\n"
        "   - Q&A format (\"Why XXX? Because XXX\") — write natural narrative paragraphs\n"
        "   - Naked formulas without surrounding explanation paragraphs\n"
        "   - Using `> [!question]` or `> [!tip]` as BODY content — callouts are ONLY for reading hints, never replace body text\n"
        "   - Using images as the main content — text is primary, images are secondary references\n\n"

        "   【Example: multi-step module (DGraFormer DCGL depth — match this level)】\n"
        "   ```\n"
        "   ### 2. Dynamic Correlation-aware Graph Learning (DCGL)\n"
        "   DCGL aims to capture dynamic correlations and focus on key correlation weights. "
        "   The core flow has three steps: dynamic weight learning, key information focusing, and graph message passing.\n\n"
        "   **Dynamic Multivariate Correlation Weight Learning**\n"
        "   Instead of using one static graph for the entire sequence, DCGL learns a separate graph for each time window.\n\n"
        "   **(1) Frequency-domain Global Seasonal Prior**\n"
        "   Raw data often contains trends and external disturbances. Computing variable correlations directly "
        "   can be masked by the overall trend. DGraFormer first applies DFT to the entire training set, "
        "   selects the top-$K_f$ frequency components by amplitude, and reconstructs the seasonal representation via IDFT:\n"
        "   $$X_{sea} = \\operatorname{IDFT}(\\operatorname{argtop}_{K_f}(|\\operatorname{DFT}(X_{all})|), \\mathcal{A}, \\Phi)$$\n"
        "   where $\\mathcal{A}$ is the amplitude set and $\\Phi$ is the phase set.\n"
        "   Then cosine similarity is computed on $X_{sea}$ to obtain the global correlation weight matrix $C$.\n"
        "   This step can be understood as: extracting a relatively stable variable correlation prior from global training data, "
        "   which serves as the foundation for subsequent window-level dynamic graph learning.\n\n"
        "   **(2) Local Dynamic Fine-tuning**\n"
        "   For the $w$-th time window, the paper uses two sets of learnable node embeddings to generate window-specific parametric correlation matrices:\n"
        "   $$(F_w)_1 = \\operatorname{Linear}((E_w)_1), \\quad R_w = \\operatorname{ReLU}(\\tanh((F_w)_1(F_w)_2^\\top))$$\n"
        "   where $(E_w)_1, (E_w)_2$ are randomly initialized and trainable node embeddings.\n"
        "   The purpose of this step: let each window have its own local correlation structure, "
        "   rather than sharing the same adjacency matrix across all time periods.\n\n"
        "   **(3) Global-Local Dynamic Fusion**\n"
        "   The final correlation graph for window $w$ fuses the global prior $C$ and local parametric graph $R_w$:\n"
        "   $$\\mathcal{E}_w = \\alpha C + (1-\\alpha)R_w$$\n"
        "   At the beginning of training $\\alpha=0.9$ (more reliance on global prior); as training progresses, "
        "   $\\alpha$ gradually drops to $0.1$, increasing the role of the local learnable graph.\n\n"
        "   > [!important] Top-$K_e$ is not just for reducing computation — more importantly, it suppresses spurious correlation edges, "
        "   > preventing noisy relationships from diffusing during graph message passing.\n"
        "   ```\n\n"
        "   Notice the rhythm: each sub-step follows \"problem context -> method -> formula -> symbol explanation -> physical meaning\", "
        "   with ample narrative text before and after formulas, and a callout at the end for an intuition-correcting insight.\n"
        "   **Your architecture MUST match Example B in depth.**\n\n"

        "7. innovations: 3-4 items, 1 sentence each, highlighting key differences.\n\n"

        "8. experiments: Concise markdown list, **at most 3 key findings** (datasets + baselines + conclusions).\n"
        "   - Datasets (names only, one sentence)\n"
        "   - Baselines (names only, one sentence)\n"
        "   - Key findings (at most 3 qualitative bullets, one line each)\n"
        "   - **NO specific metric values** (MSE, MAE, accuracy, improvement %, etc.)\n"
        "   - **NO \"as shown in Table X\" / \"see Figure X\" / \"in Table X\" / \"in Figure X\" — NO figure/table references at all**\n"
        "   - Each conclusion is a synthetic judgment, not a data report\n"
        "   - Do NOT include ablation details or experimental setup.\n\n"

        "   【Example: wrong vs correct experiments writing】\n"
        "   ❌ Wrong: \"As shown in Table 1, the model achieves the best results on 9 datasets.\"\n"
        "   ✅ Correct: \"The model demonstrates strong performance across multiple benchmarks.\"\n\n"
        "   ❌ Wrong: \"As shown in Table 2, the plug-in module reduces MSE by 12.3% on PatchTST.\"\n"
        "   ✅ Correct: \"The plug-in module brings consistent performance gains across multiple Transformer backbones.\"\n\n"

        "9. thoughts: Can be empty string. If written, **at least 100 words** of substantive reflection.\n"
        "   Use first person (\"I think...\"). Write real insights: methodological inspiration transferable to your own work, "
        "   judgments about research directions, connections to prior work.\n"
        "   NO filler like \"good paper\" / \"well conducted experiments\" / \"enters my research coordinate system\".\n\n"

        "10. figure_notes: Select ONLY the 3-5 most important figures/tables, 1-2 sentences each.\n"
        "    Do NOT list all figures.\n\n"

        "11. limitations: Author-stated or inferrable limitations. Empty list if none.\n\n"

        "12. Metadata: topics (3-5), aliases (paper short name), related_papers (3-8 classic papers).\n\n"

        "13. Do NOT include any file paths or image links (`![...](...)`) in any field.\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "【SELF-CHECK — Verify before outputting】\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "- [ ] summary field contains the original English abstract (or \"Abstract not available\")\n"
        "- [ ] architecture length clearly exceeds problem + method + result + experiments combined\n"
        "- [ ] architecture contains NO `> [!question]` or `> [!tip]` replacing body text\n"
        "- [ ] architecture has a `**Key Insights:**` paragraph for each core module\n"
        "- [ ] experiments contains NO \"as shown in Table X\" / \"see Figure X\" / \"in Table X\" / \"in Figure X\"\n"
        "- [ ] experiments has at most 3 key findings\n"
        "- [ ] no field contains specific metric values (MSE, MAE, accuracy, improvement %, etc.)\n"
        "- [ ] thoughts is either empty or has at least 100 words of substantive reflection\n\n"

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
        "基于下面提供的论文解析内容，输出严格 JSON（不要 markdown 代码块，不要注释）。\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "【硬规则 — 违反任何一条笔记会被打回】\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "## 通用禁令\n"
        "❌ 禁止编造数值、URL、citekey、Zotero 链接或个人观点\n"
        "❌ 禁止写具体指标数值（MSE=0.42、提升5%等）\n"
        '❌ 禁止写"如表X所示""如图X所示""见表X""见图X"——任何表号图号都不出现\n'
        "❌ 禁止在字段中写文件路径或图片链接\n"
        '❌ 禁止写"这篇论文写得很好""实验充分""进入我的研究坐标系"等空话\n\n'

        "## 各字段要求\n\n"

        '1. summary：**英文摘要原文**，禁止缩写改写。无摘要则写 "Abstract not available"\n\n'

        "2. tldr：**一句话**，不加粗、不换行、≤80字\n\n"

        "3. problem：只写正文，**不要重复 `- **Problem:**` 标签**（模板会添加）。\n"
        "   包含 2-4 个 `- ` 子列表，每条 ≤2 行。禁止长段落和深层嵌套。\n"
        "   示例：\n"
        "   传统 Transformer 时序模型以时间点为 token，存在以下问题：\n"
        "   - 同一时间戳下的变量不一定代表同一事件，可能存在延迟或物理意义差异；\n"
        "   - 多变量过早融合到一个 token，削弱变量自身独立表征。\n\n"

        "4. method：只写正文，**不要重复 `- **Method:**` 标签**。3-4 个 `- ` 子列表，每条一句话。\n"
        "   示例：\n"
        "   iTransformer 采用倒置视角重新组织输入：\n"
        "   - 将每个变量的完整历史序列嵌入为一个变量 token；\n"
        "   - 在变量 token 之间使用 self-attention，捕捉多变量相关性；\n"
        "   - 对每个变量 token 应用 FFN，学习该变量的非线性时间表示。\n\n"

        "5. result：只写正文，**不要重复 `- **Result:**` 标签**。2-3 条定性结论。\n\n"

        "6. architecture：**核心部分，字数须超过 problem+method+result+experiments 总和**。\n\n"
        "   结构：\n"
        "   - `### 1. 整体思路`：一句话核心洞察 + 3-5 步数据流（含输入输出形状）\n"
        "   - `### 2. XXX模块`、`### 3. YYY模块`... 逐个展开\n\n"
        "   每个模块节奏：\n"
        "   - 开头：模块主导思想/要解决的根本问题\n"
        "   - 用 `**加粗子标题**` 拆分，**不要用 `####`**\n"
        "   - 子部分按「问题语境 → 做法 → 公式 → 符号解释 → 物理含义」写\n"
        "   - 公式前后必须有解释段落，禁止裸堆公式\n"
        "   - 每个核心模块末尾有 `**关键理解：**` 段落（1-3 条 insight）\n"
        "   - 架构部分末尾说明 Loss Function 和优化策略\n\n"
        "   禁止：❌ 一行描述  ❌ 问答体  ❌ `> [!question]`/`> [!tip]` 替代正文  ❌ 连续堆放图片\n\n"

        "7. innovations：3-4 条，每条 1 句话\n\n"

        "8. experiments：用 `- **key:** value` 行内格式，最多 3 条主要结论。\n"
        "   格式示例：\n"
        "   - **数据集:** Time-MMD、Time-IMM\n"
        "   - **Baseline:** PatchTST、iTransformer、Time-MMD\n"
        "   - **主要结论:** 模型在多个基准上全面领先，即插即用模块在多种骨干上均带来提升。\n\n"

        '9. thoughts：可留空。若写则 ≥100 字，用"我"的视角写实质思考（方法论启发/领域判断/工作关联）。\n\n'

        "10. figure_notes：选 3-5 张最重要的图，每条 1-2 句话概括核心信息。\n\n"

        "11. limitations：论文自述或可推断的局限，无则空列表。\n\n"

        "12. 元数据：topics（3-5个）、aliases（论文简称）、related_papers（3-8个经典论文）。\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "【自检】\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "- summary 有英文摘要原文\n"
        "- architecture 字数 > problem+method+result+experiments\n"
        "- 每个 core module 有 `**关键理解：**`，无 `> [!question]`/`> [!tip]` 替代正文\n"
        "- experiments 最多 3 条结论，无表号/图号/具体数值\n"
        "- thoughts 为空或 ≥100 字\n\n"

        "JSON 字段（value 可为空字符串/空列表，不要省略 key）：\n"
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
        f"{json.dumps(references[:10], ensure_ascii=False, indent=2)}\n\n"
        "用户笔记风格补充（与上面的硬规则冲突时，以上面的硬规则为准）：\n"
        f"{style_guide}"
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

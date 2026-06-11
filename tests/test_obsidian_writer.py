"""Tests for obsidian_writer.py (formatting, template rendering)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.obsidian_writer import (  # noqa: E402
    _clean_abstract,
    _cleanup_architecture,
    _cleanup_experiments,
    _cleanup_figure_table_refs,
    _cleanup_thoughts,
    _fix_latex_escapes,
    _restore_latex_backslashes,
    _format_bullets,
    _format_text,
    _format_yaml_list,
    _select_abstract,
    _strip_section_label,
    _render_template,
    render_markdown,
    load_template,
)


# ----------------------------------------------------------------------- #
# _format_bullets
# ----------------------------------------------------------------------- #

def test_format_bullets_list():
    result = _format_bullets(["a", "b", "c"])
    assert result == "- a\n- b\n- c"


def test_format_bullets_empty():
    result = _format_bullets([])
    assert result == ""


def test_format_bullets_string():
    result = _format_bullets("single item")
    assert result == "- single item"


def test_format_bullets_non_list():
    result = _format_bullets(42)
    assert result == "- 42"


# ----------------------------------------------------------------------- #
# _format_text
# ----------------------------------------------------------------------- #

def test_format_text_none():
    assert _format_text(None) == "（待补充）"


def test_format_text_string():
    assert _format_text("hello") == "hello"


def test_format_text_number():
    assert _format_text(42) == "42"


def test_format_text_empty_list():
    assert _format_text([]) == "（待补充）"


def test_format_text_list():
    result = _format_text(["line1", "line2"])
    assert "line1" in result
    assert "line2" in result


def test_format_text_dict():
    result = _format_text({"key": "val"})
    assert "**key:**" in result
    assert "val" in result


# ----------------------------------------------------------------------- #
# _format_yaml_list
# ----------------------------------------------------------------------- #

def test_format_yaml_list():
    result = _format_yaml_list(["a", "b"])
    assert result == "  - a\n  - b"


def test_format_yaml_list_empty():
    result = _format_yaml_list([])
    assert result == "  []"


def test_strip_section_label():
    assert _strip_section_label("- **Problem:** 正文", "Problem") == "正文"


def test_select_abstract_prefers_complete_candidate():
    assert _select_abstract("Short abstract", "A much more complete abstract text.") == "A much more complete abstract text."


# ----------------------------------------------------------------------- #
# _clean_abstract
# ----------------------------------------------------------------------- #

def test_clean_abstract_hyphenation():
    result = _clean_abstract("applica-\ntions")
    assert "applications" in result.split()[0]


def test_clean_abstract_month_artifact():
    result = _clean_abstract("Jan\nThis is the abstract text.")
    assert result == "This is the abstract text."


def test_clean_abstract_year_artifact():
    result = _clean_abstract("2025\nThis is the abstract.")
    assert result == "This is the abstract."


def test_clean_abstract_empty():
    assert _clean_abstract("") == ""


# ----------------------------------------------------------------------- #
# _render_template
# ----------------------------------------------------------------------- #

def test_render_template_simple():
    template = "Title: {{title}}\nYear: {{year}}"
    variables = {"title": "Test Paper", "year": "2025"}
    result = _render_template(template, variables)
    assert result == "Title: Test Paper\nYear: 2025"


def test_render_template_with_filter():
    template = "Created: {{exportDate | format('YYYY-MM-DD')}}"
    variables = {"exportDate": "2025-06-08"}
    result = _render_template(template, variables)
    assert "2025-06-08" in result


def test_render_template_missing_key():
    template = "{{title}} by {{author}}"
    variables = {"title": "Paper"}
    result = _render_template(template, variables)
    assert "Paper" in result
    assert "{{author}}" in result  # kept as-is


def test_render_template_no_placeholders():
    template = "Plain text without placeholders"
    result = _render_template(template, {})
    assert result == "Plain text without placeholders"


# ----------------------------------------------------------------------- #
# load_template (should not crash)
# ----------------------------------------------------------------------- #

def test_load_template():
    template = load_template()
    assert len(template) > 0
    assert "{{title}}" in template or "title" in template


# ----------------------------------------------------------------------- #
# _cleanup_figure_table_refs
# ----------------------------------------------------------------------- #

def test_cleanup_figure_table_refs_chinese():
    text = "如图1所示，模型效果很好。"
    result = _cleanup_figure_table_refs(text)
    assert "如图1所示" not in result
    assert "模型效果很好" in result


def test_cleanup_figure_table_refs_english():
    text = "As shown in Figure 2, the results are good."
    result = _cleanup_figure_table_refs(text)
    assert "Figure 2" not in result
    assert "the results are good" in result


def test_cleanup_figure_table_refs_table():
    text = "如表3所示，性能提升了10%。"
    result = _cleanup_figure_table_refs(text)
    assert "如表3所示" not in result


def test_cleanup_figure_table_refs_subfigure():
    text = "如图3(b)所示，MMoE包含两个子模块。"
    result = _cleanup_figure_table_refs(text)
    assert "如图3(b)所示" not in result
    assert "MMoE包含两个子模块" in result


def test_cleanup_figure_table_refs_multiple():
    text = "如图1所示和如表2所示，结果一致。"
    result = _cleanup_figure_table_refs(text)
    assert "如图1所示" not in result
    assert "如表2所示" not in result


def test_cleanup_figure_table_refs_empty():
    assert _cleanup_figure_table_refs("") == ""


# ----------------------------------------------------------------------- #
# _cleanup_experiments
# ----------------------------------------------------------------------- #

def test_cleanup_experiments_removes_metrics():
    text = "MSE=0.42, MAE降低了12.3%"
    result = _cleanup_experiments(text)
    assert "MSE=0.42" not in result
    assert "12.3%" not in result


def test_cleanup_experiments_removes_figure_refs():
    text = "如表1所示，TiMi在数据集上取得最优。"
    result = _cleanup_experiments(text)
    assert "如表1所示" not in result
    assert "TiMi在数据集上取得最优" in result


def test_cleanup_experiments_empty():
    assert _cleanup_experiments("") == ""


# ----------------------------------------------------------------------- #
# _cleanup_architecture
# ----------------------------------------------------------------------- #

def test_cleanup_architecture_removes_question_callouts():
    text = "TMoE使用文本作为输入。\n\n> [!question] 为什么选择MoE？\n> 因为文本与序列之间缺乏直接语义对应。\n\nSMoE使用时序表征。"
    result = _cleanup_architecture(text)
    assert "[!question]" not in result
    assert "TMoE使用文本作为输入" in result
    assert "SMoE使用时序表征" in result


def test_cleanup_architecture_removes_tip_callouts():
    text = "模块A的设计思路。\n\n> [!tip] 注意：这里有一个关键点\n\n模块B的设计思路。"
    result = _cleanup_architecture(text)
    assert "[!tip]" not in result
    assert "模块A的设计思路" in result
    assert "模块B的设计思路" in result


def test_cleanup_architecture_preserves_figure_refs():
    text = "如图1所示，现有三种对齐关系。"
    result = _cleanup_architecture(text)
    assert "如图1所示" in result
    assert "现有三种对齐关系" in result


def test_render_markdown_omits_empty_artifacts():
    analysis = {
        "title": "Test Paper",
        "year": "2026",
        "summary": "This is the complete original abstract.",
        "abstract": "This is incomplete-",
        "tldr": "一句话总结",
        "problem": "- **Problem:** 问题正文",
        "method": "- **Method:** 方法正文",
        "result": "- **Result:** 结果正文",
        "architecture": "### 1. 整体思路\n架构正文",
        "innovations": [],
        "experiments": "- 结论",
        "thoughts": "",
        "figure_notes": [],
        "limitations": [],
        "topics": [],
        "aliases": [],
        "related_papers": [],
    }
    result = render_markdown(analysis, "", "analysis.json")
    assert "- 无" not in result
    assert "**PDF 附件:**" not in result
    assert "进入我的研究坐标系" not in result
    assert "- **Problem:** - **Problem:**" not in result
    assert "This is the complete original abstract." in result


def test_cleanup_architecture_empty():
    assert _cleanup_architecture("") == ""


# ----------------------------------------------------------------------- #
# _cleanup_thoughts
# ----------------------------------------------------------------------- #

def test_cleanup_thoughts_empty():
    assert _cleanup_thoughts("") == ""


def test_cleanup_thoughts_filler_only():
    text = "这篇论文已经进入我的研究坐标系了"
    assert _cleanup_thoughts(text) == ""


def test_cleanup_thoughts_substantive():
    text = "我认为这篇论文的方法论启发在于它可以很好地迁移到我目前的时序预测研究中，特别是其动态图学习的思路。"
    assert _cleanup_thoughts(text) == text


def test_cleanup_thoughts_callout_with_content():
    text = "> [!quote] 重要发现\n\n我认为这个方法可以迁移到我的研究中，值得进一步探索其在多变量场景下的表现。"
    assert _cleanup_thoughts(text) == text


# ----------------------------------------------------------------------- #
# _fix_latex_escapes
# ----------------------------------------------------------------------- #

def test_fix_latex_escapes_hat():
    text = "$$\\\\hat{h}^l = \\\\text{LayerNorm}$$"
    result = _fix_latex_escapes(text)
    assert "\\\\hat" not in result
    assert "\\hat" in result
    assert "\\text" in result


def test_fix_latex_escapes_mathbb():
    text = "$$x \\\\in \\\\mathbb{R}^{L \\\\times C}$$"
    result = _fix_latex_escapes(text)
    assert "\\\\mathbb" not in result
    assert "\\mathbb" in result
    assert "\\in" in result
    assert "\\times" in result


def test_fix_latex_escapes_no_change():
    text = "$$\\hat{h} = \\text{LN}$$"
    result = _fix_latex_escapes(text)
    assert result == text


def test_fix_latex_escapes_empty():
    assert _fix_latex_escapes("") == ""


# ----------------------------------------------------------------------- #
# _restore_latex_backslashes
# ----------------------------------------------------------------------- #

def test_restore_latex_backslashes_tab():
    text = "\\t is a command"
    # Insert a literal tab before 'ext' to simulate JSON-parsed \text
    text_with_tab = text.replace("\\t", "\t")
    result = _restore_latex_backslashes(text_with_tab)
    assert "\t" not in result
    assert "\\t" in result


def test_restore_latex_backslashes_backspace():
    text = "bar{H}"
    # Insert a literal backspace before 'ar' to simulate JSON-parsed \bar
    text_with_bs = text.replace("ar", "\bar")
    result = _restore_latex_backslashes(text_with_bs)
    assert "\b" not in result
    assert "\\bar" in result


def test_restore_latex_backslashes_1016():
    text = "1016\\hat{h}1016"
    result = _restore_latex_backslashes(text)
    assert "1016" not in result
    assert "$$\\hat{h}$$" in result


def test_restore_latex_backslashes_no_change():
    text = "$$\\hat{h} = \\text{LN}$$"
    result = _restore_latex_backslashes(text)
    assert result == text


def test_restore_latex_backslashes_empty():
    assert _restore_latex_backslashes("") == ""

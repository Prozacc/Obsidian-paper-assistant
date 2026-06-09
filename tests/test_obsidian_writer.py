"""Tests for obsidian_writer.py (formatting, template rendering)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.obsidian_writer import (  # noqa: E402
    _clean_abstract,
    _format_bullets,
    _format_text,
    _format_yaml_list,
    _render_template,
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
    assert result == "- 无"


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
    assert result == "  - "


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

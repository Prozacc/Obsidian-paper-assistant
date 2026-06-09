"""Tests for llm_analyzer.py (prompt building, JSON parsing, cleaning)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.llm_analyzer import (  # noqa: E402
    _clean_authors,
    _sanitize_json_text,
    build_prompt,
    clean_analysis,
    parse_llm_json,
)


# ----------------------------------------------------------------------- #
# _clean_authors
# ----------------------------------------------------------------------- #

def test_clean_authors_basic():
    raw = ["John Smith", "Jane Doe", "University of Oxford", "Google Inc."]
    result = _clean_authors(raw)
    assert "John Smith" in result
    assert "Jane Doe" in result
    assert "University of Oxford" not in result
    assert "Google Inc." not in result


def test_clean_authors_empty():
    assert _clean_authors([]) == []


def test_clean_authors_dedup():
    raw = ["John Smith", "John Smith", "john smith"]
    result = _clean_authors(raw)
    assert len(result) == 1  # case-insensitive dedup


def test_clean_authors_too_short():
    raw = ["A", "AB"]
    result = _clean_authors(raw)
    assert result == []


def test_clean_authors_too_many_words():
    raw = ["a b c d e f g"]
    result = _clean_authors(raw)
    assert result == []


# ----------------------------------------------------------------------- #
# _sanitize_json_text
# ----------------------------------------------------------------------- #

def test_sanitize_escapes_path():
    text = r'{"path": "C:\Users\name"}'
    result = _sanitize_json_text(text)
    # The \U in \Users may be treated as invalid escape; either way it gets doubled
    assert r"\\Users" in result or r"\\\\Users" in result


def test_sanitize_valid_escapes_preserved():
    text = r'{"text": "hello\nworld\t!"}'
    result = _sanitize_json_text(text)
    assert r"\n" in result
    assert r"\t" in result


# ----------------------------------------------------------------------- #
# parse_llm_json
# ----------------------------------------------------------------------- #

def test_parse_plain_json():
    result = parse_llm_json('{"title": "Test Paper", "year": "2025"}')
    assert result["title"] == "Test Paper"
    assert result["year"] == "2025"


def test_parse_fenced_json():
    text = '```json\n{"title": "Test"}\n```'
    result = parse_llm_json(text)
    assert result["title"] == "Test"


def test_parse_with_preface():
    text = 'Here is the analysis:\n{"title": "Test"}'
    result = parse_llm_json(text)
    assert result["title"] == "Test"


def test_parse_not_json():
    import json
    with pytest.raises((ValueError, json.JSONDecodeError)):
        parse_llm_json("not json at all")
    import json


# ----------------------------------------------------------------------- #
# clean_analysis
# ----------------------------------------------------------------------- #

def test_clean_analysis_uses_llm_authors():
    data = {
        "title": "Test",
        "authors": ["Alice", "Bob"],
        "year": "2025",
        "journal": "Nature",
        "abstract": "test abstract",
        "summary": "summary",
        "tldr": "tldr",
        "problem": "problem",
        "method": "method",
        "result": "result",
        "architecture": "arch",
        "innovations": ["a", "b"],
        "experiments": "exp",
        "thoughts": "thoughts",
        "figure_notes": ["f1"],
        "limitations": ["lim"],
        "topics": ["ML"],
        "aliases": ["alias"],
        "related_papers": ["r1"],
    }
    paper_json = {"pdf": "test.pdf", "title": "Original", "authors": ["Bad Parsed"], "abstract": "abs"}
    result = clean_analysis(data, paper_json)
    assert result.authors == ["Alice", "Bob"]  # LLM authors win
    assert result.title == "Test"
    assert result.paper == "test.pdf"


def test_clean_analysis_fallback_authors():
    data = {"title": "T", "authors": []}
    paper_json = {"pdf": "test.pdf", "authors": ["John Smith"]}
    result = clean_analysis(data, paper_json)
    assert "John Smith" in result.authors


def test_clean_analysis_empty():
    data = {}
    paper_json = {"pdf": "x.pdf", "title": "T", "authors": [], "abstract": "abs"}
    result = clean_analysis(data, paper_json)
    assert result.title == "T"
    assert result.year == ""


# ----------------------------------------------------------------------- #
# build_prompt (smoke: should not crash, should contain title)
# ----------------------------------------------------------------------- #

def test_build_prompt_includes_title():
    paper = {
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models...",
        "sections": [
            {"heading": "Introduction", "text": "Recurrent neural networks..."},
        ],
        "references": ["[1] Vaswani et al., 2017"],
        "images": [
            {"caption": "Figure 1: The Transformer architecture", "figure_label": "Figure 1"},
        ],
    }
    prompt = build_prompt(paper)
    assert "Attention Is All You Need" in prompt
    assert "Transformer" in prompt
    assert "Figure 1" in prompt


def test_build_prompt_empty_paper():
    prompt = build_prompt({"title": "", "abstract": "", "sections": [], "references": [], "images": []})
    assert len(prompt) > 0

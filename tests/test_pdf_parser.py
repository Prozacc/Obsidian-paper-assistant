"""Tests for pdf_parser.py utility functions (no PDF required)."""

import sys
from pathlib import Path

import pytest

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pdf_parser import (  # noqa: E402
    _clean_lines,
    _cluster_bboxes,
    _estimate_body_font_size,
    _is_likely_figure_region,
    _is_tiny_graphic_region,
    _is_valid_heading,
    _make_figure_name,
    _overlap_ratio,
    _rect_area,
    _slugify,
)
from scripts.obsidian_writer import _simplify_journal  # noqa: E402


# ----------------------------------------------------------------------- #
# _slugify
# ----------------------------------------------------------------------- #

def test_slugify_basic():
    assert _slugify("Hello World") == "hello_world"
    assert _slugify("Figure 1: Architecture Overview") == "figure_1_architecture_overview"
    assert _slugify("!@#$%") == "figure"  # fallback for no alphanumeric chars


def test_slugify_empty():
    assert _slugify("") == "figure"  # fallback
    assert _slugify("!!!") == "figure"


def test_slugify_truncation():
    long_text = "a" * 200
    result = _slugify(long_text)
    assert len(result) <= 80


# ----------------------------------------------------------------------- #
# _clean_lines
# ----------------------------------------------------------------------- #

def test_clean_lines_basic():
    assert _clean_lines("  hello  \n\n  world  \n") == ["hello", "world"]


def test_clean_lines_empty():
    assert _clean_lines("") == []
    assert _clean_lines("   \n  \n  ") == []


# ----------------------------------------------------------------------- #
# _rect_area / _overlap_ratio
# ----------------------------------------------------------------------- #

def test_rect_area():
    import fitz
    r = fitz.Rect(0, 0, 10, 5)
    assert _rect_area(r) == 50.0


def test_overlap_ratio_full():
    import fitz
    a = fitz.Rect(0, 0, 10, 10)
    b = fitz.Rect(0, 0, 10, 10)
    assert _overlap_ratio(a, b) == 1.0


def test_overlap_ratio_none():
    import fitz
    a = fitz.Rect(0, 0, 5, 5)
    b = fitz.Rect(10, 10, 15, 15)
    assert _overlap_ratio(a, b) == 0.0


def test_overlap_ratio_partial():
    import fitz
    a = fitz.Rect(0, 0, 10, 10)
    b = fitz.Rect(5, 5, 15, 15)
    ratio = _overlap_ratio(a, b)
    assert 0.2 < ratio < 0.3  # (5*5)/(10*10) = 0.25


# ----------------------------------------------------------------------- #
# _is_tiny_graphic_region / _is_likely_figure_region
# ----------------------------------------------------------------------- #

class FakePage:
    """Fake fitz.Page for size checks."""
    def __init__(self, width=595, height=842):  # A4 portrait
        import fitz
        self.rect = fitz.Rect(0, 0, width, height)


def test_is_tiny_graphic_region():
    import fitz
    assert _is_tiny_graphic_region(fitz.Rect(0, 0, 2, 2)) is True
    assert _is_tiny_graphic_region(fitz.Rect(0, 0, 2, 10)) is True
    assert _is_tiny_graphic_region(fitz.Rect(0, 0, 100, 100)) is False


def test_is_likely_figure_region():
    import fitz
    page = FakePage()
    assert _is_likely_figure_region(fitz.Rect(50, 50, 250, 250), page) is True
    assert _is_likely_figure_region(fitz.Rect(0, 0, 20, 20), page) is False
    assert _is_likely_figure_region(fitz.Rect(0, 0, 10, 500), page) is False  # aspect > 20
    assert _is_likely_figure_region(fitz.Rect(0, 0, 590, 830), page) is False  # > 85% page


# ----------------------------------------------------------------------- #
# _cluster_bboxes
# ----------------------------------------------------------------------- #

def test_cluster_bboxes_no_overlap():
    import fitz
    bboxes = [fitz.Rect(0, 0, 10, 10), fitz.Rect(50, 50, 60, 60)]
    result = _cluster_bboxes(bboxes, x_gap=30, y_gap=30)
    assert len(result) == 2


def test_cluster_bboxes_merges_close():
    import fitz
    bboxes = [fitz.Rect(0, 0, 10, 10), fitz.Rect(15, 0, 25, 10)]
    result = _cluster_bboxes(bboxes, x_gap=30, y_gap=30)
    assert len(result) == 1


# ----------------------------------------------------------------------- #
# _is_valid_heading
# ----------------------------------------------------------------------- #

def test_is_valid_heading_numbered():
    lines_info = [
        {"text": "1. Introduction", "avg_size": 14, "max_size": 14, "is_bold": True, "y": 100},
    ]
    body_size = _estimate_body_font_size([lines_info, [{"text": "x" * 30, "avg_size": 10, "max_size": 10, "is_bold": False, "y": 200}]])
    assert _is_valid_heading("1. Introduction", lines_info[0], body_size) is True


def test_is_valid_heading_common_section():
    # "methods" in lowercase without font info → no visual cue, rejected
    assert _is_valid_heading("methods", None, 10.0) is False
    # All-uppercase common sections pass via ALLCAPS path
    assert _is_valid_heading("METHODS", None, 10.0) is True
    # Title-case common sections pass
    assert _is_valid_heading("Methods", None, 10.0) is True


def test_is_valid_heading_blacklist():
    assert _is_valid_heading("2025", None, 10.0) is False
    assert _is_valid_heading("http://example.com", None, 10.0) is False
    assert _is_valid_heading("Copyright 2025", None, 10.0) is False


def test_is_valid_heading_too_short():
    assert _is_valid_heading("AB", None, 10.0) is False


def test_is_valid_heading_too_long():
    assert _is_valid_heading("a " * 20, None, 10.0) is False


# ----------------------------------------------------------------------- #
# _make_figure_name
# ----------------------------------------------------------------------- #

def test_make_figure_name_with_label():
    result = _make_figure_name(1, 1, "Figure 2", "Figure 2: The proposed architecture")
    assert result.startswith("figure_2")


def test_make_figure_name_no_label():
    result = _make_figure_name(3, 2, None, None)
    assert result == "page_003_img_002"


# ----------------------------------------------------------------------- #
# _simplify_journal (from obsidian_writer)
# ----------------------------------------------------------------------- #

def test_simplify_journal_kdd():
    result = _simplify_journal("Proceedings of the 31st ACM SIGKDD International Conference")
    assert "KDD" in result


def test_simplify_journal_neurips():
    result = _simplify_journal("Neural Information Processing Systems 2025")
    assert "NeurIPS" in result


def test_simplify_journal_unknown():
    result = _simplify_journal("Some Random Journal")
    assert result == "Some Random Journal"


def test_simplify_journal_empty():
    assert _simplify_journal("") == ""

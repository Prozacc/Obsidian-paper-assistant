"""PDF parsing utilities based on PyMuPDF.

This module provides a small CLI and reusable helpers for extracting
text, images, and a light-weight paper structure from PDF files.

Usage:
    python tools/pdf_parser.py input.pdf --out output_dir
    python tools/pdf_parser.py input.pdf --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence, TypedDict

import fitz  # PyMuPDF


class FigureCandidate(TypedDict):
    bbox: fitz.Rect
    caption: str | None
    figure_label: str | None


# Regex for numbered / roman-numeral headings
SECTION_HEADING_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*"  # numbered headings like 1 or 2.3
    r"|[IVXLC]+"  # roman numerals
    r")\s*[:.)-]?\s+(.+)$",
    re.IGNORECASE,
)

# All-caps lines that look like headings
ALLCAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z\s&\-/]{2,}$")

REFERENCE_RE = re.compile(r"^(?:\[\d+\]|\d+\.\s+).+")
FIGURE_CAPTION_START_RE = re.compile(r"(?i)^\s*(?:fig\.|figure)\s*\d+\s*[:.)-]\s*")

# Lines that should NEVER be treated as section headings
_HEADING_BLACKLIST_RE = re.compile(
    r"^\d+(?:\.\d+)*\s*$"  # just numbers
    r"|^\d+\s*$"  # single number
    r"|^[^\w]*$"  # no words
    r"|^(?:ACM|IEEE|Proceedings|Copyright|Reference Format|CCS Concepts|arXiv:)"
    r"|(?:\d{4}\s+Copyright|\d{1,2}(?:st|nd|rd|th)\s+Conference)"
    r"|(?:http|https|www\.|doi\.org|@)"  # URLs/emails
    r"|^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"  # month lines
    r"|(?:[A-Z][a-z]+,\s+[A-Z][a-z]+,\s*(?:China|USA|Canada|UK|Germany|France))"
    r"|^\d{1,2}\s*[–-]\s*\d{1,2}$"  # page ranges
    r"|^\d+\s+pages"  # "14 pages"
    r"|^\d{4}-\d{2}-\d{2}$"  # dates
    r"|^\d{4}\s+[A-Z][a-zA-Z]+(?:,\s+[A-Z][a-zA-Z]+)*"  # e.g. "2025 Shanghai, China"
)

_MIN_HEADING_WORDS = 1
_MAX_HEADING_WORDS = 15

_COMMON_SECTIONS = {
    "introduction", "background", "methodology", "method", "methods",
    "experiments", "experiment", "results", "discussion", "related work",
    "conclusion", "conclusions", "acknowledgments", "acknowledgements",
    "references", "appendix", "abstract", "preliminaries", "problem statement",
    "model architecture", "training", "evaluation", "future work",
    "definitions", "overview", "analysis", "implementation",
}


@dataclass
class ExtractedImage:
    page_number: int
    image_index: int
    path: Path
    caption: str | None = None
    figure_label: str | None = None
    kind: str = "embedded"


@dataclass
class PaperSection:
    heading: str
    text: str
    page_start: int
    page_end: int


@dataclass
class PaperExtraction:
    pdf: str
    title: str | None
    authors: list[str]
    abstract: str | None
    keywords: list[str]
    sections: list[PaperSection]
    references: list[str]
    images: list[ExtractedImage]
    json_path: str | None = None


def extract_text(pdf_path: str | Path) -> str:
    """Extract all text from a PDF.

    This is the simplest fallback: useful for quick inspection and for papers
    that already contain a reliable text layer.
    """
    doc = fitz.open(str(pdf_path))
    try:
        texts: list[str] = []
        for page in doc:
            texts.append(str(page.get_text("text")))
        return "\n".join(texts)
    finally:
        doc.close()


def _extract_page_text_reading_order(page: fitz.Page) -> str:
    """Extract page text using a reading order heuristic.

    Many academic PDFs are laid out in two columns. This helper splits the
    page around the vertical midpoint and reassembles words in a left-column
    then right-column order.
    """
    words = [word for word in page.get_text("words") if len(word) >= 5 and len(word[4].strip()) > 0]
    if not words:
        return str(page.get_text("text"))

    page_rect = page.rect
    mid_x = page_rect.x0 + page_rect.width / 2

    left_words = [word for word in words if word[0] < mid_x]
    right_words = [word for word in words if word[0] >= mid_x]

    def sort_key(word: Any) -> tuple[float, float, float]:
        return (float(word[1]), float(word[0]), float(word[2]))

    def lines_from_words(page_words: list[Any]) -> list[str]:
        if not page_words:
            return []
        page_words = sorted(page_words, key=sort_key)
        lines: list[list[Any]] = []
        current_line: list[Any] = [page_words[0]]
        current_y = float(page_words[0][1])
        y_threshold = max(3.0, page_rect.height * 0.005)

        for word in page_words[1:]:
            if abs(float(word[1]) - current_y) <= y_threshold:
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]
                current_y = float(word[1])
        lines.append(current_line)

        rendered_lines: list[str] = []
        for line in lines:
            ordered_line = sorted(line, key=lambda w: float(w[0]))
            rendered_lines.append(" ".join(str(w[4]) for w in ordered_line).strip())
        return [line for line in rendered_lines if line]

    left_text = "\n".join(lines_from_words(left_words)).strip()
    right_text = "\n".join(lines_from_words(right_words)).strip()

    if left_text and right_text:
        return f"{left_text}\n\n{right_text}"
    return left_text or right_text or str(page.get_text("text"))


def extract_page_texts(pdf_path: str | Path) -> list[str]:
    """Extract text for each page using a column-aware reading order."""
    doc = fitz.open(str(pdf_path))
    try:
        return [_extract_page_text_reading_order(page) for page in doc]
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Figure extraction heuristics
# --------------------------------------------------------------------------- #

def _cluster_bboxes(bboxes: list[fitz.Rect], x_gap: float = 30, y_gap: float = 50) -> list[fitz.Rect]:
    """Merge spatially adjacent bounding boxes into clusters iteratively."""
    if not bboxes:
        return []
    clusters = [fitz.Rect(b) for b in bboxes]
    changed = True
    while changed:
        changed = False
        new_clusters: list[fitz.Rect] = []
        used: set[int] = set()
        for i, c1 in enumerate(clusters):
            if i in used:
                continue
            merged = fitz.Rect(c1)
            for j, c2 in enumerate(clusters):
                if i == j or j in used:
                    continue
                x_dist = max(0.0, max(merged.x0 - c2.x1, c2.x0 - merged.x1))
                y_dist = max(0.0, max(merged.y0 - c2.y1, c2.y0 - merged.y1))
                if x_dist <= x_gap and y_dist <= y_gap:
                    merged |= c2
                    used.add(j)
                    changed = True
            new_clusters.append(merged)
        clusters = new_clusters
    return clusters


def _rect_area(rect: fitz.Rect) -> float:
    return max(0.0, rect.width) * max(0.0, rect.height)


def _overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    inter = fitz.Rect(a)
    inter &= b
    inter_area = _rect_area(inter)
    smaller = min(_rect_area(a), _rect_area(b))
    if smaller <= 0:
        return 0.0
    return inter_area / smaller


def _is_tiny_graphic_region(bbox: fitz.Rect) -> bool:
    return bbox.width < 4 or bbox.height < 4 or _rect_area(bbox) < 40


def _is_likely_figure_region(bbox: fitz.Rect, page: fitz.Page) -> bool:
    """Heuristic to filter out tiny icons, decorations, and noise."""
    area = _rect_area(bbox)
    page_area = page.rect.width * page.rect.height
    if bbox.width < 35 or bbox.height < 35:
        return False
    if area < 4500:
        return False
    if area / page_area < 0.004 and area < 9000:
        return False
    aspect = bbox.width / max(bbox.height, 1)
    if aspect > 20 or aspect < 0.03:
        return False
    if area / page_area > 0.85:
        return False
    return True


def _is_meaningful_drawing_rect(rect: fitz.Rect) -> bool:
    """Keep drawing primitives that can contribute to a vector figure."""
    area = _rect_area(rect)
    if rect.width < 3 or rect.height < 3:
        return False
    if area < 50:
        return False
    return True


def _dedupe_figure_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate crops after caption-based merging."""
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.get("caption") is not None,
            _rect_area(item["bbox"]),
        ),
        reverse=True,
    )
    kept: list[dict[str, Any]] = []
    for candidate in ordered:
        bbox = candidate["bbox"]
        if any(_overlap_ratio(bbox, other["bbox"]) > 0.90 for other in kept):
            continue
        kept.append(candidate)
    return sorted(kept, key=lambda item: (item["bbox"].y0, item["bbox"].x0))


def extract_images(
    pdf_path: str | Path,
    output_dir: str | Path,
    page_texts: list[str] | None = None,
) -> list[ExtractedImage]:
    """Extract figure regions by clustering spatially adjacent image blocks."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    extracted: list[ExtractedImage] = []
    try:
        figure_dir = output_dir / "png"
        figure_dir.mkdir(parents=True, exist_ok=True)

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_text = page_texts[page_index] if page_texts and page_index < len(page_texts) else ""
            bboxes: list[fitz.Rect] = []
            # Embedded image blocks
            for block in page.get_text("dict").get("blocks", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == 1:
                    bboxes.append(fitz.Rect(block["bbox"]))
            # Vector drawings
            for d in page.get_drawings():
                if not isinstance(d, dict):
                    continue
                rect = d.get("rect")
                if rect:
                    r = fitz.Rect(rect)
                    if _is_meaningful_drawing_rect(r):
                        bboxes.append(r)

            clusters = _cluster_bboxes(bboxes, x_gap=24, y_gap=24)
            clusters.sort(key=lambda r: (r.y0, r.x0))

            captioned_candidates: dict[str, FigureCandidate] = {}
            uncaptioned_candidates: list[FigureCandidate] = []
            for cluster_bbox in clusters:
                if _is_tiny_graphic_region(cluster_bbox):
                    continue

                block_caption = _find_caption_near_bbox(page, cluster_bbox)
                block_label = _guess_label_from_caption(block_caption)

                if block_caption and block_label:
                    key = block_label
                    if key not in captioned_candidates:
                        captioned_candidates[key] = {
                            "bbox": fitz.Rect(cluster_bbox),
                            "caption": block_caption,
                            "figure_label": block_label,
                        }
                    else:
                        captioned_candidates[key]["bbox"] |= cluster_bbox
                        existing_caption = captioned_candidates[key]["caption"] or ""
                        if len(block_caption) > len(existing_caption):
                            captioned_candidates[key]["caption"] = block_caption
                    continue

                if _is_likely_figure_region(cluster_bbox, page):
                    uncaptioned_candidates.append(
                        {
                            "bbox": fitz.Rect(cluster_bbox),
                            "caption": None,
                            "figure_label": None,
                        }
                    )

            candidates = _dedupe_figure_candidates(
                list(captioned_candidates.values()) + uncaptioned_candidates
            )

            figure_num = 0
            for candidate in candidates:
                cluster_bbox = candidate["bbox"]
                if not _is_likely_figure_region(cluster_bbox, page):
                    continue

                block_caption = candidate["caption"]
                block_label = candidate["figure_label"]
                bottom_padding = 55 if block_caption else 8
                crop_rect = cluster_bbox + (-8, -8, 8, bottom_padding)
                crop_rect &= page.rect

                figure_num += 1
                base_name = _make_figure_name(page_index + 1, figure_num, block_label, block_caption)
                out_path = figure_dir / f"{base_name}.png"
                suffix = 1
                while out_path.exists():
                    out_path = figure_dir / f"{base_name}_{suffix}.png"
                    suffix += 1

                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=crop_rect, alpha=False)
                pix.save(str(out_path))

                extracted.append(
                    ExtractedImage(
                        page_number=page_index + 1,
                        image_index=figure_num,
                        path=out_path,
                        caption=block_caption,
                        figure_label=block_label,
                        kind="figure_crop",
                    )
                )
    finally:
        doc.close()
    return extracted


def _clean_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:80] if slug else "figure"


def _guess_figure_metadata(page_text: str) -> tuple[str | None, str | None]:
    match = re.search(r"(?im)^(figure|fig\.)\s*(\d+)[\.:\-]?\s*(.+)$", page_text)
    if not match:
        return None, None
    label = f"Figure {match.group(2)}"
    caption = f"{label}: {match.group(3).strip()}"
    return label, caption


def _guess_label_from_caption(caption: str | None) -> str | None:
    if not caption:
        return None
    match = re.search(r"(?i)\bfigure\s*(\d+)\b", caption)
    if match:
        return f"Figure {match.group(1)}"
    return None


def _find_caption_near_bbox(page: fitz.Page, bbox: fitz.Rect) -> str | None:
    text_dict = page.get_text("dict")
    lines: list[tuple[float, fitz.Rect, str]] = []
    expanded_x0 = bbox.x0 - 35
    expanded_x1 = bbox.x1 + 35

    def has_horizontal_overlap(line_bbox: fitz.Rect) -> bool:
        overlap = min(expanded_x1, line_bbox.x1) - max(expanded_x0, line_bbox.x0)
        if overlap > 0:
            return True
        center_x = (line_bbox.x0 + line_bbox.x1) / 2
        return expanded_x0 <= center_x <= expanded_x1

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if not isinstance(line, dict):
                continue
            line_bbox = fitz.Rect(line["bbox"])
            if (
                line_bbox.y0 >= bbox.y1
                and line_bbox.y0 <= bbox.y1 + 120
                and has_horizontal_overlap(line_bbox)
            ):
                spans = line.get("spans", [])
                text = " ".join(
                    span.get("text", "") for span in spans if isinstance(span, dict)
                )
                text = text.strip()
                if text:
                    lines.append((line_bbox.y0, line_bbox, text))
    if not lines:
        return None
    lines.sort(key=lambda item: (item[0], item[1].x0))

    caption_start = None
    for idx, (_, _, text) in enumerate(lines):
        if FIGURE_CAPTION_START_RE.search(text):
            caption_start = idx
            break

    if caption_start is None:
        return None

    caption_lines = [lines[caption_start][2]]
    last_y = lines[caption_start][0]
    for y, _, text in lines[caption_start + 1 : caption_start + 4]:
        if y - last_y > 22:
            break
        if len(caption_lines) > 1 and caption_lines[-1].rstrip().endswith("."):
            break
        if FIGURE_CAPTION_START_RE.search(text):
            break
        caption_lines.append(text)
        last_y = y

    joined = " ".join(caption_lines)
    return re.sub(r"\s+", " ", joined).strip() or None


def _make_figure_name(page_number: int, image_index: int, figure_label: str | None, caption: str | None) -> str:
    if figure_label:
        base = _slugify(figure_label)
        if caption:
            caption_slug = _slugify(caption)
            if caption_slug and caption_slug != base:
                return f"{base}_{caption_slug}"
        return base
    return f"page_{page_number:03d}_img_{image_index:03d}"


# --------------------------------------------------------------------------- #
# Font-aware text extraction                                                   #
# --------------------------------------------------------------------------- #

def _extract_lines_with_fonts(doc: fitz.Document) -> list[list[dict]]:
    """Extract per-page lines with font size and bold flags."""
    pages_info: list[list[dict]] = []
    for page in doc:
        lines_info: list[dict] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s.get("text", "") for s in spans).strip()
                if not text:
                    continue
                sizes = [s.get("size", 12) for s in spans]
                avg_size = sum(sizes) / len(sizes)
                max_size = max(sizes)
                is_bold = any((s.get("flags", 0) & 16) != 0 for s in spans)
                bbox = fitz.Rect(line["bbox"])
                lines_info.append(
                    {
                        "text": text,
                        "avg_size": avg_size,
                        "max_size": max_size,
                        "is_bold": is_bold,
                        "bbox": bbox,
                        "y": bbox.y0,
                    }
                )
        lines_info.sort(key=lambda x: x["y"])
        pages_info.append(lines_info)
    return pages_info


def _extract_title(lines_info: list[dict]) -> str | None:
    """Pick the largest-font text near the top of the first page as title."""
    if not lines_info:
        return None
    candidates = []
    for idx, info in enumerate(lines_info[:45]):
        text = info["text"]
        if len(text) < 8:
            continue
        if _HEADING_BLACKLIST_RE.search(text):
            continue
        candidates.append((idx, info))
    if not candidates:
        return None
    # Largest font size wins; tie-break by earlier y position
    best_idx, best = min(candidates, key=lambda x: (-x[1]["max_size"], x[1]["y"]))
    title_lines = [best["text"]]
    best_size = best["max_size"]
    # Merge immediately following lines with similar size (multi-line titles)
    for i in range(best_idx + 1, min(best_idx + 5, len(lines_info))):
        info = lines_info[i]
        if abs(info["max_size"] - best_size) <= 1.5 and info["y"] - best["y"] < 70:
            if not _HEADING_BLACKLIST_RE.search(info["text"]):
                title_lines.append(info["text"])
            else:
                break
        else:
            break
    return " ".join(title_lines)


def _extract_authors(lines_info: list[dict], title: str | None) -> list[str]:
    """Collect author names from lines just below the title."""
    if not lines_info:
        return []
    title_y = -1.0
    if title:
        for info in lines_info:
            if info["text"] == title or (len(title) > 20 and info["text"] in title):
                title_y = info["y"]
                break
        if title_y < 0:
            # partial match
            for info in lines_info:
                if title[:30] in info["text"]:
                    title_y = info["y"]
                    break

    authors: list[str] = []
    seen: set[str] = set()
    for info in lines_info:
        if title_y >= 0:
            if info["y"] <= title_y:
                continue
            if info["y"] > title_y + 220:
                break
        text = info["text"]
        if len(text) > 250 or len(text) < 3:
            continue
        lower = text.lower()
        if any(tok in lower for tok in ("abstract", "keywords", "introduction")):
            continue
        if "@" in text or "http" in text:
            continue
        # Skip obvious affiliation lines
        if any(tok in lower for tok in (
            "university", "school", "institute", "college", "laboratory",
            "lab", "email", "department", "center", "centre", "corporation",
            "inc.", "ltd.", "org", "google", "microsoft", "amazon",
        )):
            continue
        if _HEADING_BLACKLIST_RE.search(text):
            continue
        # Author lines are usually moderate size
        if info["avg_size"] < 8 or info["avg_size"] > 16:
            continue
        parts = re.split(r"\s{2,}|,\s*|\band\b|\*", text, flags=re.IGNORECASE)
        for p in parts:
            p = p.strip().strip("†‡*•")
            if not p or len(p) < 3 or len(p) > 40:
                continue
            if p in seen:
                continue
            # Simple name heuristic: mostly letters/spaces/hyphens, 1-4 words
            if re.match(r"^[A-Za-z\s\-\.']+$", p) and len(p.split()) <= 5:
                seen.add(p)
                authors.append(p)
    return authors


def _extract_abstract(text: str) -> str | None:
    match = re.search(
        r"(?is)\babstract\b\s*[:\-]?\s*(.+?)(?:\n\s*keywords\b|\n\s*\d+(?:\.\d+)?\s+[A-Z]|"
        r"\n\s*introduction\b|\n\s*1\s+introduction\b|\n\s*I\s+INTRODUCTION\b|\Z)",
        text,
    )
    if not match:
        return None
    abstract = match.group(1).strip()
    abstract = re.split(r"\n\s*\d+\s+[A-Z][a-z]", abstract, maxsplit=1)[0]
    return abstract or None


def _extract_keywords(text: str) -> list[str]:
    match = re.search(
        r"(?is)\bkeywords?\b\s*[:\-]?\s*(.+?)(?:\n\s*\d+(?:\.\d+)?\s+[A-Z]|"
        r"\n\s*introduction\b|\n\s*1\s+introduction\b|\n\s*I\s+INTRODUCTION\b|\Z)",
        text,
    )
    if not match:
        return []
    raw = match.group(1).strip()
    # Limit to first line to avoid sucking in references / body text
    raw = raw.split("\n")[0]
    keywords = [item.strip() for item in re.split(r"[,;]", raw) if item.strip()]
    return keywords


# --------------------------------------------------------------------------- #
# Section splitting with font-aware validation                                 #
# --------------------------------------------------------------------------- #

def _estimate_body_font_size(lines_info: list[list[dict]]) -> float:
    sizes: list[float] = []
    for page_lines in lines_info:
        for info in page_lines:
            text = info["text"]
            if len(text) > 20 and not _HEADING_BLACKLIST_RE.search(text):
                sizes.append(round(info["avg_size"], 1))
    if not sizes:
        return 10.0
    return Counter(sizes).most_common(1)[0][0]


def _is_valid_heading(text: str, line_info: dict | None, body_font_size: float) -> bool:
    if not text or len(text) < 3:
        return False
    if _HEADING_BLACKLIST_RE.search(text):
        return False
    word_count = len(text.split())
    if word_count < _MIN_HEADING_WORDS or word_count > _MAX_HEADING_WORDS:
        return False

    text_lower = text.lower()
    is_common = text_lower in _COMMON_SECTIONS

    m = SECTION_HEADING_RE.match(text)
    if m:
        content = m.group(1)
        # Heading content must contain at least one letter
        if not re.search(r"[a-zA-Z]", content):
            return False
        # Skip lines that look like author affiliations / URLs
        if "@" in content or "http" in content.lower():
            return False
        return True

    # All-caps lines
    if text.isupper():
        if is_common:
            return True
        if line_info and line_info["max_size"] > body_font_size * 1.05:
            return True
        return False

    # Title-case or capitalised short phrases
    if (text.istitle() or (text and text[0].isupper())) and word_count <= 4:
        if is_common:
            return True
        if line_info and line_info["max_size"] > body_font_size * 1.08:
            return True

    return False


def _split_sections(
    page_texts: list[str], lines_info: list[list[dict]]
) -> tuple[list[PaperSection], list[str]]:
    body_font_size = _estimate_body_font_size(lines_info)
    sections: list[PaperSection] = []
    references: list[str] = []
    current_heading = "Document"
    current_lines: list[str] = []
    current_start = 1

    for page_number, (page_text, page_lines) in enumerate(zip(page_texts, lines_info), start=1):
        line_map: dict[str, dict] = {}
        for info in page_lines:
            if info["text"] not in line_map:
                line_map[info["text"]] = info

        for line in _clean_lines(page_text):
            lower = line.lower()

            if lower == "references":
                if current_lines:
                    sections.append(
                        PaperSection(
                            heading=current_heading,
                            text="\n".join(current_lines).strip(),
                            page_start=current_start,
                            page_end=page_number,
                        )
                    )
                    current_lines = []
                current_heading = "References"
                current_start = page_number
                continue

            if current_heading == "References":
                if REFERENCE_RE.match(line):
                    references.append(line)
                elif references:
                    references[-1] = f"{references[-1]} {line}"
                continue

            line_info = line_map.get(line)
            if _is_valid_heading(line, line_info, body_font_size):
                if current_lines:
                    sections.append(
                        PaperSection(
                            heading=current_heading,
                            text="\n".join(current_lines).strip(),
                            page_start=current_start,
                            page_end=page_number,
                        )
                    )
                    current_lines = []
                current_heading = line.strip()
                current_start = page_number
                continue

            current_lines.append(line)

    if current_lines and current_heading != "References":
        sections.append(
            PaperSection(
                heading=current_heading,
                text="\n".join(current_lines).strip(),
                page_start=current_start,
                page_end=max(1, len(page_texts)),
            )
        )

    return sections, references


# --------------------------------------------------------------------------- #
# Main parser                                                                   #
# --------------------------------------------------------------------------- #

def parse_paper_pdf(pdf_path: str | Path, output_dir: str | Path) -> PaperExtraction:
    """Parse a paper PDF into a light-weight structured representation."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paper_dir = output_dir / pdf_path.stem
    paper_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    try:
        page_texts = [_extract_page_text_reading_order(page) for page in doc]
        lines_info = _extract_lines_with_fonts(doc)
    finally:
        doc.close()

    full_text = "\n\n".join(page_texts)

    images = extract_images(pdf_path, paper_dir / "images", page_texts=page_texts)
    sections, references = _split_sections(page_texts, lines_info)

    first_page_lines = lines_info[0] if lines_info else []
    title = _extract_title(first_page_lines)
    authors = _extract_authors(first_page_lines, title)

    if not title and page_texts:
        naive_lines = _clean_lines(page_texts[0])
        for nl in naive_lines:
            if len(nl) > 15 and not _HEADING_BLACKLIST_RE.search(nl):
                title = nl
                break

    json_path = paper_dir / f"{pdf_path.stem}.json"
    extraction = PaperExtraction(
        pdf=str(pdf_path),
        title=title,
        authors=authors,
        abstract=_extract_abstract(full_text),
        keywords=_extract_keywords(full_text),
        sections=sections,
        references=references,
        images=images,
        json_path=str(json_path),
    )
    json_path.write_text(
        json.dumps(extraction_to_dict(extraction), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return extraction


def extraction_to_dict(extraction: PaperExtraction) -> dict:
    data = asdict(extraction)
    data["sections"] = [asdict(section) for section in extraction.sections]
    data["images"] = [
        {
            "page_number": image.page_number,
            "image_index": image.image_index,
            "path": str(image.path),
            "caption": image.caption,
            "figure_label": image.figure_label,
        }
        for image in extraction.images
    ]
    return data


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract text/images from PDF using PyMuPDF")
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Output directory")
    parser.add_argument("--text-only", action="store_true", help="Only extract text")
    parser.add_argument("--images-only", action="store_true", help="Only extract images")
    parser.add_argument("--json", action="store_true", help="Output structured paper JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if sum(bool(flag) for flag in (args.text_only, args.images_only, args.json)) > 1:
        parser.error("--text-only, --images-only and --json cannot be used together")

    if args.text_only:
        text = extract_text(args.pdf)
        args.out.mkdir(parents=True, exist_ok=True)
        text_path = args.out / f"{args.pdf.stem}.txt"
        text_path.write_text(text, encoding="utf-8")
        print(json.dumps({"text_path": str(text_path)}, ensure_ascii=False, indent=2))
        return 0

    if args.images_only:
        images = extract_images(args.pdf, args.out / "images")
        print(
            json.dumps(
                {
                    "image_count": len(images),
                    "images": [str(img.path) for img in images],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    extraction = parse_paper_pdf(args.pdf, args.out)
    print(json.dumps(extraction_to_dict(extraction), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

"""Improved figure extraction for academic PDFs.

Uses PyMuPDF with high-resolution rendering and smarter figure detection
to avoid full-page captures and mixed content regions.

Usage:
    python scripts/extract_figures_v2.py input.pdf --out output_dir
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

FIGURE_CAPTION_RE = re.compile(r"(?i)^\s*(?:fig\.|figure)\s*\d+")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:80] if slug else "figure"


def _find_caption_near(page: fitz.Page, bbox: fitz.Rect) -> str | None:
    """Find figure caption text near a bounding box."""
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_bbox = fitz.Rect(line["bbox"])
            # Caption should be below the figure and horizontally overlap
            if (
                line_bbox.y0 >= bbox.y1
                and line_bbox.y0 <= bbox.y1 + 100
                and abs(line_bbox.x0 - bbox.x0) < 50
            ):
                text = " ".join(
                    s.get("text", "") for s in line.get("spans", [])
                ).strip()
                if FIGURE_CAPTION_RE.search(text):
                    return text
    return None


def _get_text_regions(page: fitz.Page) -> list[fitz.Rect]:
    """Get bounding boxes of all text blocks on the page."""
    regions = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") == 0:  # text block
            regions.append(fitz.Rect(block["bbox"]))
    return regions


def _overlaps_any(rect: fitz.Rect, others: list[fitz.Rect], threshold: float = 0.5) -> bool:
    """Check if rect overlaps significantly with any rectangle in others."""
    for other in others:
        inter = fitz.Rect(rect) & other
        inter_area = max(0, inter.width) * max(0, inter.height)
        rect_area = max(0, rect.width) * max(0, rect.height)
        if rect_area > 0 and inter_area / rect_area > threshold:
            return True
    return False


def extract_figures_v2(
    pdf_path: str | Path,
    output_dir: str | Path,
    dpi: int = 300,
    zoom: int = 4,
) -> list[dict]:
    """Extract figures using high-res page rendering + text-region masking.

    Strategy:
    1. Render each page at high DPI via PyMuPDF
    2. Find all text blocks (these are NOT figures)
    3. Find embedded images and vector drawing clusters
    4. Filter: skip regions that overlap heavily with text
    5. Filter: skip full-page or near-full-page regions
    6. Crop and save at high resolution
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    figure_dir = output_dir / "png"
    figure_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    extracted = []

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height

            # --- Collect all graphical elements ---
            bboxes: list[fitz.Rect] = []

            # Embedded raster images
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    rects = page.get_image_rects(xref)
                    for rect in rects:
                        if not rect.is_empty:
                            bboxes.append(fitz.Rect(rect))
                except Exception:
                    pass

            # Vector drawings (paths, lines, curves)
            for d in page.get_drawings():
                rect = d.get("rect")
                if not rect:
                    continue
                r = fitz.Rect(rect)
                area = r.width * r.height
                if r.width < 5 or r.height < 5 or area < 100:
                    continue
                bboxes.append(r)

            if not bboxes:
                continue

            # --- Cluster nearby graphical elements ---
            clusters = _cluster_rects(bboxes, x_gap=20, y_gap=20)

            # --- Get text regions for filtering ---
            text_regions = _get_text_regions(page)

            # --- Process each cluster ---
            figure_num = 0
            for cluster in clusters:
                area = cluster.width * cluster.height
                area_ratio = area / page_area

                # Skip tiny regions
                if cluster.width < 40 or cluster.height < 40:
                    continue
                if area < 3000:
                    continue

                # Skip full-page or near-full-page regions
                if area_ratio > 0.50:
                    continue

                # Skip wide horizontal strips (likely headers/footers/page numbers)
                aspect = cluster.width / max(cluster.height, 1)
                if cluster.width > page_rect.width * 0.85 and cluster.height < page_rect.height * 0.12:
                    continue

                # Skip extreme aspect ratios
                if aspect > 12 or aspect < 0.1:
                    continue

                # Skip if region is mostly text (>50% overlap with text blocks)
                if _overlaps_any(cluster, text_regions, threshold=0.50):
                    continue

                # Find caption
                caption = _find_caption_near(page, cluster)
                label = None
                if caption:
                    m = re.search(r"(?i)\bfigure\s*(\d+)\b", caption)
                    if m:
                        label = f"Figure {m.group(1)}"

                # Add small padding
                pad = 6
                crop_rect = fitz.Rect(
                    max(0, cluster.x0 - pad),
                    max(0, cluster.y0 - pad),
                    min(page_rect.width, cluster.x1 + pad),
                    min(page_rect.height, cluster.y1 + pad),
                )

                figure_num += 1
                if label:
                    base_name = _slugify(label)
                    if caption:
                        cap_slug = _slugify(caption)
                        if cap_slug and cap_slug != base_name:
                            base_name = f"{base_name}_{cap_slug}"
                else:
                    base_name = f"page_{page_num:03d}_img_{figure_num:03d}"

                out_path = figure_dir / f"{base_name}.png"
                suffix = 1
                while out_path.exists():
                    out_path = figure_dir / f"{base_name}_{suffix}.png"
                    suffix += 1

                # Render at high resolution
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, clip=crop_rect, alpha=False)
                pix.save(str(out_path))

                extracted.append({
                    "page_number": page_num,
                    "image_index": figure_num,
                    "path": str(out_path),
                    "caption": caption,
                    "figure_label": label,
                })

    finally:
        doc.close()

    return extracted


def _cluster_rects(
    rects: list[fitz.Rect], x_gap: float = 20, y_gap: float = 20
) -> list[fitz.Rect]:
    """Merge spatially adjacent rectangles into clusters."""
    if not rects:
        return []
    clusters = [fitz.Rect(r) for r in rects]
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


def main():
    parser = argparse.ArgumentParser(description="Improved figure extraction")
    parser.add_argument("pdf", type=Path, help="Input PDF")
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--zoom", type=int, default=4)
    args = parser.parse_args()

    out_dir = args.out / "images"
    figures = extract_figures_v2(args.pdf, out_dir, dpi=args.dpi, zoom=args.zoom)
    print(json.dumps({"count": len(figures), "figures": figures}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

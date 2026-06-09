"""Fetch latest papers from arXiv and process them.

Usage:
    python scripts/fetch_arxiv.py                    # Default: last 7 days, max 5 papers
    python scripts/fetch_arxiv.py --days 14 --max 10  # Last 14 days, max 10 papers
    python scripts/fetch_arxiv.py --query "time series forecasting" --max 3
"""

from __future__ import annotations

import argparse
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

def _build_ssl_context() -> ssl.SSLContext:
    """Create a verified SSL context with graceful fallback.

    On systems with a missing CA bundle (some minimal Docker images, old
    Windows installs), falls back to ``certifi`` if installed.
    """
    try:
        ctx = ssl.create_default_context()
        # Quick smoke test: can we actually verify?
        return ctx
    except (ssl.SSLError, OSError):
        pass

    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        return ctx
    except ImportError:
        pass

    raise RuntimeError(
        "SSL verification unavailable. Install certifi (`pip install certifi`) "
        "or ensure your system CA bundle is configured."
    )

_SSL_CTX = _build_ssl_context()

# Allow running as `python scripts/fetch_arxiv.py` from skill root
_SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

ARXIV_API = "http://export.arxiv.org/api/query"
DEFAULT_QUERY = (
    'cat:cs.LG AND (abs:"time series" OR abs:"temporal forecasting" '
    'OR abs:"time series forecasting" OR abs:"multivariate time series")'
)
DOWNLOAD_DIR = Path(os.getenv("PAPER_DOWNLOAD_DIR", "./papers"))


def search_arxiv(
    query: str = DEFAULT_QUERY,
    max_results: int = 10,
    days: int = 7,
) -> list[dict]:
    """Search arXiv and return recent papers."""
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results * 3,  # fetch more, then filter by date
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    print(f"Searching arXiv: {query[:60]}...")

    req = urllib.request.Request(url, headers={"User-Agent": "PaperAssistant/1.0"})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    cutoff = datetime.utcnow() - timedelta(days=days)
    papers: list[dict] = []

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        pdf_link = None
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_link = link.get("href")
                break

        if not (title_el is not None and published_el is not None and pdf_link):
            continue

        title = " ".join(title_el.text.strip().split())
        published = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
        published_naive = published.replace(tzinfo=None)

        if published_naive < cutoff:
            continue

        authors = []
        for author in entry.findall("atom:author", ns):
            name_el = author.find("atom:name", ns)
            if name_el is not None:
                authors.append(name_el.text.strip())

        abstract = " ".join(summary_el.text.strip().split()) if summary_el is not None else ""

        papers.append({
            "title": title,
            "authors": authors,
            "published": published_naive.strftime("%Y-%m-%d"),
            "pdf_url": pdf_link,
            "abstract": abstract[:200],
        })

        if len(papers) >= max_results:
            break

    return papers


def download_pdf(url: str, dest_dir: Path) -> Path:
    """Download a PDF from arXiv."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    dest = dest_dir / filename

    if dest.exists():
        print(f"  Exists: {dest.name}")
        return dest

    print(f"  Downloading: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "PaperAssistant/1.0"})
    with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
        dest.write_bytes(resp.read())
    print(f"  -> {dest}")
    return dest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch and download latest arXiv papers")
    parser.add_argument("--query", type=str, default=DEFAULT_QUERY, help="arXiv search query")
    parser.add_argument("--max", type=int, default=5, help="Max papers to download")
    parser.add_argument("--days", type=int, default=7, help="Look back N days")
    parser.add_argument("--dir", type=Path, default=DOWNLOAD_DIR, help="Download directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = build_arg_parser().parse_args(argv)

    # Search
    papers = search_arxiv(query=args.query, max_results=args.max, days=args.days)
    if not papers:
        print("No recent papers found.")
        return 0

    print(f"\nFound {len(papers)} papers:\n")
    for i, p in enumerate(papers, 1):
        print(f"  {i}. [{p['published']}] {p['title']}")
        print(f"     {p['authors'][0]} et al." if p['authors'] else "")
    print()

    # Download
    downloaded: list[Path] = []
    for i, p in enumerate(papers, 1):
        print(f"[{i}/{len(papers)}] {p['title']}")
        try:
            pdf_path = download_pdf(p["pdf_url"], args.dir)
            downloaded.append(pdf_path)
        except Exception as e:
            print(f"  Failed: {e}")

        # Be nice to arXiv API
        if i < len(papers):
            time.sleep(3)

    print(f"\nDone: {len(downloaded)}/{len(papers)} papers downloaded")
    for p in downloaded:
        print(f"  {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

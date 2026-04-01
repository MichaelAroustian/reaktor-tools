"""
inspect_toc.py — Detect the Table of Contents start page and page count in a PDF.
Useful for determining --toc-start and --toc-pages values for pdf_to_chapters.py.

Usage:
    # Basic — auto-detect and report
    python inspect_toc.py ~/Downloads/Reaktor_6_Building_in_Core.pdf

    # Show raw blocks from detected ToC pages (useful if pdf_to_chapters.py finds 0 entries)
    python inspect_toc.py ~/Downloads/Reaktor_6_Building_in_Core.pdf --debug

    # Increase search range if ToC not found in first 20 pages
    python inspect_toc.py ~/Downloads/some_other.pdf --search-limit 50

Options:
    pdf                 Path to the PDF file
    --search-limit INT  How many pages to scan from the start (default: 20)
    --debug             Print raw blocks from detected ToC pages

Requirements:
    pip install pymupdf
"""

import fitz
import re
import argparse
from pathlib import Path


def is_toc_page(page):
    """Return True if this page looks like a ToC page."""
    text = page.get_text()
    has_toc_heading = bool(re.search(r'\btable of contents\b|\bcontents\b', text.lower()))
    dot_leader_lines = len(re.findall(r'(?:\.{4,}|(?:\. ){3,}\.)\s*\w+', text))
    return has_toc_heading or dot_leader_lines >= 3


def find_toc(doc, search_limit=20):
    """
    Scan the first `search_limit` pages to find where the ToC starts
    and how many pages it spans.
    Returns (toc_start, toc_pages) — both 1-indexed.
    """
    toc_start = None
    toc_pages = 0

    for i in range(min(search_limit, len(doc))):
        if is_toc_page(doc[i]):
            if toc_start is None:
                toc_start = i + 1  # convert to 1-indexed
            toc_pages += 1
        elif toc_start is not None:
            break

    return toc_start, toc_pages


def print_raw_blocks(doc, toc_start, toc_pages, blocks_per_page=10):
    """Print raw text blocks from ToC pages for format diagnosis."""
    print(f"\n--- RAW BLOCKS (first {blocks_per_page} text blocks per page) ---")
    for page_idx in range(toc_start - 1, toc_start - 1 + toc_pages):
        page = doc[page_idx]
        blocks = page.get_text("blocks", sort=True)
        print(f"\n=== Page {page_idx + 1} ===")
        count = 0
        for i, block in enumerate(blocks):
            if block[6] == 0:  # text only
                print(f"\nBlock {i}:")
                print(repr(block[4]))
                count += 1
                if count >= blocks_per_page:
                    remaining = sum(1 for b in blocks[i+1:] if b[6] == 0)
                    if remaining:
                        print(f"\n  ... {remaining} more blocks on this page")
                    break


def main():
    parser = argparse.ArgumentParser(
        description='Detect ToC start page and page count in a PDF.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('pdf', help='Path to the PDF file')
    parser.add_argument(
        '--search-limit',
        type=int,
        default=20,
        help='How many pages to scan from the start (default: 20)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print raw blocks from detected ToC pages'
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    total = len(doc)
    print(f"PDF: {pdf_path.name} ({total} pages)")

    toc_start, toc_pages = find_toc(doc, args.search_limit)

    if toc_start is None:
        print(f"ToC not found in the first {args.search_limit} pages.")
        print("Try increasing --search-limit")
    else:
        print(f"ToC starts: page {toc_start}")
        print(f"ToC pages:  {toc_pages}")
        print(f"\nUse with pdf_to_chapters.py:")
        print(f"  --toc-start {toc_start} --toc-pages {toc_pages}")

        if args.debug:
            print_raw_blocks(doc, toc_start, toc_pages)


if __name__ == '__main__':
    main()

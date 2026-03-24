"""
inspect_toc.py — Detect the Table of Contents start page and page count in a PDF.
Useful for determining --toc-start and --toc-pages values for pdf_to_clean_html.py.

Usage:
    python inspect_toc.py ~/Downloads/Reaktor_6_Building_in_Core.pdf

Output example:
    PDF: Reaktor_6_Building_in_Core.pdf (162 pages)
    ToC starts: page 4
    ToC pages:  5

    Use with pdf_to_clean_html.py:
      --toc-start 4 --toc-pages 5

Requirements:
    pip install pymupdf
"""

import fitz
import re
import argparse
from pathlib import Path


def is_toc_page(page):
    text = page.get_text()
    has_toc_heading = bool(re.search(r'\btable of contents\b|\bcontents\b', text.lower()))
    # Match both styles: '......' and '. . . . .'
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
            # We've passed the ToC
            break

    return toc_start, toc_pages


def main():
    parser = argparse.ArgumentParser(
        description='Detect ToC start page and page count in a PDF.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'pdf',
        help='Path to the PDF file'
    )
    parser.add_argument(
        '--search-limit',
        type=int,
        default=20,
        help='How many pages to scan from the start (default: 20)'
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
        print(f"\nUse with pdf_to_clean_html.py:")
        print(f"  --toc-start {toc_start} --toc-pages {toc_pages}")


if __name__ == '__main__':
    main()
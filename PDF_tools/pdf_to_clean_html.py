"""
pdf_to_clean_html.py — Convert a PDF to clean per-page HTML with a ToC index.

Usage:
    # Basic — output goes to PDF parent dir / PDF stem
    python pdf_to_clean_html.py ~/Downloads/Reaktor_6_Building_in_Core.pdf

    # Custom output directory
    python pdf_to_clean_html.py ~/Downloads/Reaktor_6_Building_in_Core.pdf -o ~/reaktor-docs

    # Different ToC location (for other PDFs)
    python pdf_to_clean_html.py ~/Downloads/some_other.pdf --toc-start 3 --toc-pages 2

Options:
    pdf                 Path to the PDF file
    -o, --output        Output directory (default: PDF parent dir / PDF stem)
    --toc-start INT     Page number where ToC starts (default: 4)
    --toc-pages INT     Number of ToC pages to parse (default: 5)

Output structure:
    <output>/
    ├── index.html              ToC with section links
    ├── page-index.html         Full page list fallback
    └── <pdf-stem>/
        ├── page-001.html
        ├── page-002.html
        └── page-NNN.html

Requirements:
    pip install pymupdf
"""

import fitz
import re
import argparse
from pathlib import Path


def parse_toc(page):
    """Parse ToC entries from a page into list of (section, title, page_num).
    Handles two formats:
      Format 1: section + 'title .... page_num'  (Reaktor 6 style)
      Format 2: section + title + page_num        (Reaktor 5.5 style)
    """
    blocks = page.get_text("blocks", sort=True)
    entries = []

    for block in blocks:
        if block[6] != 0:
            continue

        lines = [l.strip() for l in block[4].splitlines() if l.strip()]
        if len(lines) < 2:
            continue

        # First non-empty line should be the section number
        section = lines[0]
        if not re.match(r'^\d+(\.\d+)*$', section):
            continue

        # Format 1: "title .... page_num" or "title . . . . page_num" on one line
        if len(lines) == 2:
            m = re.match(r'^(.+?)\s*(?:\.{2,}|(?:\. ){2,}\.)\s*(\d+)$', lines[1])
            if m:
                entries.append((section, m.group(1).strip(), int(m.group(2))))

        # Format 2: title on line 2, page_num on line 3 (no dot leaders)
        elif len(lines) >= 3:
            title = lines[1]
            m = re.match(r'^(\d+)$', lines[2])
            if m:
                entries.append((section, title, int(m.group(1))))

    return entries


def build_toc_index(entries, pdf_stem, output_dir):
    """Build a section-level index HTML from parsed ToC entries."""
    lines = [
        '<!DOCTYPE html>',
        '<html>',
        '<head><meta charset="utf-8">',
        f'<title>{pdf_stem} — Table of Contents</title>',
        '<style>',
        '  body { font-family: sans-serif; max-width: 900px; margin: 2em auto; }',
        '  .section-1 { font-size: 1.2em; font-weight: bold; margin-top: 1.5em; }',
        '  .section-2 { margin-left: 1.5em; }',
        '  .section-3 { margin-left: 3em; font-size: 0.95em; }',
        '  a { text-decoration: none; color: #2255aa; }',
        '  a:hover { text-decoration: underline; }',
        '  .page-num { color: #888; font-size: 0.85em; margin-left: 0.5em; }',
        '</style>',
        '</head><body>',
        f'<h1>{pdf_stem}</h1>',
        '<h2>Table of Contents</h2>',
        '<ul style="list-style:none; padding:0;">',
    ]

    for section, title, page_num in entries:
        depth = section.count('.') + 1
        css_class = f'section-{min(depth, 3)}'
        filename = f"{pdf_stem}/page-{page_num:03d}.html"
        lines.append(
            f'<li class="{css_class}">'
            f'<a href="{filename}">{section} {title}</a>'
            f'<span class="page-num">p.{page_num}</span>'
            f'</li>'
        )

    lines.append('</ul>')
    lines.append('<hr><p><a href="page-index.html">Full page index</a></p>')
    lines.append('</body></html>')

    toc_file = output_dir / 'index.html'
    toc_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"ToC index written: {toc_file}")


def build_page_index(total, pdf_stem, output_dir):
    """Build a simple full page index as fallback."""
    lines = [
        '<!DOCTYPE html><html><body>',
        f'<h1>{pdf_stem} — All Pages</h1>',
        '<p><a href="index.html">Table of Contents</a></p>',
        '<ul>',
    ]
    for i in range(1, total + 1):
        lines.append(
            f'<li><a href="{pdf_stem}/page-{i:03d}.html">Page {i}</a></li>'
        )
    lines.append('</ul></body></html>')

    page_index_file = output_dir / 'page-index.html'
    page_index_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Page index written: {page_index_file}")


def pdf_to_clean_html(pdf_path, output_dir=None, toc_start=4, toc_pages=5):
    pdf_path = Path(pdf_path).expanduser()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir = Path(output_dir).expanduser() if output_dir else pdf_path.parent / pdf_path.stem
    pages_dir = output_dir / pdf_path.stem
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = len(doc)
    pdf_stem = pdf_path.stem

    print(f"Processing '{pdf_stem}' — {total} pages")
    print(f"Output: {output_dir}")

    # --- Pass 1: Convert each page to clean HTML ---
    for i, page in enumerate(doc):
        page_num = i + 1
        filename = f"page-{page_num:03d}.html"
        blocks = page.get_text("blocks", sort=True)

        lines = [
            '<!DOCTYPE html>',
            '<html><head><meta charset="utf-8">',
            f'<title>{pdf_stem} — Page {page_num}</title>',
            '</head><body>',
            '<p>',
            f'<a href="../index.html">ToC</a> | ',
            f'<a href="../page-index.html">All Pages</a>',
        ]

        if page_num > 1:
            lines.append(f' | <a href="page-{page_num-1:03d}.html">← Previous</a>')
        if page_num < total:
            lines.append(f' | <a href="page-{page_num+1:03d}.html">Next →</a>')
        lines.append(f' | <em>Page {page_num} of {total}</em>')
        lines.append('</p><hr>')

        for block in blocks:
            if block[6] == 0:
                text = block[4].strip()
                if text:
                    escaped = text.replace('&', '&amp;').replace('<', '&lt;')
                    for para in escaped.split('\n'):
                        para = para.strip()
                        if para:
                            lines.append(f'<p>{para}</p>')

        lines.append('</body></html>')
        (pages_dir / filename).write_text('\n'.join(lines), encoding='utf-8')
        print(f"  Page {page_num}/{total}", end='\r')

    print(f"\nPass 1 complete — {total} pages written")

    # --- Pass 2: Parse ToC ---
    toc_start_idx = toc_start - 1  # convert to 0-indexed
    toc_end_idx = toc_start_idx + toc_pages
    print(f"Parsing ToC from pages {toc_start}–{toc_start + toc_pages - 1}...")

    toc_entries = []
    for page_idx in range(toc_start_idx, min(toc_end_idx, total)):
        entries = parse_toc(doc[page_idx])
        print(f"  Page {page_idx + 1}: {len(entries)} entries found")
        toc_entries.extend(entries)

    if toc_entries:
        print(f"  Total: {len(toc_entries)} ToC entries")
        build_toc_index(toc_entries, pdf_stem, output_dir)
    else:
        print("  Warning: no ToC entries found — generating page index only")

    build_page_index(total, pdf_stem, output_dir)

    print(f"\nDone.")
    print(f"  ToC index : {output_dir}/index.html")
    print(f"  Page index: {output_dir}/page-index.html")
    print(f"  Pages     : {pages_dir}/page-NNN.html")


def main():
    parser = argparse.ArgumentParser(
        description='Convert a PDF to clean per-page HTML with a ToC index.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'pdf',
        help='Path to the PDF file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: PDF parent dir / PDF stem)',
        default=None
    )
    parser.add_argument(
        '--toc-start',
        type=int,
        default=4,
        help='Page number where ToC starts (default: 4)'
    )
    parser.add_argument(
        '--toc-pages',
        type=int,
        default=5,
        help='Number of ToC pages to parse (default: 5)'
    )

    args = parser.parse_args()
    pdf_to_clean_html(
        args.pdf,
        output_dir=args.output,
        toc_start=args.toc_start,
        toc_pages=args.toc_pages
    )


if __name__ == '__main__':
    main()
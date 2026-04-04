"""
pdf_to_chapters.py — Split a PDF into plain text files per chapter with an HTML index.

Usage:
    # Basic — auto-detect ToC, output to PDF parent dir / PDF stem
    python pdf_to_chapters.py ~/Downloads/Reaktor_6_Building_in_Core.pdf

    # Custom output directory
    python pdf_to_chapters.py ~/Downloads/Reaktor_6_Building_in_Core.pdf -o ~/reaktor-docs

    # Specify ToC location manually
    python pdf_to_chapters.py ~/Downloads/some_other.pdf --toc-start 5 --toc-pages 4

    # PDF with roman numeral front matter (e.g. 12 pages before page 1)
    python pdf_to_chapters.py ~/Downloads/VAFilterDesign_2.1.0.pdf --toc-start 5 --toc-pages 4 --page-offset 12

    # Debug ToC parsing — print raw blocks and exit without generating files
    python pdf_to_chapters.py ~/Downloads/some_other.pdf --toc-start 5 --toc-pages 4 --debug

Known settings:
    Reaktor 6 Building in Primary: --toc-start 4  --toc-pages 11  --page-offset 0
    Reaktor 6 Building in Core:    --toc-start 4  --toc-pages 5   --page-offset 0
    Reaktor 5.5 Core Reference:    --toc-start 4  --toc-pages 12  --page-offset 0
    VA Filter Design 2.1.0:        --toc-start 5  --toc-pages 4   --page-offset 12

Options:
    pdf                 Path to the PDF file
    -o, --output        Output directory (default: PDF parent dir / PDF stem)
    --toc-start INT     Page number where ToC starts
    --toc-pages INT     Number of ToC pages to parse
    --page-offset INT   Number of front matter pages before printed page 1 (default: 0)
    --search-limit INT  How many pages to scan for ToC in auto-detect (default: 20)
    --debug             Print raw ToC blocks and parsed entries, then exit

Output structure:
    <o>/
    ├── index.html
    ├── chapter-01-<slug>.txt
    ├── chapter-02-<slug>.txt
    └── ...

Requirements:
    pip install pymupdf
"""

import fitz
import re
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# ToC detection
# ---------------------------------------------------------------------------

def is_toc_page(page):
    """Return True if this page looks like a ToC page."""
    text = page.get_text()
    blocks = page.get_text("blocks", sort=True)

    # Check for ToC heading — must be a short standalone line, not body text
    has_toc_heading = False
    for block in blocks[:5]:
        if block[6] != 0:
            continue
        for line in block[4].splitlines():
            line = line.strip()
            if re.match(r'^(table of contents|contents)$', line.lower()):
                has_toc_heading = True
                break

    # Dot leaders — both '......' and '. . . . .' styles
    dot_leader_lines = len(re.findall(r'(?:\.{4,}|(?:\. ){3,}\.)\s*\w+', text))

    return has_toc_heading or dot_leader_lines >= 3


def find_toc(doc, search_limit=20):
    """Auto-detect ToC start page and page count. Returns (toc_start, toc_pages) 1-indexed."""
    toc_start = None
    toc_pages = 0
    for i in range(min(search_limit, len(doc))):
        if is_toc_page(doc[i]):
            if toc_start is None:
                toc_start = i + 1
            toc_pages += 1
        elif toc_start is not None:
            break
    return toc_start, toc_pages


# ---------------------------------------------------------------------------
# ToC parsing
# ---------------------------------------------------------------------------

def clean_title(title):
    """Strip trailing dot leaders and whitespace from a title."""
    return re.sub(r'\s*\.{2,}.*$', '', title).strip()


def parse_toc(page):
    """Parse ToC entries from a page.
    Handles four formats:
      Format 1: section + 'title .... page_num'       (Reaktor 6 style, dot leaders)
      Format 2: section + title (possibly wrapped) + page_num  (separate lines)
      Format 3: 'section title' + page_num             (multi-digit section, same line)
      Format 4: 'Title' + page_num                     (unnumbered, e.g. History, Index)
    Returns list of (section, title, page_num).
    """
    blocks = page.get_text("blocks", sort=True)
    entries = []

    for block in blocks:
        if block[6] != 0:
            continue

        lines = [l.strip() for l in block[4].splitlines() if l.strip()]
        if not lines:
            continue

        first = lines[0]

        # Format 1 & 2: section number alone on first line
        if re.match(r'^\d+(\.\d+)*$', first):
            section = first

            # Format 1: "title .... page_num" on one line
            if len(lines) == 2:
                m = re.match(r'^(.+?)\s*(?:\.{2,}|(?:\. ){2,}\.)\s*(\d+)$', lines[1])
                if m:
                    entries.append((section, clean_title(m.group(1)), int(m.group(2))))
                    continue

            # Format 2: section alone + title (possibly wrapped across lines) + page_num
            # Find page number by scanning backwards for last purely numeric line
            if len(lines) >= 3:
                pn_idx = None
                for j in range(len(lines) - 1, 0, -1):
                    if re.match(r'^\d+$', lines[j]):
                        pn_idx = j
                        break
                if pn_idx and pn_idx >= 2:
                    title = clean_title(' '.join(lines[1:pn_idx]))
                    entries.append((section, title, int(lines[pn_idx])))
                    continue

        # Format 3: 'section title' on one line, page_num on next
        # Scan line by line within the block to handle multi-entry blocks
        block_lines = block[4].splitlines()
        i = 0
        while i < len(block_lines):
            line = block_lines[i].strip()
            m = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', line)
            if m:
                section = m.group(1)
                title = clean_title(m.group(2))
                # Page number may be after dot leaders on same line
                pn_same = re.search(r'(?:\.{2,}|(?:\. ){2,}\.)\s*(\d+)\s*$', line)
                if pn_same:
                    entries.append((section, title, int(pn_same.group(1))))
                elif i + 1 < len(block_lines):
                    next_line = block_lines[i + 1].strip()
                    pn_next = re.match(r'^(\d+)$', next_line)
                    if pn_next:
                        entries.append((section, title, int(pn_next.group(1))))
                        i += 1  # skip consumed page number line
            i += 1

        # Format 4: unnumbered entry — 'Title\npage_num'
        # Only match short lines that look like headings (not body text)
        if (len(lines) == 2
                and not re.match(r'^\d', first)
                and len(first.split()) <= 4
                and re.match(r'^(\d+)$', lines[1])):
            entries.append((first, first, int(lines[1])))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for entry in entries:
        key = (entry[0], entry[2])  # (section, page_num)
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    return unique


def get_top_level_chapters(toc_entries):
    """Filter to top-level entries only (no dots in section, or unnumbered like History/Index)."""
    return [(s, t, p) for s, t, p in toc_entries if '.' not in s]


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------

def debug_toc(doc, toc_start, toc_pages, page_offset):
    """Print raw blocks and parsed entries from ToC pages."""
    print(f"\n--- RAW BLOCKS ---")
    all_entries = []
    for page_idx in range(toc_start - 1, toc_start - 1 + toc_pages):
        page = doc[page_idx]
        blocks = page.get_text("blocks", sort=True)
        print(f"\n=== Page {page_idx + 1} ===")
        for i, block in enumerate(blocks):
            if block[6] == 0:
                print(f"\nBlock {i}:")
                print(repr(block[4]))
        entries = parse_toc(page)
        all_entries.extend(entries)

    print(f"\n--- PARSED ENTRIES ({len(all_entries)} total) ---")
    if all_entries:
        for section, title, page_num in all_entries:
            physical = page_num + page_offset
            print(f"  {section:10} printed p.{page_num:4} → physical p.{physical:4}  {title}")
    else:
        print("  None found — parse_toc() regex did not match this PDF's format.")
        print("  Check the raw blocks above and report to fix the parser.")

    chapters = get_top_level_chapters(all_entries)
    print(f"\n--- TOP-LEVEL CHAPTERS ({len(chapters)} total) ---")
    for section, title, page_num in chapters:
        physical = page_num + page_offset
        print(f"  {section:10} printed p.{page_num:4} → physical p.{physical:4}  {title}")


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def slugify(text):
    """Convert a title to a filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')[:50]


def extract_chapter_text(doc, start_page, end_page):
    """Extract plain text from start_page to end_page (1-indexed physical pages, inclusive)."""
    lines = []
    for page_num in range(start_page, end_page + 1):
        page = doc[page_num - 1]
        text = page.get_text().strip()
        if text:
            lines.append(f"--- Page {page_num} ---\n")
            lines.append(text)
            lines.append("\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------

def build_index(chapters, pdf_stem, output_dir):
    """Build an HTML index linking to each chapter text file."""
    lines = [
        '<!DOCTYPE html>',
        '<html>',
        '<head><meta charset="utf-8">',
        f'<title>{pdf_stem}</title>',
        '<style>',
        '  body { font-family: sans-serif; max-width: 800px; margin: 2em auto; }',
        '  li { margin: 0.5em 0; }',
        '  a { text-decoration: none; color: #2255aa; }',
        '  a:hover { text-decoration: underline; }',
        '  .meta { color: #888; font-size: 0.85em; margin-left: 0.5em; }',
        '</style>',
        '</head><body>',
        f'<h1>{pdf_stem}</h1>',
        '<ul>',
    ]

    for section, title, filename, start_page, end_page in chapters:
        page_count = end_page - start_page + 1
        label = f"{section} {title}" if re.match(r'^\d', section) else title
        lines.append(
            f'<li>'
            f'<a href="{filename}">{label}</a>'
            f'<span class="meta">p.{start_page}–{end_page} ({page_count} pages)</span>'
            f'</li>'
        )

    lines.append('</ul>')
    lines.append('</body></html>')

    index_file = output_dir / 'index.html'
    index_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Index written: {index_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def pdf_to_chapters(pdf_path, output_dir=None, toc_start=None, toc_pages=None,
                    page_offset=0, search_limit=20, debug=False):
    pdf_path = Path(pdf_path).expanduser()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    total = len(doc)
    pdf_stem = pdf_path.stem

    print(f"PDF: {pdf_stem} ({total} pages)")
    if page_offset:
        print(f"Page offset: {page_offset} (printed page 1 = physical page {page_offset + 1})")

    # Auto-detect ToC if not specified
    if toc_start is None or toc_pages is None:
        print("Auto-detecting ToC...")
        toc_start, toc_pages = find_toc(doc, search_limit)
        if toc_start is None:
            raise RuntimeError(
                "ToC not found. Use --toc-start and --toc-pages manually. "
                "Run with --debug to diagnose."
            )
        print(f"  Found ToC: page {toc_start}, {toc_pages} pages")

    # Debug mode — print raw blocks and parsed entries, then exit
    if debug:
        debug_toc(doc, toc_start, toc_pages, page_offset)
        return

    # Parse ToC
    toc_entries = []
    for page_idx in range(toc_start - 1, min(toc_start - 1 + toc_pages, total)):
        toc_entries.extend(parse_toc(doc[page_idx]))

    if not toc_entries:
        raise RuntimeError(
            "ToC pages found but no entries parsed. "
            "Run with --debug to diagnose the format."
        )

    chapters = get_top_level_chapters(toc_entries)
    print(f"  Found {len(chapters)} top-level chapters")

    # Set up output directory
    output_dir = Path(output_dir).expanduser() if output_dir else pdf_path.parent / pdf_stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract each chapter using physical page numbers (printed + offset)
    chapter_meta = []
    for i, (section, title, printed_start) in enumerate(chapters):
        physical_start = printed_start + page_offset

        if i + 1 < len(chapters):
            physical_end = chapters[i + 1][2] + page_offset - 1
        else:
            physical_end = total

        # Clamp to valid range
        physical_start = max(1, min(physical_start, total))
        physical_end = max(physical_start, min(physical_end, total))

        # Use numeric prefix for numbered chapters, slug-only for unnumbered
        if re.match(r'^\d+$', section):
            filename = f"chapter-{int(section):02d}-{slugify(title)}.txt"
        else:
            filename = f"{slugify(section)}.txt"

        filepath = output_dir / filename

        print(f"  Chapter {section}: '{title}' "
              f"(physical pages {physical_start}–{physical_end})...", end=' ')

        text = extract_chapter_text(doc, physical_start, physical_end)
        filepath.write_text(text, encoding='utf-8')
        print(f"{filepath.stat().st_size // 1024}KB")

        chapter_meta.append((section, title, filename, physical_start, physical_end))

    build_index(chapter_meta, pdf_stem, output_dir)

    print(f"\nDone. Output: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Split a PDF into plain text chapter files with an HTML index.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('pdf', help='Path to the PDF file')
    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: PDF parent dir / PDF stem)',
        default=None
    )
    parser.add_argument(
        '--toc-start',
        type=int,
        default=None,
        help='Page number where ToC starts'
    )
    parser.add_argument(
        '--toc-pages',
        type=int,
        default=None,
        help='Number of ToC pages to parse'
    )
    parser.add_argument(
        '--page-offset',
        type=int,
        default=0,
        help='Number of front matter pages before printed page 1 (default: 0)'
    )
    parser.add_argument(
        '--search-limit',
        type=int,
        default=20,
        help='Pages to scan for ToC in auto-detect mode (default: 20)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print raw ToC blocks and parsed entries, then exit without generating files'
    )

    args = parser.parse_args()
    pdf_to_chapters(
        args.pdf,
        output_dir=args.output,
        toc_start=args.toc_start,
        toc_pages=args.toc_pages,
        page_offset=args.page_offset,
        search_limit=args.search_limit,
        debug=args.debug
    )


if __name__ == '__main__':
    main()
"""
tests/test_pdf_to_chapters.py
------------------------------
Regression tests for PDF_tools/pdf_to_chapters.py.

Tests are skipped if the PDFs are not cached in /tmp.
To run locally, ensure the PDFs exist (they are downloaded during setup):

    curl -L -o /tmp/REAKTOR_6_Building_in_Primary.pdf <url>
    curl -L -o /tmp/REAKTOR_6_Building_in_Core.pdf <url>
    curl -L -o /tmp/Reaktor_5_Core_Reference_English.pdf <url>
    curl -L -o /tmp/VAFilterDesign_2.1.0.pdf <url>

Run with:  uv run python -m pytest tests/test_pdf_to_chapters.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "PDF_tools"))

# ── helpers ───────────────────────────────────────────────────────────────────

def parse_chapters(pdf_path, toc_start, toc_pages, page_offset=0):
    """Return list of (section, title, page_num) top-level chapters parsed from a PDF."""
    try:
        import fitz
    except ImportError:
        pytest.skip("pymupdf not installed (run: uv sync --extra pdf-tools)")

    from pdf_to_chapters import parse_toc, get_top_level_chapters

    doc = fitz.open(str(pdf_path))
    entries = []
    for page_idx in range(toc_start - 1, toc_start - 1 + toc_pages):
        entries.extend(parse_toc(doc[page_idx]))
    return get_top_level_chapters(entries)


def require_pdf(path):
    """Skip test if the PDF is not cached locally."""
    p = Path(path)
    if not p.exists():
        pytest.skip(f"PDF not available: {p}")
    return p


# ── known-good chapter titles (slugified names must match docs/ filenames) ───

PRIMARY_CHAPTERS = [
    "Welcome to Building in Primary",
    "Introductory Topics",
    "Subtractive Synthesizer",
    "Echo Effect Macro",
    "Basic Step Sequencer",
    "Advanced Step Sequencer",
    "Additive Synthesizer",
    "Drag and Drop Sampler",
    "A Quick Guide to Initialization",
    "Creating and Customizing Interfaces",
    "Automation",
    "KOMPLETE KONTROL and MASCHINE 2 Integration",
    "Internal Connection Protocol",
    "Optimization Techniques",
    "An Introduction to Core",
    "Table Framework",
    "Compiled Core Cell Code Cache",
    "Module Reference",
]

CORE_CHAPTERS = [
    "Welcome to Building in Core",
    "REAKTOR Core Fundamentals",
    "Additional Connectivity Features",
    "Processing Model of Core",
    "Building Practices and Conventions",
    "Macro Reference",
]

CORE5_CHAPTERS = [
    "First Steps in Reaktor Core",
    "Getting Into Reaktor Core",
    "Reaktor Core Fundamentals: The Core Signal Model",
    "Structures with Internal State",
    "Audio Processing at Its Core",
    "Conditional Processing",
    "More Signal Types",
    "Arrays",
    "Building Optimal Structures",
    "Appendix A. Reaktor Core User Interface",
    "Appendix B. Reaktor Core Concept",
    "Appendix C. Core Macro Ports",
    "Appendix D. Core Cell Ports",
    "Appendix E. Built-in Busses",
    "Appendix F. Built-in Modules",
    "Appendix G. Expert Macros",
    "Appendix H. Standard Macros",
    "Appendix I. Core Cell Library",
]

VA_FILTER_CHAPTERS = [
    "Fourier theory",
    "Analog 1-pole filters",
    "Time-discretization",
    "State variable filter",
    "Ladder filter",
    "Nonlinearities",
    "State-space form",
    "Raising the filter order",
    "Classical signal processing filters",
    "Special filter types",
    "Multinotch filters",
]


# ── tests ─────────────────────────────────────────────────────────────────────

def test_primary_chapter_count_and_titles():
    pdf = require_pdf("/tmp/REAKTOR_6_Building_in_Primary.pdf")
    chapters = parse_chapters(pdf, toc_start=4, toc_pages=11, page_offset=0)
    titles = [t for _, t, _ in chapters]
    assert len(titles) == 18, f"Expected 18 chapters, got {len(titles)}: {titles}"
    for expected in PRIMARY_CHAPTERS:
        assert expected in titles, f"Missing chapter: '{expected}'"


def test_core_chapter_count_and_titles():
    pdf = require_pdf("/tmp/REAKTOR_6_Building_in_Core.pdf")
    chapters = parse_chapters(pdf, toc_start=4, toc_pages=5, page_offset=0)
    titles = [t for _, t, _ in chapters]
    assert len(titles) == 6, f"Expected 6 chapters, got {len(titles)}: {titles}"
    for expected in CORE_CHAPTERS:
        assert expected in titles, f"Missing chapter: '{expected}'"


def test_core5_chapter_count_and_titles():
    pdf = require_pdf("/tmp/Reaktor_5_Core_Reference_English.pdf")
    chapters = parse_chapters(pdf, toc_start=4, toc_pages=12, page_offset=0)
    titles = [t for _, t, _ in chapters]
    assert len(titles) == 18, f"Expected 18 chapters, got {len(titles)}: {titles}"
    for expected in CORE5_CHAPTERS:
        assert expected in titles, f"Missing chapter: '{expected}'"


def test_va_filter_chapter_count_and_titles():
    pdf = require_pdf("/tmp/VAFilterDesign_2.1.0.pdf")
    chapters = parse_chapters(pdf, toc_start=5, toc_pages=4, page_offset=12)
    titles = [t for _, t, _ in chapters]
    # 11 numbered chapters + History + Index = 13
    assert len(titles) == 13, f"Expected 13 chapters, got {len(titles)}: {titles}"
    for expected in VA_FILTER_CHAPTERS:
        assert expected in titles, f"Missing chapter: '{expected}'"


def test_va_filter_first_four_chapters_clean():
    """Regression: chapters 1–4 must NOT contain sub-section text or page numbers in their titles."""
    pdf = require_pdf("/tmp/VAFilterDesign_2.1.0.pdf")
    chapters = parse_chapters(pdf, toc_start=5, toc_pages=4, page_offset=12)
    # Chapters 1-4 are the ones that were broken before the fix
    numbered = [(s, t) for s, t, _ in chapters if s.isdigit() and int(s) <= 4]
    for section, title in numbered:
        assert "." not in title or title.startswith("Appendix"), \
            f"Chapter {section} title contains sub-section noise: '{title}'"
        assert not any(c.isdigit() for c in title.split()[0] if c != "."), \
            f"Chapter {section} title starts with a number: '{title}'"
        # Must not contain dot leaders
        assert ".." not in title, f"Chapter {section} title contains dot leaders: '{title}'"


def test_va_filter_chapter_pages_ascending():
    """Chapter start pages must be strictly ascending (correct page assignment)."""
    pdf = require_pdf("/tmp/VAFilterDesign_2.1.0.pdf")
    chapters = parse_chapters(pdf, toc_start=5, toc_pages=4, page_offset=12)
    pages = [p for _, _, p in chapters]
    for i in range(1, len(pages)):
        assert pages[i] > pages[i - 1], \
            f"Page {pages[i]} (chapter {i+1}) ≤ page {pages[i-1]} (chapter {i}) — not ascending"


def test_all_pdfs_no_garbled_titles():
    """No chapter title from any PDF should contain dot leaders or raw sub-section content."""
    cases = [
        ("/tmp/REAKTOR_6_Building_in_Primary.pdf",       4, 11,  0),
        ("/tmp/REAKTOR_6_Building_in_Core.pdf",           4,  5,  0),
        ("/tmp/Reaktor_5_Core_Reference_English.pdf",     4, 12,  0),
        ("/tmp/VAFilterDesign_2.1.0.pdf",                 5,  4, 12),
    ]
    for pdf_path, toc_start, toc_pages, offset in cases:
        if not Path(pdf_path).exists():
            continue
        chapters = parse_chapters(Path(pdf_path), toc_start, toc_pages, offset)
        for section, title, _ in chapters:
            assert ".." not in title, \
                f"{Path(pdf_path).name} ch.{section}: dot leaders in title: '{title}'"
            # Title should not be excessively long (> 80 chars = likely noise)
            assert len(title) <= 80, \
                f"{Path(pdf_path).name} ch.{section}: suspiciously long title ({len(title)} chars): '{title[:60]}...'"


"""
tests/test_tools.py
-------------------
Unit tests for reaktor_mcp.py helpers and tool handlers.

Run with:  uv run pytest tests/
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from reaktor_mcp import resolve_safe, format_directory, call_tool


def run(coro):
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# resolve_safe
# ─────────────────────────────────────────────────────────────────────────────

def test_resolve_safe_valid():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        assert resolve_safe(root, "subdir") == root / "subdir"


def test_resolve_safe_root_itself():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        assert resolve_safe(root, ".") == root


def test_resolve_safe_traversal_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        assert resolve_safe(root, "../../etc/passwd") is None


def test_resolve_safe_double_dot_inside_root():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        (root / "sub").mkdir()
        assert resolve_safe(root, "sub/../sub") == root / "sub"


# ─────────────────────────────────────────────────────────────────────────────
# format_directory
# ─────────────────────────────────────────────────────────────────────────────

def test_format_directory_empty():
    with tempfile.TemporaryDirectory() as tmp:
        assert format_directory(Path(tmp)) == "(empty)"


def test_format_directory_files_and_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "alpha.ens").write_bytes(b"\x00" * 1024)
        (p / "beta_dir").mkdir()
        result = format_directory(p)
        assert "FILE  alpha.ens" in result
        assert "DIR   beta_dir/" in result
        assert "1.0 KB" in result


def test_format_directory_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "z.ens").write_bytes(b"")
        (p / "a.ens").write_bytes(b"")
        lines = format_directory(p).splitlines()
        assert lines[0].startswith("FILE  a.ens")
        assert lines[1].startswith("FILE  z.ens")


# ─────────────────────────────────────────────────────────────────────────────
# list_files
# ─────────────────────────────────────────────────────────────────────────────

def test_list_files_unknown_location():
    result = run(call_tool("list_files", {"location": "nonexistent"}))
    assert "Error" in result[0].text and "unknown location" in result[0].text


def test_list_files_path_traversal():
    result = run(call_tool("list_files", {"location": "ensembles", "subpath": "../../etc"}))
    assert "Error" in result[0].text


def test_list_files_missing_dir():
    result = run(call_tool("list_files", {"location": "ensembles", "subpath": "__does_not_exist__"}))
    assert "not found" in result[0].text.lower() or "Error" in result[0].text


# ─────────────────────────────────────────────────────────────────────────────
# get_file_info
# ─────────────────────────────────────────────────────────────────────────────

def test_get_file_info_unknown_location():
    result = run(call_tool("get_file_info", {"location": "bad", "filepath": "x.ens"}))
    assert "Error" in result[0].text


def test_get_file_info_missing_file():
    result = run(call_tool("get_file_info", {"location": "ensembles", "filepath": "__no_such_file.ens"}))
    assert "not found" in result[0].text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# copy_ensemble
# ─────────────────────────────────────────────────────────────────────────────

def test_copy_ensemble_bad_source_location():
    result = run(call_tool("copy_ensemble", {
        "source_location": "nowhere", "source_path": "x.ens", "dest_path": "y.ens",
    }))
    assert "Error" in result[0].text


def test_copy_ensemble_missing_source():
    result = run(call_tool("copy_ensemble", {
        "source_location": "ensembles",
        "source_path": "__no_such.ens",
        "dest_path": "test_output.ens",
    }))
    assert "not found" in result[0].text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# create_folder
# ─────────────────────────────────────────────────────────────────────────────

def test_create_folder_traversal_blocked():
    result = run(call_tool("create_folder", {"path": "../../tmp/evil"}))
    assert "Error" in result[0].text


# ─────────────────────────────────────────────────────────────────────────────
# search_docs
# ─────────────────────────────────────────────────────────────────────────────

def test_search_docs_empty_query():
    result = run(call_tool("search_docs", {"query": ""}))
    assert "Error" in result[0].text


def test_search_docs_bad_manual():
    result = run(call_tool("search_docs", {"query": "filter", "manual": "unknown"}))
    assert "Error" in result[0].text


def test_search_docs_finds_results():
    result = run(call_tool("search_docs", {"query": "oscillator", "manual": "primary", "max_results": 5}))
    text = result[0].text
    assert "oscillator" in text.lower() or "No results" in text


def test_search_docs_no_results():
    result = run(call_tool("search_docs", {"query": "xyzzy_impossible_token_12345"}))
    assert "No results" in result[0].text


def test_search_docs_respects_max_results():
    result = run(call_tool("search_docs", {"query": "the", "manual": "primary", "max_results": 3}))
    # Count result entries (lines starting with '[primary]')
    hits = [l for l in result[0].text.splitlines() if l.startswith("[primary]")]
    assert len(hits) <= 3


# ─────────────────────────────────────────────────────────────────────────────
# read_doc_chapter
# ─────────────────────────────────────────────────────────────────────────────

def test_read_doc_chapter_bad_manual():
    result = run(call_tool("read_doc_chapter", {"manual": "nope", "chapter": "filter"}))
    assert "Error" in result[0].text


def test_read_doc_chapter_no_match():
    result = run(call_tool("read_doc_chapter", {"manual": "primary", "chapter": "xyzzy_no_match"}))
    assert "No chapter matching" in result[0].text
    assert "Available:" in result[0].text


def test_read_doc_chapter_partial_match():
    # "filter" is a chapter in the modules manual, not primary
    result = run(call_tool("read_doc_chapter", {"manual": "modules", "chapter": "filter"}))
    text = result[0].text
    assert "filter" in text.lower()
    assert "─" in text  # header separator present


def test_read_doc_chapter_core_fundamentals():
    result = run(call_tool("read_doc_chapter", {"manual": "core", "chapter": "fundamentals"}))
    assert len(result[0].text) > 200


def test_read_doc_chapter_modules_math():
    result = run(call_tool("read_doc_chapter", {"manual": "modules", "chapter": "math"}))
    assert len(result[0].text) > 100


# ─────────────────────────────────────────────────────────────────────────────
# list_doc_chapters
# ─────────────────────────────────────────────────────────────────────────────

def test_list_doc_chapters_bad_manual():
    result = run(call_tool("list_doc_chapters", {"manual": "nope"}))
    assert "Error" in result[0].text


def test_list_doc_chapters_primary():
    result = run(call_tool("list_doc_chapters", {"manual": "primary"}))
    text = result[0].text
    assert "18 chapter" in text
    assert "chapter-01" in text


def test_list_doc_chapters_core():
    result = run(call_tool("list_doc_chapters", {"manual": "core"}))
    text = result[0].text
    assert "chapter-01" in text
    assert "[core]" in text


def test_list_doc_chapters_modules():
    result = run(call_tool("list_doc_chapters", {"manual": "modules"}))
    text = result[0].text
    assert "15 chapter" in text


# ─────────────────────────────────────────────────────────────────────────────
# write_session_note
# ─────────────────────────────────────────────────────────────────────────────

def test_write_session_note_empty_content():
    result = run(call_tool("write_session_note", {"content": ""}))
    assert "Error" in result[0].text


def test_write_session_note_appends(tmp_path, monkeypatch):
    notes_file = tmp_path / "session-notes.md"
    notes_file.write_text("# Session Notes\n")

    # Redirect the open() call inside write_session_note to our temp file
    import reaktor_mcp
    original_open = open

    def patched_open(path, *args, **kwargs):
        if "session-notes.md" in str(path):
            return original_open(notes_file, *args, **kwargs)
        return original_open(path, *args, **kwargs)

    monkeypatch.setitem(__builtins__ if isinstance(__builtins__, dict) else vars(__builtins__), "open", patched_open)  # type: ignore

    run(call_tool("write_session_note", {
        "content": "FM depth max is 5000 Hz per unit.",
        "heading": "FM Depth",
    }))

    appended = notes_file.read_text()
    assert "FM Depth" in appended
    assert "FM depth max is 5000" in appended


# ─────────────────────────────────────────────────────────────────────────────
# send_osc
# ─────────────────────────────────────────────────────────────────────────────

def test_send_osc_bad_address():
    result = run(call_tool("send_osc", {"address": "no-slash"}))
    assert "Error" in result[0].text


def test_send_osc_fire_and_forget():
    # UDP is connectionless — sending to an unused port should still "succeed"
    result = run(call_tool("send_osc", {
        "address": "/test/ping",
        "args": [0.0],
        "host": "127.0.0.1",
        "port": 19999,
    }))
    assert "OSC sent" in result[0].text


# ─────────────────────────────────────────────────────────────────────────────
# unknown tool
# ─────────────────────────────────────────────────────────────────────────────

def test_unknown_tool():
    result = run(call_tool("does_not_exist", {}))
    assert "unknown tool" in result[0].text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# list_templates
# ─────────────────────────────────────────────────────────────────────────────

def test_list_templates_returns_listing():
    result = run(call_tool("list_templates", {}))
    text = result[0].text
    # Either lists the templates dir or reports it's missing
    assert "TEMPLATES" in text or "not found" in text.lower()


def test_list_templates_contains_blank():
    result = run(call_tool("list_templates", {}))
    text = result[0].text
    # blank.ens should be present if the templates dir exists
    if "not found" not in text.lower():
        assert "blank.ens" in text


# ─────────────────────────────────────────────────────────────────────────────
# open_in_reaktor
# ─────────────────────────────────────────────────────────────────────────────

def test_open_in_reaktor_bad_location():
    result = run(call_tool("open_in_reaktor", {"location": "nowhere", "filepath": "x.ens"}))
    assert "Error" in result[0].text


def test_open_in_reaktor_traversal_blocked():
    result = run(call_tool("open_in_reaktor", {"location": "ensembles", "filepath": "../../etc/passwd"}))
    assert "Error" in result[0].text


def test_open_in_reaktor_missing_file():
    result = run(call_tool("open_in_reaktor", {"location": "ensembles", "filepath": "__no_such.ens"}))
    assert "not found" in result[0].text.lower()



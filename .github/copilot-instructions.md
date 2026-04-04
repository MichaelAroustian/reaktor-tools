# Copilot Instructions

## Project Overview

This is a Python MCP (Model Context Protocol) server that gives Claude Desktop read-only access to Native Instruments Reaktor 6 file libraries. The core server is `reaktor_mcp.py`.

## Environment & Commands

This project uses [`uv`](https://docs.astral.sh/uv/) — not pip or poetry.

```bash
# Install dependencies
uv sync

# Run the MCP server directly
uv run python reaktor_mcp.py

# Run tests
uv run pytest tests/

# Run a single test
uv run pytest tests/test_tools.py::test_function_name
```

## Architecture

`reaktor_mcp.py` is a single-file MCP server built with the `mcp` Python library. It exposes two tools (`list_files`, `get_file_info`) over stdio transport to Claude Desktop.

**Three named roots** (configurable via env vars):
- `"factory library"` — Reaktor Factory Library
- `"user library"` — Reaktor User Library
- `"ensembles"` — User Ensembles

All path access is sandboxed through `resolve_safe()`, which rejects any path that resolves outside its allowed root.

**Critical constraint:** Logging must go to `reaktor_mcp.log` (never stdout). Stdout is the MCP stdio transport channel — writing anything there breaks the protocol.

All Reaktor files (`.ens`, Core/Primary modules) are **binary format** and cannot be read as text. Tools support browsing and metadata only.

## Key Conventions

- Location names are always lowercase strings matching the `ALLOWED_ROOTS` dict keys.
- Tool handlers live in a single `@app.call_tool()` function, dispatched by `name`.
- Path env vars (`REAKTOR_FACTORY_LIBRARY`, `REAKTOR_USER_LIBRARY`, `REAKTOR_USER_ENSEMBLES`) override defaults without code changes.
- `skills/SKILL.md` is a Copilot skill definition describing the Reaktor domain knowledge available to this assistant.
- `config/` holds Claude Desktop MCP config templates; `config/claude_desktop_config.local.json` is gitignored.
- `docs/` contains PDF reference materials (Reaktor 6 manuals, VA Filter Design paper).
- `PDF_tools/` contains one-off scripts for processing those PDFs into usable formats.

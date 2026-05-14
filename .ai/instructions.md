# reaktor-tools — Project Instructions

## What This Is

Single-file Python MCP server (`reaktor_mcp.py`) that gives AI assistants access to Native Instruments Reaktor 6. Transport is **stdio** — stdout is the MCP wire protocol, never write there. All logging goes to `reaktor_mcp.log` via the `log` logger (`logging.getLogger(__name__)`).

## Git & PR Workflow

- **Never push directly to `main`, `master`, or `develop`** — all changes must go via a PR.
- **Never force push to any branch** unless the user explicitly approves it for that specific case.
- **Commit and PR messages must be confirmed by the user** before pushing or merging.
- Always use `--body-file` for `gh pr create` (never inline `--body`); write the body to a temp file first.
- Branch heads are auto-deleted after merge.
- All PR review conversations must be resolved before merging.
- Linear history only — no merge commits (squash or rebase).

These rules are enforced via GitHub rulesets (`protected-branches` and `no-force-push`). Admin bypass exists for the repo owner only.

## Commands

```bash
uv sync                             # install deps (uv only — never pip/poetry)
uv run python reaktor_mcp.py        # start server manually
uv run python -m pytest tests/      # run all tests
uv sync --extra pdf-tools           # add optional PDF deps (pymupdf)
tail -f reaktor_mcp.log             # watch logs (stdout is off-limits)
git --no-pager log --oneline -10    # ALWAYS --no-pager — git opens less otherwise
git --no-pager diff --stat          # same for diff, show, etc.
```

**Git commit messages must be written to a file** — never use a multi-line shell string, it leaves the terminal in dquote mode:
```bash
cat > /tmp/msg.txt << 'EOF'
Subject line

Body here.
EOF
git commit -F /tmp/msg.txt
```

**`gh pr create` bodies must also use `--body-file`** — same dquote trap applies. Never use `--body "..."` or inline heredocs with `gh`:
```bash
gh pr create --base main --head my-branch \
  --title "PR title here" \
  --body-file /tmp/pr_body.md
```
Use the `create_file` tool to write `/tmp/pr_body.md` — do **not** use `cat > /tmp/pr_body.md << 'EOF'` in the shell, as backtick-wrapped content in the body will corrupt the heredoc and leave the terminal stuck.

The repo also has `core.pager=cat` set in `.git/config` as a safety net.

## Architecture

All 15 tool handlers live in a **single `@app.call_tool()` function**, dispatched by `name` with `if/elif` branches. Do not refactor into a dispatch table or separate functions.

**Adding a tool requires exactly two edits:**
1. Append a `Tool(...)` entry in `list_tools()`
2. Add an `elif name == "new_tool":` branch in `call_tool()`

**Four named roots** (always lowercase keys):

| Key | Default path | Write? |
|---|---|---|
| `"factory library"` | `/Applications/Native Instruments/Reaktor 6/Library` | ❌ |
| `"user library"` | `~/Documents/Native Instruments/Reaktor 6/Library` | ❌ |
| `"ensembles"` | `~/Documents/Native Instruments/User Content/Reaktor/Ensembles` | ✅ |
| `"templates"` | `templates/` in this repo | ❌ |

Override any root via env vars: `REAKTOR_FACTORY_LIBRARY`, `REAKTOR_USER_LIBRARY`, `REAKTOR_USER_ENSEMBLES`, `REAKTOR_TEMPLATES`. OSC: `REAKTOR_OSC_HOST` / `REAKTOR_OSC_PORT` (default `127.0.0.1:10000`). App path: `REAKTOR_APP`.

## Critical Conventions

- **`resolve_safe(root, subpath)`** is the security boundary — call it first in every filesystem branch; return `[TextContent(type="text", text="Error: ...")]` immediately if it returns `None`.
- **Error responses must start with `"Error:"`** — tests `assert "Error" in result[0].text`.
- **Write access is `"ensembles"`-only.** Always resolve write destinations against `REAKTOR_USER_ENSEMBLES`.
- **Never use `print()`.** Use `log.info(...)`, `log.debug(...)`, `log.error(...)`.
- All Reaktor files (`.ens`, `.mdl`, `.ism`, `.rcm`) are **proprietary binary** — never attempt to read or write them as text.

## Testing Pattern

```python
def run(coro): return asyncio.run(coro)
result = run(call_tool("list_files", {"location": "ensembles", "subpath": "../../etc"}))
assert "Error" in result[0].text
```

- All handlers return `list[TextContent]` — always check `result[0].text`.
- Tests that hit real library paths tolerate `"not found"` — those dirs may not exist in CI.
- Live Robot/OSC tests are auto-skipped if port 8270 is not reachable (`pytest.mark.skipif`).

## Key Integration Points

**OSC:** Enable in Reaktor via **File → OSC Settings → Enable OSC → port 10000**. OSC addresses are fully user-defined per-ensemble (the label on a "Message In" module becomes the address, prepended with `/`). Use `get_reaktor_prefs` to check live OSC state before calling `send_osc`.

**Robot XML-RPC (port 8270):** Built into Reaktor 6.5.0, disabled by default. ⚠️ Enabling it causes a hard crash on **File > Open** — both keys are currently removed from the plist. Keywords taking a structure path need `args=[[]]` for root level (not `args=[]`).

**Ensemble analysis (no Reaktor required):** `.ens` binaries contain human-readable strings — module names, parameter labels, port descriptions, help text, preset names. `explain_ensemble` extracts and categorizes these to produce a structured explanation of what an ensemble does. `read_ensemble_strings` gives the raw dump. `describe_structure` walks the live module tree via Robot (requires port 8270).

**New ensemble workflow:** Binary format has no public API. Only path: `copy_ensemble` (source `"templates"`) → `open_in_reaktor` → build patch manually → use `send_osc` to control parameters. `templates/blank.ens` is NI's official blank template.

**Docs search:** `docs/` holds chapter-by-chapter `.txt` files extracted from PDFs. `search_docs` does case-insensitive substring search across them; `read_doc_chapter` uses substring matching on filenames (`"filter"` matches `chapter-10-filter.txt`).

**Session memory:** `write_session_note` appends timestamped entries to `.ai/skills/session-notes.md`. Use it to persist findings across sessions.

## Key Files

| File | Role |
|---|---|
| `reaktor_mcp.py` | Entire server: path config, helpers, `list_tools()`, `call_tool()` |
| `tests/test_tools.py` | All unit tests; import `call_tool` directly and run with `asyncio.run()` |
| `templates/blank.ens` | Minimal binary template for new ensembles |
| `.ai/skills/session-notes.md` | Persistent session log |
| `.ai/skills/maxmsp-mcp-research.md` | Comparative research: Max/MSP MCP projects and lessons for Reaktor |
| `.ai/skills/reaktor-robot-skill.md` | Complete Robot XML-RPC keyword reference (source-verified) |
| `.ai/skills/reaktor-codebase-skill.md` | Reaktor C++ codebase architecture, build system, conventions |
| `KOM-Reaktor/` (local) | Reaktor 6 source at `/Users/michael.aroustian/Documents/_dev/repos/_NI/Komplete/KOM-Reaktor` |
| `docs/` | Manual `.txt` files for `search_docs` / `read_doc_chapter` |
| `pyproject.toml` | `uv` project; `pdf-tools` extra adds `pymupdf` |

## Skill Files

Load from `.ai/skills/` when the context requires it:

| File | When to load |
|---|---|
| `reaktor-overview.md` | Architecture, file formats, docs index, community links |
| `reaktor-primary-skill.md` | Building in Primary: modules, wiring, patch patterns |
| `reaktor-core-skill.md` | Building in Core: cells, buses, DSP patterns |
| `reaktor-robot-skill.md` | Robot XML-RPC keyword reference |
| `maxmsp-mcp-research.md` | Comparative research: Max/MSP MCP lessons |
| `session-notes.md` | Persistent session log — read for context, write via `write_session_note` |

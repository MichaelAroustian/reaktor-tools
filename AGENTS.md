# AGENTS.md — reaktor-tools

## Project Overview

Python MCP server (`reaktor_mcp.py`) that gives Claude Desktop access to Native Instruments Reaktor 6 file libraries, documentation, OSC control, and session notes. Transport is **stdio** — Claude Desktop launches the server as a subprocess and communicates over stdin/stdout.

---

## Commands

```bash
uv sync                             # install deps (use uv, never pip/poetry)
uv run python reaktor_mcp.py        # start the MCP server manually
uv run python -m pytest tests/      # run all tests
uv run python -m pytest tests/test_tools.py::test_send_osc_bad_address  # single test
uv sync --extra pdf-tools           # add optional PDF processing deps
```

Watch the log (stdout is reserved for the MCP transport — never write there):
```bash
tail -f reaktor_mcp.log
```

**Terminal rule:** Always use `git --no-pager` for git commands (or pipe to `| cat`) — never let a pager open in a non-interactive terminal session.

```bash
git --no-pager diff --stat
git --no-pager log --oneline -10
git --no-pager show
```

---

## Architecture

`reaktor_mcp.py` is a single-file MCP server. All 15 tool handlers live inside one `@app.call_tool()` function, dispatched by `name` with `if/elif` branches.

**Three named roots** (location strings are always lowercase):

| Location key | Default path | Write? |
|---|---|---|
| `"factory library"` | `/Applications/Native Instruments/Reaktor 6/Library` | ❌ |
| `"user library"` | `~/Documents/Native Instruments/Reaktor 6/Library` | ❌ |
| `"ensembles"` | `~/Documents/Native Instruments/User Content/Reaktor/Ensembles` | ✅ |

Override with env vars: `REAKTOR_FACTORY_LIBRARY`, `REAKTOR_USER_LIBRARY`, `REAKTOR_USER_ENSEMBLES`.

All path access is sandboxed through `resolve_safe(root, subpath)`, which returns `None` if the resolved path escapes the root. Every filesystem-accessing tool must call this first.

**Critical constraint:** Logging must go to `reaktor_mcp.log` (never stdout). Stdout is the MCP stdio transport — writing anything there breaks the protocol.

All Reaktor files (`.ens`, Core/Primary modules) are **binary format** and cannot be read as text.

---

## Tools

| Tool | Access | Description |
|------|--------|-------------|
| `list_files` | read | List files/folders in a Reaktor root (including `templates`) |
| `get_file_info` | read | File metadata (name, size, modified date) |
| `copy_ensemble` | write | Create a new ensemble by copying an existing .ens file into the ensembles root |
| `create_folder` | write | Create a subfolder in the ensembles root |
| `search_docs` | read | Full-text search across processed manual text files in `docs/` |
| `read_doc_chapter` | read | Read the full text of a specific manual chapter |
| `list_doc_chapters` | read | List all available chapters in a manual |
| `send_osc` | network | Send an OSC message to a running Reaktor instance |
| `get_reaktor_prefs` | read | Read Reaktor's macOS preferences plist (OSC config, MIDI devices, last ensemble) |
| `write_session_note` | write | Append a timestamped note to `skills/session-notes.md` |
| `search_user_library` | network | Search the NI Reaktor User Library website (returns browser URL if blocked) |
| `list_templates` | read | List available template `.ens` files in the local `templates/` folder |
| `open_in_reaktor` | local | Open an ensemble file in Reaktor 6 (launches Reaktor if not running) |
| `restart_reaktor` | local | Quit Reaktor 6 and reopen it (optionally with a specific ensemble) |
| `call_reaktor_robot` | local | Call a Robot Framework keyword on the running Reaktor via XML-RPC (port 8270) |

---

## Key Conventions

- Location names are always lowercase strings matching the `ALLOWED_ROOTS` dict keys: `"factory library"`, `"user library"`, `"ensembles"`, `"templates"`.
- `"templates"` is a read-only root pointing to `templates/` in this repo. Override with `REAKTOR_TEMPLATES` env var.
- Tool handlers live in a single `@app.call_tool()` function, dispatched by `name`.
- Path env vars (`REAKTOR_FACTORY_LIBRARY`, `REAKTOR_USER_LIBRARY`, `REAKTOR_USER_ENSEMBLES`, `REAKTOR_TEMPLATES`) override defaults without code changes.
- `REAKTOR_APP` env var overrides the Reaktor 6 app path used by `open_in_reaktor` (default: `/Applications/Native Instruments/Reaktor 6/Reaktor 6.app`).
- OSC env vars: `REAKTOR_OSC_HOST` (default `127.0.0.1`), `REAKTOR_OSC_PORT` (default `10000`).
- OSC must be enabled in Reaktor via **File → OSC Settings** before `send_osc` has any effect.
- OSC addresses are **fully user-defined** per-ensemble — the label on a "Message In" module becomes the OSC address (prepended with `/`). There is no system-wide scheme.
- `skills/` holds skill definitions and session notes for domain knowledge and build history.
- `docs/` contains processed manual text files (chapter-by-chapter `.txt` files extracted from PDFs via `PDF_tools/`).
- `config/` holds Claude Desktop MCP config templates; `config/claude_desktop_config.local.json` is gitignored.

---

## Reaktor Robot Server (XML-RPC on port 8270)

The retail Reaktor 6.5.0 binary includes a built-in Robot Framework XML-RPC server that exposes full GUI-automation keywords. It is gated by a feature flag and disabled by default.

> ⚠️ **KNOWN CRASH — DO NOT ACTIVATE WITHOUT READING THIS**
>
> In Reaktor 6.5.0, enabling the Robot feature flag causes a hard crash (`SIGABRT` at a deterministic code path, `imageOffset:18941000`) whenever `File > Open` is invoked. This makes the Robot server **mutually exclusive with normal file-dialog usage**. The root cause is in Reaktor's internals and is not data-driven (clearing preferences does not help).
>
> **Current status: both keys have been removed from the user plist.** Robot server is disabled. `File > Open` works normally.
>
> To re-enable (accepting the `File > Open` crash):
> ```bash
> defaults write "com.native-instruments.Reaktor 6" "5d4e071323382551707559765a3322d24e9e3fcd" -int 1
> defaults write "com.native-instruments.Reaktor 6" "RobotSNO" -string "391"
> ```
> To disable again:
> ```bash
> defaults delete "com.native-instruments.Reaktor 6" "5d4e071323382551707559765a3322d24e9e3fcd"
> defaults delete "com.native-instruments.Reaktor 6" "RobotSNO"
> ```

### Setup (when Robot crash is acceptable)

```bash
# Feature flag — integer 1 in the user plist is sufficient (no sudo required)
defaults write "com.native-instruments.Reaktor 6" "5d4e071323382551707559765a3322d24e9e3fcd" -int 1

# Serial number — 391 = Reaktor Full product ID (enables Full-flavour keywords)
defaults write "com.native-instruments.Reaktor 6" "RobotSNO" -string "391"
```

After writing these keys, **restart Reaktor**. Port 8270 should be listening within a few seconds.

### Verify

```bash
lsof -i :8270   # should show Reaktor LISTEN
python3 -c "import xmlrpc.client; print(xmlrpc.client.ServerProxy('http://127.0.0.1:8270').run_keyword('Is Active', [], {}))"
```

### Why it works

- The feature flag `5d4e071323382551707559765a3322d24e9e3fcd` (`SHA1("Reaktor" + "Robot")`) written as integer `1` to the **user** plist is sufficient. Writing to the system plist (with `sudo`) is not required.
- `RobotSNO` is written to the **user** plist (`~/Library/Preferences/com.native-instruments.Reaktor 6.plist`) and tells `reaktor::robot::Activation` the product flavour. `391` = Reaktor Full (enables all keywords).
- `NI::GP::Registry::initSystemAndUser("Reaktor 6", ...)` reads both the system and user plists at startup.

### Available keywords (partial list)

| Keyword | Args | Description |
|---------|------|-------------|
| `Is Active` | — | Returns `True` if Reaktor is running |
| `Get Version` | — | Returns `"Reaktor 6.5.0 (R0)"` |
| `New Ensemble` | — | Create a fresh ensemble |
| `Save Project` | — | Save current project |
| `Open Project` | `filename` | Open a `.ens` or `.nksr` file |
| `Get Project Name` | — | Returns the filename of current project |
| `Is Edit Mode` | — | Returns `True` if in edit mode |
| `Is Touched` | — | Returns `True` if there are unsaved changes |
| `Get Num Modules` | `path[]` | Count modules at a structure path |
| `Create Instrument` | `parentPath[]` | Insert a new Primary instrument |
| `Create Macro` | `parentPath[]` | Insert a new Primary macro |
| `Create Core Cell` | `parentPath[]` | Insert a new Core cell |
| `Load Via Structure` | `files[], path[]` | Drop `.ens`/`.ism`/`.mdl` into structure view |
| `Delete Module` | `path[]` | Delete a module by path |
| `Find Module By Label` | `parentPath[], label` | Find a module by its label string |
| `Process File Load Requests` | — | Flush any pending file-load queue |

**Path argument convention:** Keywords marked `path[]` or `parentPath[]` take the path as an array passed as the first element of `args`. Use `[[]]` for the root level (empty path). Example: `args=[[]]` not `args=[]`.

---

All Reaktor file types are proprietary binary formats. They cannot be read or written as text.

| Extension | Magic | Format |
|---|---|---|
| `.ens` | `c7 65 ...` | Binary chunk format: `DSIN`/`RTKR`/`hsin`/`NRKT` markers + embedded class names (`KEnsemble`, `KSModul`, `KInPort`, `KOutPort`) |
| `.mdl` | `NRKT` | zlib-compressed binary (Primary instrument module) |
| `.ism` | similar | zlib-compressed binary (Primary instrument sub-module) |
| `.rcm` | `RXMF` | zlib-compressed binary (Core module) |

**Creating ensembles programmatically** is not supported — the binary format has no public API. The workflow is:
1. `copy_ensemble` with `source_location="templates"` to copy a template `.ens`
2. `open_in_reaktor` to load it into Reaktor
3. Build the patch manually; use `send_osc` to control parameters

**`templates/blank.ens`** — NI's official blank template (copied from `/Applications/Native Instruments/Reaktor 6/New.ens`). Minimal ensemble with stereo I/O ports.

---

## Adding a New Tool

Two places, in order:

1. Append a `Tool(...)` entry inside `list_tools()` in `reaktor_mcp.py`
2. Add an `elif name == "new_tool":` branch inside `call_tool()`

Every filesystem-accessing branch must call `resolve_safe(root, subpath)` first and return an `"Error:"` `TextContent` if it returns `None`.

---

## Documentation in `docs/`

| Manual key | Directory | Chapters |
|---|---|---|
| `getting-started` | `REAKTOR_6_Getting_Started_English_0419/` | 10 |
| `diving-deeper` | `REAKTOR_6_Diving_Deeper_English_0817/` | 12 |
| `primary` | `REAKTOR_6_Building_in_Primary_English_0419/` | 18 |
| `core` | `reaktor-6-building-in-core/` | 6 |
| `modules` | `Reaktor_5_Modules_and_Macros_Reference_English/` | 15 |
| `core5` | `reaktor-5-5-core-reference/` | 18 |
| `va-filter` | `va-filter-design/` | 13 |

`read_doc_chapter` uses substring matching on filenames — `"filter"` matches `chapter-10-filter.txt`.

---

## Reaktor OSC Setup

OSC must be enabled once inside Reaktor before `send_osc` has any effect:
**File → OSC Settings → Enable OSC → Receive port: 10000 → OK**

Full step-by-step in [`README.md`](README.md#reaktor-osc-setup). Use `get_reaktor_prefs` to check the live state — look for `Enabled: YES ✓` and the receive port number.

---

## Reaktor Preferences (macOS)

Plist: `~/Library/Preferences/com.native-instruments.Reaktor 6.plist`
Read via `plutil -convert json` (falls back to `plistlib`).
Key OSC fields: `OscWasRunning` (enabled flag), `OscLocalPort` (receive port, commonly `10000`).

---

## Testing Patterns

Tests import `call_tool` directly and run it synchronously:

```python
def run(coro): return asyncio.run(coro)
result = run(call_tool("list_files", {"location": "ensembles", "subpath": "../../etc"}))
assert "Error" in result[0].text
```

- All handlers return `list[TextContent]` — check `result[0].text`
- Error responses always start with `"Error:"`
- Tests that hit the real library/ensemble paths must tolerate a `"not found"` response — those directories may not exist in CI

---

## Claude Desktop Integration

The server is registered via `~/Library/Application Support/Claude/claude_desktop_config.json`.
See [`config/README.md`](config/README.md) for the exact merge procedure.
The server command uses `uv run --project /path/to/reaktor-tools python reaktor_mcp.py`.

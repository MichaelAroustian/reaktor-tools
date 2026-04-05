# reaktor-tools

MCP server and resources for building with Native Instruments Reaktor 6.  
Gives Claude Desktop access to your Reaktor file libraries, manuals, OSC control, and session notes.

## MCP Server

`reaktor_mcp.py` is the MCP server. It exposes four file roots and thirteen tools:

### File roots

| Location | Description | Write? |
|----------|-------------|--------|
| `factory library` | Reaktor Factory Library (factory Core/Primary modules) | ❌ |
| `user library` | Your Reaktor User Library (your Core/Primary modules) | ❌ |
| `ensembles` | Your Reaktor User Ensembles (your patches) | ✅ |
| `templates` | Local ensemble templates in `templates/` (this repo) | ❌ |

### Tools

| Tool | Description |
|------|-------------|
| `list_files` | List files and folders in any Reaktor root |
| `get_file_info` | File name, size, and modification date |
| `copy_ensemble` | Create a new ensemble by copying an existing `.ens` file |
| `create_folder` | Create a subfolder in the ensembles root |
| `search_docs` | Full-text search across the processed Reaktor manuals |
| `read_doc_chapter` | Read the full text of a specific manual chapter |
| `list_doc_chapters` | List available chapters in a manual |
| `send_osc` | Send an OSC message to a running Reaktor instance |
| `get_reaktor_prefs` | Read Reaktor's preferences (OSC config, MIDI devices, last ensemble) |
| `write_session_note` | Append a timestamped note to `skills/session-notes.md` |
| `search_user_library` | Search the NI Reaktor User Library (returns browser URL if site blocks access) |
| `list_templates` | List available template `.ens` files in `templates/` |
| `open_in_reaktor` | Open an ensemble in Reaktor 6 (launches Reaktor if not running) |

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Desktop](https://claude.ai/download)

---

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:yourusername/reaktor-tools.git
cd reaktor-tools
```

### 2. Install uv

```bash
brew install uv        # macOS (Homebrew)
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Connect to Claude Desktop

See [`config/README.md`](config/README.md) for instructions.

---

## Configuration

Override default paths with environment variables — no code changes needed:

| Variable | Default |
|----------|---------|
| `REAKTOR_FACTORY_LIBRARY` | `/Applications/Native Instruments/Reaktor 6/Library` |
| `REAKTOR_USER_LIBRARY` | `~/Documents/Native Instruments/Reaktor 6/Library` |
| `REAKTOR_USER_ENSEMBLES` | `~/Documents/Native Instruments/User Content/Reaktor/Ensembles` |
| `REAKTOR_TEMPLATES` | `templates/` in this repo |
| `REAKTOR_APP` | `/Applications/Native Instruments/Reaktor 6/Reaktor 6.app` |
| `REAKTOR_OSC_HOST` | `127.0.0.1` |
| `REAKTOR_OSC_PORT` | `10000` |

### Reaktor OSC Setup

OSC must be enabled inside Reaktor before `send_osc` has any effect. Do this once per installation:

1. Open Reaktor 6
2. Go to **File → OSC Settings** (macOS menu bar)
3. Check **"Enable OSC"** (the checkbox at the top of the dialog)
4. Set **Receive port** to `10000` (or any port — just set `REAKTOR_OSC_PORT` to match)
5. Leave **Send port** and **IP** at their defaults unless sending OSC back out
6. Click **OK** and keep Reaktor running — OSC is active until you quit

To verify OSC is configured correctly without opening the dialog again, use the `get_reaktor_prefs` tool — it reads the live plist and reports:
```
OSC
  Enabled:   YES ✓
  Receive port: 10000
```

> **Note:** OSC addresses are fully ensemble-specific. There is no system-wide address scheme. Each "Message In" module in your ensemble has a label — that label becomes the OSC address (e.g. a module labelled `volume` listens on `/volume`). You define all addresses yourself when building the patch.

---

## Documentation

The `docs/` folder contains chapter-by-chapter text files extracted from the official Reaktor PDFs:

| Key | Manual |
|-----|--------|
| `getting-started` | Reaktor 6 Getting Started (10 chapters) |
| `diving-deeper` | Reaktor 6 Diving Deeper (12 chapters) |
| `primary` | Reaktor 6 Building in Primary (18 chapters) |
| `core` | Reaktor 6 Building in Core (6 chapters) |
| `modules` | Reaktor 5 Modules & Macros Reference (15 chapters) |
| `core5` | Reaktor 5.5 Core Reference (18 chapters) |
| `va-filter` | VA Filter Design 2.1.0 (13 chapters) |

Search with `search_docs`, list chapters with `list_doc_chapters`, read a chapter with `read_doc_chapter`.

---

## Development

```bash
# Run tests
uv run python -m pytest tests/

# Watch logs
tail -f reaktor_mcp.log
```
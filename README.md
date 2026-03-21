# reaktor-tools

Tools and resources for building with Native Instruments Reaktor 6.

## MCP Server

`reaktor_mcp.py` is an MCP server that gives Claude Desktop read access to your
Reaktor file library. It exposes three locations:

| Location | Description |
|----------|-------------|
| `factory library` | Reaktor Factory Library (factory Core/Primary modules) |
| `user library` | Your Reaktor User Library (your Core/Primary modules) |
| `ensembles` | Your Reaktor User Ensembles (your patches) |

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Desktop](https://claude.ai/download)

---

## Repository Setup

### 1. Clone the repository

```bash
git clone git@github.com:yourusername/reaktor-tools.git
cd reaktor-tools
```

### 2. Install uv

If you don't have `uv` installed:

```bash
# macOS (Homebrew)
brew install uv

# macOS/Linux (installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
winget install astral-sh.uv
```

Verify the install:

```bash
which uv
uv --version
```

### 3. Install dependencies

```bash
uv sync
```

This creates a `.venv` in the project root and installs all dependencies.

### 4. Verify the install

```bash
uv run python -c "import mcp; print('mcp ok')"
```

---

## PyCharm Setup

### 1. Open the project

Open the `reaktor-tools` folder in PyCharm.

### 2. Add the Python interpreter

Go to **Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter**.

Select **Existing** and navigate to:

```
/path/to/reaktor-tools/.venv/bin/python
```

### 3. Verify

The interpreter shown in the bottom status bar should read `.venv` and point to
the project root — not a system Python or a different project's venv.

---

## MCP Server Setup

See [`config/README.md`](config/README.md) for instructions on connecting the
server to Claude Desktop.

---

## Paths

Default paths are set in `reaktor_mcp.py`. They can be overridden with environment
variables without touching the code:

| Variable | Default |
|----------|---------|
| `REAKTOR_FACTORY_LIBRARY` | `/Applications/Native Instruments/Reaktor 6/Library` |
| `REAKTOR_USER_LIBRARY` | `~/Documents/Native Instruments/Reaktor 6/Library` |
| `REAKTOR_USER_ENSEMBLES` | `~/Documents/Native Instruments/User Content/Reaktor/Ensembles` |

---

## Logging

The server logs to `reaktor_mcp.log` in the project root. To monitor in real time:

```bash
tail -f reaktor_mcp.log
```
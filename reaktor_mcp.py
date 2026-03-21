"""
reaktor_mcp.py
--------------
MCP server for Reaktor file access.
Provides read-only tools for browsing and organising Reaktor files.

Note: All Reaktor files (.ens, Core, Primary modules) are binary format
and cannot be read as text. Tools here support browsing and file management only.

Configuration (environment variables):
    REAKTOR_FACTORY_LIBRARY — path to Reaktor Factory Library (factory Core/Primary modules)
    REAKTOR_USER_LIBRARY    — path to Reaktor User Library (my Core/Primary modules)
    REAKTOR_USER_ENSEMBLES  — path to Reaktor User Ensembles (my ensembles)
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ── Logging ────────────────────────────────────────────────────────────────────
# Logs to a file alongside this script so stdout stays clean for MCP stdio transport
log_path = Path(__file__).parent / "reaktor_mcp.log"
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
REAKTOR_FACTORY_LIBRARY = Path(
    os.environ.get(
        "REAKTOR_FACTORY_LIBRARY",
        "/Applications/Native Instruments/Reaktor 6/Library",
    )
).resolve()

REAKTOR_USER_LIBRARY = Path(
    os.environ.get(
        "REAKTOR_USER_LIBRARY",
        Path.home() / "Documents/Native Instruments/Reaktor 6/Library",
    )
).resolve()

REAKTOR_USER_ENSEMBLES = Path(
    os.environ.get(
        "REAKTOR_USER_ENSEMBLES",
        Path.home() / "Documents/Native Instruments/User Content/Reaktor/Ensembles",
    )
).resolve()

ALLOWED_ROOTS = {
    "factory library": REAKTOR_FACTORY_LIBRARY,
    "user library": REAKTOR_USER_LIBRARY,
    "ensembles": REAKTOR_USER_ENSEMBLES,
}

log.info("Factory Library: %s", REAKTOR_FACTORY_LIBRARY)
log.info("User Library:    %s", REAKTOR_USER_LIBRARY)
log.info("User Ensembles:  %s", REAKTOR_USER_ENSEMBLES)


# ── Helpers ────────────────────────────────────────────────────────────────────
def resolve_safe(root: Path, subpath: str) -> Path | None:
    """Resolve subpath within root. Returns None if the result escapes the root."""
    try:
        target = (root / subpath).resolve()
        if str(target).startswith(str(root)):
            return target
    except Exception as e:
        log.warning("Path resolution error: %s", e)
    return None


def get_root(location: str) -> Path | None:
    """Return the root Path for a given location name, or None if invalid."""
    return ALLOWED_ROOTS.get(location.lower())


def format_directory(target: Path) -> str:
    """Return a readable directory listing with file sizes."""
    entries = []
    for p in sorted(target.iterdir()):
        if p.is_dir():
            entries.append(f"DIR   {p.name}/")
        else:
            size_kb = p.stat().st_size / 1024
            entries.append(f"FILE  {p.name}  ({size_kb:.1f} KB)")
    return "\n".join(entries) if entries else "(empty)"


# ── Server ─────────────────────────────────────────────────────────────────────
app = Server("reaktor-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_files",
            description=(
                "List files and folders in a Reaktor directory. "
                "Use location='factory library' for the Factory Library (factory Core/Primary modules), "
                "location='user library' for the User Library (my Core/Primary modules), "
                "or location='ensembles' for User Ensembles (my patches)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles"],
                        "description": "Which Reaktor root to browse.",
                    },
                    "subpath": {
                        "type": "string",
                        "description": "Subdirectory within the root. Use '.' for the root itself.",
                        "default": ".",
                    },
                },
                "required": ["location"],
            },
        ),
        Tool(
            name="get_file_info",
            description=(
                "Get metadata about a file in the Reaktor library or ensembles — "
                "name, size, and modification date. "
                "Note: Reaktor files are binary and cannot be read as text."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles"],
                        "description": "Which Reaktor root the file lives in.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file, relative to the chosen root.",
                    },
                },
                "required": ["location", "filepath"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("Tool called: %s | args: %s", name, arguments)

    # ── list_files ─────────────────────────────────────────────────────────────
    if name == "list_files":
        location = arguments.get("location", "")
        subpath = arguments.get("subpath", ".")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'. Use 'factory library', 'user library', or 'ensembles'.")]

        target = resolve_safe(root, subpath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"Directory not found: {subpath}")]

        if not target.is_dir():
            return [TextContent(type="text", text=f"Not a directory: {subpath}")]

        listing = format_directory(target)
        header = f"[{location.upper()}] {target}\n{'─' * 60}\n"
        log.debug("list_files: %d entries in %s", len(list(target.iterdir())), target)
        return [TextContent(type="text", text=header + listing)]

    # ── get_file_info ──────────────────────────────────────────────────────────
    elif name == "get_file_info":
        location = arguments.get("location", "")
        filepath = arguments.get("filepath", "")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'.")]

        target = resolve_safe(root, filepath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"File not found: {filepath}")]

        if not target.is_file():
            return [TextContent(type="text", text=f"Not a file: {filepath}")]

        stat = target.stat()
        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        info = (
            f"Name:     {target.name}\n"
            f"Location: {location}\n"
            f"Path:     {target}\n"
            f"Size:     {size_kb:.1f} KB\n"
            f"Modified: {modified}\n"
            f"Format:   binary (Reaktor proprietary)"
        )
        log.debug("get_file_info: %s", target)
        return [TextContent(type="text", text=info)]

    # ── unknown ────────────────────────────────────────────────────────────────
    log.error("Unknown tool: %s", name)
    return [TextContent(type="text", text=f"Error: unknown tool '{name}'")]


# ── Entry point ────────────────────────────────────────────────────────────────
async def main():
    log.info("reaktor-tools MCP server starting")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
    log.info("reaktor-tools MCP server stopped")


if __name__ == "__main__":
    asyncio.run(main())
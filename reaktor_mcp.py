import asyncio
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json

# ── Configure your Reaktor folder here ──────────────────────────────
REAKTOR_ROOT = Path.home() / "Documents" / "Native Instruments" / "Reaktor 6" / "User Library"
# ────────────────────────────────────────────────────────────────────

app = Server("reaktor-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_files",
            description="List files in a directory within the Reaktor user library",
            inputSchema={
                "type": "object",
                "properties": {
                    "subpath": {
                        "type": "string",
                        "description": "Subdirectory to list (relative to Reaktor root). Use '.' for root.",
                        "default": "."
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="read_file",
            description="Read the contents of a file (e.g. a .ens ensemble file)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to file, relative to Reaktor root"
                    }
                },
                "required": ["filepath"]
            }
        ),
        Tool(
            name="write_file",
            description="Write content to a file in the Reaktor user library",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Destination path, relative to Reaktor root"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["filepath", "content"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "list_files":
        subpath = arguments.get("subpath", ".")
        target = (REAKTOR_ROOT / subpath).resolve()

        # Safety: keep within Reaktor root
        if not str(target).startswith(str(REAKTOR_ROOT)):
            return [TextContent(type="text", text="Error: path outside Reaktor root")]

        if not target.exists():
            return [TextContent(type="text", text=f"Directory not found: {target}")]

        entries = []
        for p in sorted(target.iterdir()):
            kind = "DIR" if p.is_dir() else "FILE"
            entries.append(f"{kind}  {p.name}")

        return [TextContent(type="text", text="\n".join(entries) or "(empty)")]

    elif name == "read_file":
        filepath = arguments["filepath"]
        target = (REAKTOR_ROOT / filepath).resolve()

        if not str(target).startswith(str(REAKTOR_ROOT)):
            return [TextContent(type="text", text="Error: path outside Reaktor root")]

        if not target.exists():
            return [TextContent(type="text", text=f"File not found: {target}")]

        content = target.read_text(encoding="utf-8", errors="replace")
        return [TextContent(type="text", text=content)]

    elif name == "write_file":
        filepath = arguments["filepath"]
        content = arguments["content"]
        target = (REAKTOR_ROOT / filepath).resolve()

        if not str(target).startswith(str(REAKTOR_ROOT)):
            return [TextContent(type="text", text="Error: path outside Reaktor root")]

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return [TextContent(type="text", text=f"Written: {target}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
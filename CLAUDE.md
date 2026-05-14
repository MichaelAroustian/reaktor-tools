# Claude — reaktor-tools

1. Read **`.ai/instructions.md`** for the repo overview, architecture, commands, and conventions.
2. Load skill files from **`.ai/skills/`** on demand — only when the context requires them.

## Claude-specific

- This project is connected to Claude Desktop via MCP (`reaktor_mcp.py`). You are the primary agent using these tools.
- Use the `write_session_note` tool to persist key findings across sessions.

# Copilot — reaktor-tools

1. Read **`.ai/instructions.md`** for the repo overview, architecture, commands, and conventions.
2. Load skill files from **`.ai/skills/`** on demand — only when the context requires them.

## Code Generation Rules

- **Never use `print()`.** All logging goes through the `log` logger (`logging.getLogger(__name__)`), which writes to `reaktor_mcp.log`. Stdout is the MCP transport.
- **New tools require two edits:** append a `Tool(...)` to `list_tools()` and add an `elif` branch in `call_tool()`. Do not refactor into a dispatch table or separate functions.
- **All filesystem access must go through `resolve_safe(root, subpath)`** — return an `"Error:"` `TextContent` immediately if it returns `None`. Never access paths directly.
- **Write operations are `"ensembles"`-only.** Any tool that creates or modifies files must resolve against `REAKTOR_USER_ENSEMBLES`, never against `REAKTOR_FACTORY_LIBRARY` or `REAKTOR_USER_LIBRARY`.
- **Error responses must start with `"Error:"`** — tests assert on this prefix.
- Use `uv` for all dependency and environment management — never `pip` or `poetry`.

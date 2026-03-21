# Configuration

## Claude Desktop MCP Setup

`claude_desktop_config.json` is a template showing the `reaktor-tools` MCP server
configuration. You need to merge the `mcpServers` block into your live Claude Desktop
config file.

### 1. Locate your live config file

| Platform | Path |
|----------|------|
| macOS    | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows  | `%APPDATA%\Claude\claude_desktop_config.json` |

### 2. Add the `mcpServers` block

Open your live config. It will already contain a `preferences` block (and possibly
other keys). Add `mcpServers` as a new key inside the same root JSON object, after
`preferences`, separated by a comma. Replace `/path/to/reaktor-tools` with the
absolute path to wherever you cloned this repository.

Your file should end up looking like this:

```json
{
  "preferences": {
    "coworkWebSearchEnabled": true,
    "ccdScheduledTasksEnabled": false,
    "coworkScheduledTasksEnabled": false,
    "sidebarMode": "chat"
  },
  "mcpServers": {
    "reaktor-tools": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--project",
        "/path/to/reaktor-tools",
        "python",
        "/path/to/reaktor-tools/reaktor_mcp.py"
      ]
    }
  }
}
```

Do not create a second `{...}` object — the entire file must remain a single valid
JSON object with `mcpServers` merged in alongside any existing keys.

If your live config already has a `mcpServers` block, add `reaktor-tools` as an
additional entry alongside your existing servers.

### 3. Check your `uv` path

The template assumes `uv` is installed via Homebrew at `/opt/homebrew/bin/uv`.
Verify your path with:

```bash
which uv
```

Update the `command` value in the config if your path differs.

### 4. Restart Claude Desktop

Fully quit Claude Desktop (Cmd+Q on macOS) and reopen it. The reaktor-tools
server should connect automatically.

---

## Local Config

`claude_desktop_config.local.json` is gitignored and not committed to the repository.
It is a copy of your live config for reference and backup purposes only.
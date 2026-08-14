# M4ST Mesh — OpenWork GitHub plugin

This subdirectory is a **MCP-only** Claude Code plugin bundle for OpenWork's
"Install a plugin from GitHub" flow.

Why this exists:
- OpenWork's GitHub plugin installer does **not** clone the repo, so local
  stdio servers with relative paths (`./mcp_servers/...`) cannot be launched
  from an installed plugin. A **remote URL** server is the portable option.
- Skills/commands/agents currently fail to install on Windows due to an
  OpenWork path bug (`Invalid cloud plugin path`), so this bundle intentionally
  ships **no** skills/commands/agents — only the remote MCP server.

## Install

1. Start the M4ST mesh server (from the M4STCLAW repo):
   ```
   python start.py
   ```
2. In OpenWork: **Settings → Extensions → Install a plugin from GitHub** →
   ```
   https://github.com/m4stanuj/MAST/tree/main/plugin
   ```
3. Preview → Install. The `m4st-mesh` remote MCP server registers and connects
   to `http://localhost:8000/mcp`.

## Note for other clients

For Claude Code / Cursor / Windsurf / Codex (where the repo is checked out
locally), the repo-root `.claude-plugin/` + `.mcp.json` with relative stdio
paths is the right choice. This `plugin/` bundle is specifically for OpenWork's
non-cloning GitHub install.
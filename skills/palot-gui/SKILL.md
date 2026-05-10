---
name: palot-gui
description: >
  Use when user wants a desktop GUI for OpenWork/OpenCode. Palot is an
  Electron app that wraps OpenCode with multi-project management, live diff
  visualization, real-time SSE streaming, and sub-agent cards. Works on
  Windows (x64/ARM64), macOS, and Linux. Reads the SAME opencode.json and
  MCP servers — zero extra config needed.
---

# Palot — Desktop GUI for OpenWork

## What is Palot?
Palot is an open-source Electron desktop app that wraps OpenCode with a
full visual interface. Since OpenWork runs on OpenCode, Palot works
**out of the box** with your existing `opencode.json` and all 15 MCP servers.

**GitHub:** https://github.com/ItsWendell/palot  
**Latest release:** https://github.com/ItsWendell/palot/releases

## Key Features (vs raw OpenCode terminal)
- **Multi-project workspace** — manage multiple projects in one window
- **Live diff viewer** — every file edit shown as old vs new inline diff
- **Real-time streaming** — SSE-based response streaming with Markdown render
- **Sub-agent cards** — live activity cards for delegated tasks
- **Permission UI** — approve/deny tool calls inline (allow once / always)
- **Model picker** — searchable across all providers in your opencode.json
- **Cmd+K palette** — switch sessions, projects, create chats
- **mDNS discovery** — auto-find OpenCode servers on local network
- **Auto-updates** — built-in updater with one-click restart

## Install (Windows — recommended for Mast)

```powershell
# Option 1: Download NSIS installer (Windows x64/ARM64)
# Go to: https://github.com/ItsWendell/palot/releases/latest
# Download: Palot-Setup-x.x.x.exe
# Run installer → Palot will auto-detect OpenCode

# Option 2: Build from source (requires Bun 1.3.8+)
git clone https://github.com/ItsWendell/palot.git
cd palot
bun install
cd apps/desktop && bun run dev
```

## Requirements
1. **OpenCode CLI** installed: `scoop install opencode` or `choco install opencode`
2. **Your opencode.json** at `~/.config/opencode/opencode.json` (already done ✅)
3. Palot reads MCP servers from the same config — nothing extra needed

## How Palot + OpenWork Works Together

```
Palot (Desktop GUI)
    ↓ spawns
OpenCode Server (localhost:auto-port)
    ↓ loads
opencode.json (your providers, plugins, MCPs)
    ↓ starts
15 Python MCP Servers (memory, research, browser, etc.)
    ↓ routes through
llm_fallback.py (56 keys, 9 task-aware chains)
```

## Task: Install Palot GUI

```bash
# Check if OpenCode is installed
opencode --version

# Download Palot installer
# Windows: Palot-Setup-X.X.X.exe from releases page
# Run → it finds OpenCode automatically
# Open Palot → pick your workspace folder → start chatting
```

## Limitations
- Palot is alpha (v0.3.x) — occasional rough edges
- macOS build not code-signed (right-click → Open to bypass Gatekeeper)
- Composio MCP and external C:/workk/ paths disabled in Palot by default
  (they're toggled off in opencode.json when `disabled: true`)

## When to Use
- Tere ko multiple projects ek saath manage karna hai
- File diffs visually dekhni hain
- Background mein agent run karna hai while you browse
- Non-technical users ko OpenWork expose karna hai

## When NOT to Use
- Script/automation pipelines (terminal/CLI better)
- Low-spec machine (Electron is heavier than terminal)
- SSH/remote server (use `openwrk` headless CLI instead)

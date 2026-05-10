---
name: context7-docs
description: |
  Context7 MCP — injects up-to-date library docs directly into agent context.
  No more stale training data for library APIs.

  Triggers when user says:
  - "check docs", "library docs", "official docs"
  - "context7", "latest API"
  - mentions any library name with "how to use"
---

# Context7 — Live Library Documentation MCP

**Always up-to-date docs for any library, injected directly into context.**
Never use stale training data for library APIs again.

---

## MCP Config

```jsonc
{
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

No API key needed — free public MCP endpoint.

---

## Tools

- `resolve-library-id` — Find the correct library ID
- `get-library-docs` — Fetch current docs for a library

---

## Usage Examples

```
# Get FastMCP docs (relevant for your MCP servers!)
resolve-library-id("fastmcp")
get-library-docs("/tadata/fastmcp", topic="server setup")

# Get latest OpenCode SDK docs
resolve-library-id("opencode")
get-library-docs("/opencode-ai/opencode")

# Python libraries
get-library-docs("/scrapling", topic="stealth scraping")
get-library-docs("/chromadb", topic="vector search")
```

---

## Why This Matters for OpenWork v6

Your 9 Python MCP servers use:
- `FastMCP` (mcp v1.x) — docs often stale in training data
- `chromadb` — rapidly evolving API
- `scrapling` — new library, not in training
- `playwright` — frequent updates

Context7 ensures your agent has **correct, current** docs for all of these.

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Up-to-date | ✅ 10/10 |
| Coverage | 9/10 |
| Zero Setup | ✅ 10/10 |

**Overall: 10/10** — Add this to every project!

---
name: web-search-exa
description: |
  Exa web search MCP — real-time web search for agents. No API key needed via OpenCode.
  
  Triggers when user says:
  - "search the web", "look up", "find online"
  - "latest news", "current price", "who is"
  - "research", "find repos"
---

# Exa Web Search MCP

**Real-time web search built into your agent.**
No API key required — uses OpenCode's native websearch integration.

---

## Option 1: OpenCode Native (Recommended — Zero Config)

OpenCode has built-in Exa search. Already active if you use omo.

```jsonc
// Already enabled via oh-my-opencode plugin
// Tools: web_search, web_fetch
```

---

## Option 2: Direct Exa MCP Config

```jsonc
{
  "mcp": {
    "exa": {
      "type": "remote", 
      "url": "https://mcp.exa.ai/mcp"
    }
  }
}
```

---

## Option 3: Brave Search (Privacy-first, Free tier)

```jsonc
{
  "mcp": {
    "brave-search": {
      "command": ["npx", "-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

Free tier: 2000 queries/month. Get key: https://api.search.brave.com

---

## Tools Available

- `web_search` — Search the web with a query
- `web_fetch` — Fetch content from a specific URL
- `find_similar` — Find similar pages to a URL
- `search_news` — Search recent news

---

## Usage for OpenWork v6 Freelance Pipeline

```
# Find freelance gigs
web_search("upwork python automation gigs 2026")

# Research client
web_search("company X tech stack careers")

# Find GitHub repos
web_search("github fastmcp Windows MCP server 2026")
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Real-time | ✅ 10/10 |
| Quality | 9/10 |
| Setup | ✅ Zero config via omo |

**Overall: 10/10** — Already bundled with omo. Just use it!

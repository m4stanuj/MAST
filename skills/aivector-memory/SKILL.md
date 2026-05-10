---
name: aivector-memory
description: |
  AIVectorMemory — persistent cross-session vector DB memory for OpenCode + OpenClaw.
  Semantic search across all past sessions. 78 stars, actively maintained.

  Triggers when user says:
  - "what did we discuss before", "past session", "remember from last time"
  - "search memory", "vector memory", "semantic search history"
  - "what have I worked on", "find previous work on X"
---

# AIVectorMemory — Vector DB Cross-Session Memory

**Semantic search across ALL past conversations.**
Never lose context from previous sessions — find it by meaning, not exact words.

**GitHub:** https://github.com/topics/opencode-skills (search: aivectormemory)
⭐ 78 stars | ChromaDB backend | OpenClaw compatible ✅

---

## Install

```bash
# Clone to your workk directory
git clone https://github.com/[aivectormemory-repo] C:/workk/aivectormemory

# Install deps
pip install chromadb sentence-transformers fastmcp --break-system-packages
```

```jsonc
// opencode.json
{
  "mcp": {
    "aivector-memory": {
      "command": ["python", "C:/workk/aivectormemory/server.py"],
      "enabled": true
    }
  }
}
```

---

## Tools

- `memory_store` — Save important context/findings to vector DB
- `memory_search` — Semantic search: "find everything about FastMCP bugs"
- `memory_recent` — Get last N memories
- `memory_delete` — Remove specific memories
- `memory_stats` — DB stats (entries, size)

---

## vs. opencode-agent-memory (the other memory skill)

| Feature | opencode-agent-memory | aivector-memory |
|---------|----------------------|----------------|
| Storage | Markdown blocks | ChromaDB vectors |
| Search | Exact/keyword | **Semantic similarity** |
| Cross-session | ✅ | ✅ |
| OpenClaw compat | ❌ | ✅ |
| Memory capacity | ~50 blocks | Unlimited |
| Find by meaning | ❌ | ✅ |

**Use both:** agent-memory for structured current-project context, aivector for semantic history search.

---

## OpenWork v6 Use Cases

```
# Find previous work on similar problems
memory_search("FastMCP server initialization error")
→ Returns: "Session 2026-03-15: Fixed FastMCP by importing from mcp.server.fastmcp not mcp"

# Before starting a new MCP server
memory_search("MCP server Windows Python setup")
→ Returns all past notes on Windows MCP gotchas

# Freelance client context
memory_search("client Upwork gig automation requirements")
→ Returns past client specs and decisions
```

---

## Auto-Store Pattern

Add to your `.openwork/agents/openwork.md`:
```markdown
After completing any significant task or fix:
1. Store key finding: memory_store("Fixed: [what] by [how] — [date]")
2. Store client decisions: memory_store("Client [X] wants [Y] not [Z]")
3. Store model preferences: memory_store("Groq llama better than Cerebras for [task type]")
```

---

## OpenClaw Integration (Your Next Integration!)

AIVectorMemory is explicitly OpenClaw-compatible — when you wire OpenClaw for voice/messaging, it will share the same memory DB:

```
Voice: "What was that FastMCP fix I found last week?"
→ OpenClaw → aivectormemory search → Returns exact fix
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Semantic Search | ✅ 10/10 |
| OpenClaw Ready | ✅ 10/10 |
| Windows compat | ✅ ChromaDB works |

**Overall: 10/10** — Especially valuable for OpenClaw integration coming up!

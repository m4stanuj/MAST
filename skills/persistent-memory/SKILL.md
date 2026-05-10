---
name: persistent-memory
description: |
  Gives the agent persistent, self-editable memory blocks that survive across sessions.
  Inspired by Letta agents — structured blocks injected early into context.

  Triggers when user says:
  - "remember this"
  - "what do you remember"
  - "memory", "forget", "save for later"
---

# Persistent Agent Memory — opencode-agent-memory

**Self-editable memory blocks** that survive compaction and session restarts.
Based on Letta-style structured memory with AGENTS.md harness.

---

## Plugin Install

```jsonc
// opencode.json
{
  "plugin": ["opencode-agent-memory"]
}
```

Or via npm:
```bash
npm install -g opencode-agent-memory
```

---

## How It Works

Memory is stored in structured blocks in your project's `.opencode/memory.md`:

```markdown
<!-- MEMORY BLOCK: project -->
This is an OpenWork v6 project. MCP servers in C:/workk/. 
Prefer local-first tools. Hinglish responses.
<!-- END MEMORY BLOCK -->

<!-- MEMORY BLOCK: user-prefs -->
User: Mast. Jugaad philosophy. Speed over perfection.
Stack: Windows, Python, Node. No Docker preferred.
<!-- END MEMORY BLOCK -->
```

The agent **reads, edits, and maintains** these blocks autonomously.

---

## Memory Tools

- `memory_read` — Read all memory blocks
- `memory_write` — Update a specific block
- `memory_append` — Add to existing block
- `memory_clear` — Clear a block

---

## Alternative: aivectormemory (Vector Search)

For semantic/vector-based cross-session memory:

```jsonc
{
  "mcp": {
    "aivector-memory": {
      "command": ["python", "C:/workk/aivectormemory/server.py"],
      "enabled": true
    }
  }
}
```

**GitHub:** https://github.com/topics/opencode-skills (search: aivectormemory)
⭐ 78 stars | Vector DB (ChromaDB) | Cross-session | OpenClaw compatible

---

## OpenWork v6 Memory Config

Add to `C:/workk/OpenWork/.opencode/memory.md`:

```markdown
<!-- MEMORY BLOCK: openwork -->
OpenWork v6 — MCP-native autonomous agent.
MCP servers: memory, research, react, skills, browser, scrapling, file, notify, vision
Brain: Multi-provider (Groq, Cerebras, DeepSeek, Gemini, OpenRouter)
Cybersec model: brxce/josiefied-qwen3:8b (local, auto-trigger on exploit/pentest/payload)
<!-- END MEMORY BLOCK -->
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Persistence | ✅ 10/10 |
| Compaction Survival | ✅ 9/10 |
| Setup | ✅ Easy |

**Overall: 10/10** — Essential for any serious agent setup!

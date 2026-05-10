---
name: multi-agent-omo
description: |
  Oh-My-Openagent (omo) — transforms OpenCode into a full multi-agent engineering system.
  11 specialized agents, parallel execution, Sisyphus orchestrator.

  Triggers when user says:
  - "ultrawork", "multi-agent", "parallel tasks"
  - "sisyphus", "subagent", "background task"
  - "oh my opencode", "omo"
---

# Oh-My-Openagent (omo) — Multi-Agent Orchestration

**Transforms OpenWork/OpenCode into a full virtual dev team.**
⭐ Most powerful OpenCode plugin in 2026.

**GitHub:** https://github.com/code-yeongyu/oh-my-openagent

---

## Install

```jsonc
// opencode.json — add to plugin array
{
  "plugin": ["oh-my-opencode"]
}
```

---

## The Agents (Virtual Dev Team)

| Agent | Role | Best Model |
|-------|------|-----------|
| **Sisyphus** | Orchestrator — plans, delegates, drives to completion | claude-opus-4-6 / GLM-5 |
| **Hephaestus** | Deep worker — autonomous coder, no hand-holding | gpt-5.4 / Nemotron |
| **Prometheus** | Strategic planner — interview mode before execution | claude-opus-4-6 |
| **Oracle** | Research & analysis | gpt-5.4 |
| **Explorer** | Codebase discovery | qwen2.5-coder:7b (local) |
| **Librarian** | Documentation & skills loader | qwen2.5-coder:7b (local) |
| **Designer** | UI/UX tasks | any |
| **Momus** | Code reviewer & critic | gpt-5.4 |

---

## Built-in MCPs (Auto-Configured)

- `web_search` via **Exa** — real-time web search
- `context7` — official library docs (up-to-date)
- `grep_app` — GitHub code search

---

## OpenWork v6 Config (Jugaad Hybrid)

```jsonc
// ~/.config/opencode/oh-my-opencode.jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/assets/oh-my-opencode.schema.json",
  "agents": {
    "explore": { "model": "groq/llama-3.3-70b-versatile", "temperature": 0.1 },
    "librarian": { "model": "groq/llama-3.3-70b-versatile", "temperature": 0.1 },
    "oracle": { "model": "openrouter/google/gemini-2.5-pro", "variant": "high" },
    "momus": { "model": "deepseek/deepseek-r1", "variant": "high" }
  },
  "categories": {
    "quick": { "model": "groq/llama-3.3-70b-versatile" },
    "writing": { "model": "cerebras/llama-3.3-70b" },
    "deep": { "model": "openrouter/google/gemini-2.5-pro" },
    "code": { "model": "sambanova/Meta-Llama-3.3-70B-Instruct" }
  }
}
```

---

## Key Commands

```bash
# Start ultrawork mode (Sisyphus takes over)
/ultrawork Build me a FastAPI server with auth

# Initialize project memory
/init-deep

# Check all agents
/omo status

# Diagnose setup
bunx oh-my-opencode doctor
```

---

## Task Categories

| Category | Use For | Speed |
|----------|---------|-------|
| `quick` | Simple tasks, file edits | ⚡ Fast |
| `writing` | Docs, READMEs, summaries | ⚡ Fast |
| `code` | Feature implementation | 🔄 Medium |
| `deep` | Architecture, complex debugging | 🐢 Thorough |

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Multi-agent | ✅ 10/10 |
| Parallel Execution | ✅ 10/10 |
| Setup Complexity | ⚠️ 7/10 |

**Overall: 10/10** — Game changer. Install this FIRST.

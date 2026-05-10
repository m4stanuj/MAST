---
name: token-optimizer
description: |
  Token usage optimization — prune stale tool outputs, analyze usage, reduce context bloat.
  
  Triggers when user says:
  - "context too long", "token limit", "reduce tokens"
  - "context bloat", "running out of context"
  - "optimize", "prune old messages"
---

# Token Optimizer — Context Management Skills

**Maximize agent efficiency by managing context window intelligently.**
Critical for long OpenWork v6 automation sessions.

---

## Plugin 1: Token Pruner

Automatically removes stale tool outputs from conversation context.

```jsonc
{
  "plugin": ["opencode-token-pruner"]
}
```

**What it prunes:**
- Duplicate file reads
- Old bash command outputs (keeps last N)
- Redundant search results
- Tool errors that were resolved

---

## Plugin 2: Token Usage Analyzer

Real-time token analysis per session.

```jsonc
{
  "plugin": ["opencode-token-analyzer"]
}
```

**Commands:**
```bash
/tokens          # Current usage breakdown
/tokens history  # Usage across sessions
/tokens expensive # Most expensive tool calls
```

---

## Manual Optimization Strategies

### 1. Skill-based Context Loading

Instead of loading everything upfront:
```
# BAD: All skills loaded at once
# GOOD: Load skills on demand
use_skill("browser")        # Only when browsing
use_skill("screenpipe")     # Only when searching history
```

### 2. Session Handoff

When approaching context limit, create handoff:
```bash
/handoff  # Creates continuation prompt for new session
```

### 3. AGENTS.md Hierarchy (via omo /init-deep)

Generate lean per-directory context:
```bash
/init-deep  # Creates AGENTS.md in each subdirectory
```

Result: Agent loads only relevant context per task.

---

## OpenWork v6 Token Budget (Estimated)

| Provider | Context | Cost/1M tokens | Best For |
|----------|---------|----------------|---------|
| Groq (free) | 32K | $0 | Quick tasks |
| Cerebras (free) | 8K | $0 | Speed |
| DeepSeek | 128K | ~$0.14 | Long sessions |
| Gemini 2.5 Pro | 1M | ~$1.25 | Very long sessions |
| Claude Opus | 200K | $15 | Complex reasoning |

**Tip:** Route long automation sessions to DeepSeek or Gemini to minimize cost.

---

## .opencode/rules/token-hygiene.md

Create this file:
```markdown
# Token Hygiene Rules

- After completing a subtask, summarize findings in 3 bullet points max
- Don't re-read files you've already processed; reference them by name
- Use /handoff when context > 80% full
- Prefer grep/search over reading entire files
- After bash commands, acknowledge key output only — don't echo full output
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Automatic | ✅ 9/10 |
| Context Savings | ~30-50% |

**Overall: 9/10** — Essential for long automation sessions!

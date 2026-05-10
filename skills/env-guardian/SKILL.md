---
name: env-guardian
description: |
  ENV Guardian — prevents agents from reading or leaking .env files and API keys.
  Shows key names and fingerprints only, never values.

  Triggers when user says:
  - "api key", "env file", "environment variable"
  - "what keys do I have", "check .env"
  - "credentials", "secrets"
---

# ENV Guardian — Keep Your Secrets Safe

**Agent can see WHAT keys you have, but NEVER their values.**
Prevents accidental key leakage in logs, commits, or chat history.

---

## Plugin Install

```jsonc
{
  "plugin": ["opencode-env-sitter"]
}
```

---

## How It Works

Instead of:
```
GROQ_API_KEY=gsk_abc123xyz...  # ❌ Full value visible
```

Agent sees:
```
GROQ_API_KEY=[SET] sha256:a3f2...  # ✅ Hash only
GEMINI_API_KEY=[SET] sha256:b8c1...
OPENROUTER_API_KEY=[NOT SET]
```

---

## Protected Files

All `.env*` patterns blocked from direct read:
- `.env`
- `.env.local`
- `.env.production`
- `secrets.env`

---

## OpenWork v6 .gitignore Setup

```gitignore
# CRITICAL — Never commit these
.env
.env.*
*.env
opencode.json          # Contains API keys!
.opencode/memory.md    # May contain sensitive context
C:/workk/**/.env
C:/workk/**/secrets*
```

---

## Key Inventory (Safe View)

Agent can run `env-sitter check` to show:
```
API Keys Status:
✅ GROQ_API_KEY        [SET] gsk_****...4f2a
✅ CEREBRAS_API_KEY    [SET] csk_****...9b1c  
✅ DEEPSEEK_API_KEY    [SET] sk-****...3d4e
✅ GEMINI_API_KEY      [SET] AIza****...7f8g  ← The one that leaked!
✅ OPENROUTER_API_KEY  [SET] sk-or-****...2h3i
❌ ANTHROPIC_API_KEY   [NOT SET]
❌ SAMBANOVA_API_KEY   [NOT SET]
```

---

## After Key Leak Recovery Checklist

1. `env-sitter audit` — check which keys are in git history
2. `git log --all -p | grep "AIza"` — find Gemini key in git
3. Revoke + rotate all exposed keys
4. Add `opencode.json` to `.gitignore` if not done
5. Use `git filter-repo` to scrub history if key was committed

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Security | ✅ 10/10 |
| Relevance to You | 🔥 10/10 |

**Overall: 10/10** — Especially after that Gemini key leak, bhai!

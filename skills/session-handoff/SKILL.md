---
name: session-handoff
description: |
  Session handoff — creates continuation prompts when context gets full or task switches.
  Never lose progress between sessions.

  Triggers when user says:
  - "handoff", "continue later", "new session"
  - "context full", "save progress"
  - "switch task", "resume"
---

# Session Handoff — Continuity Between Sessions

**Never lose your place.** Creates focused continuation prompts when switching sessions.

---

## Plugin Install

```jsonc
{
  "plugin": ["opencode-handoff"]
}
```

---

## Usage

```bash
/handoff                    # Create handoff for current task
/handoff "finishing auth"   # With custom note
```

**Output example:**
```markdown
# Session Handoff — 2026-04-03 12:45

## Current Task
Building FastAPI auth module for OpenWork freelance client

## Progress
- ✅ JWT token generation
- ✅ Login endpoint  
- 🔄 Refresh token logic (in progress)
- ❌ Rate limiting (not started)

## Key Files
- `src/auth/jwt.py` — token logic
- `src/routes/auth.py` — endpoints
- `tests/test_auth.py` — 8/12 tests passing

## Next Steps
1. Complete refresh token in `jwt.py:generate_refresh()`
2. Add rate limiting middleware
3. Run full test suite

## Context
Client: Upwork gig #12345
Stack: FastAPI + PostgreSQL + Redis
Deadline: Tomorrow 5pm IST
```

---

## Manual Handoff Template

If plugin not installed, create `.opencode/handoff.md`:

```markdown
# HANDOFF — {date}

## Task
{what you were doing}

## Done
- 

## In Progress
- 

## Not Started
- 

## Files Modified
- 

## Resume Command
```

---

## Auto-Handoff on Context Compaction

Add to `.opencode/agents/openwork.md`:
```markdown
When approaching 80% context usage:
1. Summarize current task state
2. List completed and pending items
3. Note key file paths
4. Create handoff file at .opencode/handoff-{timestamp}.md
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Session Continuity | ✅ 10/10 |
| Setup | ✅ Easy |

**Overall: 9/10** — Must-have for long freelance automation sessions!

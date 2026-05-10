---
name: safety-net
description: |
  Safety net — catches destructive git and filesystem commands before execution.
  Prevents accidental rm -rf, git reset --hard, force pushes, etc.

  Triggers when user says:
  - "be careful", "dangerous command", "safety"
  - "undo", "what did you delete"
  - "rollback", "restore"
---

# Safety Net — Catch Destructive Commands

**Prevents accidental data loss in automation sessions.**
Critical for 24/7 unattended OpenWork pipelines.

---

## Plugin Install

```jsonc
{
  "plugin": ["opencode-cc-safety-net"]
}
```

---

## What It Catches

### Git Danger Zone 🔴
```bash
git reset --hard        # ⛔ BLOCKED — prompts for confirmation
git push --force        # ⛔ BLOCKED
git clean -fd           # ⛔ BLOCKED
git branch -D           # ⚠️ WARNING
```

### Filesystem Danger Zone 🔴
```bash
rm -rf /               # ⛔ BLOCKED
rm -rf *               # ⛔ BLOCKED — too broad
del /f /s /q C:\       # ⛔ BLOCKED
rmdir /s               # ⚠️ WARNING
```

### Safe Alternatives Suggested
```
rm -rf ./temp/         # ✅ OK — specific directory
git push --force-with-lease  # ✅ Safe force push
git stash              # ✅ Alternative to reset
```

---

## Custom Rules for OpenWork

Create `.opencode/rules/safety.md`:
```markdown
# Safety Rules

ALWAYS confirm before:
- Deleting any file in C:/workk/ (MCP server files)
- Modifying opencode.json (breaks all MCPs)
- git reset on OpenWork repo
- Stopping any running MCP server process
- Modifying .env files

NEVER:
- rm -rf without explicit absolute path
- force push to main/master
- Delete database files without backup
- Kill processes matching: python, node (MCP servers might be running)
```

---

## Backup Hook

Add pre-execution backup for critical dirs:

```bash
# .opencode/hooks/pre-destruct.sh
#!/bin/bash
echo "Creating safety backup before destructive operation..."
cp -r C:/workk/OpenWork/.opencode /tmp/openwork-backup-$(date +%Y%m%d-%H%M%S)/
echo "Backup created at /tmp/"
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Data Protection | ✅ 10/10 |
| False Positive Rate | Low |

**Overall: 10/10** — Non-negotiable for autonomous agents!

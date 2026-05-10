---
name: m4st-scheduler
description: >
  Schedule tasks in Hinglish natural language. Uses APScheduler via scheduler_mcp.py.
  Understands: "kal subah 9 baje", "har roz 6 PM", "30 minute baad", "Monday ko".
  Use for: reminders, recurring tasks, delayed execution, cron-style schedules.
allow_implicit_invocation: true
triggers:
  - "schedule"
  - "remind"
  - "baad mein"
  - "kal"
  - "subah"
  - "shaam"
  - "har roz"
  - "every day"
  - "reminder"
  - "cron"
---

# M4ST Scheduler Skill

## Hinglish Time Parsing (built-in)

```
"30 minute baad"      → +30 minutes from now
"kal subah 9 baje"    → tomorrow 9:00 AM
"har roz 6 PM"        → daily at 18:00 (recurring)
"agle hafte Monday"   → next Monday
"10 second mein"      → +10 seconds
"raat 11 baje"        → 23:00 tonight
"do ghante baad"      → +2 hours
"her ghante"          → every hour (recurring)
```

## MCP Tools
- `schedule_task(task, time_expr, repeat?)` — schedule anything
- `schedule_list()` — show all scheduled tasks
- `schedule_cancel(id)` — cancel a scheduled task
- `schedule_status()` — APScheduler health check

## Usage Examples
```
User: "yrr mujhe 30 min baad reminder de ki standup hai"
MAST: [schedule_task("standup reminder", "30 minute baad")]
      → "Done bhai! 30 minute mein remind karunga."

User: "har roz subah 8 baje mera daily brief banao"
MAST: [schedule_task("daily_brief", "har roz 8 baje", repeat=True)]
      → "Set! Roz subah 8 baje brief ready hoga."
```

## Notes
- APScheduler via bridge_core/scheduler.py
- Schedules persist in data/schedules.json
- Notifications via notify_mcp (Telegram / ntfy.sh)
- Set TELEGRAM_BOT_TOKEN in .env for mobile reminders

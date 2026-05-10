#!/usr/bin/env python3
"""
scheduler_mcp.py — M4ST Scheduler MCP v3.0
============================================
Wraps actual M4STCLAW scheduler.py — Hinglish time parsing, APScheduler,
condition-based triggers, missed schedule recovery.

"kal subah 9 baje reminder bhejo" → cron job auto-created.
"har Monday 10 AM pe status check karo" → weekly schedule.
"15 minute mein screenshot lo" → one-shot delay trigger.

Tools:
  sched_add     — Add schedule in natural language (Hinglish supported)
  sched_list    — List all active schedules
  sched_remove  — Remove a schedule by ID
  sched_status  — Scheduler health + next run times
  sched_parse   — Parse time string only (no schedule creation)
"""
import sys, os, json, time
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or os.path.expanduser("~/.config/opencode"))
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))

# Try to load actual scheduler.py from M4STCLAW
_sched_mod = None
_BRIDGE_CANDIDATES = [
    Path(os.environ.get("M4ST_BRIDGE_DIR", "")),
    Path.home() / ".config" / "opencode" / "bridge_core",
    Path(__file__).parent / "bridge_core",
    Path(__file__).parent.parent / "bridge_core",
]
for c in _BRIDGE_CANDIDATES:
    if c and (c / "scheduler.py").exists():
        sys.path.insert(0, str(c))
        try:
            import scheduler as _sched_mod
            break
        except Exception:
            pass

from _mcp_base import mcp_loop, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list

def _log(m): print(f"[scheduler_mcp] {m}", file=sys.stderr, flush=True)
if _sched_mod:
    _log("✅ scheduler.py loaded from M4STCLAW bridge")
else:
    _log("⚠️  scheduler.py not found — using embedded Hinglish parser")

# ══════════════════════════════════════════════════════════════════════
#  EMBEDDED HINGLISH TIME PARSER (from M4STCLAW scheduler.py)
#  Used as fallback when scheduler.py not found
# ══════════════════════════════════════════════════════════════════════
import re
from datetime import datetime, timedelta

HINGLISH_MAP = {
    "subah": "morning", "dopahar": "afternoon", "shaam": "evening",
    "raat": "night", "kal": "tomorrow", "aaj": "today",
    "abhi": "now", "parso": "day_after", "minute": "minutes",
    "ghante": "hours", "din": "days", "hafta": "weeks",
    "har": "every", "roz": "daily", "somwar": "monday",
    "mangalwar": "tuesday", "budhwar": "wednesday", "guruwar": "thursday",
    "shukrawar": "friday", "shaniwar": "saturday", "raviwar": "sunday",
    "ek": "1", "do": "2", "teen": "3", "char": "4", "paanch": "5",
    "chhe": "6", "saat": "7", "aath": "8", "nau": "9", "das": "10",
    "gyarah": "11", "barah": "12", "bees": "20", "tees": "30",
    "pandrah": "15", "bis": "20",
}

TIME_OF_DAY = {
    "morning": (9, 0), "subah": (9, 0), "afternoon": (14, 0),
    "dopahar": (14, 0), "evening": (17, 0), "shaam": (17, 0),
    "night": (21, 0), "raat": (21, 0),
}

def _parse_time_natural(text: str) -> dict:
    """Parse natural language / Hinglish time expression."""
    text_lower = text.lower().strip()
    # Translate Hinglish
    for hindi, eng in HINGLISH_MAP.items():
        text_lower = re.sub(rf'\b{hindi}\b', eng, text_lower)

    now = datetime.now()
    result = {"type": None, "trigger_time": None, "interval_minutes": None,
              "cron": None, "human_readable": None}

    # X minutes/hours from now
    m = re.search(r'(\d+)\s*(minutes?|hours?|mins?|hrs?)', text_lower)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        mins = n if "min" in unit else n * 60
        trigger = now + timedelta(minutes=mins)
        result.update({"type": "delay", "trigger_time": trigger.strftime("%Y-%m-%d %H:%M"),
                       "interval_minutes": mins, "human_readable": f"In {n} {unit}"})
        return result

    # Daily at time
    if "daily" in text_lower or "roz" in text_lower or "every day" in text_lower:
        hour, minute = _extract_time(text_lower)
        result.update({"type": "cron", "cron": f"{minute} {hour} * * *",
                       "human_readable": f"Daily at {hour:02d}:{minute:02d}"})
        return result

    # Weekly — specific day
    days = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
    for day, dow in days.items():
        if day in text_lower:
            hour, minute = _extract_time(text_lower)
            result.update({"type": "cron", "cron": f"{minute} {hour} * * {dow}",
                           "human_readable": f"Every {day.capitalize()} at {hour:02d}:{minute:02d}"})
            return result

    # Tomorrow at time
    if "tomorrow" in text_lower:
        hour, minute = _extract_time(text_lower)
        trigger = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0)
        result.update({"type": "once", "trigger_time": trigger.strftime("%Y-%m-%d %H:%M"),
                       "human_readable": f"Tomorrow at {hour:02d}:{minute:02d}"})
        return result

    # Specific time today
    hour, minute = _extract_time(text_lower)
    if hour >= 0:
        trigger = now.replace(hour=hour, minute=minute, second=0)
        if trigger < now:
            trigger += timedelta(days=1)
        result.update({"type": "once", "trigger_time": trigger.strftime("%Y-%m-%d %H:%M"),
                       "human_readable": f"At {hour:02d}:{minute:02d}"})
        return result

    return {"type": "unknown", "error": "Could not parse time expression", "original": text}

def _extract_time(text: str) -> tuple:
    """Extract hour, minute from text. Returns (-1, 0) if not found."""
    # HH:MM format
    m = re.search(r'(\d{1,2}):(\d{2})', text)
    if m: return int(m.group(1)), int(m.group(2))
    # "X AM/PM"
    m = re.search(r'(\d{1,2})\s*(am|pm)', text)
    if m:
        h = int(m.group(1))
        if m.group(2) == "pm" and h != 12: h += 12
        if m.group(2) == "am" and h == 12: h = 0
        return h, 0
    # Time of day words
    for word, (h, mn) in TIME_OF_DAY.items():
        if word in text: return h, mn
    return -1, 0

# ── Simple schedule store (when scheduler.py not available) ───────────
_SCHED_FILE = _CONFIG_DIR / "schedules.json"

def _load_schedules() -> list:
    try:
        if _SCHED_FILE.exists():
            return json.loads(_SCHED_FILE.read_text(encoding="utf-8"))
    except: pass
    return []

def _save_schedules(scheds: list):
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _SCHED_FILE.write_text(json.dumps(scheds, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log(f"schedule save error: {e}")

# ══════════════════════════════════════════════════════════════════════
#  TOOL HANDLERS
# ══════════════════════════════════════════════════════════════════════

def _t_sched_add(args: dict) -> str:
    task = args.get("task", "").strip()
    time_str = args.get("time", args.get("when", "")).strip()
    label = args.get("label", task[:40])
    if not task: return "ERROR: task required"

    # Use actual scheduler.py if available
    if _sched_mod:
        if hasattr(_sched_mod, "schedule_add"):
            result = _sched_mod.schedule_add(task, time_str, label=label)
            return json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
        if hasattr(_sched_mod, "t_schedule_add"):
            try:
                # Infer interval from time string
                parsed = _parse_time_natural(time_str or task)
                interval = parsed.get("interval_minutes", 60)
                result = _sched_mod.t_schedule_add(task, interval_minutes=interval, label=label)
                return str(result)
            except Exception as e:
                _log(f"scheduler.t_schedule_add error: {e}")

    # Fallback: parse and store
    parsed = _parse_time_natural(time_str or task)
    sched = {
        "id": int(time.time()),
        "task": task,
        "label": label,
        "time_str": time_str,
        "parsed": parsed,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active": True,
    }
    scheds = _load_schedules()
    scheds.append(sched)
    _save_schedules(scheds)
    return json.dumps({
        "success": True,
        "schedule_id": sched["id"],
        "label": label,
        "trigger": parsed.get("human_readable", "unknown"),
        "type": parsed.get("type"),
        "cron": parsed.get("cron"),
        "trigger_time": parsed.get("trigger_time"),
        "note": "⚠️ Start M4STCLAW bridge (start.bat) to actually execute scheduled tasks"
    }, ensure_ascii=False)


def _t_sched_list(args: dict) -> str:
    if _sched_mod and hasattr(_sched_mod, "t_schedule_list"):
        return str(_sched_mod.t_schedule_list())
    scheds = _load_schedules()
    active = [s for s in scheds if s.get("active", True)]
    return json.dumps({"schedules": active, "total": len(active)}, ensure_ascii=False, indent=2)


def _t_sched_remove(args: dict) -> str:
    sched_id = args.get("id") or args.get("schedule_id")
    if sched_id is None: return "ERROR: id required"
    if _sched_mod and hasattr(_sched_mod, "t_schedule_remove"):
        return str(_sched_mod.t_schedule_remove(int(sched_id)))
    scheds = _load_schedules()
    before = len(scheds)
    scheds = [s for s in scheds if s.get("id") != int(sched_id)]
    if len(scheds) < before:
        _save_schedules(scheds)
        return f"✅ Schedule {sched_id} removed"
    return f"Schedule {sched_id} not found"


def _t_sched_status(args: dict) -> str:
    if _sched_mod:
        status = {"scheduler_loaded": True}
        if hasattr(_sched_mod, "SCHEDULE_FILE"):
            status["schedule_file"] = str(_sched_mod.SCHEDULE_FILE)
    else:
        scheds = _load_schedules()
        status = {
            "scheduler_loaded": False,
            "note": "Set M4ST_BRIDGE_DIR to mast/bridge for full APScheduler support",
            "stored_schedules": len(scheds),
            "active_schedules": len([s for s in scheds if s.get("active")])
        }
    return json.dumps(status, ensure_ascii=False, indent=2)


def _t_sched_parse(args: dict) -> str:
    text = args.get("text", args.get("time", "")).strip()
    if not text: return "ERROR: text required"
    result = _parse_time_natural(text)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── MCP wiring ────────────────────────────────────────────────────────

_TOOLS = [
    ("sched_add",    "Add schedule in natural language. Hinglish supported: 'kal subah 9 baje', 'har Monday 10 AM', '15 minute mein'"),
    ("sched_list",   "List all active schedules"),
    ("sched_remove", "Remove a schedule by ID"),
    ("sched_status", "Scheduler health and active schedule count"),
    ("sched_parse",  "Parse a time string to structured format (no schedule created)"),
]

_SCHEMAS = {
    "sched_add":    {"type":"object","properties":{"task":{"type":"string","description":"Task to schedule"},"time":{"type":"string","description":"When to run: 'kal subah 9 baje', 'har Monday 10 AM', '30 minute mein'"},"label":{"type":"string"}},"required":["task"]},
    "sched_list":   {"type":"object","properties":{}},
    "sched_remove": {"type":"object","properties":{"id":{"type":"integer"}},"required":["id"]},
    "sched_status": {"type":"object","properties":{}},
    "sched_parse":  {"type":"object","properties":{"text":{"type":"string","description":"Time expression to parse"}},"required":["text"]},
}

_HANDLERS = {
    "sched_add":    _t_sched_add,
    "sched_list":   _t_sched_list,
    "sched_remove": _t_sched_remove,
    "sched_status": _t_sched_status,
    "sched_parse":  _t_sched_parse,
}

def handle(msg: dict):
    method = msg.get("method", "")
    rid = msg.get("id")
    if method == "initialize":
        mcp_initialize(rid, "scheduler", "3.0.0")
    elif method == "tools/list":
        mcp_tools_list(rid, _TOOLS, _SCHEMAS)
    elif method == "tools/call":
        name = msg.get("params",{}).get("name","")
        args = msg.get("params",{}).get("arguments",{})
        if name not in _HANDLERS:
            mcp_error(rid, -32601, f"Unknown tool: {name}"); return
        try:
            mcp_respond(rid, str(_HANDLERS[name](args)))
        except Exception as e:
            _log(f"{name} error: {e}")
            mcp_error(rid, -32000, str(e))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        print("scheduler_mcp: OK")
        print(f"  scheduler.py: {'✅ loaded' if _sched_mod else '⚠️  embedded fallback (Hinglish parser active)'}")
        # Test parse
        tests = ["kal subah 9 baje", "har Monday 10 AM", "30 minute mein", "roz raat 11 baje"]
        for t in tests:
            r = _parse_time_natural(t)
            print(f"  parse '{t}' → {r.get('human_readable','?')} [{r.get('type','?')}]")
        sys.exit(0)
    _log("scheduler MCP v3.0 | Hinglish time parsing active")
    mcp_loop("scheduler", handle)

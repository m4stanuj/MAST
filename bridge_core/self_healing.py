"""
M4ST Self-Healing Engine v1
============================
Jab koi tool fail ho:
  1. Error analyze karo (AI se)
  2. Fix suggest karo (different tool / different args)
  3. Retry karo (max 3 attempts)
  4. Alternative tool try karo agar available hai
  5. Final failure mein user-friendly message do

Features:
  - Error classification (timeout, wrong args, missing deps, network)
  - AI-powered fix suggestions
  - Alternative tool mapping
  - Retry with exponential backoff
  - Healing log (learn from fixes)
"""

import json
import time
import os
from typing import Callable, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Brain caller ──────────────────────────────────────────────────────
def _brain(prompt: str, max_tokens: int = 400) -> str:
    try:
        from smart_brain import smart_brain_call
        result = smart_brain_call(None,
            [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        return (result.get("message", {}).get("content") or "").strip()
    except Exception as e:
        return f"BRAIN_ERROR: {e}"

# ── Error classifier ──────────────────────────────────────────────────
ERROR_PATTERNS = {
    "missing_arg":    ["required", "missing", "argument", "parameter", "positional"],
    "not_found":      ["not found", "no such file", "FileNotFoundError", "path does not exist"],
    "network":        ["ConnectionError", "timeout", "connect", "unreachable", "HTTPError", "refused"],
    "permission":     ["permission", "Access Denied", "PermissionError", "not allowed"],
    "import_missing": ["ModuleNotFoundError", "ImportError", "No module"],
    "browser":        ["WebDriverException", "NoSuchElement", "StaleElement", "selenium"],
    "rate_limit":     ["rate limit", "429", "quota", "too many requests"],
    "wrong_type":     ["TypeError", "int()", "str()", "NoneType", "unexpected type"],
}

def classify_error_type(error_str: str) -> str:
    err_lower = error_str.lower()
    for etype, patterns in ERROR_PATTERNS.items():
        if any(p.lower() in err_lower for p in patterns):
            return etype
    return "unknown"

# ── Alternative tool map ──────────────────────────────────────────────
TOOL_ALTERNATIVES = {
    "browser_click":         ["t_tandem_click", "t_vision_click", "smart_click"],
    "browser_open":          ["t_tandem_navigate", "open_url"],
    "browser_fill":          ["t_tandem_type", "type_text"],
    "browser_get_text":      ["t_tandem_get_text", "t_tandem_snapshot"],
    "browser_screenshot":    ["take_screenshot", "t_tandem_screenshot"],
    "t_vision_click":        ["smart_click", "t_tandem_click", "click_mouse"],
    "search_web":            ["t_research", "t_quick_fact", "t_tandem_web_search"],
    "t_research":            ["search_web", "t_tandem_read_page", "t_quick_fact"],
    "run_command":           ["t_run_python", "t_code_agent"],
    "t_email_send":          ["t_telegram_send", "t_discord_send"],
    "t_twitter_post":        ["t_tandem_twitter_post"],
    "t_linkedin_post":       ["t_tandem_linkedin_post"],
    "t_whatsapp_send":       ["t_tandem_whatsapp_send"],
    "t_excel_create":        ["t_excel_smart_fill", "t_csv_to_excel"],
    "t_word_create":         ["t_word_smart_edit", "create_file"],
    "t_pdf_fill_form":       ["t_pdf_vision_fill", "t_pdf_to_word_fill"],
    "t_run_python":          ["run_command", "t_code_agent"],
}

# ── AI Fix Suggester ──────────────────────────────────────────────────
def ai_suggest_fix(tool_name: str, args: dict, error: str,
                   error_type: str) -> dict:
    """
    AI se fix suggest karwao.
    Returns: {"new_tool": str, "new_args": dict, "explanation": str}
    """
    alts = TOOL_ALTERNATIVES.get(tool_name, [])
    alt_hint = f"Alternative tools available: {', '.join(alts)}" if alts else ""

    prompt = f"""
M4ST tool failure analysis:

Tool: {tool_name}
Args: {json.dumps(args)}
Error: {error[:200]}
Error type: {error_type}
{alt_hint}

DIAGNOSIS:
- Error type "{error_type}" ka matlab kya hai?
- Args mein kya galat hai?
- Kya alternative approach hai?

FIX RULES:
- "missing_arg": required parameter add karo
- "not_found": path fix karo ya alternative dhundho
- "network": same tool retry karo (transient error)
- "browser": alternative selector ya tandem tool use karo
- "wrong_type": args type fix karo (str→int etc)
- "import_missing": alternative tool use karo jo installed ho

JSON only:
{{"new_tool": "tool_name", "new_args": {{}}, "explanation": "root cause + fix in 1 line"}}
"""
    raw = _brain(prompt, max_tokens=200)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        # Fallback to first alternative
        if alts:
            return {"new_tool": alts[0], "new_args": args, "explanation": "alternative tool"}
        return {"new_tool": tool_name, "new_args": args, "explanation": "retry same"}

# ── Healing log (learn from fixes) ───────────────────────────────────
_HEALING_LOG_PATH = os.path.join(ROOT, "healing_log.json")

def _load_healing_log() -> list:
    try:
        with open(_HEALING_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_healing_entry(tool: str, error_type: str,
                        fix_tool: str, fix_args: dict, success: bool):
    log = _load_healing_log()
    log.append({
        "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "orig_tool":  tool,
        "error_type": error_type,
        "fix_tool":   fix_tool,
        "fix_args":   fix_args,
        "success":    success
    })
    # Keep last 200 entries
    log = log[-200:]
    try:
        with open(_HEALING_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    except Exception as _e:
        print(f"[DEBUG] self_healing.py: {_e}")

def get_known_fix(tool: str, error_type: str) -> Optional[dict]:
    """Past healing log se known fix dhundho."""
    log = _load_healing_log()
    # Find most recent successful fix for same tool + error type
    for entry in reversed(log):
        if (entry["orig_tool"] == tool and
                entry["error_type"] == error_type and
                entry["success"]):
            return {"new_tool": entry["fix_tool"], "new_args": entry["fix_args"],
                    "explanation": "known fix from history"}
    return None

# ── Core: Self-Healing Execute ────────────────────────────────────────
# Known-good tool names cache (populated from server at runtime)
_KNOWN_TOOLS: set = set()

def register_known_tools(tool_names: set):
    """Server startup pe TOOLS dict se valid tool names register karo."""
    global _KNOWN_TOOLS
    _KNOWN_TOOLS = set(tool_names)

def _tool_exists(name: str) -> bool:
    """Check karo ki tool actually exist karta hai."""
    if not _KNOWN_TOOLS:
        return True  # Cache empty — optimistic, let run_tool handle it
    return name in _KNOWN_TOOLS

def heal_and_run(
    tool_name: str,
    args: dict,
    run_tool_fn: Callable,
    max_attempts: int = 3,
    backoff_sec: float = 1.0,
    on_retry: Callable = None
) -> tuple:
    """
    Tool ko self-healing ke saath execute karo.

    Returns:
        (result_str, success_bool, attempts_used)
    """
    current_tool = tool_name
    current_args = dict(args)
    last_error   = ""

    for attempt in range(1, max_attempts + 1):
        # Execute
        try:
            result = run_tool_fn(current_tool, current_args)
        except Exception as e:
            result = f"ERROR: {e}"

        # Success check
        if result and not str(result).startswith("ERROR"):
            if attempt > 1:
                _save_healing_entry(tool_name, classify_error_type(last_error),
                                    current_tool, current_args, True)
            return str(result), True, attempt

        last_error = str(result)
        error_type = classify_error_type(last_error)

        if attempt >= max_attempts:
            break

        # Notify caller
        if on_retry:
            on_retry(attempt, current_tool, current_args, last_error, error_type)

        # Network errors → just wait and retry same
        if error_type == "network":
            time.sleep(backoff_sec * attempt)
            continue

        # Rate limit → longer wait
        if error_type == "rate_limit":
            time.sleep(3.0 * attempt)
            continue

        # Check known fix first (fast, no AI call)
        known = get_known_fix(tool_name, error_type)
        if known:
            current_tool = known["new_tool"]
            current_args = known["new_args"]
            continue

        # AI-powered fix suggestion
        fix = ai_suggest_fix(current_tool, current_args, last_error, error_type)
        if fix:
            new_tool = fix.get("new_tool", current_tool)
            new_args = fix.get("new_args", current_args)
            # Validate suggested tool actually exists before switching
            if not _tool_exists(new_tool):
                print(f"[HEAL] Suggested tool '{new_tool}' not found — skipping")
            elif new_tool != current_tool or new_args != current_args:
                current_tool = new_tool
                current_args = new_args
                time.sleep(backoff_sec)
                continue

        # No fix found → backoff and retry same
        time.sleep(backoff_sec * attempt)

    # All attempts failed
    _save_healing_entry(tool_name, classify_error_type(last_error),
                        current_tool, current_args, False)
    return last_error, False, max_attempts

# ── Healing stats ─────────────────────────────────────────────────────
def get_healing_stats() -> dict:
    log = _load_healing_log()
    if not log:
        return {"total": 0, "success_rate": 0, "top_fixed_tools": []}

    total     = len(log)
    successes = sum(1 for e in log if e["success"])
    # Tool frequency
    tool_counts = {}
    for e in log:
        t = e["orig_tool"]
        tool_counts[t] = tool_counts.get(t, 0) + 1

    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "total": total,
        "success_rate": round(successes / total * 100, 1),
        "top_fixed_tools": [{"tool": t, "fixes": c} for t, c in top_tools]
    }

# Export
__all__ = [
    "heal_and_run", "classify_error_type", "ai_suggest_fix",
    "get_known_fix", "get_healing_stats", "TOOL_ALTERNATIVES"
]


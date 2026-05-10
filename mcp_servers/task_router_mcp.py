#!/usr/bin/env python3
"""
task_router_mcp.py — M4ST Task Router MCP v3.0
================================================
Universal task router — every message classified → routed to correct chain.
Skill-first: checks learned_skills.json before AI call.
SOUL-aware: SOUL_v3.md / SOUL.md loaded as system prompt.

Tools:
  task_route      — Classify + route to best AI chain (returns response)
  task_classify   — Classify only (no AI call)
  task_status     — Provider health + cache stats
  task_chat       — Full chat with SOUL persona + task routing
  task_skill_run  — Find and replay a learned skill
"""
import sys, os, json, time, re
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))

from _mcp_base import mcp_loop, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list

def _log(m): print(f"[task_router] {m}", file=sys.stderr, flush=True)

# ── Brain ─────────────────────────────────────────────────────────────
def _brain(messages: list, task: str = "auto", max_tokens: int = 800) -> str:
    try:
        from llm_fallback import chat_complete
        return chat_complete(messages, max_tokens=max_tokens, task=task, use_cache=True)
    except Exception as e:
        return f"ERROR: {e}"

# ── SOUL loader ───────────────────────────────────────────────────────
_soul_cache = {"text": "", "ts": 0}

def _load_soul() -> str:
    now = time.time()
    if _soul_cache["ts"] + 60 > now:
        return _soul_cache["text"]
    for p in [_CONFIG_DIR / "SOUL_MAST.md", _CONFIG_DIR / "SOUL.md",
              Path(__file__).parent.parent / "SOUL_MAST.md", Path(__file__).parent.parent / "SOUL.md"]:
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            _soul_cache.update({"text": text, "ts": now})
            return text
    return ""

# ── Task classifier ───────────────────────────────────────────────────
# Keywords from actual llm_fallback._TASK_KEYWORDS (English + Hinglish)
TASK_SIGNALS = {
    "pentest":  ["recon", "scan", "nmap", "osint", "pentest", "vulnerability", "cve",
                 "exploit", "shodan", "subfinder", "nikto", "nuclei", "vuln", "finding",
                 "/recon", "/scan", "/cve", "/pt", "target pe", "scan karo", "recon karo"],
    "vision":   ["screenshot", "image", "screen", "visual", "look at", "describe image",
                 "gui", "click where", "find button", "dekho", "dikhao", "kya dikh raha",
                 "screen pe kya", "capture"],
    "agent":    ["automate", "step by step", "plan and execute", "workflow", "pipeline",
                 "multi-step", "/ultrawork", "ultrawork", "khud karo", "automate karo",
                 "background mein", "har baar", "batch", "sisyphus"],
    "code":     ["code", "function", "script", "debug", "refactor", "implement", "class", "galat hai",
                 "python", "javascript", "typescript", "bug", "error", "compile", "syntax",
                 "likho code", "banao", "fix karo", "repair", "kya galat hai", "program", "likh"],
    "research": ["research", "find information", "search", "deep dive", "comprehensive", "dhundho",
                 "dhundo", "pata lagao", "information chahiye", "latest news", "kya hain",
                 "sab kuch batao", "multiple sources", "investigate"],
    "write":    ["write", "draft", "compose", "essay", "article", "blog", "email",
                 "document", "report", "summary", "likho", "email banao", "draft karo",
                 "document banao", "letter", "proposal", "readme", "notes"],
    "reason":   ["reason", "analyze", "explain why", "think step", "solve", "math", "logic",
                 "compare", "pros and cons", "evaluate", "kyun", "kaise", "samjhao",
                 "analyze karo", "sochke bata", "difference", "better kaunsa"],
    "speed":    ["quick", "fast", "jaldi", "jaldi bata", "short answer", "briefly",
                 "seedha bata", "ek line mein", "tldr", "simple", "bas bata", "chhota"],
}

def classify_task(message: str) -> str:
    msg = message.lower()
    scores = {t: sum(1 for sig in sigs if sig in msg) for t, sigs in TASK_SIGNALS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "speed"

# ── Skills search ─────────────────────────────────────────────────────
_SKILLS_FILE = _CONFIG_DIR / "learned_skills.json"

def _search_skills(query: str) -> list:
    try:
        if not _SKILLS_FILE.exists(): return []
        skills = json.loads(_SKILLS_FILE.read_text(encoding="utf-8"))
        q_words = set(re.sub(r'[^\w\s]', ' ', query.lower()).split())
        hits = []
        for s in skills:
            kws = set(" ".join(s.get("keywords", []) + s.get("trigger_phrases", [])).lower().split())
            score = len(q_words & kws) / max(len(q_words | kws), 1)
            if score > 0.35:
                hits.append((score, s))
        return [s for _, s in sorted(hits, key=lambda x: -x[0])[:3]]
    except Exception:
        return []

# ══════════════════════════════════════════════════════════════════════
#  TOOL HANDLERS
# ══════════════════════════════════════════════════════════════════════

def _t_task_route(args: dict) -> str:
    message = args.get("message", "").strip()
    task_hint = args.get("task_hint", "auto")
    use_soul = args.get("use_soul", True)
    max_tokens = int(args.get("max_tokens", 800))
    if not message: return "ERROR: message required"

    t0 = time.time()
    # 1. Check skills DB first
    skill_hit = None
    skills = _search_skills(message)
    if skills:
        skill_hit = skills[0].get("name")
        _log(f"skill match: {skill_hit}")

    # 2. Classify
    task = task_hint if task_hint != "auto" else classify_task(message)
    _log(f"routed: task={task}")

    # 3. Build messages
    messages = []
    if use_soul:
        soul = _load_soul()
        if soul:
            # Only first 40 lines as system prompt (keep tokens low)
            soul_short = "\n".join(soul.split("\n")[:40])
            messages.append({"role": "system", "content": soul_short})
    messages.append({"role": "user", "content": message})

    # 4. Call brain
    response = _brain(messages, task=task, max_tokens=max_tokens)
    elapsed = int((time.time() - t0) * 1000)

    return json.dumps({
        "response": response,
        "task_type": task,
        "latency_ms": elapsed,
        "skill_match": skill_hit,
    }, ensure_ascii=False)


def _t_task_classify(args: dict) -> str:
    message = args.get("message", "")
    if not message: return "ERROR: message required"
    task = classify_task(message)
    matched = [sig for sig in TASK_SIGNALS.get(task, []) if sig in message.lower()]
    chain_desc = {
        "pentest":  "DeepSeek-R1 → Kimi K2 → Nemotron → Groq",
        "vision":   "Gemini 2.5 Flash → MiMo-Omni → Llama4",
        "agent":    "Kimi K2 → Qwen3-235B → Nemotron → Groq",
        "code":     "Kimi K2 → Qwen3-Coder → MiMo-Pro → Nemotron",
        "research": "Kimi K2 → DeepSeek-R1 → Nemotron → Gemini 2.5 Pro",
        "write":    "Cerebras → Groq → Nemotron → MiniMax",
        "reason":   "Kimi K2 → DeepSeek-R1 → Nemotron → Qwen3-235B",
        "speed":    "Groq → Cerebras → Nemotron → MiniMax",
    }
    return json.dumps({
        "task_type": task,
        "chain": chain_desc.get(task, "Default chain"),
        "signals_matched": matched,
    }, ensure_ascii=False)


def _t_task_status(args: dict) -> str:
    try:
        from llm_fallback import status_report
        return status_report()
    except Exception as e:
        return f"Status unavailable: {e}"


def _t_task_chat(args: dict) -> str:
    """Full chat with SOUL + routing — used for all-purpose M4STCLAW chat."""
    message = args.get("message", "").strip()
    history = args.get("history", [])
    if not message: return "ERROR: message required"
    task = classify_task(message)
    messages = []
    soul = _load_soul()
    if soul:
        messages.append({"role": "system", "content": "\n".join(soul.split("\n")[:40])})
    messages.extend(history[-6:])  # keep last 3 turns for context
    messages.append({"role": "user", "content": message})
    return _brain(messages, task=task, max_tokens=int(args.get("max_tokens", 1000)))


def _t_task_skill_run(args: dict) -> str:
    query = args.get("query", args.get("message", "")).strip()
    if not query: return "ERROR: query required"
    skills = _search_skills(query)
    if not skills:
        return json.dumps({"found": False, "message": "No matching skill found. Try task_route instead."})
    best = skills[0]
    # Would normally replay the tool_chain — here we summarize
    return json.dumps({
        "found": True,
        "skill_id": best.get("skill_id"),
        "name": best.get("name"),
        "description": best.get("description"),
        "category": best.get("category"),
        "tool_chain": best.get("tool_chain", []),
        "use_count": best.get("use_count", 1),
        "created_at": best.get("created_at"),
    }, ensure_ascii=False, indent=2)


# ── MCP wiring ────────────────────────────────────────────────────────

_TOOLS = [
    ("task_route",     "Classify message + route to best AI chain. Returns response + task_type + latency."),
    ("task_classify",  "Classify message to task type only — no AI call. Returns task_type + chain + signals."),
    ("task_status",    "Provider health, cache stats, available chains."),
    ("task_chat",      "Full chat with M4STCLAW SOUL persona + auto task routing. Supports history."),
    ("task_skill_run", "Search learned skills DB and replay best match for query."),
]

_SCHEMAS = {
    "task_route": {
        "type": "object",
        "properties": {
            "message":    {"type": "string"},
            "task_hint":  {"type": "string", "description": "auto|speed|reason|code|vision|research|write|agent|pentest|hinglish"},
            "use_soul":   {"type": "boolean"},
            "max_tokens": {"type": "integer"},
        },
        "required": ["message"]
    },
    "task_classify": {"type":"object","properties":{"message":{"type":"string"}},"required":["message"]},
    "task_status":   {"type":"object","properties":{}},
    "task_chat": {
        "type": "object",
        "properties": {
            "message":    {"type": "string"},
            "history":    {"type": "array", "description": "Previous messages [{role, content}]"},
            "max_tokens": {"type": "integer"},
        },
        "required": ["message"]
    },
    "task_skill_run": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},
}

_HANDLERS = {
    "task_route":     _t_task_route,
    "task_classify":  _t_task_classify,
    "task_status":    _t_task_status,
    "task_chat":      _t_task_chat,
    "task_skill_run": _t_task_skill_run,
}

def handle(msg: dict):
    method = msg.get("method", "")
    rid = msg.get("id")
    if method == "initialize":
        mcp_initialize(rid, "task-router", "3.0.0")
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
        print("task_router_mcp: OK")
        soul = _load_soul()
        print(f"  SOUL loaded: {'✅' if soul else '❌ (SOUL_MAST.md not found at ' + str(_CONFIG_DIR) + ')'}")
        # Test classification
        tests = [("recon karo example.com","pentest"),("screenshot lo","vision"),
                 ("code likho Python","code"),("jaldi bata","speed"),("samjhao mujhe","reason")]
        for msg, exp in tests:
            got = classify_task(msg)
            print(f"  {'✅' if got==exp else '⚠️ '} '{msg}' → {got}")
        sys.exit(0)
    _log("task-router MCP v3.0 | SOUL hot-reload active")
    mcp_loop("task-router", handle)

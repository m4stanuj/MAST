#!/usr/bin/env python3
"""
m4st_agent_mcp.py — M4ST Agent Orchestrator MCP v3.0
======================================================
Wraps actual M4STCLAW agents.py — 10 specialized agents with real system
prompts + OMO Sisyphus parallel orchestrator.

Tools:
  agent_switch     — Switch to a named agent mode
  agent_ask        — Ask a specific agent a question
  agent_current    — Get current active agent
  agent_list       — List all agents with triggers
  agent_ultrawork  — OMO Sisyphus parallel orchestration
  agent_plan       — Plan subtasks for a goal
  agent_multi      — Run multiple agents in parallel

Agents (from M4STCLAW agents.py):
  jarvis, coder, researcher, hacker, designer, analyst, writer, teacher, trader, planner
"""
import sys, os, json, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))
_BRIDGE_DIR = Path(os.environ.get("M4ST_BRIDGE_DIR", ""))

# Try to load actual agents.py from M4STCLAW
_agents_mod = None
_BRIDGE_CANDIDATES = [
    _BRIDGE_DIR,
    Path.home() / ".config" / "opencode" / "bridge_core",
    Path(__file__).parent / "bridge_core",
    Path(__file__).parent.parent / "bridge_core",
]
for c in _BRIDGE_CANDIDATES:
    if c and (c / "agents.py").exists():
        sys.path.insert(0, str(c))
        try:
            import agents as _agents_mod
            break
        except Exception:
            pass

sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_loop, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list

def _log(m): print(f"[agent_mcp] {m}", file=sys.stderr, flush=True)

# ── Agent registry (actual M4STCLAW agents with real system prompts) ──
# If agents.py found, use it. Otherwise use this embedded copy.
if _agents_mod and hasattr(_agents_mod, "AGENTS"):
    AGENTS = _agents_mod.AGENTS
    _log(f"✅ agents.py loaded — {len(AGENTS)} agents")
else:
    _log("⚠️  agents.py not found — using embedded definitions")
    AGENTS = {
        "jarvis": {
            "name": "MAST Jarvis", "emoji": "🤖",
            "triggers": ["jarvis", "normal mode", "default", "wapas", "m4stclaw mode"],
            "task_type": "speed",
            "system": "Tu M4STCLAW hai — Mast ka personal AI operator. Hinglish mein baat kar.\nDirect, helpful, no filler. Tools freely use kar. Kaam pehle, explanation baad mein.\nJugaad mindset — free/local solutions prefer karo. Always honest.",
        },
        "coder": {
            "name": "Senior Dev", "emoji": "👨‍💻",
            "triggers": ["coder mode", "senior dev", "developer mode", "code mode", "coding"],
            "task_type": "code",
            "system": "You are a senior software engineer with 10+ years experience.\nWrite clean, production-grade code. Always provide working, tested code.\nTech: Python, JavaScript/TypeScript, React, FastAPI, Docker.\nPrefer simple solutions. Add proper error handling. Consider edge cases.",
        },
        "researcher": {
            "name": "Research Analyst", "emoji": "🔬",
            "triggers": ["research mode", "researcher", "analyst mode", "investigate"],
            "task_type": "research",
            "system": "You are a meticulous research analyst. For every research task:\n1. Search multiple sources\n2. Cross-verify key facts\n3. Note conflicting information\n4. Cite sources clearly\n5. Distinguish facts from opinions\nWrite structured reports: Summary, Key Findings, Analysis, Sources.\nIf uncertain, say so explicitly. Never hallucinate sources.",
        },
        "hacker": {
            "name": "CEH Security Analyst + CAI", "emoji": "🔐",
            "triggers": ["hacker mode", "security mode", "ceh mode", "pentest mode", "ethical hacker",
                        "osint mode", "recon mode", "vuln mode"],
            "task_type": "pentest",
            "system": "You are a Certified Ethical Hacker (CEH) and OSINT analyst.\nYou have access to M4STCLAW CAI tools: recon_*, vuln_*, pentest_memory.\nWorkflow: session start → recon → vuln scan → findings → session end.\nALWAYS: authorized systems only, explain vuln AND remediation, use OWASP/MITRE/CVE.\nRisk rating: Critical/High/Med/Low. Save everything to pentest_memory.\nHinglish OK. Technical + concise.",
            "cai_tools": ["pt_recon_summary", "pt_vuln_nmap", "pt_vuln_nuclei", "pt_vuln_cve",
                          "pt_session_start", "pt_finding_add", "pt_context_get"],
        },
        "designer": {
            "name": "Frontend Wizard", "emoji": "🎨",
            "triggers": ["designer mode", "frontend", "ui mode", "css expert", "web dev"],
            "task_type": "code",
            "system": "You are an expert frontend developer obsessed with beautiful, performant UIs.\nExpertise: HTML5, CSS3, JavaScript, React, Tailwind, Framer Motion.\nMobile-first, responsive, accessible (WCAG 2.1 AA).\nModern aesthetic — avoid generic AI-slop design.\nReal working code, no placeholders. Prefer dark themes, glassmorphism, micro-interactions.",
        },
        "analyst": {
            "name": "Data Analyst", "emoji": "📊",
            "triggers": ["analyst mode", "data mode", "analysis mode", "chart mode"],
            "task_type": "reason",
            "system": "You are a senior data analyst.\n1. Understand data structure\n2. Clean and validate data\n3. Apply appropriate analysis (stats, trends, correlations)\n4. Create clear visualizations (suggest chart types)\n5. Draw actionable insights\nTools: pandas, numpy, matplotlib, seaborn, plotly.\nAlways explain what numbers mean, flag statistical limitations.",
        },
        "writer": {
            "name": "Content Writer", "emoji": "✍️",
            "triggers": ["writer mode", "content mode", "copywriter", "write mode", "blog mode"],
            "task_type": "write",
            "system": "You are an expert content writer and copywriter.\nHook reader in first sentence. Clear, active voice. SEO-friendly when appropriate.\nStyles: blog posts, social media, email marketing, product descriptions, ad copy.\nAlways ask: Will this resonate with the target audience?",
        },
        "teacher": {
            "name": "Patient Teacher", "emoji": "📚",
            "triggers": ["teacher mode", "explain mode", "sikhao", "samjhao", "beginner"],
            "task_type": "speed",
            "system": "You are a patient, clear teacher.\n1. Start with simple analogy\n2. Build up complexity gradually\n3. Use everyday examples\n4. Check understanding with questions\n5. Summarize key points\nLanguage: Hinglish preferred. Never assume prior knowledge.",
        },
        "trader": {
            "name": "Market Analyst", "emoji": "📈",
            "triggers": ["trader mode", "market mode", "stocks mode", "trading mode"],
            "task_type": "research",
            "system": "You are a market analyst (NOT financial advisor).\nProvide: technical analysis, fundamental analysis, market sentiment.\nALWAYS include: 'This is analysis only, not financial advice. DYOR.'\nFor Indian markets: NSE/BSE, Nifty, Sensex context. Show bull AND bear cases.",
        },
        "planner": {
            "name": "Project Planner", "emoji": "📋",
            "triggers": ["planner mode", "project mode", "planning mode", "organize"],
            "task_type": "agent",
            "system": "You are an expert project manager.\n1. Break into phases and milestones\n2. Estimate time and resources (realistic)\n3. Identify dependencies and blockers\n4. Define success criteria\n5. Risk assessment\nOutput: structured plan with timeline, priorities (P0/P1/P2), next actions.\nPrefer MVP approach — ship fast, iterate.",
        },
    }

# ── Active agent state ────────────────────────────────────────────────
_current_agent = "jarvis"
_agent_lock = threading.Lock()

# ── Brain ─────────────────────────────────────────────────────────────
def _brain(prompt: str, task: str = "speed", system: str = "", max_tokens: int = 800) -> str:
    # If agents.py loaded, use its _brain
    if _agents_mod and hasattr(_agents_mod, "_brain"):
        return _agents_mod._brain(prompt, task_type=task, system=system, max_tokens=max_tokens)
    try:
        from llm_fallback import chat_complete
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return chat_complete(messages, max_tokens=max_tokens, task=task, use_cache=False)
    except Exception as e:
        return f"ERROR: {e}"

import re

def _detect_agent(message: str) -> str:
    msg = message.lower()
    for aid, agent in AGENTS.items():
        if any(t in msg for t in agent.get("triggers", [])):
            return aid
    return _current_agent

# ── SOUL loader (for persona injection) ──────────────────────────────
def _soul_system() -> str:
    for p in [_CONFIG_DIR / "SOUL_MAST.md", _CONFIG_DIR / "SOUL.md", Path(__file__).parent.parent / "SOUL_MAST.md", Path(__file__).parent.parent / "SOUL.md"]:
        if p.exists():
            return "\n".join(p.read_text(encoding="utf-8").split("\n")[:30])
    return ""

# ══════════════════════════════════════════════════════════════════════
#  TOOL HANDLERS
# ══════════════════════════════════════════════════════════════════════

def _t_agent_switch(args: dict) -> str:
    agent_name = args.get("agent", "").lower().strip()
    for aid, agent in AGENTS.items():
        if aid == agent_name or any(t in agent_name for t in agent.get("triggers", [])):
            global _current_agent
            with _agent_lock:
                _current_agent = aid
            return f"{agent['emoji']} Switched to {agent['name']} mode"
    return f"Agent '{agent_name}' not found. Available: {', '.join(AGENTS.keys())}"


def _t_agent_ask(args: dict) -> str:
    agent_name = args.get("agent", _current_agent).lower()
    question = args.get("question", args.get("message", "")).strip()
    if not question: return "ERROR: question/message required"
    # Use actual agents.py t_ask_agent if available
    if _agents_mod and hasattr(_agents_mod, "t_ask_agent"):
        return _agents_mod.t_ask_agent(agent_name, question)
    agent = AGENTS.get(agent_name, AGENTS.get(_current_agent, AGENTS["jarvis"]))
    result = _brain(question, task=agent.get("task_type", "speed"),
                    system=agent.get("system", ""), max_tokens=args.get("max_tokens", 800))
    return f"{agent['emoji']} **{agent['name']}**:\n{result}"


def _t_agent_current(args: dict) -> str:
    with _agent_lock:
        agent = AGENTS.get(_current_agent, AGENTS["jarvis"])
    return json.dumps({
        "agent_id": _current_agent,
        "name": agent["name"],
        "emoji": agent["emoji"],
        "task_type": agent.get("task_type"),
        "triggers": agent.get("triggers", []),
    }, ensure_ascii=False)


def _t_agent_list(args: dict) -> str:
    rows = []
    for aid, agent in AGENTS.items():
        rows.append({
            "id": aid, "name": agent["name"], "emoji": agent["emoji"],
            "task_chain": agent.get("task_type"), "triggers": agent.get("triggers", [])[:3],
            "active": aid == _current_agent,
        })
    return json.dumps(rows, ensure_ascii=False, indent=2)


def _t_agent_plan(args: dict) -> str:
    goal = args.get("goal", "").strip()
    max_agents = min(int(args.get("max_agents", 4)), 6)
    if not goal: return "ERROR: goal required"

    # Use actual plan_execute_verify if available
    if _agents_mod and hasattr(_agents_mod, "plan_execute_verify") and args.get("execute", False):
        return _agents_mod.plan_execute_verify(goal)

    agent_list = "\n".join(f"- {k}: {v['name']} ({v.get('task_type')})" for k, v in AGENTS.items())
    plan_prompt = f"""Goal: {goal}

Available agents:
{agent_list}

Break this into {max_agents} or fewer subtasks. Each subtask to best agent.
Return ONLY valid JSON (no markdown fences):
{{
  "complexity": "simple|medium|complex",
  "subtasks": [
    {{"agent": "jarvis", "task": "specific task", "depends_on": []}},
    {{"agent": "coder", "task": "specific task", "depends_on": [0]}}
  ],
  "parallel_groups": [[0], [1, 2], [3]]
}}"""
    raw = _brain(plan_prompt, task="agent", max_tokens=600)
    # Parse JSON
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"): p = p[4:].strip()
            try: return json.dumps({"goal": goal, "plan": json.loads(p)}, ensure_ascii=False, indent=2)
            except: continue
    try:
        import re as _re
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if m:
            plan = json.loads(m.group())
            plan["goal"] = goal
            return json.dumps(plan, ensure_ascii=False, indent=2)
    except: pass
    # Fallback plan
    return json.dumps({"goal": goal, "plan": {
        "complexity": "medium",
        "subtasks": [
            {"agent": "planner", "task": f"Break down: {goal}", "depends_on": []},
            {"agent": "coder" if "code" in goal.lower() else "researcher", "task": f"Execute: {goal}", "depends_on": [0]},
            {"agent": "analyst", "task": "Review and validate", "depends_on": [1]},
        ],
        "parallel_groups": [[0], [1], [2]]
    }}, ensure_ascii=False, indent=2)


def _run_agent(agent_id: str, task: str, context: str = "") -> dict:
    t0 = time.time()
    agent = AGENTS.get(agent_id, AGENTS["jarvis"])
    # Use actual agents.py if available
    if _agents_mod and hasattr(_agents_mod, "t_ask_agent"):
        prompt = f"{context}\n\n{task}" if context else task
        result = _agents_mod.t_ask_agent(agent_id, prompt)
    else:
        prompt = f"Goal context: {context}\n\nYour task: {task}" if context else f"Task: {task}"
        result = _brain(prompt, task=agent.get("task_type", "speed"),
                        system=agent.get("system", ""), max_tokens=600)
    return {
        "agent": agent_id, "name": agent["name"], "emoji": agent["emoji"],
        "task": task, "result": result, "latency_ms": int((time.time()-t0)*1000),
        "success": not (result or "").startswith("ERROR"),
    }


def _t_agent_multi(args: dict) -> str:
    agents_list = args.get("agents", ["jarvis"])
    task = args.get("task", "").strip()
    if not task: return "ERROR: task required"
    # Use actual multi_agent_run if available
    if _agents_mod and hasattr(_agents_mod, "multi_agent_run"):
        return _agents_mod.multi_agent_run(task, agents=agents_list)
    results = []
    with ThreadPoolExecutor(max_workers=min(len(agents_list), 4)) as ex:
        futures = {ex.submit(_run_agent, aid, task): aid for aid in agents_list if aid in AGENTS}
        for fut in as_completed(futures, timeout=60):
            try: results.append(fut.result(timeout=5))
            except Exception as e: results.append({"agent": futures[fut], "result": f"ERROR: {e}", "success": False})
    return json.dumps({"task": task, "results": results}, ensure_ascii=False, indent=2)


def _t_agent_ultrawork(args: dict) -> str:
    goal = args.get("goal", "").strip()
    max_agents = min(int(args.get("max_agents", 4)), 6)
    timeout_s = min(int(args.get("timeout_seconds", 120)), 300)
    if not goal: return "ERROR: goal required"

    # Use actual plan_execute_verify from agents.py
    if _agents_mod and hasattr(_agents_mod, "plan_execute_verify"):
        _log(f"ultrawork via agents.py: {goal[:60]}")
        return _agents_mod.plan_execute_verify(goal, max_iterations=3)

    _log(f"ultrawork fallback: {goal[:60]}")
    t0 = time.time()

    # Plan
    plan_raw = _t_agent_plan({"goal": goal, "max_agents": max_agents})
    try:
        plan_data = json.loads(plan_raw)
        plan = plan_data.get("plan", plan_data)
        subtasks = plan.get("subtasks", [])
    except Exception:
        subtasks = [{"agent": "jarvis", "task": goal, "depends_on": []}]

    if not subtasks:
        return f"Planning failed for: {goal}"

    # Execute
    results = []
    completed = {}
    for group_idx, group in enumerate(plan.get("parallel_groups", [[i] for i in range(len(subtasks))])):
        group_tasks = [(i, subtasks[i]) for i in group if i < len(subtasks)]
        if len(group_tasks) == 1:
            idx, st = group_tasks[0]
            ctx = "\n".join(completed[d]["result"][:300] for d in st.get("depends_on", []) if d in completed)
            res = _run_agent(st.get("agent","jarvis"), st.get("task",""), ctx)
            completed[idx] = res; results.append(res)
        else:
            with ThreadPoolExecutor(max_workers=min(len(group_tasks), 4)) as ex:
                futs = {}
                for idx, st in group_tasks:
                    ctx = "\n".join(completed[d]["result"][:300] for d in st.get("depends_on",[]) if d in completed)
                    futs[ex.submit(_run_agent, st.get("agent","jarvis"), st.get("task",""), ctx)] = idx
                for fut in as_completed(futs, timeout=timeout_s):
                    idx = futs[fut]
                    try: res = fut.result(timeout=5)
                    except Exception as e: res = {"agent":"?","result":f"ERROR:{e}","success":False}
                    completed[idx] = res; results.append(res)

    # Synthesize
    summary_parts = [f"{r.get('emoji','🤖')} {r.get('name')}: {r.get('result','')[:400]}" for r in results if r.get("success")]
    synthesis = _brain(
        f"Goal: {goal}\n\n" + "\n\n".join(summary_parts) + "\n\nSynthesize into coherent final response:",
        task="agent", max_tokens=1000
    )
    return json.dumps({
        "goal": goal,
        "agents_used": [r.get("agent") for r in results],
        "individual_results": results,
        "synthesis": synthesis,
        "total_time_ms": int((time.time()-t0)*1000),
    }, ensure_ascii=False, indent=2)


# ── MCP wiring ────────────────────────────────────────────────────────

_TOOLS = [
    ("agent_switch",    "Switch to a named agent mode (jarvis/coder/hacker/researcher/designer/analyst/writer/teacher/trader/planner)"),
    ("agent_ask",       "Ask a specific agent a question — uses that agent's system prompt and task chain"),
    ("agent_current",   "Get currently active agent info"),
    ("agent_list",      "List all available agents with their triggers and task chains"),
    ("agent_plan",      "Plan subtasks for a complex goal — assigns to best agents"),
    ("agent_multi",     "Run multiple agents in parallel on the same task"),
    ("agent_ultrawork", "OMO Sisyphus full orchestration — plan → parallel execute → synthesize"),
]

_SCHEMAS = {
    "agent_switch":    {"type":"object","properties":{"agent":{"type":"string","description":f"Agent: {', '.join(AGENTS.keys())}"}},"required":["agent"]},
    "agent_ask":       {"type":"object","properties":{"agent":{"type":"string"},"question":{"type":"string"},"max_tokens":{"type":"integer"}},"required":["question"]},
    "agent_current":   {"type":"object","properties":{}},
    "agent_list":      {"type":"object","properties":{}},
    "agent_plan":      {"type":"object","properties":{"goal":{"type":"string"},"max_agents":{"type":"integer"},"execute":{"type":"boolean"}},"required":["goal"]},
    "agent_multi":     {"type":"object","properties":{"agents":{"type":"array","items":{"type":"string"}},"task":{"type":"string"}},"required":["task"]},
    "agent_ultrawork": {"type":"object","properties":{"goal":{"type":"string"},"max_agents":{"type":"integer"},"timeout_seconds":{"type":"integer"}},"required":["goal"]},
}

_HANDLERS = {
    "agent_switch":    _t_agent_switch,
    "agent_ask":       _t_agent_ask,
    "agent_current":   _t_agent_current,
    "agent_list":      _t_agent_list,
    "agent_plan":      _t_agent_plan,
    "agent_multi":     _t_agent_multi,
    "agent_ultrawork": _t_agent_ultrawork,
}

def handle(msg: dict):
    method = msg.get("method", "")
    rid = msg.get("id")
    if method == "initialize":
        mcp_initialize(rid, "m4st-agents", "1.0.0")
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
        print("m4st_agent_mcp: OK")
        print(f"  agents.py loaded: {'✅' if _agents_mod else '⚠️  (embedded fallback active)'}")
        print(f"  agents available: {', '.join(AGENTS.keys())}")
        sys.exit(0)
    _log(f"agents MCP v3.0 | agents.py={'loaded' if _agents_mod else 'embedded'}")
    mcp_loop("m4st-agents", handle)

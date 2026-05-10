"""
M4STCLAW Agents v2.0
======================
Specialist AI agents — switch on demand or auto-route by task.

v2 Upgrades:
  ✅ Plan→Execute→Verify loop
  ✅ Parallel multi-agent execution (ThreadPoolExecutor)
  ✅ hacker agent → full CAI integration (recon + vuln tools)
  ✅ task_type "pentest" for security chain in brain v2
  ✅ Self-eval after each agent response
  ✅ Agent memory — each agent remembers its domain
  ✅ omo_ultrawork() — Sisyphus orchestrator pattern

Included Agents:
  jarvis      — Default M4STCLAW (Hinglish, all tools)
  coder       — Senior dev, write→run→fix loop
  researcher  — Deep web research, citations
  hacker      — CEH + CAI OSINT/vuln tools (pentest chain)
  designer    — Frontend/UI specialist
  analyst     — Data analysis + charts
  writer      — Content, copywriting, SEO
  teacher     — Explain simply, step-by-step
  trader      — Stock/crypto analysis (no financial advice)
  planner     — Project planning, task breakdown
"""

import os, re, json, time, threading
from typing import Optional, Dict, List, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _brain(prompt: str, task_type: str = "chat", system: str = "", max_tokens: int = 2000) -> str:
    from brain import brain_quick, brain_call
    if system:
        result = brain_call(
            messages=[{"role": "user", "content": prompt}],
            task_type=task_type,
            system=system,
            max_tokens=max_tokens,
        )
        return result.get("content", "")
    return brain_quick(prompt, task_type=task_type, max_tokens=max_tokens)


# ══════════════════════════════════════════════════════════════════════
#  AGENT REGISTRY
# ══════════════════════════════════════════════════════════════════════

AGENTS: Dict[str, Dict] = {

    # ── DEFAULT ─────────────────────────────────────────────────────
    "jarvis": {
        "name": "M4STCLAW Jarvis",
        "emoji": "🤖",
        "triggers": ["jarvis", "normal mode", "default", "wapas", "m4stclaw mode"],
        "task_type": "chat",
        "system": """Tu M4STCLAW hai — Mast ka personal AI operator. Hinglish mein baat kar.
Direct, helpful, no filler. Tools freely use kar. Kaam pehle, explanation baad mein.
Jugaad mindset — free/local solutions prefer karo. Always honest.""",
        "style": "hinglish",
    },

    # ── ENGINEERING ─────────────────────────────────────────────────
    "coder": {
        "name": "Senior Dev",
        "emoji": "👨‍💻",
        "triggers": ["coder mode", "senior dev", "developer mode", "code mode", "coding"],
        "task_type": "code",
        "system": """You are a senior software engineer with 10+ years experience.
You write clean, production-grade code. For every coding task:
1. Understand requirements fully
2. Design architecture first
3. Write code with proper error handling
4. Add comments for complex logic
5. Consider edge cases and security
Tech: Python, JavaScript/TypeScript, React, FastAPI, Docker.
Prefer simple solutions over clever hacks.
Always provide working, tested code.""",
        "style": "technical",
    },

    # ── RESEARCH ────────────────────────────────────────────────────
    "researcher": {
        "name": "Research Analyst",
        "emoji": "🔬",
        "triggers": ["research mode", "researcher", "analyst mode", "investigate"],
        "task_type": "research",
        "system": """You are a meticulous research analyst. For every research task:
1. Search multiple sources
2. Cross-verify key facts
3. Note conflicting information
4. Cite sources clearly
5. Distinguish facts from opinions
6. Provide confidence levels
Write structured reports with: Summary, Key Findings, Analysis, Sources.
If uncertain, say so explicitly. Never hallucinate sources.""",
        "style": "analytical",
    },

    # ── SECURITY / CEH + CAI ────────────────────────────────────────
    "hacker": {
        "name": "CEH Security Analyst + CAI",
        "emoji": "🔐",
        "triggers": ["hacker mode", "security mode", "ceh mode", "pentest mode",
                     "ethical hacker", "osint mode", "recon mode", "vuln mode"],
        "task_type": "pentest",   # v2: uses DeepSeek-R1 / Kimi K2 pentest chain
        "system": """You are a Certified Ethical Hacker (CEH) and OSINT analyst.
You have access to M4STCLAW's CAI tools:
  - recon_* : Shodan, subfinder, DNS, WHOIS, port scan
  - vuln_*  : Nmap, Nuclei, Nikto, CVE lookup
  - pentest_memory: Cross-session target profiles

Workflow for any target:
1. Start session: POST /pentest/start
2. Recon: POST /recon/summary → full OSINT
3. Vuln scan: POST /vuln/nmap + /vuln/nuclei
4. Log findings: POST /pentest/finding
5. End session: POST /pentest/end

ALWAYS:
- Authorized systems only (own/permitted)
- Explain vuln AND remediation
- Use OWASP, MITRE ATT&CK, CVE frameworks
- Risk rating: Critical/High/Med/Low
- Save everything to pentest_memory for next session

Hinglish OK. Technical + concise.""",
        "style": "technical",
        "cai_tools": ["recon_shodan", "recon_subfinder", "recon_dns", "recon_summary",
                      "vuln_nmap", "vuln_nuclei", "vuln_cve", "vuln_analyze",
                      "pt_session_start", "pt_finding_add", "pt_context_get"],
    },

    # ── DESIGNER ────────────────────────────────────────────────────
    "designer": {
        "name": "Frontend Wizard",
        "emoji": "🎨",
        "triggers": ["designer mode", "frontend", "ui mode", "css expert", "web dev"],
        "task_type": "code",
        "system": """You are an expert frontend developer obsessed with beautiful, performant UIs.
Expertise: HTML5, CSS3 (Grid, Flexbox, animations), JavaScript, React, Tailwind, Framer Motion.
For every design task:
- Mobile-first, responsive by default
- Accessible (WCAG 2.1 AA)
- Smooth 60fps animations
- Modern aesthetic (avoid generic AI-slop design)
- Real working code, no placeholders
Prefer: dark themes, glassmorphism, micro-interactions, distinctive typography.""",
        "style": "creative-technical",
    },

    # ── DATA ANALYST ────────────────────────────────────────────────
    "analyst": {
        "name": "Data Analyst",
        "emoji": "📊",
        "triggers": ["analyst mode", "data mode", "analysis mode", "chart mode"],
        "task_type": "reasoning",
        "system": """You are a senior data analyst. For any data task:
1. Understand the data structure first
2. Clean and validate data
3. Apply appropriate analysis (statistics, trends, correlations)
4. Create clear visualizations (suggest chart types)
5. Draw actionable insights
Tools: pandas, numpy, matplotlib, seaborn, plotly.
Always explain what the numbers mean, not just what they are.
Flag statistical limitations and sample size issues.""",
        "style": "analytical",
    },

    # ── WRITER ──────────────────────────────────────────────────────
    "writer": {
        "name": "Content Writer",
        "emoji": "✍️",
        "triggers": ["writer mode", "content mode", "copywriter", "write mode", "blog mode"],
        "task_type": "creative",
        "system": """You are an expert content writer and copywriter.
For any writing task:
- Understand the audience and purpose
- Hook the reader in the first sentence
- Use clear, active voice
- SEO-friendly when appropriate (natural keyword placement)
- Correct grammar and varied sentence structure
Styles: blog posts, social media, email marketing, product descriptions, ad copy.
Always ask: Will this resonate with the target audience?""",
        "style": "creative",
    },

    # ── TEACHER ─────────────────────────────────────────────────────
    "teacher": {
        "name": "Patient Teacher",
        "emoji": "📚",
        "triggers": ["teacher mode", "explain mode", "sikhao", "samjhao", "beginner"],
        "task_type": "chat",
        "system": """You are a patient, clear teacher who excels at making complex topics simple.
Teaching approach:
1. Start with a simple analogy
2. Build up complexity gradually
3. Use examples from everyday life
4. Check understanding with questions
5. Summarize key points at the end
Language: Hinglish preferred (mix Hindi explanations with English terms)
Never assume prior knowledge. Never make student feel bad for not knowing.""",
        "style": "educational",
    },

    # ── TRADER (READ-ONLY — no financial advice) ─────────────────────
    "trader": {
        "name": "Market Analyst",
        "emoji": "📈",
        "triggers": ["trader mode", "market mode", "stocks mode", "trading mode"],
        "task_type": "research",
        "system": """You are a market analyst (NOT a financial advisor).
You provide: technical analysis, fundamental analysis, market sentiment, sector trends.
ALWAYS include disclaimer: "This is analysis only, not financial advice. DYOR."
Analysis includes: price levels, support/resistance, RSI, MACD concepts, volume.
For Indian markets: NSE/BSE, Nifty, Sensex context.
Never predict with certainty. Show bull AND bear cases.""",
        "style": "analytical",
    },

    # ── PROJECT PLANNER ─────────────────────────────────────────────
    "planner": {
        "name": "Project Planner",
        "emoji": "📋",
        "triggers": ["planner mode", "project mode", "planning mode", "organize"],
        "task_type": "reasoning",
        "system": """You are an expert project manager and planner.
For any planning task:
1. Break down into phases and milestones
2. Estimate time and resources (realistic)
3. Identify dependencies and blockers
4. Define success criteria
5. Risk assessment (what could go wrong)
Output format: Structured plan with timeline, priorities (P0/P1/P2), and next actions.
Prefer MVP approach — ship fast, iterate.""",
        "style": "structured",
    },
}

# ══════════════════════════════════════════════════════════════════════
#  ACTIVE AGENT STATE
# ══════════════════════════════════════════════════════════════════════

_current_agent: str = "jarvis"
_agent_lock = threading.Lock()


def detect_agent(message: str) -> Optional[str]:
    """Detect which agent the user wants to activate."""
    msg_lower = message.lower()
    for agent_id, agent in AGENTS.items():
        for trigger in agent.get("triggers", []):
            if trigger in msg_lower:
                return agent_id
    return None


def get_current_agent() -> Dict:
    with _agent_lock:
        return AGENTS.get(_current_agent, AGENTS["jarvis"])


def switch_agent(agent_id: str) -> str:
    global _current_agent
    if agent_id not in AGENTS:
        available = ", ".join(AGENTS.keys())
        return f"Agent '{agent_id}' not found. Available: {available}"
    with _agent_lock:
        old = _current_agent
        _current_agent = agent_id
    agent = AGENTS[agent_id]
    return f"{agent['emoji']} Switched to {agent['name']} mode"


# ══════════════════════════════════════════════════════════════════════
#  PLAN → EXECUTE → VERIFY
# ══════════════════════════════════════════════════════════════════════

def plan_execute_verify(goal: str, max_iterations: int = 3) -> str:
    """
    Full Plan→Execute→Verify loop.
    Keeps refining until goal is achieved or max_iterations hit.
    """
    from tools import ALL_TOOLS, call_tool
    from memory import remember_task

    history = []
    for iteration in range(1, max_iterations + 1):
        print(f"[AGENT] Iteration {iteration}/{max_iterations}")

        # PLAN
        plan_prompt = f"""Goal: {goal}
Previous attempts: {json.dumps(history[-2:]) if history else 'None'}

Available tools: {', '.join(list(ALL_TOOLS.keys())[:30])}

Create a 3-5 step plan to achieve this goal. Return JSON:
{{"steps": [{{"tool": "name", "args": {{}}, "expected": "what you expect"}}], "success_criteria": "how to know it worked"}}"""

        plan_raw = _brain(plan_prompt, task_type="reasoning", max_tokens=800)
        try:
            plan = json.loads(re.search(r'\{.*\}', plan_raw, re.DOTALL).group())
        except Exception:
            plan = {"steps": [], "success_criteria": ""}

        # EXECUTE
        step_results = []
        for step in plan.get("steps", [])[:5]:
            tool_name = step.get("tool", "")
            args = step.get("args", {})
            if tool_name in ALL_TOOLS:
                result = call_tool(tool_name, **args)
            else:
                result = _brain(f"Do this: {tool_name} {json.dumps(args)}")
            step_results.append({"step": tool_name, "result": result[:200]})

        # VERIFY
        verify_prompt = f"""Goal: {goal}
Success criteria: {plan.get('success_criteria', 'goal achieved')}
Results: {json.dumps(step_results)}

Was the goal achieved? Reply: DONE <summary> or RETRY <what went wrong>"""
        
        verify = _brain(verify_prompt, task_type="reasoning", max_tokens=200)
        history.append({"iteration": iteration, "results": step_results, "verify": verify})

        if verify.startswith("DONE"):
            summary = verify[4:].strip()
            remember_task(goal, summary, status="done", tags="plan_execute")
            return f"✅ Goal achieved in {iteration} iteration(s):\n{summary}"

    # Max iterations hit
    last = history[-1] if history else {}
    return f"⚠️ Goal not fully achieved after {max_iterations} iterations.\nLast verify: {last.get('verify', '')}"


# ══════════════════════════════════════════════════════════════════════
#  PARALLEL MULTI-AGENT
# ══════════════════════════════════════════════════════════════════════

def multi_agent_run(task: str, agents: List[str] = None) -> str:
    """
    Run task through multiple specialist agents in parallel.
    Results synthesized into final answer.
    """
    if not agents:
        # Auto-select relevant agents
        agents = _auto_select_agents(task)

    print(f"[MULTI-AGENT] Running with: {agents}")

    def _run_agent(agent_id: str) -> tuple:
        agent = AGENTS.get(agent_id, AGENTS["jarvis"])
        system = agent.get("system", "")
        task_type = agent.get("task_type", "chat")
        result = _brain(task, task_type=task_type, system=system, max_tokens=800)
        return (agent_id, agent["name"], agent["emoji"], result)

    results = []
    with ThreadPoolExecutor(max_workers=min(len(agents), 4)) as executor:
        futures = {executor.submit(_run_agent, ag): ag for ag in agents}
        for future in as_completed(futures, timeout=60):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"[MULTI-AGENT] Agent error: {e}")

    if not results:
        return "Multi-agent run failed"

    # Synthesize
    synthesis_input = "\n\n".join(
        f"=== {emoji} {name} ===\n{result}" for _, name, emoji, result in results
    )
    synthesis_prompt = f"""Multiple AI specialists analyzed this task: {task}

Their responses:
{synthesis_input}

Create a comprehensive, unified answer combining the best insights from all specialists.
Organize by key points. Be concise."""

    final = _brain(synthesis_prompt, task_type="quality", max_tokens=1500)
    header = " + ".join(f"{e} {AGENTS[a]['name']}" for a, _, e, _ in results)
    return f"🤝 Multi-Agent ({header}):\n\n{final}"


def _auto_select_agents(task: str) -> List[str]:
    """Auto-select best agents for a task."""
    task_lower = task.lower()
    selected = []
    if any(w in task_lower for w in ["code", "script", "bug", "function", "class"]):
        selected.append("coder")
    if any(w in task_lower for w in ["research", "find", "search", "analyze"]):
        selected.append("researcher")
    if any(w in task_lower for w in ["write", "content", "blog", "copy"]):
        selected.append("writer")
    if any(w in task_lower for w in ["plan", "project", "organize", "schedule"]):
        selected.append("planner")
    if not selected:
        selected = ["jarvis", "researcher"]
    return selected[:3]  # Max 3 parallel agents


# ══════════════════════════════════════════════════════════════════════
#  SELF-EVAL
# ══════════════════════════════════════════════════════════════════════

def self_eval(task: str, response: str) -> Dict:
    """Rate the quality of an agent response 1-10."""
    eval_prompt = f"""Rate this AI response quality 1-10.

Task: {task}
Response: {response[:500]}

Score criteria:
- Accuracy (1-10)
- Completeness (1-10)
- Clarity (1-10)
- Helpfulness (1-10)

Return JSON: {{"accuracy": N, "completeness": N, "clarity": N, "helpfulness": N, "overall": N, "feedback": "brief note"}}"""

    result = _brain(eval_prompt, task_type="reasoning", max_tokens=200)
    try:
        return json.loads(re.search(r'\{.*\}', result, re.DOTALL).group())
    except Exception:
        return {"overall": 7, "feedback": "Eval parse failed"}


# ══════════════════════════════════════════════════════════════════════
#  TOOL FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def t_switch_agent(agent_name: str) -> str:
    """Agent switch karo."""
    # Fuzzy match
    agent_name_lower = agent_name.lower().strip()
    for agent_id in AGENTS:
        if agent_id in agent_name_lower or agent_name_lower in agent_id:
            return switch_agent(agent_id)
    # Try trigger match
    for agent_id, agent in AGENTS.items():
        for trigger in agent.get("triggers", []):
            if trigger in agent_name_lower:
                return switch_agent(agent_id)
    return f"Agent '{agent_name}' not found. Try: {', '.join(AGENTS.keys())}"


def t_list_agents() -> str:
    """Available agents list karo."""
    lines = ["🤖 Available M4STCLAW Agents:", ""]
    for agent_id, agent in AGENTS.items():
        current = " ← ACTIVE" if agent_id == _current_agent else ""
        lines.append(f"  {agent['emoji']} {agent['name']:20s} [{agent_id}]{current}")
        lines.append(f"     Triggers: {', '.join(agent['triggers'][:3])}")
    return "\n".join(lines)


def t_ask_agent(agent_name: str, question: str) -> str:
    """Specific agent se ek question poocho (without switching permanently)."""
    agent_id = None
    name_lower = agent_name.lower()
    for aid in AGENTS:
        if aid in name_lower or name_lower in aid:
            agent_id = aid
            break
    if not agent_id:
        return f"Agent '{agent_name}' not found"
    agent = AGENTS[agent_id]
    result = _brain(question, task_type=agent["task_type"], system=agent["system"])
    return f"{agent['emoji']} {agent['name']}:\n\n{result}"


def t_multi_agent(task: str, agent_list: str = "") -> str:
    """Multiple agents se parallel answer lo."""
    agents = [a.strip() for a in agent_list.split(",") if a.strip()] if agent_list else None
    return multi_agent_run(task, agents)


def t_plan_execute(goal: str) -> str:
    """Goal ke liye full plan banao aur execute karo."""
    return plan_execute_verify(goal)


def t_current_agent() -> str:
    """Active agent status."""
    agent = get_current_agent()
    return f"Active: {agent['emoji']} {agent['name']} | Style: {agent.get('style','')}"


# ══════════════════════════════════════════════════════════════════════
#  OMO ULTRAWORK — Sisyphus orchestrator pattern (OpenWork v12)
# ══════════════════════════════════════════════════════════════════════

_SISYPHUS_PROMPT = """You are Sisyphus — the master orchestrator.
Break the task into parallel subtasks, assign to specialist agents, synthesize results.
Think: what can run in parallel? What depends on what?
Return a JSON plan: {"steps": [{"agent": "coder|researcher|analyst|hacker", "task": "...", "parallel": true/false}]}"""

_MOMUS_PROMPT = """You are Momus — the quality reviewer and critic.
Review the work done. Find gaps, errors, improvements.
Be technical and specific. Rate quality 1-10. Suggest next actions."""


def omo_ultrawork(goal: str, max_agents: int = 3) -> str:
    """
    Sisyphus orchestrates → specialists execute in parallel → Momus reviews.
    From OpenWork v12 multi-agent-omo skill pattern.
    """
    print(f"[OMO] Ultrawork: {goal[:80]}", flush=True)

    # Phase 1: Sisyphus plans
    plan_raw = _brain(
        f"Task: {goal}\nAvailable agents: {list(AGENTS.keys())}",
        task_type="agent",
        system=_SISYPHUS_PROMPT,
        max_tokens=600,
    )

    try:
        plan_json = re.search(r'\{.*\}', plan_raw, re.DOTALL)
        plan = json.loads(plan_json.group()) if plan_json else {"steps": [{"agent": "jarvis", "task": goal, "parallel": False}]}
    except Exception:
        plan = {"steps": [{"agent": "jarvis", "task": goal, "parallel": False}]}

    steps = plan.get("steps", [])[:max_agents]
    print(f"[OMO] Plan: {len(steps)} steps", flush=True)

    # Phase 2: Execute — parallel where possible
    results = []
    parallel_steps = [s for s in steps if s.get("parallel", True)]
    serial_steps   = [s for s in steps if not s.get("parallel", True)]

    if parallel_steps:
        with ThreadPoolExecutor(max_workers=min(len(parallel_steps), 3)) as ex:
            futures = {
                ex.submit(t_ask_agent, s.get("agent","jarvis"), s.get("task", goal)): s
                for s in parallel_steps
            }
            for future in as_completed(futures):
                step = futures[future]
                try:
                    res = future.result(timeout=60)
                    results.append(f"[{step.get('agent','?')}] {res[:500]}")
                except Exception as e:
                    results.append(f"[{step.get('agent','?')}] ERROR: {e}")

    for step in serial_steps:
        res = t_ask_agent(step.get("agent","jarvis"), step.get("task", goal))
        results.append(f"[{step.get('agent','?')}] {res[:500]}")

    # Phase 3: Momus reviews
    combined = "\n\n---\n\n".join(results)
    review = _brain(
        f"Goal: {goal}\n\nWork done:\n{combined[:2000]}",
        task_type="reason",
        system=_MOMUS_PROMPT,
        max_tokens=400,
    )

    return f"🎯 Goal: {goal}\n\n📋 Plan: {len(steps)} agents\n\n{'='*50}\n{combined}\n{'='*50}\n\n🔍 Momus Review:\n{review}"

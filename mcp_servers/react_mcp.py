#!/usr/bin/env python3
"""
react_mcp.py — OpenWork ReAct Engine MCP Server
================================================
ReAct = Reasoning + Acting. Dynamic plan where each step
adapts based on previous result. Use for exploratory tasks.
"""
import sys, os, json, re, time
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))

# Hardened base — crash-proof loop
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_loop, mcp_send, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list

def _log(m): print(f"[react_mcp] {m}", file=sys.stderr, flush=True)

def _ensure_path():
    p = str(_CONFIG_DIR)
    if p not in sys.path: sys.path.insert(0, p)

def _brain(prompt, max_tokens=600, use_cache=False):
    _ensure_path()
    try:
        from llm_fallback import chat_complete
        return chat_complete([{"role":"user","content":prompt}], max_tokens=max_tokens, use_cache=use_cache)
    except Exception as e: return f"ERROR: {e}"

def _parse_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    try:
        m = re.search(r'\{.*\}', raw.strip(), re.DOTALL)
        return json.loads(m.group()) if m else {}
    except Exception: return {}

# ── Tool handlers ─────────────────────────────────────────────────────
def _t_react_plan(a):
    goal    = a.get("goal","")
    context = a.get("context","")
    tools   = a.get("available_tools",[])
    steps   = min(max(int(a.get("max_steps",8)),2),15)
    if not goal: return "goal required"

    tools_hint = f"\nAvailable tools: {', '.join(tools[:30])}" if tools else ""
    data = _parse_json(_brain(
        f"You are a ReAct planning engine.\n\nGOAL: {goal}\n"
        f"{f'CONTEXT: {context}' if context else ''}{tools_hint}\n\n"
        f"Create a ReAct plan with up to {steps} steps. Each step has:\n"
        f"- thought: why this step, what to expect\n"
        f"- action: exact tool name or FINISH\n"
        f"- args: tool arguments\n"
        f"- on_success: next step or done\n"
        f"- on_failure: alternative approach\n\n"
        f'JSON only:\n{{"goal":"{goal}","strategy":"1 line approach","steps":[{{"id":1,"thought":"...","action":"tool_name","args":{{}},"on_success":"...","on_failure":"..."}}],"fallback":"if all fails..."}}',
        max_tokens=1000))

    if not data or "steps" not in data:
        return f"ReAct plan failed to generate. Try react_think for a simpler analysis."

    lines = [f"🔄 ReAct Plan: {goal}", f"Strategy: {data.get('strategy','')}",""]
    for s in data.get("steps",[]):
        lines.append(f"Step {s.get('id')}: [THOUGHT] {s.get('thought','')[:100]}")
        lines.append(f"  → ACTION: {s.get('action','?')}  ARGS: {json.dumps(s.get('args',{}))[:80]}")
        lines.append(f"  ✅ {s.get('on_success','continue')}  ❌ {s.get('on_failure','retry')}")
        lines.append("")
    lines.append(f"Fallback: {data.get('fallback','manual investigation')}")
    return "\n".join(lines)

def _t_react_analyze(a):
    goal        = a.get("goal","")
    prev_steps  = a.get("prev_steps",[])
    last_result = a.get("last_result","")
    if not goal: return "goal required"

    history = "\n".join(
        f"Step {s.get('id','?')}: {s.get('action','?')} → {str(s.get('result',''))[:100]}"
        for s in prev_steps[-5:]) or "No previous steps."

    data = _parse_json(_brain(
        f"GOAL: {goal}\n\nPrevious steps:\n{history}\n\nLast result: {last_result[:500]}\n\n"
        f"Is goal achieved? What to do next?\n"
        f'JSON: {{"goal_achieved":false,"next_action":"tool_name or DONE","next_args":{{}},"reasoning":"why"}}',
        max_tokens=300))

    if data.get("goal_achieved"):
        return f"✅ Goal achieved! {data.get('reasoning','')}"
    na = data.get("next_action","DONE")
    if na == "DONE":
        return f"🏁 Done. {data.get('reasoning','')}"
    return (f"🔄 Next step:\n  Action: {na}\n"
            f"  Args: {json.dumps(data.get('next_args',{}))}\n"
            f"  Reasoning: {data.get('reasoning','')}")

def _t_react_think(a):
    situation = a.get("situation","")
    goal      = a.get("goal","")
    if not situation: return "situation required"
    result = _brain(
        f"{'GOAL: ' + goal + chr(10) if goal else ''}"
        f"SITUATION: {situation}\n\n"
        f"Think step by step: what is the best next action and why? "
        f"Be concrete — suggest a specific tool or approach.",
        max_tokens=300)
    return f"💭 Analysis:\n{result}"

def _t_react_summarize(a):
    steps = a.get("steps",[])
    goal  = a.get("goal","")
    if not steps: return "steps required"
    steps_text = "\n".join(f"  {s.get('id','?')}. {s.get('action','?')}: {str(s.get('result',''))[:80]}"
                           for s in steps)
    result = _brain(
        f"Goal: {goal}\n\nSteps executed:\n{steps_text}\n\n"
        f"Summarize: what was accomplished, what wasn't, what's the final state?",
        max_tokens=400)
    return f"📋 Execution Summary:\n{result}"

TOOLS = {
    "react_plan":      (_t_react_plan,      "Create a ReAct-style dynamic plan — each step has thought+action+failure handling. Better than static planning for exploratory tasks."),
    "react_analyze":   (_t_react_analyze,   "Given previous steps and last result, decide what to do next (core ReAct loop)."),
    "react_think":     (_t_react_think,     "Given a situation, reason about best next step — concrete tool suggestion."),
    "react_summarize": (_t_react_summarize, "Summarize completed ReAct execution steps into a final outcome."),
}
SCHEMAS = {
    "react_plan":      {"type":"object","properties":{"goal":{"type":"string"},"context":{"type":"string"},"available_tools":{"type":"array","items":{"type":"string"}},"max_steps":{"type":"integer"}},"required":["goal"]},
    "react_analyze":   {"type":"object","properties":{"goal":{"type":"string"},"prev_steps":{"type":"array"},"last_result":{"type":"string"}},"required":["goal"]},
    "react_think":     {"type":"object","properties":{"situation":{"type":"string"},"goal":{"type":"string"}},"required":["situation"]},
    "react_summarize": {"type":"object","properties":{"steps":{"type":"array"},"goal":{"type":"string"}},"required":["steps"]},
}

def _send(o): print(json.dumps(o, ensure_ascii=False), flush=True)
def _handle(req):
    m,rid = req.get("method",""),req.get("id")
    if m=="initialize": _send({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"react-mcp","version":"1.1.0"}}})
    elif m=="tools/list": _send({"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":n,"description":fd[1],"inputSchema":SCHEMAS[n]} for n,fd in TOOLS.items()]}})
    elif m=="tools/call":
        p=req.get("params",{}); tn,args=p.get("name",""),p.get("arguments",{})
        if tn in TOOLS:
            try: _send({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":str(TOOLS[tn][0](args))}]}})
            except Exception as e: _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32000,"message":str(e)}})
        else: _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Tool not found: {tn}"}})
    elif m=="notifications/initialized": pass
    elif rid is not None: _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown: {m}"}})

def main():
    _log("started — ReAct reasoning active")
    mcp_loop("react", _handle)

if __name__ == "__main__": main()

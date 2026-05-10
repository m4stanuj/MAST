#!/usr/bin/env python3
"""
skills_mcp.py — OpenWork Skill Learner MCP Server
===================================================
Successful task sequences → skills. Find, replay, manage.
"""
import sys, os, json, time, hashlib, re
from pathlib import Path

_CONFIG_DIR  = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))
_SKILLS_FILE = _CONFIG_DIR / "learned_skills.json"

# Hardened base
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_loop

def _log(m): print(f"[skills_mcp] {m}", file=sys.stderr, flush=True)

def _ensure_path():
    p = str(_CONFIG_DIR)
    if p not in sys.path: sys.path.insert(0, p)

def _brain(prompt, max_tokens=400):
    _ensure_path()
    try:
        from llm_fallback import chat_complete
        return chat_complete([{"role":"user","content":prompt}], max_tokens=max_tokens, use_cache=True)
    except Exception as e: return f"ERROR: {e}"

def _load():
    try:
        if _SKILLS_FILE.exists():
            return json.loads(_SKILLS_FILE.read_text(encoding="utf-8"))
    except Exception: pass
    return []

def _save(skills):
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _SKILLS_FILE.write_text(json.dumps(skills, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e: _log(f"save: {e}")

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
def _t_learn_skill(a):
    goal,chain = a.get("goal",""),a.get("tool_chain",[])
    if not goal or not chain: return "goal and tool_chain required"
    skills = _load()
    gh = hashlib.md5(goal.lower().encode()).hexdigest()[:8]
    for s in skills:
        if s.get("goal_hash") == gh:
            s["use_count"] = s.get("use_count",0)+1; _save(skills)
            return f"Skill already exists, use_count updated: {s['name']}"
    summary = "\n".join(f"  {i+1}. {step['tool']}({json.dumps(step.get('args',{}))[:50]})"
                        for i,step in enumerate(chain[:8]))
    meta = _parse_json(_brain(
        f'Task: "{goal}"\nTools:\n{summary}\n\n'
        f'Skill metadata JSON:\n{{"name":"3-5 word name","description":"1 sentence","category":"automation|research|office|social|coding|system|web","keywords":["k1","k2"],"trigger_phrases":["phrase1"]}}',
        max_tokens=200))
    if not meta:
        meta = {"name":f"Skill {len(skills)+1}","description":goal[:60],"category":"automation","keywords":[],"trigger_phrases":[goal[:50]]}
    sid = f"skill_{gh}_{int(time.time())}"
    skills.append({"skill_id":sid,"goal_hash":gh,"goal":goal,
                   "name":meta.get("name",""),"description":meta.get("description",""),
                   "category":meta.get("category","automation"),"keywords":meta.get("keywords",[]),
                   "trigger_phrases":meta.get("trigger_phrases",[]),"tool_chain":chain[:10],
                   "created_at":time.strftime("%Y-%m-%d %H:%M:%S"),"use_count":1,"success_rate":100})
    _save(skills)
    return f"✅ Skill learned: {meta.get('name',sid)} [{sid[-8:]}]"

def _t_search_skills(a):
    query = a.get("query","")
    if not query: return "query required"
    skills = _load()
    if not skills: return "No learned skills yet."
    ql = query.lower()
    best,best_score = None,0.0
    for s in skills:
        score = 0.0
        kw = s.get("keywords",[])
        km = sum(1 for k in kw if k.lower() in ql)
        if kw: score += (km/len(kw))*0.5
        for tr in s.get("trigger_phrases",[]):
            ov = sum(1 for w in tr.lower().split() if w in ql and len(w)>3)
            if ov and len(tr.split()): score += (ov/len(tr.split()))*0.5
        sw = set(s.get("goal","").lower().split()); gw = set(ql.split())
        if sw: score += len(sw&gw)/max(len(sw),len(gw))*0.4
        if score > best_score: best_score,best = score,s
    if not best or best_score < 0.3: return f"No matching skill for '{query}'."
    chain_preview = "\n".join(f"  {i+1}. {step.get('tool','?')}({json.dumps(step.get('args',{}))[:40]})"
                              for i,step in enumerate(best.get("tool_chain",[])[:5]))
    return (f"🎯 Matching: {best['name']} (score: {round(best_score,2)})\n"
            f"  ID: {best['skill_id'][-12:]}\n  Desc: {best['description']}\n"
            f"  Category: {best['category']} | Used: {best.get('use_count',0)}x\n"
            f"  Steps:\n{chain_preview}")

def _t_list_skills(a):
    skills = _load()
    if not skills: return "No learned skills. Complete tasks and use learn_skill to save them."
    cat = a.get("category","")
    if cat: skills = [s for s in skills if s.get("category")==cat]
    skills.sort(key=lambda x: x.get("use_count",0), reverse=True)
    by_cat = {}
    for s in skills: by_cat.setdefault(s.get("category","other"),[]).append(s)
    lines = [f"🧠 {len(skills)} Learned Skills:"]
    for c,cs in by_cat.items():
        lines.append(f"\n{c.upper()}")
        for s in cs[:6]:
            lines.append(f"  [{s['skill_id'][-8:]}] {s['name']} — {s.get('description','')[:60]} ({s.get('use_count',0)}x used)")
    return "\n".join(lines)

def _t_delete_skill(a):
    sid = a.get("skill_id","")
    if not sid: return "skill_id required"
    skills = _load(); orig = len(skills)
    skills = [s for s in skills if not s["skill_id"].endswith(sid[-8:])]
    if len(skills) < orig: _save(skills); return "✅ Skill deleted."
    return "Skill not found."

def _t_skills_stats(a):
    skills = _load()
    if not skills: return "No skills yet."
    by_cat = {}
    total_uses = sum(s.get("use_count",0) for s in skills)
    for s in skills: by_cat[s.get("category","other")] = by_cat.get(s.get("category","other"),0)+1
    top = sorted(skills, key=lambda x: x.get("use_count",0), reverse=True)[:3]
    return (f"Skills: {len(skills)} total | {total_uses} total uses\n"
            f"By category: {', '.join(f'{k}={v}' for k,v in by_cat.items())}\n"
            f"Top used: {', '.join(s['name'] for s in top)}")

TOOLS = {
    "learn_skill":   (_t_learn_skill,   "Save a successful task sequence as a learned skill for future reuse."),
    "search_skills": (_t_search_skills, "Find a learned skill matching a task description."),
    "list_skills":   (_t_list_skills,   "List all learned skills. Optional: filter by category."),
    "delete_skill":  (_t_delete_skill,  "Delete a learned skill by skill_id."),
    "skills_stats":  (_t_skills_stats,  "Skills statistics — total, categories, top used."),
}
SCHEMAS = {
    "learn_skill":   {"type":"object","properties":{"goal":{"type":"string"},"tool_chain":{"type":"array","items":{"type":"object","properties":{"tool":{"type":"string"},"args":{"type":"object"}}}}},"required":["goal","tool_chain"]},
    "search_skills": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},
    "list_skills":   {"type":"object","properties":{"category":{"type":"string","description":"automation|research|office|social|coding|system|web"}}},
    "delete_skill":  {"type":"object","properties":{"skill_id":{"type":"string"}},"required":["skill_id"]},
    "skills_stats":  {"type":"object","properties":{}},
}

def _send(o): print(json.dumps(o, ensure_ascii=False), flush=True)
def _handle(req):
    m,rid = req.get("method",""),req.get("id")
    if m=="initialize": _send({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"skills-mcp","version":"1.1.0"}}})
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
    skills = _load()
    _log(f"started — {len(skills)} learned skills")
    mcp_loop("skills", _handle)

if __name__ == "__main__": main()

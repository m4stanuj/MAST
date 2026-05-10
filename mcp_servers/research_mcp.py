#!/usr/bin/env python3
"""
research_mcp.py — OpenWork Deep Research MCP Server
=====================================================
AutoGPT-style iterative research. depth=1-4.
Search: tries requests+regex first (zero extra deps), bs4 if available.
Brain: llm_fallback.chat_complete
"""
import sys, os, json, re, time
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))

# Hardened base — crash-proof loop
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_loop, mcp_send, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list

def _log(m): print(f"[research_mcp] {m}", file=sys.stderr, flush=True)

def _ensure_path():
    p = str(_CONFIG_DIR)
    if p not in sys.path: sys.path.insert(0, p)

def _brain(prompt: str, max_tokens: int = 800) -> str:
    _ensure_path()
    try:
        from llm_fallback import chat_complete
        return chat_complete([{"role":"user","content":prompt}], max_tokens=max_tokens, use_cache=True)
    except Exception as e:
        return f"ERROR: {e}"

def _search(query: str) -> str:
    try:
        import requests
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": "", "kl": "in-en"},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=12)
        # Try bs4 first, fallback to regex
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            snippets = [el.get_text(strip=True) for el in soup.select(".result__snippet")[:4]]
        except ImportError:
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]{20,400})<', r.text)[:4]
        # Clean HTML entities
        clean = []
        for s in snippets:
            s = re.sub(r'<[^>]+>','',s)
            s = s.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>').replace('&#x27;',"'").replace('&quot;','"')
            s = s.strip()
            if s: clean.append(s)
        return "\n".join(clean) if clean else "No results found."
    except ImportError:
        return "ERROR: requests not installed — pip install requests"
    except Exception as e:
        return f"Search failed: {e}"

def _parse_json_safe(raw: str) -> dict:
    """Extract JSON from LLM response safely."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    raw = raw.strip()
    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group()) if m else {}
    except Exception:
        return {}

def deep_research(question: str, depth: int = 3) -> dict:
    start = time.time()
    max_searches = min(depth * 4, 15)
    findings: dict = {}
    sources: list = []
    search_count = 0

    # Step 1: Decompose
    data = _parse_json_safe(_brain(
        f'Research question: "{question}"\n\n'
        f'Break into 3-5 specific searchable sub-questions.\n'
        f'JSON only: {{"sub_questions": ["q1", "q2", "q3"]}}',
        max_tokens=300))
    sub_qs = data.get("sub_questions", [question])[:5]
    _log(f"'{question[:40]}' → {len(sub_qs)} sub-questions")

    # Step 2: Research each
    for sq in sub_qs:
        if search_count >= max_searches: break
        result = _search(sq); search_count += 1
        findings[sq] = result[:500]; sources.append(sq)

        if depth >= 2 and search_count < max_searches:
            fu = _parse_json_safe(_brain(
                f"Search result: {result[:300]}\n\n"
                f"Is anything important missing? If yes, one follow-up query.\n"
                f'JSON: {{"followup": "query or null"}}', max_tokens=100))
            fq = fu.get("followup","")
            if fq and fq != "null" and len(fq) > 5:
                findings[fq] = _search(fq)[:500]; sources.append(fq); search_count += 1

    # Step 3: Gap analysis
    if depth >= 3 and search_count < max_searches:
        ctx = f"Question: {question}\nFindings: " + " | ".join(
            f"{q[:30]}: {a[:60]}" for q,a in list(findings.items())[:4])
        gaps_data = _parse_json_safe(_brain(
            f"{ctx}\n\nWhat important angles are missing?\n"
            f'JSON: {{"gaps": ["gap1","gap2"]}}', max_tokens=200))
        for gap in gaps_data.get("gaps",[])[:3]:
            if search_count >= max_searches: break
            findings[f"[GAP] {gap}"] = _search(gap)[:400]; search_count += 1

    # Step 4: Synthesize
    all_f = "\n\n".join(f"Q: {q}\nA: {a}" for q,a in list(findings.items())[:10])
    final = _brain(
        f'Question: "{question}"\n\nResearch ({search_count} searches):\n{all_f[:4000]}\n\n'
        f'Write comprehensive answer:\n## Summary\n## Key Findings\n## Details\n## Conclusion',
        max_tokens=1200)

    confidence = min(95, 50 + len([f for f in findings.values() if len(f) > 100]) * 8)
    return {"answer": final, "sources": sources[:10],
            "searches_done": search_count, "elapsed": round(time.time()-start),
            "confidence": confidence}

# ── Tool handlers ─────────────────────────────────────────────────────
def _t_deep_research(a):
    q = a.get("query","")
    if not q: return "query required"
    d = max(1, min(4, int(a.get("depth", 3))))
    r = deep_research(q, d)
    return (f"🔍 Deep Research: {q}\n"
            f"📊 {r['searches_done']} searches | {r['elapsed']}s | {r['confidence']}% confidence\n\n"
            + r["answer"])

def _t_research_competitor(a):
    t = a.get("topic","")
    if not t: return "topic required"
    r = deep_research(f"Comprehensive competitor analysis: {t} - features, pricing, strengths, weaknesses", depth=3)
    return f"🏆 Competitor Analysis: {t}\n\n" + r["answer"]

def _t_research_technical(a):
    t = a.get("topic","")
    if not t: return "topic required"
    r = deep_research(f"Technical deep dive: {t} - how it works, architecture, implementation, best practices", depth=4)
    return f"⚙️ Technical: {t}\n\n" + r["answer"]

def _t_research_news(a):
    t = a.get("topic","")
    if not t: return "topic required"
    r = deep_research(f"Latest news and developments: {t} - 2025-2026", depth=2)
    return f"📰 Latest: {t}\n\n" + r["answer"]

def _t_quick_search(a):
    q = a.get("query","")
    if not q: return "query required"
    return _search(q)

TOOLS = {
    "deep_research":       (_t_deep_research,       "AutoGPT-style iterative research. depth=1(quick/3 searches) to 4(very deep/15 searches). Default=3."),
    "research_competitor": (_t_research_competitor, "Competitor analysis — features, pricing, strengths, weaknesses."),
    "research_technical":  (_t_research_technical,  "Technical deep dive — architecture, implementation, best practices."),
    "research_news":       (_t_research_news,        "Latest news and 2025-2026 developments on a topic."),
    "quick_search":        (_t_quick_search,         "Fast single web search — quick fact lookup."),
}
SCHEMAS = {
    "deep_research":       {"type":"object","properties":{"query":{"type":"string"},"depth":{"type":"integer","description":"1=quick, 2=standard, 3=deep(default), 4=very deep"}},"required":["query"]},
    "research_competitor": {"type":"object","properties":{"topic":{"type":"string"}},"required":["topic"]},
    "research_technical":  {"type":"object","properties":{"topic":{"type":"string"}},"required":["topic"]},
    "research_news":       {"type":"object","properties":{"topic":{"type":"string"}},"required":["topic"]},
    "quick_search":        {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},
}

def _send(o): print(json.dumps(o, ensure_ascii=False), flush=True)
def _handle(req):
    m, rid = req.get("method",""), req.get("id")
    if m == "initialize":
        _send({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"research-mcp","version":"1.1.0"}}})
    elif m == "tools/list":
        _send({"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":n,"description":fd[1],"inputSchema":SCHEMAS[n]} for n,fd in TOOLS.items()]}})
    elif m == "tools/call":
        p = req.get("params",{}); tn,args = p.get("name",""),p.get("arguments",{})
        if tn in TOOLS:
            try: _send({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":str(TOOLS[tn][0](args))}]}})
            except Exception as e: _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32000,"message":str(e)}})
        else: _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Tool not found: {tn}"}})
    elif m == "notifications/initialized": pass
    elif rid is not None: _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown: {m}"}})

def main():
    _log("started — AutoGPT-style deep research active")
    mcp_loop("research", _handle)

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""
memory_mcp.py — OpenWork 3-Tier Memory MCP Server v8
Uses hardened _mcp_base loop (BrokenPipe/EOF safe).
"""
import sys, os, json, time, re, threading, hashlib, atexit, copy
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))

# Import hardened base FIRST (sets up stdout UTF-8, signal handlers)
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_send, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list, mcp_loop

def _log(m): 
    try:
        print(f"[memory_mcp] {m}", file=sys.stderr, flush=True)
    except Exception:
        pass

_MEM_FILE = _CONFIG_DIR / "memory_3tier.json"
_MEM_LOCK = threading.Lock()

# ── ChromaDB optional ─────────────────────────────────────────────────
_CHROMA_OK, _chroma_col = False, None
def _init_chroma():
    global _CHROMA_OK, _chroma_col
    try:
        import chromadb
        c = chromadb.PersistentClient(path=str(_CONFIG_DIR / "memory_vectordb"))
        _chroma_col = c.get_or_create_collection("openwork_archival", metadata={"hnsw:space":"cosine"})
        _CHROMA_OK = True
        _log(f"ChromaDB: {_chroma_col.count()} entries")
    except ImportError:
        _log("ChromaDB not installed — keyword fallback")
    except Exception as e:
        _log(f"ChromaDB failed: {e} — keyword fallback")

_DEFAULT = {
    "core":     {"user_name":"","location":"","language":"hinglish","current_project":"",
                 "preferences":{},"important_facts":[],"active_context":"","updated_at":0},
    "recall":   {"recent_tasks":[],"mistakes":[],"skills_used":{}},
    "archival": {"all_tasks":[],"projects":{},"total_sessions":0},
    "meta":     {"created_at":time.time(),"last_updated":time.time(),"version":"ow-3tier-v1"},
}

def _load():
    try:
        if _MEM_FILE.exists():
            data = json.loads(_MEM_FILE.read_text(encoding="utf-8"))
            for k in _DEFAULT:
                if k not in data:
                    data[k] = copy.deepcopy(_DEFAULT[k])
            return data
    except Exception as e:
        _log(f"load error: {e}")
    return copy.deepcopy(_DEFAULT)  # FIX: deep copy so nested dicts/lists aren't shared

def _save(mem):
    def _do():
        try:
            tmp = _MEM_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(_MEM_FILE)
        except Exception as e:
            _log(f"save error: {e}")
    threading.Thread(target=_do, daemon=True).start()

def _save_now():
    """Synchronous save — called by atexit so data is never lost on clean exit."""
    try:
        with _MEM_LOCK:
            tmp = _MEM_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(_mem, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(_MEM_FILE)
    except Exception as e:
        _log(f"atexit save error: {e}")

_mem = _load()
_init_chroma()
atexit.register(_save_now)  # FIX: ensures final save even on SIGTERM/clean exit

# ── Chroma helpers ────────────────────────────────────────────────────
def _chroma_add(text, meta):
    if not _CHROMA_OK or not _chroma_col: return
    try:
        uid = hashlib.md5(text.encode()).hexdigest()
        _chroma_col.upsert(ids=[uid], documents=[text], metadatas=[meta])
    except Exception as e: _log(f"chroma add: {e}")

def _chroma_search(query, n=5):
    if not _CHROMA_OK or not _chroma_col: return []
    try:
        r = _chroma_col.query(query_texts=[query], n_results=min(n, _chroma_col.count() or 1))
        return r.get("documents", [[]])[0]
    except Exception as e:
        _log(f"chroma search: {e}")
        return []

def _kw_search(query, texts, n=5):
    q = set(query.lower().split())
    scored = []
    for t in texts:
        words = set(t.lower().split())
        score = len(q & words)
        if score > 0: scored.append((score, t))
    scored.sort(reverse=True)
    return [t for _, t in scored[:n]]

# ── Tool handlers ─────────────────────────────────────────────────────
def _t_memory_store(a):
    tier = a.get("tier","recall")
    key  = a.get("key","")
    val  = a.get("value","")
    if not key: return "key required"
    with _MEM_LOCK:
        if tier == "core":
            _mem["core"][key] = val
            _mem["core"]["updated_at"] = time.time()
        elif tier == "recall":
            if key == "task":
                tasks = _mem["recall"].setdefault("recent_tasks", [])
                tasks.insert(0, {"task": val, "ts": time.time()})
                _mem["recall"]["recent_tasks"] = tasks[:50]
            elif key == "mistake":
                _mem["recall"].setdefault("mistakes", []).insert(0, {"note": val, "ts": time.time()})
                _mem["recall"]["mistakes"] = _mem["recall"]["mistakes"][:20]
            else:
                _mem["recall"][key] = val
        elif tier == "archival":
            entry = {"key": key, "value": val, "ts": time.time()}
            _mem["archival"].setdefault("all_tasks", []).insert(0, entry)
            _mem["archival"]["all_tasks"] = _mem["archival"]["all_tasks"][:500]
            _chroma_add(f"{key}: {val}", {"tier":"archival","ts":str(time.time())})
        _mem["meta"]["last_updated"] = time.time()
        _save(_mem)
    return f"stored [{tier}] {key}"

def _t_memory_get(a):
    tier = a.get("tier","core")
    key  = a.get("key","")
    with _MEM_LOCK:
        if tier == "core":
            return json.dumps(_mem["core"] if not key else _mem["core"].get(key,""), ensure_ascii=False)
        elif tier == "recall":
            return json.dumps(_mem["recall"] if not key else _mem["recall"].get(key,[]), ensure_ascii=False)
        elif tier == "archival":
            return json.dumps(_mem["archival"].get("all_tasks",[])[:20], ensure_ascii=False)
    return "unknown tier"

def _t_memory_search(a):
    query = a.get("query","")
    n     = int(a.get("n",5))
    if not query: return "query required"
    with _MEM_LOCK:
        archival_texts = [f"{t.get('key','')}: {t.get('value','')}"
                          for t in _mem["archival"].get("all_tasks",[])]
    results = _chroma_search(query, n) if _CHROMA_OK else _kw_search(query, archival_texts, n)
    return json.dumps(results, ensure_ascii=False) if results else "no results found"

def _t_memory_context(a):
    with _MEM_LOCK:
        c   = _mem["core"]
        rec = _mem["recall"]
        tasks  = rec.get("recent_tasks",[])[:5]
        mistakes = rec.get("mistakes",[])[:3]
    lines = []
    if c.get("user_name"):  lines.append(f"User: {c['user_name']}")
    if c.get("current_project"): lines.append(f"Project: {c['current_project']}")
    if c.get("active_context"):  lines.append(f"Context: {c['active_context']}")
    if c.get("important_facts"): lines.append(f"Facts: {'; '.join(str(f) for f in c['important_facts'][:5])}")
    if tasks: lines.append(f"Recent: {'; '.join(str(t.get('task','')) for t in tasks)}")
    if mistakes: lines.append(f"Watch: {'; '.join(str(m.get('note','')) for m in mistakes)}")
    return "\n".join(lines) if lines else "No context yet. Use memory_store to save facts."

def _t_memory_clear(a):
    tier = a.get("tier","")
    with _MEM_LOCK:
        if tier == "archival":
            _mem["archival"] = {"all_tasks":[],"projects":{},"total_sessions":0}
        elif tier == "recall":
            _mem["recall"] = {"recent_tasks":[],"mistakes":[],"skills_used":{}}
        elif tier == "all":
            for k in _DEFAULT:
                _mem[k] = copy.deepcopy(_DEFAULT[k])
        else:
            return "specify tier: recall | archival | all"
        _save(_mem)
    return f"cleared {tier}"

TOOLS = [
    ("memory_store",   "Store info in memory. tier: core|recall|archival. core=user facts, recall=recent tasks, archival=long-term."),
    ("memory_get",     "Retrieve from memory. tier: core|recall|archival. Leave key empty for all."),
    ("memory_search",  "Semantic search archival memory. Returns top-n matching entries."),
    ("memory_context", "Get quick context summary: user, project, recent tasks, mistakes."),
    ("memory_clear",   "Clear a memory tier: recall | archival | all."),
]
SCHEMAS = {
    "memory_store":  {"type":"object","properties":{"tier":{"type":"string"},"key":{"type":"string"},"value":{"type":"string"}},"required":["key","value"]},
    "memory_get":    {"type":"object","properties":{"tier":{"type":"string"},"key":{"type":"string"}}},
    "memory_search": {"type":"object","properties":{"query":{"type":"string"},"n":{"type":"integer"}},"required":["query"]},
    "memory_context":{"type":"object","properties":{}},
    "memory_clear":  {"type":"object","properties":{"tier":{"type":"string"}},"required":["tier"]},
}

HANDLERS = {
    "memory_store":   _t_memory_store,
    "memory_get":     _t_memory_get,
    "memory_search":  _t_memory_search,
    "memory_context": _t_memory_context,
    "memory_clear":   _t_memory_clear,
}

def _handle(msg):
    m   = msg.get("method","")
    rid = msg.get("id")
    if m == "initialize":
        mcp_initialize(rid, "memory")
    elif m == "tools/list":
        mcp_tools_list(rid, TOOLS, SCHEMAS)
    elif m == "tools/call":
        name = msg.get("params",{}).get("name","")
        args = msg.get("params",{}).get("arguments",{})
        fn   = HANDLERS.get(name)
        if fn:
            try:
                mcp_respond(rid, fn(args))
            except Exception as e:
                mcp_error(rid, -32000, f"{name} failed: {e}")
        else:
            mcp_error(rid, -32601, f"Unknown tool: {name}")
    elif m == "notifications/initialized":
        pass

def main():
    with _MEM_LOCK:
        nfacts = len(_mem['core'].get('important_facts',[]))
        ntasks = len(_mem['recall'].get('recent_tasks',[]))
    _log(f"started — Core({nfacts} facts) Recall({ntasks} tasks)")
    mcp_loop("memory", _handle)

if __name__ == "__main__":
    main()

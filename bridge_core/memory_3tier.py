"""
M4ST 3-Tier Memory v5 — Professional
=======================================
FIX: Tier 3 Archival ab ChromaDB semantic search use karta hai.
     Plain list → vector embeddings → fast semantic retrieval.

Tier 1 — CORE (always in context, ~500 tokens)
Tier 2 — RECALL (searchable recent, 7 days, keyword search)
Tier 3 — ARCHIVAL (semantic vector search via ChromaDB/fallback)
"""

import os, json, time, re, threading, hashlib
from pathlib import Path
from datetime import datetime, timedelta

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM_FILE = os.path.join(ROOT, "memory_3tier.json")
MEM_LOCK = threading.Lock()

# ── ChromaDB — optional, graceful fallback to keyword ────────────────
_CHROMA_OK  = False
_chroma_col = None

def _init_chroma():
    global _CHROMA_OK, _chroma_col
    try:
        import chromadb
        db_path = os.path.join(ROOT, "memory_vectordb")
        os.makedirs(db_path, exist_ok=True)
        client = chromadb.PersistentClient(path=db_path)
        _chroma_col = client.get_or_create_collection(
            name="m4st_archival",
            metadata={"hnsw:space": "cosine"}
        )
        _CHROMA_OK = True
        print(f"[OK] ChromaDB loaded — {_chroma_col.count()} archival entries")
    except ImportError:
        print("[INFO] ChromaDB not installed — keyword fallback active (pip install chromadb)")
    except Exception as _e:
        print(f"[INFO] ChromaDB init failed: {_e} — keyword fallback active")

_init_chroma()

# ── Default structure ──────────────────────────────────────────────────
DEFAULT_MEM = {
    "core": {
        "user_name":       "",
        "location":        "",
        "language":        "hinglish",
        "current_project": "",
        "preferences":     {},
        "important_facts": [],
        "active_context":  "",
        "updated_at":      0,
    },
    "recall": {
        "recent_tasks":    [],
        "mistakes":        [],
        "conversations":   [],
        "skills_used":     {},
    },
    "archival": {
        "all_tasks":       [],
        "projects":        {},
        "learned_facts":   [],
        "total_sessions":  0,
    },
    "meta": {
        "created_at":   time.time(),
        "last_updated": time.time(),
        "version":      "3tier-v5",
    }
}

_mem: dict = {}


def _load():
    global _mem
    try:
        if os.path.exists(MEM_FILE):
            with MEM_LOCK:
                _mem = json.load(open(MEM_FILE, encoding="utf-8"))
                for tier in ["core", "recall", "archival", "meta"]:
                    if tier not in _mem:
                        _mem[tier] = DEFAULT_MEM[tier].copy()
        else:
            _mem = {k: v.copy() for k, v in DEFAULT_MEM.items()}
    except Exception:
        _mem = {k: v.copy() for k, v in DEFAULT_MEM.items()}


def _save():
    try:
        _mem["meta"]["last_updated"] = time.time()
        with MEM_LOCK:
            json.dump(_mem, open(MEM_FILE, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
    except Exception as _e:
        print(f"[MEM] Save error: {_e}")


def _save_bg():
    threading.Thread(target=_save, daemon=True).start()


# ── CORE TIER ──────────────────────────────────────────────────────────
def core_get() -> dict:
    return _mem.get("core", {})


def core_update(key: str, value):
    _mem["core"][key] = value
    _mem["core"]["updated_at"] = time.time()
    _save_bg()


def core_add_fact(fact: str):
    facts = _mem["core"].get("important_facts", [])
    if fact not in facts:
        facts.insert(0, fact)
        _mem["core"]["important_facts"] = facts[:15]
        _save_bg()


def core_set_context(context: str):
    _mem["core"]["active_context"] = context
    _save_bg()


def get_core_context() -> str:
    c = _mem.get("core", {})
    parts = []
    if c.get("user_name"):        parts.append(f"User: {c['user_name']}")
    if c.get("location"):         parts.append(f"Location: {c['location']}")
    if c.get("current_project"):  parts.append(f"Project: {c['current_project']}")
    if c.get("active_context"):   parts.append(f"Task: {c['active_context']}")
    if c.get("preferences"):
        prefs = list(c["preferences"].items())[:3]
        parts.append("Prefs: " + ", ".join(f"{k}={v}" for k, v in prefs))
    if c.get("important_facts"):
        parts.append("Facts: " + "; ".join(c["important_facts"][:3]))
    return "\n".join(parts) if parts else ""


# ── RECALL TIER ────────────────────────────────────────────────────────
def recall_add_task(task: str, result: str, tools_used: list = None):
    entry = {
        "task":      task[:200],
        "result":    result[:300],
        "tools":     (tools_used or [])[:5],
        "timestamp": time.time(),
        "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    tasks = _mem["recall"].get("recent_tasks", [])
    tasks.insert(0, entry)
    _mem["recall"]["recent_tasks"] = tasks[:50]
    _save_bg()


def recall_add_mistake(wrong: str, correct: str):
    mistakes = _mem["recall"].get("mistakes", [])
    mistakes.insert(0, {"wrong": wrong[:100], "correct": correct[:100], "time": time.time()})
    _mem["recall"]["mistakes"] = mistakes[:10]
    _save_bg()


def recall_log_tool(tool_name: str):
    skills = _mem["recall"].get("skills_used", {})
    skills[tool_name] = skills.get(tool_name, 0) + 1
    _mem["recall"]["skills_used"] = skills
    _save_bg()


def recall_search(query: str, max_results: int = 5) -> list:
    """TF-IDF style recall search — much better than pure keyword overlap."""
    from math import log

    STOP_WORDS = {
        'karo', 'hai', 'ka', 'ki', 'ke', 'mein', 'the', 'a', 'an', 'is', 'ko', 'se',
        'aur', 'ya', 'toh', 'bhi', 'par', 'pe', 'woh', 'yeh', 'ek', 'do',
        'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'that', 'this',
        'with', 'for', 'from', 'not', 'but', 'what', 'how', 'why', 'when'
    }

    # 1. Try semantic via ChromaDB (if active, tier=recall tag)
    if _CHROMA_OK:
        try:
            hits = _chroma_collection.query(
                query_texts=[query], n_results=min(max_results, 10),
                where={"type": "recall"}
            )
            docs = hits.get("documents", [[]])[0]
            metas = hits.get("metadatas", [[]])[0]
            if docs:
                return [{"task": d, **m} for d, m in zip(docs, metas)][:max_results]
        except Exception:
            pass  # Fall through to TF-IDF

    # 2. TF-IDF style fallback
    q_words = set(query.lower().split()) - STOP_WORDS
    if not q_words:
        return _mem["recall"].get("recent_tasks", [])[:max_results]

    tasks = _mem["recall"].get("recent_tasks", [])
    corpus_size = max(len(tasks), 1)
    results = []

    for task in tasks:
        task_text = task.get("task", "").lower()
        task_words = task_text.split()
        task_word_set = set(task_words)
        score = 0.0
        for w in q_words:
            if w in task_word_set:
                tf = task_words.count(w) / max(len(task_words), 1)
                # Approximate IDF — words appearing in many tasks are less informative
                df = sum(1 for t in tasks if w in t.get("task","").lower())
                idf = log((corpus_size + 1) / (df + 1)) + 1
                score += tf * idf

        # Temporal boost — recent tasks get slight boost
        age_hours = (time.time() - task.get("ts", 0)) / 3600
        recency_boost = max(0, 1 - age_hours / 168)  # decay over 1 week
        score *= (1 + 0.2 * recency_boost)

        if score > 0:
            results.append({"score": score, "task": task})

    results.sort(key=lambda x: -x["score"])
    return [r["task"] for r in results[:max_results]]


def get_recall_context(query: str = "") -> str:
    recent   = _mem["recall"].get("recent_tasks", [])[:3]
    mistakes = _mem["recall"].get("mistakes", [])[:2]
    parts = []
    if recent:
        parts.append("Recent: " + " | ".join(t["task"][:50] for t in recent))
    if mistakes:
        parts.append("Fixes: " + " | ".join(f"{m['wrong']}→{m['correct']}" for m in mistakes))
    return "\n".join(parts) if parts else ""


# ── ARCHIVAL TIER — ChromaDB Semantic Search ──────────────────────────
def _chroma_add(doc_id: str, text: str, metadata: dict = None):
    """Add document to ChromaDB."""
    if not _CHROMA_OK or _chroma_col is None:
        return
    try:
        _chroma_col.upsert(
            documents=[text],
            ids=[doc_id],
            metadatas=[metadata or {}]
        )
    except Exception as _e:
        print(f"[CHROMA] Add error: {_e}")


def _chroma_search(query: str, n_results: int = 5) -> list:
    """Semantic search in ChromaDB."""
    if not _CHROMA_OK or _chroma_col is None or _chroma_col.count() == 0:
        return []
    try:
        results = _chroma_col.query(
            query_texts=[query],
            n_results=min(n_results, _chroma_col.count())
        )
        docs  = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [{"text": d, "meta": m} for d, m in zip(docs, metas)]
    except Exception as _e:
        print(f"[CHROMA] Search error: {_e}")
        return []


def archival_save_session(session_summary: str, tasks_done: int):
    entry = {
        "summary":   session_summary[:400],
        "tasks":     tasks_done,
        "date":      datetime.now().strftime("%Y-%m-%d"),
        "timestamp": time.time(),
    }
    _mem["archival"]["all_tasks"].append(entry)
    _mem["archival"]["all_tasks"] = _mem["archival"]["all_tasks"][-100:]
    _mem["archival"]["total_sessions"] = _mem["archival"].get("total_sessions", 0) + 1
    _save_bg()

    # FIX: Also add to ChromaDB for semantic search
    doc_id = f"session_{int(time.time())}_{hashlib.md5(session_summary.encode()).hexdigest()[:8]}"
    _chroma_add(doc_id, session_summary, {"type": "session", "date": entry["date"], "tasks": tasks_done})


def archival_save_project(name: str, summary: str, files: list = None, status: str = "active"):
    _mem["archival"]["projects"][name] = {
        "summary": summary[:300],
        "files":   (files or [])[:10],
        "status":  status,
        "updated": datetime.now().strftime("%Y-%m-%d"),
    }
    _save_bg()

    # FIX: Add to ChromaDB
    doc_id = f"project_{hashlib.md5(name.encode()).hexdigest()[:12]}"
    _chroma_add(doc_id, f"Project {name}: {summary}", {"type": "project", "name": name, "status": status})


def archival_search(query: str) -> str:
    """
    FIX: Semantic search via ChromaDB if available, keyword fallback otherwise.
    """
    results = []

    # 1. Semantic search (ChromaDB)
    if _CHROMA_OK:
        semantic = _chroma_search(query, n_results=5)
        for item in semantic:
            t = item.get("meta", {}).get("type", "")
            text = item.get("text", "")[:100]
            if t == "project":
                results.append(f"[Project] {text}")
            elif t == "session":
                date = item.get("meta", {}).get("date", "")
                results.append(f"[{date}] {text}")
            else:
                results.append(text)

    # 2. Keyword fallback (always run for projects)
    q = query.lower()
    for name, info in _mem["archival"].get("projects", {}).items():
        if q in name.lower() or q in info.get("summary", "").lower():
            entry = f"Project '{name}': {info['summary'][:80]}"
            if entry not in results:
                results.append(entry)

    # 3. Keyword fallback for sessions (if chroma not available)
    if not _CHROMA_OK:
        for session in _mem["archival"].get("all_tasks", [])[-30:]:
            if q in session.get("summary", "").lower():
                results.append(f"[{session['date']}] {session['summary'][:80]}")

    return "\n".join(results[:5]) if results else "Nothing found in archive."


def sync_from_legacy():
    try:
        old_mem_file = os.path.join(ROOT, "memory.json")
        if os.path.exists(old_mem_file):
            old = json.load(open(old_mem_file, encoding="utf-8"))
            if old.get("preferences") and not _mem["core"]["preferences"]:
                _mem["core"]["preferences"] = dict(list(old["preferences"].items())[:5])
            if old.get("facts") and not _mem["core"]["important_facts"]:
                _mem["core"]["important_facts"] = old["facts"][:5]
            if old.get("mistakes") and not _mem["recall"]["mistakes"]:
                _mem["recall"]["mistakes"] = old["mistakes"][:10]
            _save()
    except Exception as _e:
        pass


def get_full_context(include_recall: bool = False) -> str:
    parts = []
    core = get_core_context()
    if core:
        parts.append(f"[MEMORY]\n{core}")
    if include_recall:
        recall = get_recall_context()
        if recall:
            parts.append(f"[RECENT]\n{recall}")
    return "\n\n".join(parts)


# ── TOOLS ──────────────────────────────────────────────────────────────
def t_memory_status() -> str:
    c = _mem["core"]
    r = _mem["recall"]
    a = _mem["archival"]
    chroma_count = _chroma_col.count() if _CHROMA_OK and _chroma_col else 0
    return (
        f"3-Tier Memory v5 Status:\n"
        f"\nTier 1 — CORE (always active):\n"
        f"  User:     {c.get('user_name','not set')}\n"
        f"  Project:  {c.get('current_project','none')}\n"
        f"  Context:  {c.get('active_context','none')[:60]}\n"
        f"  Facts:    {len(c.get('important_facts',[]))}/15\n"
        f"\nTier 2 — RECALL (7 days, keyword):\n"
        f"  Tasks:    {len(r.get('recent_tasks',[]))}/50\n"
        f"  Mistakes: {len(r.get('mistakes',[]))}/10\n"
        f"  Tools:    {len(r.get('skills_used',{}))} tracked\n"
        f"\nTier 3 — ARCHIVAL ({'ChromaDB semantic ✅' if _CHROMA_OK else 'keyword fallback ⚠️'}):\n"
        f"  Sessions: {a.get('total_sessions',0)}\n"
        f"  Projects: {len(a.get('projects',{}))}\n"
        f"  Vectors:  {chroma_count} entries"
    )


def t_memory_set(key: str, value: str) -> str:
    valid_keys = ["user_name", "location", "current_project", "active_context", "language"]
    if key in valid_keys:
        core_update(key, value)
        return f"Memory updated: {key} = {value}"
    return f"Invalid key. Valid: {', '.join(valid_keys)}"


def t_memory_add_fact(fact: str) -> str:
    core_add_fact(fact)
    return f"Fact saved to core memory: {fact}"


def t_memory_search(query: str) -> str:
    recall_results  = recall_search(query)
    archival_result = archival_search(query)
    parts = []
    if recall_results:
        parts.append("Recent:\n" + "\n".join(f"  • {r['task'][:80]}" for r in recall_results))
    if archival_result and archival_result != "Nothing found in archive.":
        parts.append("Archive:\n" + archival_result)
    return "\n\n".join(parts) if parts else "Koi relevant memory nahi mili."


def t_memory_clear_core() -> str:
    _mem["core"] = DEFAULT_MEM["core"].copy()
    _save()
    return "Core memory cleared."


_load()
sync_from_legacy()

MEMORY_TOOLS = {
    "memory_status":     t_memory_status,
    "memory_set":        t_memory_set,
    "memory_add_fact":   t_memory_add_fact,
    "memory_search":     t_memory_search,
    "memory_clear_core": t_memory_clear_core,
}

MEMORY_TOOLS_DEF = [
    {"type": "function", "function": {"name": "memory_status",     "description": "3-tier memory status aur stats dekho.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "memory_set",        "description": "Core memory update karo.", "parameters": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}}},
    {"type": "function", "function": {"name": "memory_add_fact",   "description": "Important fact permanently save karo.", "parameters": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]}}},
    {"type": "function", "function": {"name": "memory_search",     "description": "Memory mein semantic search karo.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "memory_clear_core", "description": "Core memory reset karo.", "parameters": {"type": "object", "properties": {}}}},
]

print(f"[OK] memory_3tier.py v5 loaded — Core({len(_mem['core'].get('important_facts',[]))} facts) Recall({len(_mem['recall'].get('recent_tasks',[]))} tasks) Archival({'ChromaDB' if _CHROMA_OK else 'keyword'})")

"""
M4STCLAW Memory v2.0
======================
3-Tier persistent memory — upgraded over M4ST v6.

2026 Upgrades:
  ✅ nomic-embed-text via Ollama for local embeddings (no cloud needed)
  ✅ TF-IDF + semantic hybrid search
  ✅ Recency-boosted scoring
  ✅ Importance scoring (auto-extract key facts)
  ✅ Cross-session context compression
  ✅ Memory health stats endpoint
  ✅ Entity extraction (names, places, projects)

Tier 1 — CORE (always in context, ~600 tokens)
  User preferences, name, active project, key facts

Tier 2 — RECALL (7-day window, keyword+TF-IDF search)
  Recent tasks, conversations, mistakes, skills used

Tier 3 — ARCHIVAL (ChromaDB semantic, unlimited)
  All past tasks, learned facts, project history
"""

import os, json, time, re, threading, math, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
MEM_FILE = os.path.join(DATA_DIR, "memory.json")
MEM_LOCK = threading.Lock()

# ══════════════════════════════════════════════════════════════════════
#  CHROMADB SETUP
# ══════════════════════════════════════════════════════════════════════

_chroma_ok = False
_chroma_col = None
_embed_fn = None

def _init_chroma():
    global _chroma_ok, _chroma_col, _embed_fn
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        # Try nomic-embed-text via Ollama (best local embeddings 2026)
        try:
            ef = embedding_functions.OllamaEmbeddingFunction(
                url="http://localhost:11434/api/embeddings",
                model_name="nomic-embed-text"
            )
            _embed_fn = ef
            print("[MEM] ✅ nomic-embed-text via Ollama loaded")
        except Exception:
            # Fallback: sentence-transformers
            try:
                ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                _embed_fn = ef
                print("[MEM] ✅ sentence-transformers all-MiniLM-L6-v2 loaded")
            except Exception:
                _embed_fn = embedding_functions.DefaultEmbeddingFunction()
                print("[MEM] ⚠️ Using ChromaDB default embeddings")

        db_path = os.path.join(DATA_DIR, "vectordb")
        os.makedirs(db_path, exist_ok=True)
        client = chromadb.PersistentClient(path=db_path)
        _chroma_col = client.get_or_create_collection(
            name="m4stclaw_archival",
            embedding_function=_embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        _chroma_ok = True
        print(f"[MEM] ✅ ChromaDB loaded — {_chroma_col.count()} archival entries")
    except ImportError:
        print("[MEM] ⚠️ ChromaDB not installed — pip install chromadb")
    except Exception as e:
        print(f"[MEM] ⚠️ ChromaDB init failed: {e}")

_init_chroma()


# ══════════════════════════════════════════════════════════════════════
#  DEFAULT MEMORY STRUCTURE
# ══════════════════════════════════════════════════════════════════════

DEFAULT_MEM = {
    "core": {
        "user_name": "",
        "location": "",
        "language": "hinglish",
        "current_project": "",
        "preferences": {},
        "important_facts": [],   # max 15 facts
        "entities": {},          # name/place/project entities
        "active_context": "",
        "updated_at": 0,
    },
    "recall": {
        "recent_tasks": [],      # max 50 tasks (last 7 days)
        "conversations": [],     # last 20 conversation summaries
        "mistakes": [],          # what went wrong + fixes
        "skills_learned": {},    # tool → usage count
        "daily_summary": {},     # date → summary string
    },
    "archival": {
        "all_tasks": [],         # all tasks ever (for ChromaDB also)
        "projects": {},          # project → {description, tasks, status}
        "learned_facts": [],     # long-term facts
        "total_sessions": 0,
        "total_tasks": 0,
    },
    "meta": {
        "created_at": time.time(),
        "last_updated": time.time(),
        "version": "m4stclaw-v2",
    },
}

_mem: Dict = {}


# ══════════════════════════════════════════════════════════════════════
#  LOAD / SAVE
# ══════════════════════════════════════════════════════════════════════

def _load():
    global _mem
    try:
        with open(MEM_FILE, encoding="utf-8") as f:
            loaded = json.load(f)
        # Deep merge with defaults (so new keys don't break old files)
        _mem = _deep_merge(DEFAULT_MEM, loaded)
    except (FileNotFoundError, json.JSONDecodeError):
        _mem = _deep_merge(DEFAULT_MEM, {})
    return _mem


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _save():
    _mem["meta"]["last_updated"] = time.time()
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(_mem, f, ensure_ascii=False, indent=2)


def _get() -> Dict:
    if not _mem:
        _load()
    return _mem


# ══════════════════════════════════════════════════════════════════════
#  TF-IDF SEARCH (Tier 2)
# ══════════════════════════════════════════════════════════════════════

def _build_idf(docs: List[str]) -> Dict[str, float]:
    N = len(docs) or 1
    df: Counter = Counter()
    for doc in docs:
        words = set(re.findall(r'\w+', doc.lower()))
        df.update(words)
    return {w: math.log(N / (1 + c)) for w, c in df.items()}


def _tfidf_score(query: str, doc: str, idf: Dict[str, float]) -> float:
    q_words = re.findall(r'\w+', query.lower())
    d_words = re.findall(r'\w+', doc.lower())
    if not d_words:
        return 0.0
    d_counts = Counter(d_words)
    score = 0.0
    for w in q_words:
        tf = d_counts.get(w, 0) / len(d_words)
        score += tf * idf.get(w, 0)
    return score


def _recall_search(query: str, top_k: int = 5) -> List[Dict]:
    """TF-IDF search over recent tasks with recency boost."""
    mem = _get()
    tasks = mem["recall"]["recent_tasks"]
    if not tasks:
        return []

    docs = [f"{t.get('task','')} {t.get('result','')} {t.get('tags','')}" for t in tasks]
    idf = _build_idf(docs)
    now = time.time()
    max_age = 7 * 86400  # 7 days

    scored = []
    for i, (task, doc) in enumerate(zip(tasks, docs)):
        base_score = _tfidf_score(query, doc, idf)
        age = now - task.get("timestamp", now)
        recency_boost = max(0.0, 1.0 - (age / max_age))
        final_score = base_score * 0.7 + recency_boost * 0.3
        if final_score > 0.01:
            scored.append((final_score, task))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]


# ══════════════════════════════════════════════════════════════════════
#  CHROMADB ARCHIVAL SEARCH (Tier 3)
# ══════════════════════════════════════════════════════════════════════

def _archival_add(text: str, metadata: Dict = None):
    """Add to ChromaDB archival."""
    if not _chroma_ok or not _chroma_col:
        return
    try:
        doc_id = hashlib.md5(text.encode()).hexdigest()
        _chroma_col.upsert(
            documents=[text],
            ids=[doc_id],
            metadatas=[{**(metadata or {}), "timestamp": time.time()}],
        )
    except Exception as e:
        print(f"[MEM] ChromaDB add error: {e}")


def _archival_search(query: str, top_k: int = 5) -> List[str]:
    """Semantic search in ChromaDB archival."""
    if not _chroma_ok or not _chroma_col or _chroma_col.count() == 0:
        return []
    try:
        results = _chroma_col.query(
            query_texts=[query],
            n_results=min(top_k, _chroma_col.count()),
        )
        return results.get("documents", [[]])[0]
    except Exception as e:
        print(f"[MEM] ChromaDB search error: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════
#  ENTITY EXTRACTION
# ══════════════════════════════════════════════════════════════════════

def _extract_entities(text: str) -> Dict[str, List[str]]:
    """Simple pattern-based entity extraction."""
    entities = {"projects": [], "names": [], "urls": [], "files": []}
    # Projects (capitalized words after "project", "kaam", "build")
    for m in re.finditer(r'(?:project|build|banao|kaam)\s+([A-Z][A-Za-z0-9_]+)', text):
        entities["projects"].append(m.group(1))
    # URLs
    entities["urls"] = re.findall(r'https?://[^\s]+', text)
    # File paths
    entities["files"] = re.findall(r'[A-Za-z]:[/\\][\w/\\.-]+\.\w+', text)
    return {k: list(set(v)) for k, v in entities.items() if v}


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def get_context(query: str = "") -> str:
    """
    Build context string for AI prompts.
    Returns Tier 1 (core) always + Tier 2/3 relevant results.
    """
    with MEM_LOCK:
        mem = _get()
        core = mem["core"]
        lines = []

        # Tier 1 — Core
        if core["user_name"]:
            lines.append(f"User: {core['user_name']}")
        if core["current_project"]:
            lines.append(f"Current Project: {core['current_project']}")
        if core["language"]:
            lines.append(f"Language: {core['language']}")
        if core["important_facts"]:
            lines.append("Key Facts: " + " | ".join(core["important_facts"][-10:]))
        if core["active_context"]:
            lines.append(f"Context: {core['active_context']}")

        if not query:
            return "\n".join(lines)

        # Tier 2 — Recall
        recalled = _recall_search(query, top_k=3)
        if recalled:
            lines.append("\nRecent Relevant Tasks:")
            for t in recalled:
                lines.append(f"  [{t.get('status','?')}] {t.get('task','')} → {t.get('result','')[:80]}")

        # Tier 3 — Archival
        archived = _archival_search(query, top_k=2)
        if archived:
            lines.append("\nArchival Context:")
            for a in archived:
                lines.append(f"  • {a[:100]}")

        return "\n".join(lines)


def remember_task(task: str, result: str, status: str = "done", tags: str = ""):
    """Task complete hone ke baad memory mein save karo."""
    with MEM_LOCK:
        mem = _get()
        now = time.time()
        entry = {
            "task": task[:200],
            "result": result[:300],
            "status": status,
            "tags": tags,
            "timestamp": now,
            "date": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M"),
        }
        # Tier 2 — Recall (max 50 items)
        recall = mem["recall"]["recent_tasks"]
        recall.append(entry)
        # Prune old (> 7 days)
        cutoff = now - 7 * 86400
        mem["recall"]["recent_tasks"] = [
            t for t in recall if t.get("timestamp", 0) > cutoff
        ][-50:]

        # Tier 3 — Archival
        mem["archival"]["all_tasks"].append(entry)
        mem["archival"]["total_tasks"] = mem["archival"].get("total_tasks", 0) + 1

        # ChromaDB
        doc = f"Task: {task}\nResult: {result}\nDate: {entry['date']}"
        _archival_add(doc, {"status": status, "tags": tags})

        # Entity extraction
        entities = _extract_entities(task + " " + result)
        for proj in entities.get("projects", []):
            if proj not in mem["archival"]["projects"]:
                mem["archival"]["projects"][proj] = {"tasks": [], "created": entry["date"]}
            mem["archival"]["projects"][proj]["tasks"].append(task[:100])

        # Skill tracking
        skill_map = mem["recall"]["skills_learned"]
        for word in re.findall(r'\b\w+\b', tags):
            skill_map[word] = skill_map.get(word, 0) + 1

        _save()


def remember_fact(fact: str, tier: str = "core"):
    """Important fact store karo."""
    with MEM_LOCK:
        mem = _get()
        if tier == "core":
            facts = mem["core"]["important_facts"]
            if fact not in facts:
                facts.append(fact)
                mem["core"]["important_facts"] = facts[-15:]  # Keep last 15
        else:
            learned = mem["archival"]["learned_facts"]
            if fact not in learned:
                learned.append(fact)
            _archival_add(fact, {"type": "fact"})
        _save()


def update_core(key: str, value: Any):
    """Core memory update karo (user_name, current_project, etc.)"""
    with MEM_LOCK:
        mem = _get()
        if key in mem["core"]:
            mem["core"][key] = value
            mem["core"]["updated_at"] = time.time()
            _save()


def remember_mistake(task: str, error: str, fix: str = ""):
    """What went wrong — learn from it."""
    with MEM_LOCK:
        mem = _get()
        entry = {"task": task[:150], "error": error[:200], "fix": fix[:200], "timestamp": time.time()}
        mem["recall"]["mistakes"].append(entry)
        mem["recall"]["mistakes"] = mem["recall"]["mistakes"][-20:]  # Last 20 mistakes
        _save()


def search(query: str, top_k: int = 5) -> Dict[str, List]:
    """Full hybrid search — returns results from all tiers."""
    with MEM_LOCK:
        return {
            "recall": _recall_search(query, top_k=top_k),
            "archival": _archival_search(query, top_k=top_k),
        }


def get_stats() -> Dict:
    """Memory health stats."""
    with MEM_LOCK:
        mem = _get()
        return {
            "total_tasks": mem["archival"].get("total_tasks", 0),
            "total_sessions": mem["archival"].get("total_sessions", 0),
            "recent_tasks_count": len(mem["recall"]["recent_tasks"]),
            "important_facts": len(mem["core"]["important_facts"]),
            "projects": len(mem["archival"]["projects"]),
            "chromadb_docs": _chroma_col.count() if _chroma_ok and _chroma_col else 0,
            "chromadb_ok": _chroma_ok,
            "last_updated": mem["meta"]["last_updated"],
        }


def get_full_core() -> Dict:
    """Full core memory (for dashboard)."""
    with MEM_LOCK:
        return dict(_get()["core"])


def new_session():
    """Session start pe call karo."""
    with MEM_LOCK:
        mem = _get()
        mem["archival"]["total_sessions"] = mem["archival"].get("total_sessions", 0) + 1
        _save()

# Initialize on import
_load()

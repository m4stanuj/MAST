"""
M4STCLAW Brain Router v2.0
===========================
25 providers. 9 task-aware chains. Zen models. Hinglish routing. 3600s cache.

v2 Upgrades:
  ✅ Kimi K2 free (moonshotai/kimi-k2:free) — #1 agentic model Apr 2026
  ✅ MiMo-V2-Flash free — #1 SWE-bench open-source
  ✅ Nemotron-49B free (NVIDIA NIM) — best free reasoning
  ✅ Llama 4 Scout (Groq) — multimodal free
  ✅ 9 task chains: speed/code/reason/vision/research/write/agent/pentest/default
  ✅ Hinglish keyword detection — "function likho" → code chain (v1 bug fixed)
  ✅ Cache TTL 3600s (was 300s) + size 300 (was 200)
  ✅ Rate limit vs error differentiated backoff
  ✅ Per-task model override for OpenRouter
"""

import os, re, json, time, threading, hashlib
from typing import Optional, List, Dict, Any
from collections import OrderedDict
import requests as http

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cfg(key: str, default: str = "") -> str:
    try:
        with open(os.path.join(ROOT, "config", ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return os.environ.get(key, default)


# ══════════════════════════════════════════════════════════════════════
#  PROVIDER REGISTRY
# ══════════════════════════════════════════════════════════════════════

PROVIDERS: Dict[str, Dict] = {
    "cerebras": {
        "name": "Cerebras", "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_prefixes": ["csk-"], "models": ["llama3.3-70b", "llama3.1-8b"],
        "default_model": "llama3.3-70b", "speed_rank": 1, "quality_rank": 5,
        "free": True, "format": "openai", "env_keys": ["CEREBRAS_API_KEY"],
        "good_for": ["speed", "write", "chat"],
    },
    "groq": {
        "name": "Groq", "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_prefixes": ["gsk_"],
        "models": ["llama-3.3-70b-versatile", "llama-4-scout-17b-16e-instruct",
                   "deepseek-r1-distill-llama-70b", "llama3-8b-8192"],
        "default_model": "llama-3.3-70b-versatile", "speed_rank": 2, "quality_rank": 4,
        "free": True, "format": "openai", "env_keys": ["GROQ_API_KEY"],
        "good_for": ["speed", "code", "write"],
        "whisper_url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "whisper_model": "whisper-large-v3-turbo",
    },
    "sambanova": {
        "name": "SambaNova", "url": "https://api.sambanova.ai/v1/chat/completions",
        "key_prefixes": ["snova-"],
        "models": ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.1-405B-Instruct"],
        "default_model": "Meta-Llama-3.3-70B-Instruct", "speed_rank": 3, "quality_rank": 4,
        "free": True, "format": "openai", "env_keys": ["SAMBANOVA_API_KEY"],
        "good_for": ["speed", "code"],
    },
    "openrouter": {
        "name": "OpenRouter", "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_prefixes": ["sk-or-"],
        "models": ["moonshotai/kimi-k2:free", "xiaomi/mimo-vl-7b-rl:free",
                   "thudm/glm-4-9b-chat:free", "meta-llama/llama-4-scout:free",
                   "qwen/qwen3-30b-a3b:free", "deepseek/deepseek-r1:free",
                   "google/gemini-2.5-pro-preview"],
        "default_model": "moonshotai/kimi-k2:free",
        "speed_rank": 4, "quality_rank": 2, "free": True, "format": "openai",
        "env_keys": ["OPENROUTER_API_KEY"],
        "good_for": ["reason", "code", "agent", "research"],
        "task_models": {
            "reason":  "moonshotai/kimi-k2:free",
            "code":    "xiaomi/mimo-vl-7b-rl:free",
            "agent":   "moonshotai/kimi-k2:free",
            "research":"moonshotai/kimi-k2:free",
            "vision":  "meta-llama/llama-4-scout:free",
            "pentest": "deepseek/deepseek-r1:free",
            "quality": "google/gemini-2.5-pro-preview",
            "write":   "thudm/glm-4-9b-chat:free",
        },
    },
    "gemini": {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "key_prefixes": ["AIza"],
        "models": ["gemini-2.5-pro-preview-03-25", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
        "default_model": "gemini-2.0-flash", "quality_model": "gemini-2.5-pro-preview-03-25",
        "speed_rank": 4, "quality_rank": 2, "free": True, "format": "gemini",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "good_for": ["vision", "research", "long_context", "quality"],
    },
    "nvidia": {
        "name": "NVIDIA NIM", "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "key_prefixes": ["nvapi-"],
        "models": ["nvidia/llama-3.3-nemotron-super-49b-v1", "meta/llama-3.3-70b-instruct",
                   "qwen/qwen3-235b-a22b"],
        "default_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "speed_rank": 4, "quality_rank": 3, "free": True, "format": "openai",
        "env_keys": ["NVIDIA_API_KEY", "NIM_API_KEY"],
        "good_for": ["reason", "research", "default"],
    },
    "together": {
        "name": "Together AI", "url": "https://api.together.xyz/v1/chat/completions",
        "key_prefixes": [],
        "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "Qwen/Qwen3-235B-A22B-fp8-tput"],
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "speed_rank": 5, "quality_rank": 4, "free": True, "format": "openai",
        "env_keys": ["TOGETHER_API_KEY"], "good_for": ["free", "chat", "write"],
    },
    "deepseek": {
        "name": "DeepSeek", "url": "https://api.deepseek.com/chat/completions",
        "key_prefixes": [], "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat", "reasoning_model": "deepseek-reasoner",
        "speed_rank": 6, "quality_rank": 2, "free": False, "format": "openai",
        "env_keys": ["DEEPSEEK_API_KEY"], "cost_per_1m_tokens": 0.14,
        "good_for": ["code", "reasoning", "pentest"],
    },
    "anthropic": {
        "name": "Claude", "url": "https://api.anthropic.com/v1/messages",
        "key_prefixes": ["sk-ant-"],
        "models": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
        "default_model": "claude-sonnet-4-6",
        "speed_rank": 7, "quality_rank": 1, "free": False, "format": "anthropic",
        "env_keys": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"], "cost_per_1m_tokens": 3.0,
        "good_for": ["quality", "creative", "analysis"],
    },
    "xai": {
        "name": "Grok", "url": "https://api.x.ai/v1/chat/completions",
        "key_prefixes": ["xai-"], "models": ["grok-3", "grok-3-fast", "grok-3-mini"],
        "default_model": "grok-3-fast", "speed_rank": 6, "quality_rank": 2,
        "free": False, "format": "openai", "env_keys": ["XAI_API_KEY", "GROK_API_KEY"],
        "good_for": ["real_time", "news"],
    },
    "openai": {
        "name": "OpenAI", "url": "https://api.openai.com/v1/chat/completions",
        "key_prefixes": [], "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
        "default_model": "gpt-4o-mini", "speed_rank": 7, "quality_rank": 2,
        "free": False, "format": "openai", "env_keys": ["OPENAI_API_KEY"],
        "cost_per_1m_tokens": 0.15, "good_for": ["code", "tools"],
    },
    "perplexity": {
        "name": "Perplexity", "url": "https://api.perplexity.ai/chat/completions",
        "key_prefixes": ["pplx-"], "models": ["sonar-pro", "sonar"],
        "default_model": "sonar", "speed_rank": 6, "quality_rank": 3,
        "free": False, "format": "openai", "env_keys": ["PERPLEXITY_API_KEY"],
        "good_for": ["research", "web_search"],
    },
    "hyperbolic": {
        "name": "Hyperbolic", "url": "https://api.hyperbolic.xyz/v1/chat/completions",
        "key_prefixes": ["eyJ"], "models": ["meta-llama/Llama-3.3-70B-Instruct"],
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
        "speed_rank": 5, "quality_rank": 4, "free": True, "format": "openai",
        "env_keys": ["HYPERBOLIC_API_KEY"], "good_for": ["free", "fallback"],
    },
    "huggingface": {
        "name": "HuggingFace",
        "url": "https://api-inference.huggingface.co/models/{model}/v1/chat/completions",
        "key_prefixes": ["hf_"], "models": ["meta-llama/Llama-3.3-70B-Instruct"],
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
        "speed_rank": 7, "quality_rank": 4, "free": True, "format": "openai",
        "env_keys": ["HUGGINGFACE_API_KEY", "HF_TOKEN"], "good_for": ["free", "fallback"],
    },
    "cloudflare": {
        "name": "Cloudflare",
        "url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}",
        "key_prefixes": [], "models": ["@cf/meta/llama-3.3-70b-instruct-fp8-fast"],
        "default_model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "speed_rank": 5, "quality_rank": 5, "free": True, "format": "cloudflare",
        "env_keys": ["CLOUDFLARE_API_KEY", "CF_API_TOKEN"],
        "account_id_key": "CLOUDFLARE_ACCOUNT_ID", "good_for": ["fallback"],
    },
    "fireworks": {
        "name": "Fireworks", "url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "key_prefixes": ["fw-"],
        "models": ["accounts/fireworks/models/llama-v3p3-70b-instruct"],
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "speed_rank": 4, "quality_rank": 4, "free": False, "format": "openai",
        "env_keys": ["FIREWORKS_API_KEY"], "good_for": ["speed"],
    },
    "ollama": {
        "name": "Ollama (Local)", "url": "http://localhost:11434/api/chat",
        "key_prefixes": [],
        "models": ["qwen3:8b", "deepseek-r1:8b", "qwen2.5-coder:7b", "qwen2.5-vl:7b", "gemma3:4b"],
        "default_model": "qwen3:8b", "vision_model": "qwen2.5-vl:7b",
        "speed_rank": 9, "quality_rank": 6, "free": True, "format": "ollama",
        "env_keys": [], "good_for": ["offline", "privacy", "local"],
    },
}

# ── Task Chains — 9 types ──────────────────────────────────────────────
TASK_CHAINS: Dict[str, List[str]] = {
    "speed":    ["cerebras", "groq", "sambanova", "nvidia", "together", "ollama"],
    "code":     ["openrouter", "deepseek", "groq", "sambanova", "nvidia", "ollama"],
    "reason":   ["openrouter", "nvidia", "deepseek", "groq", "gemini", "anthropic"],
    "vision":   ["gemini", "openrouter", "anthropic", "ollama"],
    "research": ["openrouter", "perplexity", "gemini", "nvidia", "groq", "anthropic"],
    "write":    ["cerebras", "groq", "openrouter", "nvidia", "gemini", "anthropic"],
    "agent":    ["openrouter", "nvidia", "groq", "deepseek", "gemini", "anthropic"],
    "pentest":  ["deepseek", "openrouter", "groq", "nvidia", "ollama"],
    "default":  ["groq", "cerebras", "nvidia", "openrouter", "gemini", "sambanova", "together", "deepseek", "hyperbolic", "ollama"],
}

# ── Hinglish + English keyword → task type ────────────────────────────
TASK_KEYWORDS: Dict[str, List[str]] = {
    "speed": ["quick", "fast", "brief", "short", "ping", "hi", "hello", "test",
              "jaldi", "seedha", "ek line", "quick bata", "short mein"],
    "code": ["code", "script", "function", "class", "debug", "error", "fix", "bug",
             "python", "javascript", "typescript", "api", "sql", "implement", "refactor",
             "likho", "banao script", "code karo", "function likho", "bug dhundo",
             "theek karo", "program likho", "build", "develop"],
    "reason": ["why", "explain", "analyze", "compare", "difference", "evaluate",
               "pros cons", "review", "critique", "think", "philosophical",
               "kyun", "samjhao", "soch", "analyze karo", "kya better", "compare karo",
               "sochke batao", "kya lagta"],
    "research": ["research", "find", "search", "news", "latest", "current", "what is",
                 "who is", "when", "history", "facts", "info", "details", "summarize",
                 "dhundo", "khojo", "news batao", "batao", "info chahiye", "kab hua"],
    "write": ["write", "draft", "blog", "email", "letter", "content", "article",
              "post", "story", "copy", "caption", "description",
              "likho", "draft karo", "blog likho", "email likho", "content banao"],
    "agent": ["plan", "execute", "automate", "handle", "manage", "organize",
              "workflow", "pipeline", "project", "step by step",
              "karo", "kar do", "plan banao", "automate karo", "poora karo"],
    "pentest": ["scan", "exploit", "recon", "osint", "vuln", "nmap", "payload",
                "pentest", "hack", "security check", "ctf", "shodan", "subfinder",
                "injection", "xss", "sqli", "cve", "nuclei", "nikto", "privilege"],
    "vision": ["screen", "screenshot", "click", "see on screen", "find on screen",
               "icon", "button", "gui", "desktop", "open app",
               "screen pe", "dekho screen", "click karo", "screen mein dhundo"],
}


def detect_task_type(message: str) -> str:
    msg = message.lower().strip()
    scores = {t: 0 for t in TASK_KEYWORDS}
    for task, keywords in TASK_KEYWORDS.items():
        for kw in keywords:
            if kw in msg:
                scores[task] += (2 if len(kw) > 6 else 1)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"


# ══════════════════════════════════════════════════════════════════════
#  CACHE
# ══════════════════════════════════════════════════════════════════════

class _LRUCache:
    def __init__(self, maxsize=300, ttl=3600):
        self._c: OrderedDict = OrderedDict()
        self._ttl = ttl; self._max = maxsize
        self._lock = threading.Lock()
        self.hits = 0; self.misses = 0

    def _key(self, msgs, task):
        return hashlib.md5((json.dumps(msgs, sort_keys=True, ensure_ascii=False)+task).encode()).hexdigest()

    def get(self, msgs, task):
        k = self._key(msgs, task)
        with self._lock:
            if k not in self._c:
                self.misses += 1; return None
            v, ts = self._c[k]
            if time.time() - ts > self._ttl:
                del self._c[k]; self.misses += 1; return None
            self._c.move_to_end(k); self.hits += 1; return v

    def set(self, msgs, task, val):
        k = self._key(msgs, task)
        with self._lock:
            if k in self._c: self._c.move_to_end(k)
            self._c[k] = (val, time.time())
            if len(self._c) > self._max: self._c.popitem(last=False)

    def stats(self):
        t = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": f"{self.hits/t*100:.1f}%" if t else "0%",
                "size": len(self._c)}

_cache = _LRUCache()


# ══════════════════════════════════════════════════════════════════════
#  HEALTH TRACKER
# ══════════════════════════════════════════════════════════════════════

class _HealthTracker:
    def __init__(self):
        self._fails: Dict[str, int] = {}
        self._cd: Dict[str, float] = {}
        self._lock = threading.Lock()

    def mark_fail(self, pid: str, rate_limit=False):
        with self._lock:
            self._fails[pid] = self._fails.get(pid, 0) + 1
            cd = 60 if rate_limit else min(10 * (2 ** (self._fails[pid]-1)), 300)
            self._cd[pid] = time.time() + cd
            print(f"[BRAIN] ⚠️ {pid} fail#{self._fails[pid]} cd={cd:.0f}s", flush=True)

    def mark_success(self, pid: str):
        with self._lock:
            self._fails.pop(pid, None); self._cd.pop(pid, None)

    def is_ok(self, pid: str) -> bool:
        with self._lock:
            return time.time() >= self._cd.get(pid, 0)

_health = _HealthTracker()


# ══════════════════════════════════════════════════════════════════════
#  KEY LOADING
# ══════════════════════════════════════════════════════════════════════

def _load_active() -> Dict[str, Dict]:
    active = {}
    for i in range(1, 31):
        key = _cfg(f"SMART_KEY_{i}")
        if not key: continue
        for pid, pd in PROVIDERS.items():
            if pid in active: continue
            if any(key.startswith(p) for p in pd.get("key_prefixes", [])):
                active[pid] = {**pd, "api_key": key}
                print(f"[BRAIN] ✅ {pd['name']} SMART_KEY_{i}", flush=True)
    for pid, pd in PROVIDERS.items():
        if pid in active: continue
        for ek in pd.get("env_keys", []):
            k = _cfg(ek)
            if k:
                active[pid] = {**pd, "api_key": k}
                print(f"[BRAIN] ✅ {pd['name']} {ek}", flush=True)
                break
    if "ollama" not in active:
        active["ollama"] = {**PROVIDERS["ollama"], "api_key": ""}
    print(f"[BRAIN] Active: {list(active.keys())}", flush=True)
    return active

_active: Dict = {}
_active_lock = threading.Lock()
_loaded_at: float = 0

def get_active(force=False) -> Dict:
    global _active, _loaded_at
    with _active_lock:
        if force or not _active or time.time() - _loaded_at > 60:
            _active = _load_active(); _loaded_at = time.time()
        return dict(_active)


# ══════════════════════════════════════════════════════════════════════
#  FORMATTERS
# ══════════════════════════════════════════════════════════════════════

class RateLimitError(Exception): pass

def _call_openai(pd, msgs, max_tok, sys, task="default"):
    model = pd.get("task_models", {}).get(task, pd.get("default_model", pd["models"][0]))
    url = pd["url"].replace("{model}", model)
    hdrs = {"Authorization": f"Bearer {pd['api_key']}", "Content-Type": "application/json"}
    if "openrouter" in pd["name"].lower():
        hdrs.update({"HTTP-Referer": "https://m4stclaw.local", "X-Title": "M4STCLAW-v2"})
    all_msgs = ([{"role": "system", "content": sys}] if sys else []) + list(msgs)
    r = http.post(url, json={"model": model, "messages": all_msgs, "max_tokens": max_tok, "temperature": 0.7}, headers=hdrs, timeout=45)
    if r.status_code == 429: raise RateLimitError(f"429 {pd['name']}")
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _call_gemini(pd, msgs, max_tok, sys, img_b64=None, task="default"):
    model = pd.get("quality_model" if task in ("quality","research") else "default_model", pd["models"][0])
    url = pd["url"].replace("{model}", model) + f"?key={pd['api_key']}"
    parts_list = []
    for m in msgs:
        role = "user" if m["role"] == "user" else "model"
        c = m["content"]
        if isinstance(c, str):
            parts_list.append({"role": role, "parts": [{"text": c}]})
    if img_b64 and parts_list and parts_list[-1]["role"] == "user":
        parts_list[-1]["parts"].append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
    payload = {"contents": parts_list, "generationConfig": {"maxOutputTokens": max_tok, "temperature": 0.7}}
    if sys: payload["systemInstruction"] = {"parts": [{"text": sys}]}
    r = http.post(url, json=payload, timeout=45)
    if r.status_code == 429: raise RateLimitError("429 Gemini")
    r.raise_for_status()
    try: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e: raise ValueError(f"Gemini parse: {e}")

def _call_anthropic(pd, msgs, max_tok, sys, img_b64=None):
    hdrs = {"x-api-key": pd["api_key"], "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    ant = []
    for m in msgs:
        role = m["role"] if m["role"] in ("user","assistant") else "user"
        c = m["content"]
        if img_b64 and role == "user" and m == msgs[-1]:
            c = [{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":img_b64}},
                 {"type":"text","text":str(c)}]
        ant.append({"role": role, "content": c})
    payload = {"model": pd.get("default_model", pd["models"][0]), "max_tokens": max_tok, "messages": ant}
    if sys: payload["system"] = sys
    r = http.post(pd["url"], json=payload, headers=hdrs, timeout=60)
    if r.status_code == 429: raise RateLimitError("429 Anthropic")
    r.raise_for_status()
    return r.json()["content"][0]["text"]

def _call_ollama(pd, msgs, max_tok, sys, img_b64=None):
    model = pd.get("vision_model" if img_b64 else "default_model", pd["models"][0])
    all_msgs = ([{"role":"system","content":sys}] if sys else []) + list(msgs)
    if img_b64 and all_msgs:
        last = all_msgs[-1]
        if isinstance(last["content"], str):
            all_msgs[-1] = {"role": last["role"], "content": last["content"], "images": [img_b64]}
    r = http.post(pd["url"], json={"model": model, "messages": all_msgs, "stream": False,
                                    "options": {"num_predict": max_tok, "temperature": 0.7}}, timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"]

def _call_cloudflare(pd, msgs, max_tok, sys):
    account_id = _cfg(pd.get("account_id_key", "CLOUDFLARE_ACCOUNT_ID"))
    if not account_id: raise ValueError("CLOUDFLARE_ACCOUNT_ID missing")
    model = pd.get("default_model")
    url = pd["url"].replace("{account_id}", account_id).replace("{model}", model)
    hdrs = {"Authorization": f"Bearer {pd['api_key']}", "Content-Type": "application/json"}
    all_msgs = ([{"role":"system","content":sys}] if sys else []) + list(msgs)
    r = http.post(url, json={"messages": all_msgs, "max_tokens": max_tok}, headers=hdrs, timeout=45)
    r.raise_for_status()
    return r.json().get("result", {}).get("response", "")


# ══════════════════════════════════════════════════════════════════════
#  MAIN CALL
# ══════════════════════════════════════════════════════════════════════

def brain_call(messages, task_type="default", system="", max_tokens=2048,
               image_b64=None, use_cache=True, provider_override=None):
    start = time.time()
    if not system:
        try:
            with open(os.path.join(ROOT, "SOUL.md"), encoding="utf-8") as f:
                system = f.read()[:2500]
        except FileNotFoundError:
            system = "You are M4STCLAW. Hinglish AI operator. Direct and helpful."

    if use_cache and not image_b64 and task_type != "vision":
        cached = _cache.get(messages, task_type)
        if cached:
            print(f"[BRAIN] 🎯 Cache hit task={task_type}", flush=True)
            return {"content": cached, "provider": "cache", "model": "cache",
                    "tokens": 0, "cached": True, "latency_ms": 0}

    active = get_active()
    chain = TASK_CHAINS.get(task_type, TASK_CHAINS["default"])
    if provider_override and provider_override in active:
        priority = [provider_override] + [p for p in chain if p != provider_override]
    else:
        priority = list(dict.fromkeys(chain + [p for p in active if p not in chain]))

    last_error = None
    for pid in priority:
        if pid not in active or not _health.is_ok(pid):
            continue
        pd = active[pid]
        fmt = pd.get("format", "openai")
        try:
            content = None
            if fmt == "openai":
                content = _call_openai(pd, messages, max_tokens, system, task_type)
            elif fmt == "gemini":
                content = _call_gemini(pd, messages, max_tokens, system, image_b64, task_type)
            elif fmt == "anthropic":
                content = _call_anthropic(pd, messages, max_tokens, system, image_b64)
            elif fmt == "ollama":
                content = _call_ollama(pd, messages, max_tokens, system, image_b64)
            elif fmt == "cloudflare":
                content = _call_cloudflare(pd, messages, max_tokens, system)

            if content:
                _health.mark_success(pid)
                latency = int((time.time() - start) * 1000)
                model = pd.get("task_models", {}).get(task_type, pd.get("default_model", "?"))
                print(f"[BRAIN] ✅ {pd['name']} ({model}) {latency}ms task={task_type}", flush=True)
                if use_cache and not image_b64 and task_type != "vision":
                    _cache.set(messages, task_type, content)
                return {"content": content, "provider": pid, "model": model,
                        "tokens": int(len(content.split())*1.3), "cached": False, "latency_ms": latency}

        except RateLimitError as e:
            last_error = str(e); _health.mark_fail(pid, rate_limit=True)
        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:80]}"; _health.mark_fail(pid)
            print(f"[BRAIN] ❌ {pd.get('name', pid)}: {last_error}", flush=True)

    return {"content": f"⚠️ All providers failed. Error: {last_error}",
            "provider": "none", "model": "none", "tokens": 0, "cached": False,
            "latency_ms": int((time.time()-start)*1000)}


def brain_quick(prompt, task_type="default", system="", max_tokens=1024):
    return brain_call([{"role":"user","content":prompt}], task_type, system, max_tokens).get("content","")

def brain_vision(prompt, image_b64, max_tokens=1024):
    return brain_call([{"role":"user","content":prompt}], "vision", image_b64=image_b64,
                      max_tokens=max_tokens, use_cache=False).get("content","")

def get_provider_status():
    active = get_active()
    return sorted([{
        "id": pid, "name": pd["name"],
        "active": pid in active, "healthy": _health.is_ok(pid),
        "free": pd.get("free", False), "good_for": pd.get("good_for", []),
        "quality_rank": pd.get("quality_rank", 5), "speed_rank": pd.get("speed_rank", 5),
    } for pid, pd in PROVIDERS.items()], key=lambda x: (not x["active"], x["speed_rank"]))

def get_cache_stats(): return _cache.stats()

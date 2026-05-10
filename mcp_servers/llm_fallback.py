"""
llm_fallback.py — MAST LLM Fallback Router v6.0
===================================================
Project: MAST (M4STCLAW v3 + OpenWork v12 + EIGENT v4.1 merged)
Keys: Loaded from .env — NEVER hardcoded here
Providers: Groq, Cerebras, Gemini, OpenRouter, SambaNova,
           DeepSeek, Together, NVIDIA NIM, Mistral, xAI/Grok, HuggingFace

SMART_KEY auto-detect (paste any key as SMART_KEY_N in .env):
  gsk_    = Groq       | csk-   = Cerebras  | AIza    = Gemini
  sk-or-  = OpenRouter | nvapi- = NVIDIA NIM | msk-   = Mistral
  xai-    = xAI/Grok  | hf_    = HuggingFace | sk-ant- = Anthropic
  UUID    = SambaNova  | sk-    = DeepSeek/Together

Task Chains (6 models, best-first):
  speed    : Groq → Cerebras → Nemotron → MiniMax → Gemini-Flash → OR-Default
  reason   : Kimi-K2 → DeepSeek-R1 → Nemotron → Qwen3 → MiniMax → Gemini-Pro
  code     : Kimi-K2 → Qwen3-Coder → MiMo-Pro → NVIDIA → DeepSeek → SambaNova
  vision   : Gemini-2.5-Flash → MiMo-Omni → Llama4 → Gemini-Flash → Kimi-VL → Qwen-VL
  research : Kimi-K2 → DeepSeek-R1 → Nemotron → GPT-OSS → MiniMax → Gemini-Pro
  write    : Mistral-Large → Cerebras → Groq → Nemotron → MiniMax → DeepSeek-V3
  agent    : Kimi-K2 → Qwen3 → Nemotron → Groq → Gemini-Flash → MiMo-Omni
  pentest  : NVIDIA/deepseek → NVIDIA/GLM → DeepSeek-R1 → Groq (authorized only!)
  hinglish : NVIDIA/Sarvam-M → Gemini-Flash → Groq → Cerebras
"""

import os, time, logging, json, hashlib, re, threading
from typing import Optional
from pathlib import Path

log = logging.getLogger("llm_fallback")

# ── Config dir & .env loading ─────────────────────────────────────────
def _find_config_dir() -> Path:
    env = os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG")
    if env: return Path(env)
    return Path(os.path.expanduser("~/.config/opencode"))

_CONFIG_DIR = _find_config_dir()

def _load_dotenv_simple(path: Path):
    """Simple .env loader — no dependency on python-dotenv."""
    if not path.exists(): return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val and key not in os.environ:
            os.environ[key] = val

# Try .env from multiple locations
for _env in [
    _CONFIG_DIR / ".env",
    _CONFIG_DIR / "config" / ".env",
    Path(".env"),
]:
    if _env.exists():
        _load_dotenv_simple(_env)
        log.info(f"  📂 .env loaded from {_env}")
        break

# ═══════════════════════════════════════════════════════════════
# KEY LOADING
# ═══════════════════════════════════════════════════════════════

def _load_keys(prefix: str) -> list:
    keys = []
    base = os.getenv(f"{prefix}_API_KEY", "").strip()
    if base: keys.append(base)
    for i in range(1, 21):
        k = os.getenv(f"{prefix}_API_KEY_{i}", "").strip()
        if k: keys.append(k)
    seen = set()
    return [k for k in keys if k and not (k in seen or seen.add(k))]

def _load_smart_keys() -> dict:
    _UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    smart = {}
    for i in range(1, 30):
        k = os.getenv(f"SMART_KEY_{i}", "").strip()
        if not k: continue
        if k.startswith("gsk_"):            smart.setdefault("GROQ", []).append(k)
        elif k.startswith("csk-"):          smart.setdefault("CEREBRAS", []).append(k)
        elif k.startswith("AIza"):          smart.setdefault("GEMINI", []).append(k)
        elif k.startswith("sk-or-"):        smart.setdefault("OPENROUTER", []).append(k)
        elif k.startswith("nvapi-"):        smart.setdefault("NVIDIA", []).append(k)
        elif k.startswith("msk-"):          smart.setdefault("MISTRAL", []).append(k)
        elif k.startswith("xai-"):          smart.setdefault("GROKAI", []).append(k)
        elif k.startswith("hf_"):           smart.setdefault("HUGGINGFACE", []).append(k)
        elif k.startswith("sk-ant-"):       smart.setdefault("ANTHROPIC", []).append(k)
        elif _UUID.match(k):                smart.setdefault("SAMBANOVA", []).append(k)
        elif k.startswith("sk-"):
            smart.setdefault("DEEPSEEK", []).append(k)
            smart.setdefault("TOGETHER", []).append(k)
    return smart

_smart = _load_smart_keys()

def _keys(prefix: str) -> list:
    explicit = _load_keys(prefix)
    extra = _smart.get(prefix, [])
    seen = set()
    merged = []
    for k in explicit + extra:
        if k not in seen:
            seen.add(k)
            merged.append(k)
    return merged or ["PLACEHOLDER_NO_KEY"]

GROQ_KEYS        = _keys("GROQ")
CEREBRAS_KEYS    = _keys("CEREBRAS")
GEMINI_KEYS      = _keys("GEMINI")
OPENROUTER_KEYS  = _keys("OPENROUTER")
SAMBANOVA_KEYS   = _keys("SAMBANOVA")
DEEPSEEK_KEYS    = _keys("DEEPSEEK")
TOGETHER_KEYS    = _keys("TOGETHER")
NVIDIA_KEYS      = _keys("NVIDIA")
MISTRAL_KEYS     = _keys("MISTRAL")
GROKAI_KEYS      = _keys("GROKAI")
HUGGINGFACE_KEYS = _keys("HUGGINGFACE")
ANTHROPIC_KEYS   = _keys("ANTHROPIC")

log.info(
    f"  Keys: Groq={len(GROQ_KEYS)} Cerebras={len(CEREBRAS_KEYS)} Gemini={len(GEMINI_KEYS)} "
    f"OR={len(OPENROUTER_KEYS)} SambaNo={len(SAMBANOVA_KEYS)} DeepSeek={len(DEEPSEEK_KEYS)} "
    f"NVIDIA={len(NVIDIA_KEYS)} Mistral={len(MISTRAL_KEYS)} Grok={len(GROKAI_KEYS)}"
)

# ═══════════════════════════════════════════════════════════════
# PROVIDER CONFIGS
# ═══════════════════════════════════════════════════════════════

def _p(name, keys, model, type_, base_url=None):
    d = {"name": name, "keys": keys, "model": model, "type": type_, "_idx": 0}
    if base_url: d["base_url"] = base_url
    return d

_NIM = "https://integrate.api.nvidia.com/v1"

# Core providers
_GROQ         = _p("groq",       GROQ_KEYS,      "llama-3.3-70b-versatile",                      "openai_compat", "https://api.groq.com/openai/v1")
_CEREBRAS     = _p("cerebras",   CEREBRAS_KEYS,  "llama-3.3-70b",                                "openai_compat", "https://api.cerebras.ai/v1")
_GEMINI_F     = _p("gemini",     GEMINI_KEYS,    "gemini-2.0-flash",                             "gemini")
_GEMINI_25F   = _p("gemini25f",  GEMINI_KEYS,    "gemini-2.5-flash-preview-05-20",               "gemini")
_GEMINI_25P   = _p("gemini25p",  GEMINI_KEYS,    "gemini-2.5-pro-preview-05-06",                 "gemini")
_SAMBANOVA    = _p("sambanova",  SAMBANOVA_KEYS, "Meta-Llama-3.1-405B-Instruct",                 "openai_compat", "https://api.sambanova.ai/v1")
_DEEPSEEK     = _p("deepseek",   DEEPSEEK_KEYS,  "deepseek-chat",                                "openai_compat", "https://api.deepseek.com")
_DEEPSEEK_R1  = _p("deepseekr1", DEEPSEEK_KEYS,  "deepseek-reasoner",                            "openai_compat", "https://api.deepseek.com")
_TOGETHER     = _p("together",   TOGETHER_KEYS,  "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "openai_compat", "https://api.together.xyz/v1")

# NVIDIA NIM — free 40 RPM
_NVIDIA_DSV4  = _p("nvidia_dsv4",  NVIDIA_KEYS, "nvidia/deepseek-r1-0528",                "openai_compat", _NIM)
_NVIDIA_DSFL  = _p("nvidia_dsfl",  NVIDIA_KEYS, "nvidia/deepseek-r1-0528-qwen3-8b",       "openai_compat", _NIM)
_NVIDIA_GLM   = _p("nvidia_glm",   NVIDIA_KEYS, "nvidia/llama-3.3-nemotron-super-49b-v1", "openai_compat", _NIM)
_NVIDIA_NEMO  = _p("nvidia_nemo",  NVIDIA_KEYS, "nvidia/llama-3.2-nemo-instruct",          "openai_compat", _NIM)
_NVIDIA_SARV  = _p("nvidia_sarv",  NVIDIA_KEYS, "nvidia/mistral-nemo-12b-instruct",        "openai_compat", _NIM)

# Mistral
_MISTRAL_LG   = _p("mistral_lg",  MISTRAL_KEYS, "mistral-large-latest",   "openai_compat", "https://api.mistral.ai/v1")
_MISTRAL_SM   = _p("mistral_sm",  MISTRAL_KEYS, "mistral-small-latest",   "openai_compat", "https://api.mistral.ai/v1")

# xAI / Grok
_GROK         = _p("grok",        GROKAI_KEYS,  "grok-3-mini",            "openai_compat", "https://api.x.ai/v1")

# OpenRouter free models
_OR_DEFAULT   = _p("openrouter",  OPENROUTER_KEYS, "meta-llama/llama-3.3-70b-instruct:free",       "openai_compat", "https://openrouter.ai/api/v1")
_OR_R1        = _p("or_r1",       OPENROUTER_KEYS, "deepseek/deepseek-r1:free",                     "openai_compat", "https://openrouter.ai/api/v1")
_OR_QWEN3     = _p("or_qwen3",    OPENROUTER_KEYS, "qwen/qwen3-235b-a22b:free",                     "openai_compat", "https://openrouter.ai/api/v1")
_OR_QWENCDR   = _p("or_qwencd",   OPENROUTER_KEYS, "qwen/qwen3-coder-480b-a35b-instruct:free",      "openai_compat", "https://openrouter.ai/api/v1")
_OR_GPTOSS    = _p("or_gptoss",   OPENROUTER_KEYS, "openai/gpt-oss-120b:free",                      "openai_compat", "https://openrouter.ai/api/v1")
_OR_LLAMA4    = _p("or_llama4",   OPENROUTER_KEYS, "meta-llama/llama-4-maverick:free",               "openai_compat", "https://openrouter.ai/api/v1")
_OR_VL        = _p("or_vl",       OPENROUTER_KEYS, "qwen/qwen2.5-vl-72b-instruct:free",              "openai_compat", "https://openrouter.ai/api/v1")
_OR_KIMI_VL   = _p("or_kimivl",   OPENROUTER_KEYS, "moonshotai/kimi-vl-a3b-thinking:free",           "openai_compat", "https://openrouter.ai/api/v1")
_OR_DSV3      = _p("or_dsv3",     OPENROUTER_KEYS, "deepseek/deepseek-chat-v3-0324:free",             "openai_compat", "https://openrouter.ai/api/v1")
_OR_KIMI_K2   = _p("or_kimik2",   OPENROUTER_KEYS, "moonshotai/kimi-k2:free",                        "openai_compat", "https://openrouter.ai/api/v1")
_OR_NEMOTRON  = _p("or_nemo",     OPENROUTER_KEYS, "nvidia/llama-3.3-nemotron-super-49b-v1:free",     "openai_compat", "https://openrouter.ai/api/v1")
_OR_MINIMAX   = _p("or_minimax",  OPENROUTER_KEYS, "minimax/minimax-m1:free",                         "openai_compat", "https://openrouter.ai/api/v1")
_OR_MIMO_OMNI = _p("or_mimoomni", OPENROUTER_KEYS, "alibaba/mimo-72b-omni:free",                      "openai_compat", "https://openrouter.ai/api/v1")
_OR_MIMO_PRO  = _p("or_mimopro",  OPENROUTER_KEYS, "alibaba/mimo-72b-pro:free",                       "openai_compat", "https://openrouter.ai/api/v1")

# ═══════════════════════════════════════════════════════════════
# TASK CHAINS
# ═══════════════════════════════════════════════════════════════

TASK_CHAINS = {
    "speed":        [_GROQ, _CEREBRAS, _OR_NEMOTRON, _OR_MINIMAX, _GEMINI_F, _OR_DEFAULT],
    "reason":       [_OR_KIMI_K2, _OR_R1, _OR_NEMOTRON, _OR_QWEN3, _OR_MINIMAX, _GEMINI_25P],
    "code":         [_OR_KIMI_K2, _OR_QWENCDR, _OR_MIMO_PRO, _NVIDIA_DSFL, _DEEPSEEK, _SAMBANOVA],
    "vision":       [_GEMINI_25F, _OR_MIMO_OMNI, _OR_LLAMA4, _GEMINI_F, _OR_KIMI_VL, _OR_VL],
    "research":     [_OR_KIMI_K2, _OR_R1, _OR_NEMOTRON, _OR_GPTOSS, _OR_MINIMAX, _GEMINI_25P],
    "write":        [_MISTRAL_LG, _CEREBRAS, _GROQ, _OR_NEMOTRON, _OR_MINIMAX, _OR_DSV3],
    "agent":        [_OR_KIMI_K2, _OR_QWEN3, _OR_NEMOTRON, _GROQ, _GEMINI_25F, _OR_MIMO_OMNI],
    "vision_reason":[_GEMINI_25F, _OR_MIMO_OMNI, _OR_KIMI_VL, _OR_VL, _GEMINI_25P, _OR_MINIMAX],
    "pentest":      [_NVIDIA_DSV4, _NVIDIA_GLM, _DEEPSEEK_R1, _OR_R1, _GROQ, _OR_DEFAULT],
    "hinglish":     [_NVIDIA_SARV, _GEMINI_25F, _GEMINI_F, _GROQ, _CEREBRAS, _OR_DEFAULT],
}

PROVIDERS = [
    _GROQ, _CEREBRAS, _OR_NEMOTRON, _OR_MINIMAX, _GEMINI_F,
    _SAMBANOVA, _OR_DEFAULT, _DEEPSEEK, _OR_KIMI_K2, _TOGETHER,
    _NVIDIA_DSFL, _MISTRAL_SM,
]

# ── Task keyword auto-detection ───────────────────────────────────────
_TASK_KEYWORDS = {
    "speed":    ["quick", "fast", "jaldi", "short", "briefly", "seedha bata", "ek line",
                 "tldr", "simple", "bas bata", "chhota", "instantly"],
    "reason":   ["reason", "analyze", "explain why", "think step", "solve", "math", "logic",
                 "compare", "pros and cons", "kyun", "kaise", "samjhao", "analyze karo"],
    "code":     ["code", "function", "script", "debug", "refactor", "implement", "class",
                 "python", "javascript", "bug", "error", "likho code", "banao", "fix karo"],
    "vision":   ["screenshot", "image", "screen", "visual", "gui", "dekho", "dikhao",
                 "kya dikh raha", "screen pe kya", "describe image"],
    "research": ["research", "find information", "search", "deep dive", "multiple sources",
                 "investigate", "dhundo", "pata lagao", "latest news", "batao sab"],
    "write":    ["write", "draft", "compose", "essay", "article", "blog", "email",
                 "document", "report", "summary", "likho", "email banao", "draft karo"],
    "agent":    ["automate", "step by step", "plan and execute", "workflow", "pipeline",
                 "khud karo", "automate karo", "background mein", "schedule"],
    "pentest":  ["scan", "recon", "nmap", "vulnerability", "exploit", "osint", "pentest",
                 "cve", "inject", "xss", "sqli", "burp", "nikto", "shodan"],
    "hinglish": ["hindi", "hinglish", "bhai", "yrr", "theek hai", "seedha", "mujhe batao",
                 "\u092c\u093e\u0924", "\u0938\u092e\u091d\u094b", "\u092c\u0924\u093e\u0913"],
}

def _detect_task(messages: list) -> str:
    last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    text = last.lower()
    scores = {t: sum(1 for kw in kws if kw in text) for t, kws in _TASK_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "speed"

# ═══════════════════════════════════════════════════════════════
# THREAD-SAFE STATE
# ═══════════════════════════════════════════════════════════════
_cooldowns: dict = {}
_COOLDOWNS_LOCK = threading.Lock()
_PROVIDERS_LOCK  = threading.Lock()

def _next_key(provider: dict) -> tuple:
    with _PROVIDERS_LOCK:
        keys = provider["keys"]
        now = time.time()
        start = provider["_idx"]
        for i in range(len(keys)):
            idx = (start + i) % len(keys)
            with _COOLDOWNS_LOCK:
                ok = _cooldowns.get(f"{provider['name']}:{idx}", 0) <= now
            if ok:
                provider["_idx"] = (idx + 1) % len(keys)
                return keys[idx], idx
        idx = start % len(keys)
        provider["_idx"] = (idx + 1) % len(keys)
        return keys[idx], idx

# ═══════════════════════════════════════════════════════════════
# SEMANTIC CACHE
# ═══════════════════════════════════════════════════════════════
_CACHE_FILE      = _CONFIG_DIR / "mast_cache.json"
_CACHE_LOCK      = threading.Lock()
_cache: dict     = {}
_cache_stats     = {"hits": 0, "misses": 0, "saves": 0}
_MAX_ENTRIES     = 500
_DEFAULT_TTL     = 3600
_FUZZY_THRESHOLD = 0.82
_MIN_CACHE_LEN   = 20
_NO_CACHE_PATS   = [r'current time', r'screenshot', r'click', r'right now',
                    r'abhi', r'aaj', r'kal', r'live', r'current']

def _cnorm(t: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', t.lower().strip()))

def _cfp(t: str) -> str:
    return hashlib.md5(_cnorm(t).encode()).hexdigest()

def _kwsim(a: str, b: str) -> float:
    stops = {'hai','karo','mein','ka','ki','ke','se','ko','aur','ya','toh',
             'the','a','an','is','are','was','be','have','has'}
    aw = set(_cnorm(a).split()) - stops
    bw = set(_cnorm(b).split()) - stops
    if not aw or not bw: return 0.0
    return len(aw & bw) / len(aw | bw)

def _skip_cache(q: str) -> bool:
    return any(re.search(p, q.lower()) for p in _NO_CACHE_PATS)

def _load_cache():
    global _cache
    try:
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            now = time.time()
            with _CACHE_LOCK:
                _cache = {k: v for k, v in data.items() if v.get("expires", 0) > now}
    except Exception:
        _cache = {}

def _save_cache_bg():
    def _do():
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with _CACHE_LOCK:
                _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log.debug(f"cache save: {e}")
    threading.Thread(target=_do, daemon=True).start()

def _evict():
    global _cache
    now = time.time()
    expired = [k for k, v in _cache.items() if v.get("expires", 0) < now]
    for k in expired: del _cache[k]
    if len(_cache) > _MAX_ENTRIES:
        for k, _ in sorted(_cache.items(), key=lambda x: x[1].get("last_hit", 0))[:len(_cache)-_MAX_ENTRIES]:
            del _cache[k]

def cache_get(query: str) -> Optional[str]:
    if _skip_cache(query): return None
    now = time.time()
    key = _cfp(query)
    with _CACHE_LOCK:
        if key in _cache and _cache[key].get("expires", 0) > now:
            _cache[key]["last_hit"] = now
            _cache_stats["hits"] += 1
            return _cache[key]["response"]
        best_sim, best_key = 0.0, None
        for k, v in _cache.items():
            if v.get("expires", 0) < now: continue
            s = _kwsim(query, v.get("query", ""))
            if s > best_sim: best_sim, best_key = s, k
        if best_sim >= _FUZZY_THRESHOLD and best_key:
            _cache[best_key]["last_hit"] = now
            _cache_stats["hits"] += 1
            return _cache[best_key]["response"]
    _cache_stats["misses"] += 1
    return None

def cache_set(query: str, response: str, ttl: int = _DEFAULT_TTL):
    if _skip_cache(query) or len(response) < _MIN_CACHE_LEN: return
    now = time.time()
    with _CACHE_LOCK:
        _evict()
        _cache[_cfp(query)] = {
            "query": query[:200], "response": response,
            "cached_at": now, "last_hit": now, "expires": now + ttl,
        }
        _cache_stats["saves"] += 1
    _save_cache_bg()

def cache_stats() -> str:
    total = _cache_stats["hits"] + _cache_stats["misses"]
    rate = round(_cache_stats["hits"] / total * 100, 1) if total else 0
    return (f"Cache: {len(_cache)} entries | Hit {rate}% | "
            f"Hits={_cache_stats['hits']} Misses={_cache_stats['misses']}")

_load_cache()

# ═══════════════════════════════════════════════════════════════
# HTTP CALLERS
# ═══════════════════════════════════════════════════════════════

def _try_openai_compat(provider: dict, messages: list, max_tokens: int) -> Optional[str]:
    try:
        import requests as req
    except ImportError:
        log.warning("pip install requests")
        return None
    key, key_idx = _next_key(provider)
    if "PLACEHOLDER" in key:
        log.debug(f"  ⏭ {provider['name']}: no key in .env")
        return None
    key_id = f"{provider['name']}:{key_idx}"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if "openrouter" in provider["name"] or "or_" in provider["name"]:
        headers["HTTP-Referer"] = "https://github.com/m4stanuj/MAST"
        headers["X-Title"] = "MAST"
    try:
        r = req.post(
            f"{provider['base_url']}/chat/completions",
            headers=headers,
            json={"model": provider["model"], "messages": messages,
                  "max_tokens": max_tokens, "temperature": 0.7},
            timeout=30)
        if r.status_code == 429:
            with _COOLDOWNS_LOCK:
                _cooldowns[key_id] = time.time() + 60
                if all(_cooldowns.get(f"{provider['name']}:{i}", 0) > time.time()
                       for i in range(len(provider["keys"]))):
                    _cooldowns[provider["name"]] = time.time() + 60
            return None
        if r.status_code in (401, 403):
            with _COOLDOWNS_LOCK:
                _cooldowns[key_id] = time.time() + 3600
            log.warning(f"  🔑 {provider['name']} key {key_idx}: auth fail — cooled 1h")
            return None
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        if any(x in type(e).__name__ for x in ["ConnectionError", "Timeout"]):
            with _COOLDOWNS_LOCK:
                _cooldowns[provider["name"]] = time.time() + 30
        log.warning(f"  ⚠ {provider['name']}: {e}")
        return None

def _try_gemini(provider: dict, messages: list, max_tokens: int) -> Optional[str]:
    try:
        import requests as req
    except ImportError:
        return None
    key, key_idx = _next_key(provider)
    if "PLACEHOLDER" in key: return None
    key_id = f"gemini:{key_idx}"
    contents, sys_parts = [], []
    for m in messages:
        if m["role"] == "system":
            sys_parts.append(m["content"])
        elif m["role"] == "user":
            content = ("\n\n".join(sys_parts) + "\n\n" + m["content"]).strip() if sys_parts else m["content"]
            sys_parts = []
            contents.append({"role": "user", "parts": [{"text": content}]})
        else:
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})
    merged = []
    for item in contents:
        if merged and merged[-1]["role"] == item["role"]:
            merged[-1]["parts"][0]["text"] += "\n" + item["parts"][0]["text"]
        else:
            merged.append(item)
    if not merged: return None
    try:
        r = req.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent?key={key}",
            json={"contents": merged, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}},
            timeout=30)
        if r.status_code == 429:
            with _COOLDOWNS_LOCK:
                _cooldowns[key_id] = time.time() + 60
                if all(_cooldowns.get(f"gemini:{i}", 0) > time.time()
                       for i in range(len(provider["keys"]))):
                    _cooldowns["gemini"] = time.time() + 60
            return None
        if r.status_code in (400, 403):
            if r.status_code == 403:
                with _COOLDOWNS_LOCK: _cooldowns[key_id] = time.time() + 3600
            log.warning(f"gemini: HTTP {r.status_code}")
            return None
        r.raise_for_status()
        cands = r.json().get("candidates", [])
        return cands[0]["content"]["parts"][0]["text"] if cands else None
    except Exception as e:
        log.warning(f"gemini: {e}")
        with _COOLDOWNS_LOCK:
            _cooldowns[key_id] = time.time() + 15
        return None

# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def chat_complete(messages: list, max_tokens: int = 1024, use_cache: bool = True,
                  task: str = "auto") -> str:
    """
    Main entry. Cache → task chain → full fallback.
    task: auto | speed | reason | code | vision | research |
          write | agent | vision_reason | pentest | hinglish
    """
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), None)
    if use_cache and last_user:
        cached = cache_get(last_user)
        if cached:
            log.info("  ⚡ cache hit")
            return cached

    if task == "auto":
        task = _detect_task(messages)
    chain = TASK_CHAINS.get(task, PROVIDERS)
    log.info(f"  🎯 task={task} chain=[{', '.join(p['name'] for p in chain)}]")

    now = time.time()
    tried = set()
    for provider in chain:
        with _COOLDOWNS_LOCK:
            if _cooldowns.get(provider["name"], 0) > now: continue
        tried.add(provider["name"])
        fn = _try_gemini if provider["type"] == "gemini" else _try_openai_compat
        result = fn(provider, messages, max_tokens)
        if result:
            if use_cache and last_user: cache_set(last_user, result)
            return result

    log.warning("  ⚠️ task chain exhausted — full fallback")
    for provider in PROVIDERS:
        if provider["name"] in tried: continue
        with _COOLDOWNS_LOCK:
            if _cooldowns.get(provider["name"], 0) > now: continue
        fn = _try_gemini if provider["type"] == "gemini" else _try_openai_compat
        result = fn(provider, messages, max_tokens)
        if result:
            if use_cache and last_user: cache_set(last_user, result)
            return result

    return f"ERROR: All providers failed (task='{task}'). Add keys to .env / check internet."


def get_llm(preferred: str = "groq"):
    """LangChain-compatible LLM."""
    order = [preferred] + [p["name"] for p in PROVIDERS if p["name"] != preferred]
    now = time.time()
    for pname in order:
        provider = next((p for p in PROVIDERS if p["name"] == pname), None)
        if not provider: continue
        with _COOLDOWNS_LOCK:
            if _cooldowns.get(pname, 0) > now: continue
        key, _ = _next_key(provider)
        if "PLACEHOLDER" in key: continue
        try:
            if provider["type"] == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(model=provider["model"], google_api_key=key, temperature=0.7)
            from langchain_openai import ChatOpenAI
            extra = {}
            if "openrouter" in pname or "or_" in pname:
                extra["default_headers"] = {"HTTP-Referer": "https://github.com/m4stanuj/MAST", "X-Title": "MAST"}
            return ChatOpenAI(model=provider["model"], openai_api_key=key,
                              openai_api_base=provider["base_url"], temperature=0.7, **extra)
        except Exception as e:
            log.warning(f"get_llm {pname}: {e}")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model="llama-3.3-70b-versatile", openai_api_key="no-key",
                      openai_api_base="https://api.groq.com/openai/v1")


def status_report() -> str:
    now = time.time()
    lines = ["MAST LLM Router v6.0 — Task-Aware Chains + NVIDIA NIM + Mistral + Grok", "=" * 70]
    seen = set()
    for p in list(PROVIDERS) + [p for ch in TASK_CHAINS.values() for p in ch]:
        n = p["name"]
        if n in seen: continue
        seen.add(n)
        with _COOLDOWNS_LOCK:
            cd = _cooldowns.get(n, 0)
            cooled = sum(1 for i in range(len(p["keys"])) if _cooldowns.get(f"{n}:{i}", 0) > now)
        active = len(p["keys"]) - cooled
        has_key = any("PLACEHOLDER" not in k for k in p["keys"])
        st = "🔑 NO KEY" if not has_key else (f"⏳ {int(cd-now)}s" if cd > now else "✅")
        lines.append(f"  {st:12} {n:<18} {active}/{len(p['keys'])} keys | {p['model'][:48]}")
    lines.append(f"\n  Chains: {', '.join(TASK_CHAINS.keys())}")
    lines.append(f"  {cache_stats()}")
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(status_report())
    print("\nQuick test...")
    r = chat_complete([{"role": "user", "content": "Reply exactly: MAST_OK"}], max_tokens=10)
    print(f"Response: {r}")

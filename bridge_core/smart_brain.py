"""
M4ST Smart Brain Router v2
===========================
Koi bhi API key daalo — system khud samjhega kaun sa provider hai
aur automatically routing chain mein add kar dega.

Features:
  ✅ Auto-detect provider from key prefix/format
  ✅ SMART_KEY_1 ... SMART_KEY_20 — ek jagah sabke keys
  ✅ Purane GROQ_API_KEY, CEREBRAS_API_KEY etc. bhi kaam karte hain
  ✅ Rate limit → auto next provider (already tha, aur better)
  ✅ BRAIN=auto/fast/quality/free — priority mode
  ✅ Live reload — .env change karo, restart nahi chahiye
  ✅ OpenRouter support — 100+ models ek key se
  ✅ DeepSeek support — GPT-4 quality, dirt cheap
  ✅ Gemini support — chat + vision
  ✅ Perplexity support — web-grounded answers

Usage in m4st_v2_server.py:
  from smart_brain import smart_brain_call as brain_call
  # Replace existing brain_call with this
"""

import os, re, json, time as _time, threading
import requests as http

import sys as _sys_root
if getattr(_sys_root, 'frozen', False):
    ROOT = os.path.dirname(_sys_root.executable)
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ══════════════════════════════════════════════════════════════════════
#  CONFIG READER
# ══════════════════════════════════════════════════════════════════════

def _cfg(key, default=""):
    try:
        with open(os.path.join(ROOT, "config", ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip()
    except FileNotFoundError as _e:
        print(f"[DEBUG] smart_brain.py: {_e}")
    return default

def _cfg_all():
    """Return all .env key-value pairs."""
    result = {}
    try:
        with open(os.path.join(ROOT, "config", ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and v:
                    result[k] = v
    except FileNotFoundError as _e:
        print(f"[DEBUG] smart_brain.py: {_e}")
    return result


# ══════════════════════════════════════════════════════════════════════
#  PROVIDER REGISTRY
#  Har provider ka: url, models, key_prefix, speed_rank, quality_rank
# ══════════════════════════════════════════════════════════════════════

PROVIDER_REGISTRY = {
    "groq": {
        "name":          "Groq",
        "url":           "https://api.groq.com/openai/v1/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  ["gsk_"],
        "models":        ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
        "speed_rank":    1,   # fastest
        "quality_rank":  4,
        "free":          True,
        "tool_support":  True,
        "format":        "openai",
        "env_keys":      ["GROQ_API_KEY"],       # legacy env key names
    },
    "cerebras": {
        "name":          "Cerebras",
        "url":           "https://api.cerebras.ai/v1/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  ["csk-"],
        "models":        ["llama3.3-70b", "llama3.1-70b", "llama3.1-8b"],
        "speed_rank":    2,
        "quality_rank":  4,
        "free":          True,
        "tool_support":  True,
        "format":        "openai",
        "env_keys":      ["CEREBRAS_API_KEY"],
    },
    "deepseek": {
        "name":          "DeepSeek",
        "url":           "https://api.deepseek.com/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  ["sk-"],               # same as openai — disambiguate by test
        "models":        ["deepseek-chat", "deepseek-reasoner"],
        "speed_rank":    3,
        "quality_rank":  2,
        "free":          False,                  # very cheap though ($0.14/1M tokens)
        "tool_support":  True,
        "format":        "openai",
        "env_keys":      ["DEEPSEEK_API_KEY"],
        "test_url":      "https://api.deepseek.com",   # for disambiguation
    },
    "openrouter": {
        "name":          "OpenRouter",
        "url":           "https://openrouter.ai/api/v1/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  ["sk-or-"],
        "models":        [
            "moonshotai/kimi-k2:free",
            "minimax/minimax-m2.5:free",
            "qwen/qwen3-coder-480b:free",
            "deepseek/deepseek-r1:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            "qwen/qwen3-235b-a22b:free",
            "microsoft/phi-4:free",
        ],
        "speed_rank":    4,
        "quality_rank":  2,
        "free":          True,   # free tier models available
        "tool_support":  True,
        "format":        "openai",
        "env_keys":      ["OPENROUTER_API_KEY"],
        "extra_headers": {
            "HTTP-Referer": "https://m4st.local",
            "X-Title": "M4ST AI Operator"
        },
    },
    "anthropic": {
        "name":          "Anthropic (Claude)",
        "url":           "https://api.anthropic.com/v1/messages",
        "auth_header":   "x-api-key",
        "key_prefixes":  ["sk-ant-"],
        "models":        ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-6"],
        "speed_rank":    5,
        "quality_rank":  1,   # best quality
        "free":          False,
        "tool_support":  True,
        "format":        "anthropic",
        "env_keys":      ["CLAUDE_API_KEY"],
    },
    "gemini": {
        "name":          "Google Gemini",
        "url":           "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "auth_header":   "key",   # query param, not header
        "key_prefixes":  ["AIza"],
        "models":        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "speed_rank":    3,
        "quality_rank":  2,
        "free":          True,   # generous free tier
        "tool_support":  True,
        "format":        "gemini",
        "env_keys":      ["GEMINI_API_KEY"],
    },
    "openai": {
        "name":          "OpenAI",
        "url":           "https://api.openai.com/v1/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  ["sk-proj-", "sk-svcacct-"],  # modern OpenAI keys
        "models":        ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "speed_rank":    4,
        "quality_rank":  2,
        "free":          False,
        "tool_support":  True,
        "format":        "openai",
        "env_keys":      ["OPENAI_API_KEY"],
    },
    "perplexity": {
        "name":          "Perplexity",
        "url":           "https://api.perplexity.ai/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  ["pplx-"],
        "models":        ["sonar", "sonar-pro", "sonar-reasoning"],
        "speed_rank":    4,
        "quality_rank":  3,
        "free":          False,
        "tool_support":  False,   # no tool use in perplexity
        "format":        "openai",
        "env_keys":      ["PERPLEXITY_API_KEY"],
        "note":          "Web-grounded answers — good for research/news",
    },
    "cloudflare": {
        "name":          "Cloudflare AI",
        "url":           "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  [],   # no unique prefix — needs CLOUDFLARE_ACCOUNT_ID
        "models":        ["@cf/meta/llama-3.3-70b-instruct", "@cf/meta/llama-3.1-8b-instruct"],
        "speed_rank":    5,
        "quality_rank":  4,
        "free":          True,
        "tool_support":  False,   # CF uses text-injection for tools
        "format":        "cloudflare",
        "env_keys":      ["CLOUDFLARE_API_KEY"],
        "requires_extra": ["CLOUDFLARE_ACCOUNT_ID"],
    },
    "sambanova": {
        "name":          "SambaNova",
        "url":           "https://api.sambanova.ai/v1/chat/completions",
        "auth_header":   "Bearer",
        "key_prefixes":  [],
        "models":        ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.1-405B-Instruct"],
        "speed_rank":    2,   # very fast inference chips
        "quality_rank":  3,
        "free":          True,
        "tool_support":  True,
        "format":        "openai",
        "env_keys":      ["SAMBANOVA_API_KEY"],
    },

    # ─── FREE TIER — MANY MODELS ─────────────────────────────────────
    "together": {
        "name":         "Together AI",
        "url":          "https://api.together.xyz/v1/chat/completions",
        "key_prefixes": [],
        "models":       ["meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                         "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
                         "meta-llama/Llama-3.3-70B-Instruct-Turbo"],
        "speed_rank":   3, "quality_rank": 3, "free": True,
        "tool_support": True, "format": "openai",
        "env_keys":     ["TOGETHER_API_KEY"],
    },
    "hyperbolic": {
        "name":         "Hyperbolic",
        "url":          "https://api.hyperbolic.xyz/v1/chat/completions",
        "key_prefixes": ["eyJ"],
        "models":       ["meta-llama/Llama-3.3-70B-Instruct",
                         "deepseek-ai/DeepSeek-R1",
                         "Qwen/Qwen2.5-72B-Instruct"],
        "speed_rank":   3, "quality_rank": 3, "free": True,
        "tool_support": True, "format": "openai",
        "env_keys":     ["HYPERBOLIC_API_KEY"],
    },
    "fireworks": {
        "name":         "Fireworks AI",
        "url":          "https://api.fireworks.ai/inference/v1/chat/completions",
        "key_prefixes": [],
        "models":       ["accounts/fireworks/models/llama-v3p3-70b-instruct",
                         "accounts/fireworks/models/deepseek-r1",
                         "accounts/fireworks/models/qwen2p5-72b-instruct"],
        "speed_rank":   2, "quality_rank": 3, "free": True,
        "tool_support": True, "format": "openai",
        "env_keys":     ["FIREWORKS_API_KEY"],
    },
    "nvidia_nim": {
        "name":         "NVIDIA NIM",
        "url":          "https://integrate.api.nvidia.com/v1/chat/completions",
        "key_prefixes": ["nvapi-"],
        "models":       ["meta/llama-3.3-70b-instruct",
                         "deepseek-ai/deepseek-r1",
                         "nvidia/llama-3.1-nemotron-70b-instruct"],
        "speed_rank":   2, "quality_rank": 3, "free": True,
        "tool_support": True, "format": "openai",
        "env_keys":     ["NVIDIA_API_KEY"],
    },

    # ─── SPECIALIZED ─────────────────────────────────────────────────
    "mistral": {
        "name":         "Mistral AI",
        "url":          "https://api.mistral.ai/v1/chat/completions",
        "key_prefixes": [],
        "models":       ["mistral-small-latest", "codestral-latest",
                         "mistral-large-latest", "open-mistral-nemo"],
        "speed_rank":   3, "quality_rank": 3, "free": False,
        "tool_support": True, "format": "openai",
        "env_keys":     ["MISTRAL_API_KEY"],
    },
    "xai": {
        "name":         "xAI (Grok)",
        "url":          "https://api.x.ai/v1/chat/completions",
        "key_prefixes": ["xai-"],
        "models":       ["grok-2-latest", "grok-beta", "grok-vision-beta"],
        "speed_rank":   3, "quality_rank": 2, "free": False,
        "tool_support": True, "format": "openai",
        "env_keys":     ["XAI_API_KEY"],
    },
    "cohere": {
        "name":         "Cohere",
        "url":          "https://api.cohere.com/v2/chat",
        "key_prefixes": ["trial-"],
        "models":       ["command-r-plus-08-2024", "command-r-08-2024"],
        "speed_rank":   4, "quality_rank": 3, "free": False,
        "tool_support": True, "format": "cohere",
        "env_keys":     ["COHERE_API_KEY"],
    },
    "huggingface": {
        "name":         "HuggingFace Inference",
        "url":          "https://api-inference.huggingface.co/v1/chat/completions",
        "key_prefixes": ["hf_"],
        "models":       ["meta-llama/Llama-3.3-70B-Instruct",
                         "Qwen/Qwen2.5-72B-Instruct",
                         "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"],
        "speed_rank":   5, "quality_rank": 3, "free": True,
        "tool_support": False, "format": "openai",
        "env_keys":     ["HUGGINGFACE_API_KEY"],
    },
    "qwen_dashscope": {
        "name":         "Alibaba Qwen (DashScope)",
        "url":          "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key_prefixes": [],
        "models":       ["qwen-turbo", "qwen-max", "qwen2.5-72b-instruct", "qwq-32b"],
        "speed_rank":   3, "quality_rank": 2, "free": True,
        "tool_support": True, "format": "openai",
        "env_keys":     ["DASHSCOPE_API_KEY"],
    },
    "zhipu": {
        "name":         "Zhipu AI (GLM)",
        "url":          "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "key_prefixes": [],
        "models":       ["glm-4-flash", "glm-4", "glm-4-air"],
        "speed_rank":   3, "quality_rank": 3, "free": True,
        "tool_support": True, "format": "openai",
        "env_keys":     ["ZHIPU_API_KEY"],
    },
}

# BRAIN mode → provider priority order
BRAIN_PRIORITY = {
    "auto":    ["groq", "cerebras", "sambanova", "fireworks", "nvidia_nim", "together",
                "openrouter", "hyperbolic", "cloudflare", "gemini",
                "huggingface", "qwen_dashscope", "zhipu",
                "deepseek", "mistral", "xai", "anthropic", "openai",
                "perplexity", "cohere", "ollama"],
    "fast":    ["groq", "cerebras", "sambanova", "fireworks", "nvidia_nim",
                "together", "cloudflare", "deepseek", "openrouter", "gemini",
                "anthropic", "openai"],
    "quality": ["anthropic", "deepseek", "openai", "xai", "openrouter",
                "gemini", "mistral", "perplexity", "sambanova", "cerebras", "groq"],
    "free":    ["groq", "cerebras", "openrouter", "together", "hyperbolic",
                "fireworks", "nvidia_nim", "sambanova", "cloudflare", "gemini",
                "huggingface", "zhipu", "qwen_dashscope", "ollama"],
    "local":   [],
}


# ══════════════════════════════════════════════════════════════════════
#  KEY AUTO-DETECTOR
#  Koi bhi key paste karo — provider khud detect hoga
# ══════════════════════════════════════════════════════════════════════

def detect_provider_from_key(key: str) -> str:
    """
    Key prefix se provider detect karo.
    Returns provider name (groq/anthropic/gemini/etc.) or 'unknown'
    """
    if not key or len(key) < 8:
        return "unknown"

    key = key.strip()

    # Exact prefix matches
    # Longest/most specific prefixes first — avoid mis-matching sk- as sk-ant-
    prefix_map = [
        ("sk-ant-api",   "anthropic"),
        ("sk-ant-",      "anthropic"),
        ("sk-or-",       "openrouter"),
        ("sk-proj-",     "openai"),
        ("sk-svcacct-",  "openai"),
        ("gsk_",         "groq"),
        ("csk-",         "cerebras"),
        ("AIza",         "gemini"),
        ("pplx-",        "perplexity"),
        ("xai-",         "xai"),
        ("nvapi-",       "nvidia_nim"),
        ("hf_",          "huggingface"),
        ("trial-",       "cohere"),
        ("eyJ",          "hyperbolic"),   # JWT (base64 of {)
    ]
    for prefix, provider in prefix_map:
        if key.startswith(prefix):
            return provider

    # UUID-like keys (SambaNova)
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}', key):
        return "sambanova"

    # sk- is ambiguous — could be deepseek, moonshot, qwen etc.
    # Use named env vars: DEEPSEEK_API_KEY, MISTRAL_API_KEY etc.
    if key.startswith("sk-") and len(key) > 20:
        return "sk_ambiguous"

    return "unknown"


_ambiguous_keys = set()  # track sk- ambiguous keys — warn once per reload

def detect_all_keys(env_dict: dict) -> dict:
    """
    .env dict se saare keys scan karo.
    Returns: {provider_name: [key1, key2, ...]}
    """
    global _ambiguous_keys
    _ambiguous_keys = set()   # reset on each reload
    detected = {name: [] for name in PROVIDER_REGISTRY}

    for env_key, value in env_dict.items():
        if not value or len(value) < 8 or value.startswith("YAHAN") or "*" in value:
            continue

        # Legacy named keys (GROQ_API_KEY, CEREBRAS_API_KEY etc.)
        # Supports unlimited keys: GROQ_API_KEY, GROQ_API_KEY_2 ... GROQ_API_KEY_200
        for pname, pinfo in PROVIDER_REGISTRY.items():
            for legacy_key in pinfo.get("env_keys", []):
                # Match GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_N (no upper limit)
                if env_key == legacy_key or re.match(rf"^{re.escape(legacy_key)}_\d+$", env_key):
                    if value not in detected[pname]:
                        detected[pname].append(value)

        # SMART_KEY_N — auto detect
        if re.match(r'^SMART_KEY(_\d+)?$', env_key):  # matches SMART_KEY_1 to SMART_KEY_999
            provider = detect_provider_from_key(value)
            if provider == "sk_ambiguous":
                _ambiguous_keys.add(env_key)   # collect, warn once after scan
            elif provider != "unknown" and value not in detected.get(provider, []):
                detected.setdefault(provider, []).append(value)
                print(f"[SMART BRAIN] Auto-detected: {env_key} -> {provider}")

        # ANY_KEY / API_KEY catch-all
        if env_key.endswith("_API_KEY") or env_key.endswith("_KEY"):
            provider = detect_provider_from_key(value)
            if provider != "unknown":
                if value not in detected.get(provider, []):
                    detected.setdefault(provider, []).append(value)

    # Special: Cloudflare needs ACCOUNT_ID
    cf_account = env_dict.get("CLOUDFLARE_ACCOUNT_ID", "")
    if not cf_account:
        detected["cloudflare"] = []   # Disable if no account ID

    # Warn about ambiguous sk- keys - once, summarized
    if _ambiguous_keys:
        keys_str = ", ".join(sorted(_ambiguous_keys)[:5])
        extra = f" +{len(_ambiguous_keys)-5} more" if len(_ambiguous_keys) > 5 else ""
        print(f"[SMART BRAIN] [!] {len(_ambiguous_keys)} sk- keys undetected ({keys_str}{extra})")
        print(f"[SMART BRAIN]    -> Use DEEPSEEK_API_KEY=sk-xxx or OPENAI_API_KEY=sk-xxx instead")

    return detected



# ══════════════════════════════════════════════════════════════════════
#  TASK-TYPE DETECTOR
#  User message se task type detect karo - sahi model select karo
#
#  Task Types:
#    simple    - Ollama / Groq 8b  (app open, time, screenshot)
#    chat      - Groq 70b          (general conversation)
#    tool      - Groq 70b          (tool calling, agent tasks)
#    code      - DeepSeek Chat     (coding, debug, file work)
#    reasoning - DeepSeek Reasoner (math, logic, analysis, planning)
#    research  - Perplexity / Groq (news, facts, web search)
#    vision    - Gemini / Ollama   (screen, image analysis)
#    creative  - Claude / OpenRouter (writing, stories, content)
#    long_ctx  - Gemini / Claude   (big files, long documents)
# ══════════════════════════════════════════════════════════════════════

# Keywords for each task type - Hinglish + English
# v12-merge: Enhanced Hinglish routing - Bug #14 fix ported from OpenWork v12
_TASK_SIGNALS = {
    "reasoning": [
        # English
        "why", "explain why", "analyze", "analyse", "compare", "versus", "vs",
        "pros and cons", "should i", "is it better", "difference between",
        "step by step", "how does", "logic", "reason", "think about",
        "what would happen", "if i", "tradeoff", "evaluate", "assess",
        "math", "calculate", "solve", "equation", "formula", "proof",
        "debug this logic", "what's wrong with", "find the bug",
        "plan", "strategy", "best approach", "optimal", "recommend",
        # Hinglish - v12 additions
        "kyun", "kyu", "samjhao", "explain karo", "compare karo",
        "kya better hai", "fark kya hai", "sahi kya hai",
        "sochke batao", "sochke bata", "deep analysis", "detail mein",
        "kaise kaam karta", "kya hoga agar", "suggest karo",
        "calculate karo", "solve karo", "formula batao",
        "galti dhundho", "bug kya hai", "kya galat hai",
        "plan banao", "strategy kya hogi", "best way kya hai",
        "better kaunsa", "analyze karo", "merit", "difference",
    ],
    "code": [
        # English
        "code", "script", "function", "class", "debug", "error", "bug",
        "python", "javascript", "typescript", "java", "cpp", "c++",
        "html", "css", "sql", "bash", "powershell",
        "write a", "create a file", "make a program", "implement",
        "fix this", "refactor", "optimize code", "test case",
        "api", "endpoint", "database", "query", "algorithm",
        "git", "commit", "pull request", "merge",
        # Hinglish - v12 additions
        "code likho", "code banao", "script banao", "program banao",
        "file banao", "function likho", "error fix karo",
        "debug karo", "code theek karo", "refactor karo",
        "excel banao", "word doc banao", "pdf banao",
        "likh", "fix karo", "repair", "lint", "module",
    ],
    "research": [
        # English
        "research", "find out", "look up", "what is", "who is", "when did",
        "latest news", "current", "today", "recent", "news about",
        "information about", "tell me about", "facts about",
        "wikipedia", "source", "article",
        # Hinglish - v12 additions
        "research karo", "dhundho", "kya hai", "kaun hai", "kab hua",
        "latest kya hai", "news kya hai", "aaj ka", "abhi ka",
        "batao", "jaankari do", "detail do", "information do",
        "quick fact", "jaldi batao",
        "pata lagao", "sab kuch batao", "compare karo dono",
        "information chahiye", "kya hain",
    ],
    "creative": [
        # English
        "write a story", "poem", "essay", "blog post", "caption",
        "tweet", "email", "letter", "script", "dialogue",
        "creative", "imagine", "fiction", "narrative",
        "summarize", "rewrite", "paraphrase", "translate",
        "title", "slogan", "tagline", "ad copy",
        "draft", "compose", "document", "report", "readme", "notes",
        # Hinglish - v12 additions
        "story likho", "poem likho", "essay likho", "email likho",
        "letter likho", "caption likho", "rewrite karo",
        "translate karo", "summarize karo", "shayari",
        "creative content", "content likho",
        "draft karo", "document banao", "email banao", "proposal",
        "likho",
    ],
    # v12-merge: agent task type - multi-step automation, pipelines
    "agent": [
        # English
        "automate", "step by step do", "plan and execute", "workflow",
        "pipeline", "chain", "multi-step", "loop", "batch",
        "schedule", "repeat", "background",
        # Hinglish
        "khud karo", "automate karo", "background mein", "har baar",
        "schedule karo", "batch karo", "agent",
    ],
    "excel": [
        "excel", "xlsx", "spreadsheet", "sheet", "formula", "pivot",
        "vlookup", "hlookup", "macro", "csv import", "data table",
        "word", "docx", "document", "powerpoint", "pptx", "presentation", "slide",
        "office", "google sheets", "google docs",
        "excel banao", "word banao", "sheet banao", "doc banao",
        "table banao", "report banao", "chart banao", "graph banao",
    ],
    "vision": [
        "screen", "screenshot", "image", "picture", "photo",
        "kya dikh raha", "screen pe kya", "dekh ke", "screen batao",
        "screen dikhao", "screen mein kya", "screen check",
        "find and click", "click on", "look at",
        "स्क्रीन", "देख", "screen analyze",
    ],
    "long_ctx": [
        "this file", "read this", "analyze this document", "full file",
        "entire codebase", "all files", "large", "long document",
        "yeh file padho", "poori file", "sara code",
    ],
}

# Task type - best provider + model chain
# Format: [(provider, model, fallback_ok), ...]
# fallback_ok=True means if this provider unavailable, move to next
TASK_MODEL_MAP = {
    "simple": [
        ("ollama",      "qwen2.5:7b",                    True),   # local first - reliable tool calling
        ("groq",        "llama-3.1-8b-instant",          True),   # fastest cloud
        ("cerebras",    "llama3.1-8b",                   True),
    ],
    "chat": [
        ("ollama",      "qwen2.5:7b",                    True),   # local if available
        ("groq",        "llama-3.3-70b-versatile",       True),
        ("cerebras",    "llama3.3-70b",                  True),
        ("sambanova",   "Meta-Llama-3.3-70B-Instruct",   True),
        ("openrouter",  "meta-llama/llama-3.3-70b-instruct:free", True),
    ],
    "tool": [
        ("groq",        "llama-3.3-70b-versatile",       True),   # best tool calling
        ("cerebras",    "llama3.3-70b",                  True),
        ("anthropic",   "claude-sonnet-4-6",             True),
        ("openrouter",  "deepseek/deepseek-chat-v3-0324:free", True),
        ("deepseek",    "deepseek-chat",                 True),
    ],
    "code": [
        ("openrouter",  "qwen/qwen3-coder-480b:free",           True),   # best free coding model 2026
        ("openrouter",  "moonshotai/kimi-k2:free",              True),   # excellent coder
        ("deepseek",    "deepseek-chat",                        True),
        ("ollama",      "qwen2.5-coder:7b",                     True),
        ("mistral",     "codestral-latest",                     True),
        ("openrouter",  "deepseek/deepseek-chat-v3-0324:free",  True),
        ("together",    "meta-llama/Llama-3.3-70B-Instruct-Turbo", True),
        ("anthropic",   "claude-sonnet-4-6",                    True),
        ("groq",        "llama-3.3-70b-versatile",              True),
    ],
    "reasoning": [
        ("deepseek",       "deepseek-reasoner",                            True),
        ("ollama",         "qwen3:8b",                                     True),
        ("openrouter",     "deepseek/deepseek-r1:free",                    True),
        ("together",       "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free", True),
        ("hyperbolic",     "deepseek-ai/DeepSeek-R1",                      True),
        ("nvidia_nim",     "deepseek-ai/deepseek-r1",                      True),
        ("sambanova",      "DeepSeek-R1-Distill-Llama-70B",                True),
        ("openai",         "o1-mini",                                       True),
        ("qwen_dashscope", "qwq-32b",                                      True),
        ("openrouter",     "moonshotai/kimi-k2:free",                       True),  # strong reasoner
        ("openrouter",     "google/gemini-2.0-flash-thinking-exp:free",    True),
        ("anthropic",      "claude-opus-4-6",                              True),
        ("groq",           "llama-3.3-70b-versatile",                      True),
    ],
    "research": [
        ("perplexity",  "sonar",                         True),   # web-grounded built-in
        ("groq",        "llama-3.3-70b-versatile",       True),   # + serper search
        ("openrouter",  "perplexity/sonar:free",         True),   # perplexity via OR
        ("openrouter",  "meta-llama/llama-3.3-70b-instruct:free", True),
    ],
    "vision": [
        ("ollama",      "moondream2",                    True),   # fastest local - 1.7GB, VRAM cached
        ("ollama",      "qwen2-vl:7b",                   True),   # accurate local - 6GB
        ("gemini",      "gemini-2.0-flash",              True),   # best free cloud vision
        ("openrouter",  "google/gemini-2.0-flash-exp:free", True),
        ("anthropic",   "claude-sonnet-4-6",             True),   # premium fallback
    ],
    "excel": [
        ("openrouter",  "minimax/minimax-m2.5:free",              True),  # trained on Office files
        ("openrouter",  "moonshotai/kimi-k2:free",                True),  # great at structured tasks
        ("openrouter",  "deepseek/deepseek-chat-v3-0324:free",    True),
        ("deepseek",    "deepseek-chat",                          True),
        ("anthropic",   "claude-sonnet-4-6",                      True),
        ("groq",        "llama-3.3-70b-versatile",                True),
    ],
    "creative": [
        ("anthropic",   "claude-sonnet-4-6",             True),   # best creative
        ("openrouter",  "google/gemini-2.0-flash-exp:free", True),
        ("openrouter",  "minimax/minimax-m2.5:free",      True),  # great for content
        ("deepseek",    "deepseek-chat",                 True),
        ("groq",        "llama-3.3-70b-versatile",       True),
    ],
    "long_ctx": [
        ("gemini",      "gemini-1.5-pro",                True),   # 1M context
        ("anthropic",   "claude-sonnet-4-6",             True),   # 200K context
        ("openrouter",  "google/gemini-2.0-flash-exp:free", True), # 1M via OR
        ("openrouter",  "meta-llama/llama-3.1-70b-instruct:free", True), # 128K
        ("groq",        "llama-3.3-70b-versatile",       True),
    ],
    # v12-merge: agent task type - multi-step automation, agentic workflows
    "agent": [
        ("openrouter",  "moonshotai/kimi-k2:free",              True),  # best free agent model
        ("openrouter",  "qwen/qwen3-235b-a22b:free",            True),  # strong reasoning agent
        ("groq",        "llama-3.3-70b-versatile",              True),  # fast tool calling
        ("anthropic",   "claude-sonnet-4-6",                    True),  # premium agent
        ("openrouter",  "deepseek/deepseek-chat-v3-0324:free",  True),
        ("deepseek",    "deepseek-chat",                        True),
    ],
}


def detect_task_type(messages: list) -> str:
    """
    Message content se task type detect karo.
    Returns one of: simple, chat, tool, code, reasoning, research, vision, creative, excel, long_ctx, agent
    """
    # Get last user message
    user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_msg = m.get("content", "")
            break
    if not user_msg:
        return "chat"

    msg_low   = user_msg.lower().strip()
    msg_words = set(msg_low.split())
    msg_len   = len(user_msg)

    # Long context check first (>8000 chars = definitely long context)
    if msg_len > 8000:
        return "long_ctx"

    # Vision check - screen/image keywords
    if any(kw in msg_low for kw in _TASK_SIGNALS["vision"]):
        return "vision"

    # Score each task type
    scores = {}
    for task_type, keywords in _TASK_SIGNALS.items():
        if task_type == "vision":
            continue
        score = 0
        for kw in keywords:
            if " " in kw:  # phrase match
                if kw in msg_low:
                    score += 2
            else:  # word match
                if kw in msg_words or kw in msg_low:
                    score += 1
        scores[task_type] = score

    # Reasoning boost - question words + complexity
    question_words = {"kyun", "kyu", "why", "how", "kaise", "explain", "analyze", "compare"}
    if msg_words & question_words and len(user_msg.split()) > 8:
        scores["reasoning"] = scores.get("reasoning", 0) + 2

    # Code boost - if code block present
    if "```" in user_msg or "def " in user_msg or "import " in user_msg:
        scores["code"] = scores.get("code", 0) + 3

    # Get highest score
    if scores:
        best_type = max(scores, key=lambda k: scores[k])
        if scores[best_type] > 0:
            return best_type

    # Simple command check - word count heuristic
    if len(user_msg.split()) <= 4:
        return "simple"

    return "chat"  # default


def get_model_for_task(task_type: str, prefer_free: bool = False) -> tuple:
    """
    Task type ke liye best available provider + model return karo.
    Returns (provider_name, model_name) or ("groq", "llama-3.3-70b-versatile") as fallback
    """
    candidates = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["chat"])
    brain_mode = _brain_state.get("brain_mode", "auto")

    # quality mode = prefer high quality models (Claude, DeepSeek)
    # free mode = skip paid providers
    # fast mode = prefer Groq/Cerebras

    for provider, model, fallback_ok in candidates:
        # Check brain mode restrictions
        if brain_mode == "free":
            pinfo = PROVIDER_REGISTRY.get(provider, {})
            # Allow if free, or if it's Ollama (always free)
            if not pinfo.get("free", False) and provider != "ollama":
                continue

        if brain_mode == "fast":
            # Skip slow providers for fast mode
            pinfo = PROVIDER_REGISTRY.get(provider, {})
            if pinfo.get("speed_rank", 99) > 3 and provider not in ("ollama",):
                continue

        # Ollama check - direct HTTP ping (no circular import)
        if provider == "ollama":
            try:
                now_t = _time.time()
                if not hasattr(_block_key, '_ollama_cache') or now_t - _block_key._ollama_cache[0] > 10:
                    ollama_url = _cfg("OLLAMA_URL", "http://localhost:11434")
                    r = http.get(f"{ollama_url}/api/tags", timeout=2)
                    mdls = [m.get("name","") for m in r.json().get("models",[])] if r.ok else []
                    _block_key._ollama_cache = (now_t, mdls)
                available_models = _block_key._ollama_cache[1]
                if any(model.split(":")[0] in am for am in available_models):
                    return (provider, model)
                continue
            except Exception:
                continue
        # Cloud provider check
        avail = _available_keys_for(provider)
        if avail:
            # Check if this specific model is in provider's model list
            pinfo = PROVIDER_REGISTRY.get(provider, {})
            provider_models = pinfo.get("models", [])
            if model in provider_models or not provider_models:
                return (provider, model)
            # Model not in registry but provider available - use first available model
            if fallback_ok and provider_models:
                return (provider, provider_models[0])

    # Ultimate fallback - first available provider
    for pname in _brain_state.get("routing_chain", []):
        avail = _available_keys_for(pname)
        if avail:
            pinfo = PROVIDER_REGISTRY.get(pname, {})
            models = pinfo.get("models", [])
            if models:
                return (pname, models[0])

    return ("groq", "llama-3.3-70b-versatile")  # hardcoded last resort


# ══════════════════════════════════════════════════════════════════════
#  SMART BRAIN STATE
# ══════════════════════════════════════════════════════════════════════

_brain_state = {
    "detected_keys":   {},      # {provider: [key1, key2, ...]}
    "key_cooldowns":   {},      # "provider:key_idx" - unblock_time (epoch)
    "key_call_counts": {},      # "provider:key_idx" - int
    "active_provider": "",
    "active_model":    "",
    "last_error":      "",
    "brain_mode":      "auto",
    "routing_chain":   [],      # ordered list of active providers
    "_lock":           threading.Lock(),
}

_brain_env_mtime = 0  # .env file modification time

def _key_id(pname: str, idx: int) -> str:
    return f"{pname}:{idx}"

def _is_key_available(pname: str, idx: int) -> bool:
    return _time.time() >= _brain_state["key_cooldowns"].get(_key_id(pname, idx), 0)

def _block_key(pname: str, idx: int, retry_after_sec: int = 60):
    kid = _key_id(pname, idx)
    now = _time.time()
    _brain_state["key_cooldowns"][kid] = now + retry_after_sec
    # Prune expired entries
    expired = [k for k, v in list(_brain_state["key_cooldowns"].items()) if v < now]
    for k in expired: del _brain_state["key_cooldowns"][k]
    print(f"[SMART BRAIN] [BLOCKED] {pname} key[{idx+1}] blocked for {retry_after_sec}s")
    # Emit real-time notification to UI
    try:
        from m4st_v2_server import socketio as _sio
        _sio.emit("api_key_blocked", {
            "provider":    pname,
            "key_index":   idx + 1,
            "blocked_for": retry_after_sec,
            "human":       f"{retry_after_sec//60}m {retry_after_sec%60}s" if retry_after_sec >= 60 else f"{retry_after_sec}s",
            "ready_at":    __import__("datetime").datetime.now().__class__.fromtimestamp(
                           __import__("time").time() + retry_after_sec).strftime("%H:%M:%S"),
            "type":        "invalid_key" if retry_after_sec >= 3600 else "rate_limited",
        })
    except Exception as _e:
        print(f"[DEBUG] smart_brain.py: {_e}")


def _record_success(pname: str, idx: int):
    kid = _key_id(pname, idx)
    _brain_state["key_call_counts"][kid] = _brain_state["key_call_counts"].get(kid, 0) + 1


# ── Key rotation state ────────────────────────────────────────────────
_KEY_ROTATION = {}  # provider - current key index

def _get_rotated_key(provider: str, keys: list) -> str:
    """Round-robin key rotation - distributes load across multiple API keys."""
    if not keys: return ""
    if len(keys) == 1: return keys[0]
    idx = _KEY_ROTATION.get(provider, 0)
    key = keys[idx % len(keys)]
    _KEY_ROTATION[provider] = (idx + 1) % len(keys)
    return key

def _available_keys_for(pname: str) -> list:
    """Returns list of (idx, key) tuples for available (non-blocked) keys."""
    keys = _brain_state["detected_keys"].get(pname, [])
    return [(i, k) for i, k in enumerate(keys) if _is_key_available(pname, i)]


def reload_brain(force: bool = False):
    """
    .env file se keys reload karo.
    Auto-called on every brain_call if .env has changed.
    """
    global _brain_env_mtime

    env_path = os.path.join(ROOT, "config", ".env")
    try:
        mtime = os.path.getmtime(env_path)
    except OSError:
        mtime = 0

    if not force and mtime == _brain_env_mtime:
        return  # No change

    _brain_env_mtime = mtime
    env_dict = _cfg_all()

    with _brain_state["_lock"]:
        _brain_state["detected_keys"] = detect_all_keys(env_dict)
        _brain_state["brain_mode"]    = env_dict.get("BRAIN", "auto").lower()

        # Build routing chain based on mode
        mode     = _brain_state["brain_mode"]
        priority = BRAIN_PRIORITY.get(mode, BRAIN_PRIORITY["auto"])
        chain    = [p for p in priority if _brain_state["detected_keys"].get(p)]
        _brain_state["routing_chain"] = chain

        # Summary
        active_counts = {p: len(v) for p, v in _brain_state["detected_keys"].items() if v}
        # Only print full status on actual change - suppress duplicate startup logs
        _prev_chain = getattr(reload_brain, '_last_chain', None)
        _curr_chain = '>'.join(chain[:5])
        if _curr_chain != _prev_chain or force:
            print(f"[SMART BRAIN] [RELOAD] mode={mode} | providers={len(active_counts)} | chain={_curr_chain}")
            for pname, keys in active_counts.items():
                print(f"  {pname:<15} {keys} key(s)")
            reload_brain._last_chain = _curr_chain
        if not active_counts:
            print("[SMART BRAIN] [WARNING]  No API keys in .env! Add: GROQ_API_KEY=gsk_xxx or SMART_KEY_1=gsk_xxx")

    return _brain_state["routing_chain"]


# ══════════════════════════════════════════════════════════════════════
#  PROVIDER CALL FUNCTIONS
#  Har provider ka alag format - sab normalize karke return karte hain
# ══════════════════════════════════════════════════════════════════════

def _parse_openai_response(data: dict) -> dict:
    """OpenAI format - internal format."""
    choices = data.get("choices", [])
    if not choices:
        return {"message": {"content": "", "tool_calls": []}}
    choice = choices[0].get("message", {})
    tool_calls = []
    if choice.get("tool_calls"):
        for tc in choice["tool_calls"]:
            fn   = tc.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                try: args = json.loads(args)
                except (json.JSONDecodeError, TypeError, ValueError): args = {}
            tool_calls.append({
                "id":       tc.get("id", ""),
                "function": {"name": fn.get("name", ""), "arguments": args}
            })
    return {"message": {"content": choice.get("content") or "", "tool_calls": tool_calls}}


def _call_openai_format(provider_name: str, api_key: str, model: str,
                        messages: list, max_tokens: int, tools_def: list = None,
                        extra_headers: dict = None) -> dict:
    """Generic OpenAI-compatible provider call."""
    pinfo = PROVIDER_REGISTRY[provider_name]
    url   = pinfo["url"]

    # Cloudflare URL needs account_id substituted
    if "{account_id}" in url:
        account_id = _cfg("CLOUDFLARE_ACCOUNT_ID", "")
        url = url.replace("{account_id}", account_id)

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if extra_headers:
        headers.update(extra_headers)
    if pinfo.get("extra_headers"):
        headers.update(pinfo["extra_headers"])

    payload = {
        "model":      model,
        "messages":   messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }

    # Tool support
    if tools_def and pinfo.get("tool_support"):
        if provider_name != "cloudflare":
            payload["tools"]       = tools_def
            payload["tool_choice"] = "auto"
        # Cloudflare: inject tool hint into system prompt (text-based)
        else:
            _CF_TOOLS_BRIEF = [
                "open_application(app_name)", "open_url(url)", "youtube_play(query)",
                "search_in_app(app,query)", "search_web(query)", "take_screenshot()",
                "type_text(text)", "press_key(key)", "hotkey(keys)", "get_time()",
                "get_system_info()", "notify(title,message)", "run_command(command)",
                "research(query,depth)", "quick_fact(query)", "agent_task(task)",
            ]
            tool_hint = (
                "\n\nAVAILABLE TOOLS - Respond ONLY with:\n"
                "```json\n{\"tool\": \"tool_name\", \"arguments\": {\"param\": \"value\"}}\n```\n"
                "Tools:\n" + "\n".join(f"  - {t}" for t in _CF_TOOLS_BRIEF)
            )
            for m in payload["messages"]:
                if m.get("role") == "system":
                    m["content"] = m["content"] + tool_hint
                    break

    resp = http.post(url, headers=headers, json=payload, timeout=25)

    # Handle 400 with tool_use error - retry without tools
    if resp.status_code == 400 and tools_def:
        err = {}
        try: err = resp.json()
        except Exception: pass  # json parse optional for error detail
        err_code = err.get("error", {}).get("code", "") if isinstance(err, dict) else ""
        if err_code in ("tool_use_failed", "invalid_request_error", "unsupported_parameter"):
            payload2 = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice")}
            resp = http.post(url, headers=headers, json=payload2, timeout=25)

    resp.raise_for_status()
    parsed = _parse_openai_response(resp.json())

    # Cloudflare text-based tool extraction
    if provider_name == "cloudflare" and not parsed["message"]["tool_calls"]:
        import re as _re
        text = parsed["message"].get("content", "")
        blocks = _re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.DOTALL)
        for block in blocks:
            try:
                p = json.loads(block)
                tname = p.get("tool") or p.get("name")
                targs = p.get("arguments") or p.get("args") or {}
                if tname:
                    parsed["message"]["tool_calls"].append(
                        {"id": "cf_0", "function": {"name": tname, "arguments": targs}}
                    )
                    parsed["message"]["content"] = _re.sub(
                        r"```(?:json)?\s*\{.*?\}\s*```", "", text, flags=_re.DOTALL
                    ).strip()
            except Exception as _e:
                print(f"[DEBUG] smart_brain.py: {_e}")

    return parsed



def _call_cohere_format(api_key: str, model: str, messages: list, max_tokens: int) -> dict:
    """Cohere v2 chat API."""
    sys_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")
    chat_msgs = [
        {"role": m["role"], "content": m.get("content","") or ""}
        for m in messages if m.get("role") in ("user","assistant")
    ]
    payload = {"model": model, "messages": chat_msgs,
               "max_tokens": max_tokens, "temperature": 0.1}
    if sys_msg:
        payload["system"] = sys_msg
    resp = http.post(
        "https://api.cohere.com/v2/chat",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload, timeout=25
    )
    resp.raise_for_status()
    data = resp.json()
    text = ""
    for block in data.get("message", {}).get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text += block.get("text", "")
    return {"message": {"content": text, "tool_calls": []}}


def _call_anthropic(api_key: str, model: str, messages: list,
                    max_tokens: int, tools_def: list = None) -> dict:
    """Anthropic Claude API call - converts from OpenAI format."""
    import itertools as _it
    _id_gen      = _it.count(1)
    _pending_ids = []
    ant_msgs     = []

    sys_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")

    for m in messages:
        role    = m.get("role", "")
        content = m.get("content", "") or ""
        if role == "system":
            pass  # extracted above
        elif role == "tool":
            tid = _pending_ids.pop(0) if _pending_ids else f"tool_{next(_id_gen)}"
            ant_msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tid, "content": content}
            ]})
        elif role == "assistant" and m.get("tool_calls"):
            parts = []
            if content: parts.append({"type": "text", "text": content})
            _pending_ids.clear()
            for tc in m["tool_calls"]:
                fn   = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except (json.JSONDecodeError, TypeError, ValueError): args = {}
                tid  = tc.get("id") or f"tool_{next(_id_gen)}"
                _pending_ids.append(tid)
                parts.append({"type": "tool_use", "id": tid,
                               "name": fn.get("name", ""), "input": args})
            ant_msgs.append({"role": "assistant", "content": parts})
        else:
            ant_msgs.append({"role": role, "content": content})

    # Build tool defs for Anthropic format
    ant_tools = []
    if tools_def:
        for t in tools_def:
            fn = t.get("function", {})
            ant_tools.append({
                "name":         fn.get("name", ""),
                "description":  fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
            })

    payload = {
        "model":      model,
        "max_tokens": max_tokens,
        "system":     sys_msg,
        "messages":   ant_msgs,
    }
    if ant_tools:
        payload["tools"] = ant_tools

    resp = http.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type":      "application/json",
        },
        json=payload,
        timeout=35
    )
    resp.raise_for_status()
    data = resp.json()

    tool_calls = []
    text_parts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id":       block.get("id", ""),
                "function": {"name": block["name"], "arguments": block.get("input", {})}
            })

    return {"message": {"content": "".join(text_parts), "tool_calls": tool_calls}}


def _call_gemini(api_key: str, model: str, messages: list,
                 max_tokens: int, tools_def: list = None) -> dict:
    """Google Gemini API call - converts from OpenAI format."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Convert messages to Gemini format
    gem_contents = []
    sys_parts    = []

    for m in messages:
        role    = m.get("role", "")
        content = m.get("content", "") or ""
        if role == "system":
            sys_parts.append({"text": content})
        elif role == "user" or role == "tool":
            gem_contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            if m.get("tool_calls"):
                # Tool call from assistant - functionCall parts
                parts = []
                if content:
                    parts.append({"text": content})
                for tc in m["tool_calls"]:
                    fn   = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except (json.JSONDecodeError, TypeError, ValueError): args = {}
                    parts.append({"functionCall": {"name": fn.get("name", ""), "args": args}})
                gem_contents.append({"role": "model", "parts": parts})
            else:
                gem_contents.append({"role": "model", "parts": [{"text": content}]})

    payload = {
        "contents":         gem_contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature":     0.1,
        }
    }
    if sys_parts:
        payload["systemInstruction"] = {"parts": sys_parts}

    # Tool support for Gemini
    if tools_def:
        gem_tools = []
        for t in tools_def:
            fn = t.get("function", {})
            gem_tools.append({
                "name":        fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters":  fn.get("parameters", {"type": "OBJECT", "properties": {}})
            })
        payload["tools"] = [{"functionDeclarations": gem_tools}]
        payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

    resp = http.post(url, json=payload, timeout=25)
    resp.raise_for_status()
    data = resp.json()

    text_parts  = []
    tool_calls  = []
    import itertools as _it2
    _gid = _it2.count(1)

    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id":       f"gem_{next(_gid)}",
                    "function": {"name": fc.get("name", ""), "arguments": fc.get("args", {})}
                })

    return {"message": {"content": "".join(text_parts), "tool_calls": tool_calls}}


# ══════════════════════════════════════════════════════════════════════
#  MAIN SMART BRAIN CALL
#  Drop-in replacement for existing brain_call()
# ══════════════════════════════════════════════════════════════════════

# ── reload_brain TTL guard (Fix 3) ────────────────────────────────────
_brain_last_check: float = 0.0   # epoch seconds of last mtime check
_BRAIN_CHECK_TTL: float = 5.0    # only stat the file every 5 s max

# ── Smart exponential backoff ─────────────────────────────────────────
_BACKOFF_STATE = {}  # provider - {count, last_fail}

def _backoff_wait(provider: str) -> float:
    """
    Exponential backoff: 1s - 2s - 4s - 8s - give up.
    Same provider - wait, not just skip.
    Resets after 60s success.
    """
    import time as _t
    state = _BACKOFF_STATE.get(provider, {"count": 0, "last_fail": 0})
    now = _t.time()

    # Reset if been 60s since last fail
    if now - state["last_fail"] > 60:
        _BACKOFF_STATE[provider] = {"count": 0, "last_fail": 0}
        return 0.0

    wait = min(2 ** state["count"], 8)  # 1, 2, 4, 8 max
    _BACKOFF_STATE[provider] = {"count": state["count"] + 1, "last_fail": now}
    if wait > 0:
        print(f"[BACKOFF] {provider} rate limited - waiting {wait}s before retry")
        _t.sleep(wait)
    return wait

def _backoff_success(provider: str):
    """Reset backoff on successful call."""
    _BACKOFF_STATE.pop(provider, None)


def smart_brain_call(model, messages, max_tokens: int = 2048,
                     tools_def: list = None, require_tools: bool = True,
                     task_type: str = None, system_prompt: str = None) -> dict:
    """
    Smart brain call - task type detect karke best model select karta hai.

    Task routing:
      simple    - Ollama / Groq 8b       (fast, free)
      chat      - Groq / Cerebras 70b    (good balance)
      tool      - Groq 70b               (best tool calling)
      code      - DeepSeek Chat          (best code)
      reasoning - DeepSeek Reasoner / R1 (math, logic, analysis)
      research  - Perplexity             (web-grounded answers)
      vision    - Gemini 2.0 Flash       (screen/image)
      creative  - Claude Sonnet          (writing, content)
      long_ctx  - Gemini 1.5 Pro         (1M context)

    - .env change hone pe auto-reload (no restart needed)
    - Rate limit - same task type ka next model auto
    - tools_def: TOOLS_DEF pass karo for tool calling

    Returns: {"message": {"content": str, "tool_calls": list}}
    """
    # Auto-reload if .env changed - but only stat the file every 5 s (Fix 3)
    global _brain_last_check
    _now = _time.time()
    if _now - _brain_last_check >= _BRAIN_CHECK_TTL:
        reload_brain()
        _brain_last_check = _now

    # Fix 2 - task-type-aware token budget (saves 3-8x tokens on simple calls)
    TOKEN_BUDGET = {
        "simple":    256,
        "tool":      300,
        "chat":      600,
        "creative":  800,
        "vision":    600,
        "research": 1200,
        "code":     1500,
        "long_ctx": 1800,
        "reasoning": 2048,
    }
    if task_type and max_tokens == 2048:   # only override when caller didn't set it
        max_tokens = TOKEN_BUDGET.get(task_type, 800)

    # ── Agent persona: inject system prompt ─────────────────────────
    if system_prompt:
        non_sys = [m for m in messages if m.get("role") != "system"]
        messages = [{"role": "system", "content": system_prompt}] + non_sys

    chain = _brain_state["routing_chain"]
    if not chain:
        raise Exception(
            "API keys missing in .env!\n"
            "  SMART_KEY_1=gsk_xxx  (Groq)\n"
            "  SMART_KEY_1=sk-ant-xxx  (Claude)\n"
            "  SMART_KEY_1=AIzaxxx  (Gemini)\n"
            "  or old GROQ_API_KEY=gsk_xxx also works"
        )

    # ── Task type detection - optimal model selection ─────────────────
    detected_type = task_type or detect_task_type(messages)
    optimal_provider, optimal_model = get_model_for_task(detected_type)
    print(f"[SMART BRAIN] [TASK] {detected_type} -> {optimal_provider}/{optimal_model}")

    last_error = ""

    # Build provider chain: optimal first, then rest of routing chain as fallback
    # This ensures task-optimal model is tried first, then falls back gracefully
    task_candidates = TASK_MODEL_MAP.get(detected_type, [])
    # Ordered list: [(pname, model), ...] - optimal first, then generic chain
    ordered_candidates = []
    for pname, mname, _ in task_candidates:
        if pname != "ollama":  # Ollama handled separately in brain_call wrapper
            ordered_candidates.append((pname, mname))
    # Add remaining chain providers not already in candidates
    for pname in chain:
        if not any(p == pname for p, _ in ordered_candidates):
            pinfo = PROVIDER_REGISTRY.get(pname, {})
            models = pinfo.get("models", [])
            if models:
                ordered_candidates.append((pname, models[0]))

    for pname, preferred_model in ordered_candidates:
        pinfo     = PROVIDER_REGISTRY.get(pname)
        if not pinfo:
            continue

        avail = _available_keys_for(pname)
        if not avail:
            # All keys blocked - show next unblock time
            all_keys    = _brain_state["detected_keys"].get(pname, [])
            unblock_min = min(
                (_brain_state["key_cooldowns"].get(_key_id(pname, i), 0) for i in range(len(all_keys))),
                default=0
            )
            wait = max(0, int(unblock_min - _time.time()))
            print(f"[SMART BRAIN] {pname} skipped - all {len(all_keys)} keys blocked ({wait}s)")
            continue

        # Task-optimal model first, then provider's default fallbacks
        all_provider_models = pinfo.get("models", [])
        if preferred_model in all_provider_models:
            models_to_try = [preferred_model] + [m for m in all_provider_models if m != preferred_model]
        elif preferred_model:
            # Model not in registry - try it anyway + fallback to registered models
            models_to_try = [preferred_model] + all_provider_models
        else:
            models_to_try = all_provider_models

        if not models_to_try:
            continue  # Skip provider if no models configured
        for key_idx, api_key in avail:
            for mdl_idx, model_name in enumerate(models_to_try):
                try:
                    fmt = pinfo.get("format", "openai")

                    if fmt == "anthropic":
                        result = _call_anthropic(api_key, model_name, messages, max_tokens,
                                                  tools_def if require_tools else None)
                    elif fmt == "gemini":
                        result = _call_gemini(api_key, model_name, messages, max_tokens,
                                               tools_def if require_tools else None)
                    elif fmt == "cohere":
                        result = _call_cohere_format(api_key, model_name, messages, max_tokens)
                    elif fmt in ("openai", "cloudflare"):
                        # cloudflare has special handling inside _call_openai_format
                        result = _call_openai_format(
                            pname, api_key, model_name, messages, max_tokens,
                            tools_def if require_tools else None
                        )
                    else:
                        # Unknown format - fallback to openai-compatible
                        print(f"[SMART BRAIN] Unknown format '{fmt}' for {pname} - trying openai")
                        result = _call_openai_format(
                            pname, api_key, model_name, messages, max_tokens,
                            tools_def if require_tools else None
                        )

                    _record_success(pname, key_idx)
                    calls = _brain_state["key_call_counts"].get(_key_id(pname, key_idx), 0)

                    _brain_state["active_provider"] = pname
                    _brain_state["active_model"]    = model_name
                    _brain_state["last_error"]       = ""

                    print(f"[SMART BRAIN] [SUCCESS] {pname}/{model_name} k[{key_idx+1}] calls={calls}")
                    return result

                except http.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response is not None else 0
                    if status == 429:
                        _backoff_wait(pname)  # exponential backoff before switching
                        retry_sec = 60
                        try:
                            ra = e.response.headers.get("Retry-After", "")
                            if ra: retry_sec = max(10, int(float(ra)))
                        except Exception as _e:
                            print(f"[DEBUG] smart_brain.py: {_e}")
                        _block_key(pname, key_idx, retry_sec)
                        last_error = f"{pname} rate limited ({retry_sec}s)"
                        break   # try next key of same provider
                    elif status == 401:
                        _block_key(pname, key_idx, 3600)
                        last_error = f"{pname} key[{key_idx+1}] invalid (401)"
                        break
                    elif status == 400:
                        # Try next model
                        last_error = f"{pname}/{model_name} 400 error"
                        continue
                    else:
                        last_error = f"{pname} HTTP {status}"
                        break

                except Exception as e:
                    last_error = f"{pname}: {str(e)[:80]}"
                    print(f"[SMART BRAIN] [ERROR] {last_error}")
                    break  # try next provider

    # All providers exhausted
    cooldowns = {
        k: round(v - _time.time())
        for k, v in _brain_state["key_cooldowns"].items()
        if v > _time.time()
    }
    if cooldowns:
        min_wait = min(cooldowns.values())
        raise Exception(
            f"⏳ Saari APIs rate limited — {min_wait}s mein retry karo.\n"
            f"  Last error: {last_error}\n"
            f"  Tip: zyada keys SMART_KEY_2, SMART_KEY_3 mein daalo"
        )

    raise Exception(
        f"❌ Koi provider available nahi.\n"
        f"  Last error: {last_error}\n"
        f"  Chain tried: {' → '.join(chain[:5])}{'...' if len(chain)>5 else ''}\n"
        f"  Tip: .env mein GROQ_API_KEY ya GEMINI_API_KEY dalo (dono free hain)"
    )


# ══════════════════════════════════════════════════════════════════════
#  STATUS & DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════

def get_brain_status() -> dict:
    """Dashboard ke liye full status."""
    reload_brain()
    now = _time.time()
    providers = {}
    for pname, keys in _brain_state["detected_keys"].items():
        if not keys:
            continue
        avail_count = sum(1 for i in range(len(keys)) if _is_key_available(pname, i))
        providers[pname] = {
            "total_keys":  len(keys),
            "avail_keys":  avail_count,
            "ok":          avail_count > 0,
            "calls":       sum(
                _brain_state["key_call_counts"].get(_key_id(pname, i), 0)
                for i in range(len(keys))
            ),
            "display_name": PROVIDER_REGISTRY.get(pname, {}).get("name", pname),
        }

    return {
        "mode":             _brain_state["brain_mode"],
        "chain":            _brain_state["routing_chain"],
        "active_provider":  _brain_state["active_provider"],
        "active_model":     _brain_state["active_model"],
        "providers":        providers,
        "cooldowns": {
            k: round(v - now)
            for k, v in _brain_state["key_cooldowns"].items()
            if v > now
        },
        "total_keys": sum(len(v) for v in _brain_state["detected_keys"].values()),
    }


def add_key_live(key: str) -> str:
    """
    Runtime mein naya key add karo — .env mein bhi save hoga.
    Returns: provider name jo detect hua
    """
    provider = detect_provider_from_key(key)
    if provider == "sk_ambiguous":
        return (
            "⚠️  Key prefix sk- se provider detect nahi hua (ambiguous).\n"
            "  Named env var use karo:\n"
            "    DEEPSEEK_API_KEY=sk-xxx\n"
            "    MISTRAL_API_KEY=sk-xxx\n"
            "    DASHSCOPE_API_KEY=sk-xxx\n"
            "  Ya UI Settings mein manually provider select karo."
        )
    if provider == "unknown":
        return (
            "❌ Provider detect nahi hua. Key format check karo.\n"
            "  Known prefixes: gsk_ sk-ant- sk-or- AIza csk- pplx- xai- nvapi- hf_ eyJ"
        )

    # Save to .env
    env_path = os.path.join(ROOT, "config", ".env")
    existing = _brain_state["detected_keys"].get(provider, [])
    slot     = len(existing) + 1
    pinfo    = PROVIDER_REGISTRY.get(provider, {})
    base_env = pinfo.get("env_keys", [f"{provider.upper()}_API_KEY"])[0]
    env_key  = base_env if slot == 1 else f"{base_env}_{slot}"

    try:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\n{env_key}={key}\n")
    except (OSError, IOError) as e:
        return f"❌ .env save failed: {e}"

    # Force reload
    global _brain_env_mtime
    _brain_env_mtime = 0
    reload_brain(force=True)

    return (f"✅ {provider.upper()} key add ho gaya! "
            f"({pinfo.get('name', provider)} — slot {slot})")


# ══════════════════════════════════════════════════════════════════════
#  BACKGROUND KEEPALIVE — Auto .env watch
# ══════════════════════════════════════════════════════════════════════

def _brain_watchdog():
    """Background thread — .env change hone pe auto-reload."""
    while True:
        try:
            reload_brain()
        except Exception as _wde:
            print(f"[SMART_BRAIN] watchdog reload: {_wde}")
        _time.sleep(5)


def explain_routing(task: str) -> dict:
    """Kisi task ke liye explain karo — kaun sa model use hoga aur kyun."""
    msgs = [{"role": "user", "content": task}]
    task_type = detect_task_type(msgs)
    provider, model = get_model_for_task(task_type)
    candidates = TASK_MODEL_MAP.get(task_type, [])
    descriptions = {
        "simple":    "Simple command — fast model (app open, time, screenshot)",
        "chat":      "General conversation — balanced speed + quality",
        "tool":      "Tool use / automation — best tool-calling model",
        "code":      "Code / debug — DeepSeek Chat (best code model)",
        "reasoning": "Logic / math / analysis — DeepSeek R1 Reasoner",
        "research":  "Research / news / facts — Perplexity (web-grounded)",
        "vision":    "Screen / image analysis — Gemini 2.0 Flash",
        "excel":     "Excel / Word / PowerPoint — MiniMax M2.5 (Office specialist)",
        "creative":  "Creative writing / content — Claude Sonnet",
        "long_ctx":  "Long document / big file — Gemini 1.5 Pro (1M context)",
    }
    chain_info = []
    for p, m, _ in candidates[:6]:
        pinfo = PROVIDER_REGISTRY.get(p, {})
        keys  = len(_brain_state["detected_keys"].get(p, []))
        chain_info.append({
            "provider": p, "model": m,
            "name": pinfo.get("name", p),
            "free": pinfo.get("free", False),
            "keys": keys,
            "available": keys > 0 or p == "ollama",
            "selected": p == provider and m == model,
        })
    return {
        "task": task, "task_type": task_type,
        "description": descriptions.get(task_type, ""),
        "selected": {"provider": provider, "model": model},
        "chain": chain_info,
    }

_watchdog_thread = threading.Thread(target=_brain_watchdog, daemon=True, name="brain_watchdog")
_watchdog_thread.start()

# Initial load — only if .env exists, defer to first call otherwise
# Use a short sleep so module imports finish before we print the chain
import os as _os_sb
if _os_sb.path.exists(_os_sb.path.join(ROOT, "config", ".env")):
    reload_brain(force=True)  # single startup load
else:
    print("[SMART BRAIN] .env not found — create from .env.template and add API keys")

# Guard: server calls reload_brain() on every request — deduplicate via mtime cache
# (already handled by _brain_env_mtime check — no extra code needed)


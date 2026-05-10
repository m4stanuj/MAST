# MAST v1.0
**Unified AI Stack — M4STCLAW v3 + OpenWork v12 + EIGENT v4.1**

> *Working > Perfect · Shipped > Planned · 80% in 3hrs > 100% in 3 days*

---

## What is MAST?

MAST is Mast's (Anuj's) unified personal AI operator — a Jarvis-style system built on top of OpenCode. It merges:

- **M4STCLAW v3** — pentest MCPs, bridge_core (recon/vuln/scheduler/agents), SOUL identity
- **OpenWork v12** — 15 hardened MCP servers, semantic cache, 56 API key rotation
- **EIGENT v4.1** — lean 6-agent config, NVIDIA NIM integration, working-first philosophy

### What's New in MAST over predecessors

| Feature | OpenWork v12 | M4STCLAW v3 | **MAST v1.0** |
|---------|:---:|:---:|:---:|
| MCP Servers | 15 | 19 | **21** |
| Providers | 7 | 8 | **11** |
| NVIDIA NIM | ❌ | ✅ (partial) | ✅ **full** |
| Mistral | ❌ | ❌ | ✅ **1B tok/mo free** |
| xAI/Grok | ❌ | ❌ | ✅ |
| Hardcoded keys | ✅ (bad) | ✅ (bad) | **❌ env-only** |
| SMART_KEY detect | ❌ | ✅ | ✅ |
| Hinglish chain | ❌ | ❌ | ✅ **Sarvam-M** |
| Pentest chain | ❌ | ✅ | ✅ **NVIDIA primary** |
| Task chains | 9 | 9 | **11** |
| Skills | 22 | 28 | **28** |

---

## Quick Start

```powershell
# 1. Extract MAST.zip somewhere (e.g. C:\MAST)
# 2. Run installer
powershell -ExecutionPolicy Bypass -File install.ps1

# 3. Fill in your API keys
notepad %USERPROFILE%\.config\opencode\config\.env

# 4. Done — run OpenCode in any project
cd C:\your-project
opencode
```

---

## Free Providers — Add These First (₹0 cost)

| Provider | Prefix | Signup | Best For |
|----------|--------|--------|----------|
| **Groq** | `gsk_` | console.groq.com | Speed (315 TPS) |
| **NVIDIA NIM** | `nvapi-` | build.nvidia.com | Code, Pentest, Hinglish |
| **Gemini** | `AIza` | aistudio.google.com | Vision, Reasoning |
| **Mistral** | `msk-` | console.mistral.ai | Writing (1B tok/mo FREE) |
| **Cerebras** | `csk-` | cloud.cerebras.ai | Ultra-fast (1000 TPS) |
| **OpenRouter** | `sk-or-` | openrouter.ai | Kimi K2, MiMo-V2, R1 FREE |
| **SambaNova** | UUID | cloud.sambanova.ai | Large models free |

**SMART_KEY**: paste any key as `SMART_KEY_1=yourkey` — prefix auto-detected.

---

## Architecture

```
MAST/
├── SOUL_MAST.md           ← Agent identity (hot-reload, edit anytime)
├── install.ps1            ← Full Windows installer
├── INSTALL_SKILLS.bat     ← Skills-only quick install
├── mcp_servers/           ← 21 MCP servers
│   ├── llm_fallback.py    ← Brain: 11 providers, 11 task chains, semantic cache
│   ├── memory_mcp.py      ← 3-tier memory (RAM + SQLite + ChromaDB)
│   ├── pentest_mcp.py     ← CEH tools (authorized targets only)
│   ├── task_router_mcp.py ← Auto task classification + routing
│   ├── m4st_agent_mcp.py  ← 6-agent OMO Sisyphus orchestrator
│   ├── scheduler.py       ← Hinglish time parsing + APScheduler
│   ├── coding.py          ← Dev agent bridge
│   └── ...15 more
├── bridge_core/           ← M4STCLAW Python modules
│   ├── smart_brain.py     ← Local brain with LRU cache, TF-IDF recall
│   ├── agents.py          ← Plan→Critique→Refine agent loop
│   ├── recon.py           ← OSINT + network recon
│   ├── vuln.py            ← Vulnerability scanning
│   ├── memory_3tier.py    ← SQLite + ChromaDB memory
│   └── ...9 more
├── skills/                ← 28 OpenCode skills (SKILL.md files)
├── config/
│   ├── .env               ← API keys (NEVER commit this)
│   ├── opencode.json      ← OpenCode config
│   └── m4st_agents_config.json ← 6-agent specs
└── data/                  ← Runtime data (cache, memory, logs)
```

---

## Task Chains

| Chain | Primary Model | Use Case |
|-------|--------------|----------|
| `speed` | Groq → Cerebras | Quick answers, tool calls |
| `reason` | Kimi K2 → DeepSeek R1 | Math, logic, analysis |
| `code` | Kimi K2 → Qwen3-Coder | Write, debug, refactor |
| `vision` | Gemini 2.5 Flash → MiMo-Omni | Screenshots, GUI |
| `research` | Kimi K2 → DeepSeek R1 | Multi-source research |
| `write` | **Mistral Large** → Cerebras | Docs, emails, blogs |
| `agent` | Kimi K2 → Qwen3-235B | Multi-step automation |
| `pentest` | **NVIDIA/deepseek-r1** → NVIDIA/GLM | CEH labs only |
| `hinglish` | **NVIDIA/Sarvam-M** → Gemini | Indic/Hinglish tasks |
| `vision_reason` | Gemini 2.5 Flash → MiMo-Omni | Visual reasoning |
| `default` | Groq → Cerebras → NVIDIA → Gemini | Fallback |

---

## Security

- **Safety guard P0**: blocks `rm -rf`, `DROP TABLE`, `format c:`, `del /f /s`
- **localhost only**: never binds to 0.0.0.0
- **Pentest**: `authorized_targets.txt` checked in CODE before any scan
- **Keys**: `.env` only — add to `.gitignore` immediately
- **Telegram**: `MAST_ALLOWED_CHAT_IDS` only

---

## Adding More Keys

```env
# In config/.env — add as _1, _2, _3...
NVIDIA_API_KEY_1=nvapi-xxxxx
NVIDIA_API_KEY_2=nvapi-yyyyy

# Or use SMART_KEY auto-detect
SMART_KEY_1=nvapi-xxxxx   # auto-detected as NVIDIA
SMART_KEY_2=msk-yyyyy     # auto-detected as Mistral
SMART_KEY_3=gsk_zzzzz     # auto-detected as Groq
```

---

*MAST v1.0 — May 2026 | mastjarvis-cmyk | 80% in 3hrs > 100% in 3 days*

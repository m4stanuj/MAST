# CHANGELOG / FIXES

## [v1.0.2] - 2026-05-29

### Added
- Public launch assets: `PRESENTATION.md`, `SOCIAL.md`, `DEMO_STORYBOARD.md`, and `ALGORITHM.md`.
- `ECOSYSTEM.md` mapping all M4ST repositories and their roles.
- README badges, at-a-glance stats, algorithm summary, and project resources table.
- MIT `LICENSE` file to match README badge.
- GitHub Actions CI workflow for Python syntax compilation.

### Verified
- Python syntax compile across `mcp_servers/` and `bridge_core/`.
- Markdown code fences balanced for root docs.

## [v1.0.1] - 2026-05-10

### 🔴 Fixed
- **SOUL Identity Loading**: Fixed incorrect references to `SOUL_v3.md` in `coding.py`, `task_router_mcp.py`, and `m4st_agent_mcp.py`. Now correctly points to `SOUL_MAST.md` with a fallback to `SOUL.md`. Agent identity now loads successfully across all tools.
- **Bridge Core Paths**: Fixed an issue in `recon.py` and `vuln.py` where they searched for the non-existent `bridge/` directory instead of the actual `bridge_core/` directory. Direct brain calls for pentest tasks now execute without silently failing.
- **Environment Variable Paths**: Fixed `.env` loading in multiple core files (`brain.py`, `smart_brain.py`, `voice.py`, `recon.py`, `vuln.py`, `research.py`). Changed paths from `ROOT/.env` to the correct `config/.env` structure.
- **Task Routing Schema**: Added `hinglish` to the `task_hint` parameter in `task_router_mcp.py` to match the newly added fallback chains.
- **Setup Script Syntax**: Fixed a `SyntaxError` in `setup_mcp.py` caused by invalid nested quotes inside an f-string, ensuring compatibility with Python 3.10 and 3.11.
- **Windows Terminal Stability**: Removed emojis (like 🔄, ✅, ⚠️, 🧠) from `smart_brain.py` print statements that were causing `UnicodeEncodeError` crashes on default Windows command prompts.

### 🟡 Added
- **API Keys Template**: Added new required slots in `config/.env` for `TAVILY_API_KEY`, `PERPLEXITY_API_KEY`, `EXA_API_KEY` to support the web-grounded research chains.
- **Voice Configurations**: Added explicit slots for `WHISPER_API_KEY` and set `WAKE_WORD=hey mast` by default.
- **Graphiti Memory Integration**: Set up `.env` placeholders for `FALKORDB_URL` and `GRAPHITI_KEY` to prepare for T4 Graphiti temporal KG memory.
- **Authorized Targets List**: Added placeholder HackTheBox and TryHackMe subnet IPs and `scanme.nmap.org` to `config/authorized_targets.txt` for easier out-of-the-box CEH scanning capabilities.

### 🔵 Infrastructure
- **CI Pipeline**: Introduced GitHub Actions CI (`.github/workflows/ci.yml`) to automatically check Python syntax and run basic MCP import checks upon push to the repository.

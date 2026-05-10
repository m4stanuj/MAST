#!/usr/bin/env python3
"""
coding_mcp.py — M4ST Coding MCP v1.0 (v3.1 addition)
======================================================
Eigent-compatible coding interface for M4STCLAW.
Routes all code tasks through llm_fallback "code" chain:
  NIM-DeepSeek-V4-Flash → Kimi-K2 → Qwen3-Coder → MiMo-Pro → Nemotron → DeepSeek

Why this exists:
  Eigent m4st_agents_config.json mein Developer Agent uses coding_mcp.
  task_router mein coding kaam karta hai, lekin Eigent ek dedicated
  "coding_mcp" server expect karta hai. Yeh thin wrapper hai.

Tools:
  code_complete   — Write / complete code from description
  code_debug      — Debug code + explain fix
  code_refactor   — Refactor for quality/performance
  code_review     — Review code, suggest improvements
  code_explain    — Explain code in Hinglish or English
  code_test       — Generate unit tests for given code
  code_shell      — Generate shell/PowerShell command for a task

Usage in opencode.json:
  "coding": {
    "command": "python",
    "args": ["mcp_servers/coding_mcp.py"],
    "enabled": true
  }
"""
import sys, os, json
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))

from _mcp_base import mcp_loop, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list

def _log(m): print(f"[coding_mcp] {m}", file=sys.stderr, flush=True)

# ── Brain (code chain) ────────────────────────────────────────────────
def _brain(messages: list, max_tokens: int = 2000) -> str:
    try:
        from llm_fallback import chat_complete
        return chat_complete(messages, max_tokens=max_tokens, task="code", use_cache=False)
    except Exception as e:
        return f"ERROR: {e}"

# ── SOUL system prompt ────────────────────────────────────────────────
_SOUL_TEXT = ""
def _get_soul() -> str:
    global _SOUL_TEXT
    if _SOUL_TEXT:
        return _SOUL_TEXT
    for p in [_CONFIG_DIR / "SOUL_MAST.md", _CONFIG_DIR / "SOUL.md",
              Path(__file__).parent.parent / "SOUL_MAST.md", Path(__file__).parent.parent / "SOUL.md"]:
        if p.exists():
            _SOUL_TEXT = p.read_text(encoding="utf-8", errors="replace")[:1500]
            return _SOUL_TEXT
    return "You are M4ST's coding agent. Write clean, runnable code. No pseudocode."

_CODE_SYSTEM = """You are M4ST's Developer Agent — specialized in writing, debugging, and reviewing code.
Rules:
- Always write RUNNABLE code — never pseudocode
- Add brief inline comments for non-obvious logic
- Python: follow PEP8. JS/TS: use modern syntax
- If debugging: explain what was wrong + what you fixed
- If no language specified: infer from context, default Python
- Hinglish OK in explanations
- Output format: code block first, then brief explanation
"""

# ── Tool handlers ─────────────────────────────────────────────────────

def _t_code_complete(args: dict) -> str:
    desc = args.get("description", "").strip()
    lang = args.get("language", "").strip()
    context = args.get("context", "").strip()
    if not desc:
        return "ERROR: description required (what to build)"
    prompt = f"Write {'`' + lang + '`' + ' ' if lang else ''}code for: {desc}"
    if context:
        prompt += f"\n\nContext / existing code:\n```\n{context}\n```"
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


def _t_code_debug(args: dict) -> str:
    code = args.get("code", "").strip()
    error = args.get("error", "").strip()
    lang = args.get("language", "").strip()
    if not code:
        return "ERROR: code required"
    prompt = f"Debug this{' ' + lang if lang else ''} code"
    if error:
        prompt += f"\n\nError / symptom:\n{error}"
    prompt += f"\n\nCode:\n```{lang}\n{code}\n```"
    prompt += "\n\nExplain: what was wrong, what you changed, why it's fixed."
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


def _t_code_refactor(args: dict) -> str:
    code = args.get("code", "").strip()
    goal = args.get("goal", "improve readability and performance").strip()
    lang = args.get("language", "").strip()
    if not code:
        return "ERROR: code required"
    prompt = f"Refactor this{' ' + lang if lang else ''} code. Goal: {goal}\n\n```{lang}\n{code}\n```"
    prompt += "\n\nShow refactored version + 2-3 bullet points on what changed."
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


def _t_code_review(args: dict) -> str:
    code = args.get("code", "").strip()
    lang = args.get("language", "").strip()
    focus = args.get("focus", "bugs, security, performance").strip()
    if not code:
        return "ERROR: code required"
    prompt = (
        f"Review this{' ' + lang if lang else ''} code. Focus: {focus}\n\n"
        f"```{lang}\n{code}\n```\n\n"
        "Format: Issues (numbered, severity HIGH/MED/LOW) → Suggestions → Verdict (ship / needs work / rewrite)"
    )
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


def _t_code_explain(args: dict) -> str:
    code = args.get("code", "").strip()
    lang = args.get("language", "").strip()
    level = args.get("level", "intermediate").strip()  # beginner / intermediate / expert
    hinglish = args.get("hinglish", True)
    if not code:
        return "ERROR: code required"
    style = "Hinglish (Hindi + English mix)" if hinglish else "English"
    prompt = (
        f"Explain this{' ' + lang if lang else ''} code in {style} for a {level} developer.\n\n"
        f"```{lang}\n{code}\n```"
    )
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


def _t_code_test(args: dict) -> str:
    code = args.get("code", "").strip()
    lang = args.get("language", "python").strip()
    framework = args.get("framework", "").strip()
    if not code:
        return "ERROR: code required"
    fw_hint = f" using {framework}" if framework else ""
    prompt = (
        f"Write unit tests{fw_hint} for this {lang} code.\n\n"
        f"```{lang}\n{code}\n```\n\n"
        "Cover: happy path, edge cases, error conditions. Add brief comment per test group."
    )
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


def _t_code_shell(args: dict) -> str:
    task = args.get("task", "").strip()
    shell = args.get("shell", "powershell").strip()  # powershell / bash / cmd
    os_hint = args.get("os", "windows").strip()
    if not task:
        return "ERROR: task required (what shell command should do)"
    prompt = (
        f"Write a {shell} command / script for {os_hint} that: {task}\n\n"
        "Requirements:\n"
        "- Safe — no destructive operations without confirmation\n"
        "- Add brief explanation of what each part does\n"
        "- If multi-step, show as script with comments"
    )
    msgs = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    return _brain(msgs)


# ── MCP dispatch ──────────────────────────────────────────────────────

TOOLS = {
    "code_complete": {
        "description": "Write / complete code from a description. Routed to NIM-DeepSeek-V4-Flash → Kimi-K2 → Qwen3-Coder chain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What to build"},
                "language":    {"type": "string", "description": "Programming language (optional, auto-inferred)"},
                "context":     {"type": "string", "description": "Existing code or context to build on (optional)"},
            },
            "required": ["description"],
        },
    },
    "code_debug": {
        "description": "Debug code — finds bug, explains fix, returns working version.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":     {"type": "string", "description": "Broken code"},
                "error":    {"type": "string", "description": "Error message or symptom (optional)"},
                "language": {"type": "string", "description": "Language (optional)"},
            },
            "required": ["code"],
        },
    },
    "code_refactor": {
        "description": "Refactor code for readability, performance, or a specific goal.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":     {"type": "string", "description": "Code to refactor"},
                "goal":     {"type": "string", "description": "Refactoring goal (default: readability + performance)"},
                "language": {"type": "string", "description": "Language (optional)"},
            },
            "required": ["code"],
        },
    },
    "code_review": {
        "description": "Review code for bugs, security issues, and performance. Returns severity-rated issues.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":     {"type": "string", "description": "Code to review"},
                "focus":    {"type": "string", "description": "Review focus (default: bugs, security, performance)"},
                "language": {"type": "string", "description": "Language (optional)"},
            },
            "required": ["code"],
        },
    },
    "code_explain": {
        "description": "Explain code in Hinglish or English. Adjustable level: beginner/intermediate/expert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":     {"type": "string", "description": "Code to explain"},
                "language": {"type": "string", "description": "Language (optional)"},
                "level":    {"type": "string", "description": "beginner / intermediate / expert (default: intermediate)"},
                "hinglish": {"type": "boolean", "description": "Explain in Hinglish (default: true)"},
            },
            "required": ["code"],
        },
    },
    "code_test": {
        "description": "Generate unit tests for given code. Covers happy path, edge cases, errors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":      {"type": "string", "description": "Code to test"},
                "language":  {"type": "string", "description": "Language (default: python)"},
                "framework": {"type": "string", "description": "Test framework (pytest, jest, etc. — optional)"},
            },
            "required": ["code"],
        },
    },
    "code_shell": {
        "description": "Generate shell/PowerShell/bash command or script for a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task":  {"type": "string", "description": "What the command should do"},
                "shell": {"type": "string", "description": "powershell / bash / cmd (default: powershell)"},
                "os":    {"type": "string", "description": "windows / linux / mac (default: windows)"},
            },
            "required": ["task"],
        },
    },
}

_HANDLERS = {
    "code_complete":  _t_code_complete,
    "code_debug":     _t_code_debug,
    "code_refactor":  _t_code_refactor,
    "code_review":    _t_code_review,
    "code_explain":   _t_code_explain,
    "code_test":      _t_code_test,
    "code_shell":     _t_code_shell,
}


def _handle(req: dict) -> dict:
    method = req.get("method", "")
    rid    = req.get("id")

    if method == "initialize":
        return mcp_initialize(req, "coding_mcp", "1.0.0")

    if method == "tools/list":
        return mcp_tools_list(req, TOOLS)

    if method == "tools/call":
        name = req.get("params", {}).get("name", "")
        args = req.get("params", {}).get("arguments", {})
        handler = _HANDLERS.get(name)
        if not handler:
            return mcp_error(rid, -32601, f"Unknown tool: {name}")
        try:
            result = handler(args)
            return mcp_respond(rid, result)
        except Exception as e:
            _log(f"ERROR in {name}: {e}")
            return mcp_error(rid, -32603, str(e))

    return mcp_error(rid, -32601, f"Unknown method: {method}")


if __name__ == "__main__":
    _log("coding_mcp v1.0 started — code chain: NIM-DeepSeek-V4-Flash → Kimi-K2 → Qwen3-Coder → MiMo-Pro")
    mcp_loop(_handle)

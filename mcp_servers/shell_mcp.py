"""
shell_mcp.py — OpenWork Shell/Terminal MCP Server v1.0
Run shell commands, Python snippets, check programs, manage processes.
Place in: C:/Users/<user>/.config/opencode/shell_mcp.py
"""
import sys, os, json, subprocess
from pathlib import Path

# ── reuse existing base ────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import (
    mcp_send, mcp_respond, mcp_error,
    mcp_initialize, mcp_loop, get_config_dir
)

def _log(m): print(f"[shell_mcp] {m}", file=sys.stderr, flush=True)

# ── safety: block destructive patterns ────────────────────────────────────
_BLOCKED = [
    "rm -rf /", "format c:", "del /s /q c:\\",
    "rd /s /q c:\\", ":(){:|:&};:", "mkfs", "dd if=/dev/zero"
]
def _blocked(cmd: str) -> bool:
    c = cmd.lower()
    return any(b in c for b in _BLOCKED)

# ── tools ──────────────────────────────────────────────────────────────────
TOOLS = [
    ("shell_run",    "Run PowerShell or CMD command. Returns stdout+stderr. Max timeout 120s."),
    ("shell_python", "Execute a Python code snippet. Returns print output + errors."),
    ("shell_which",  "Check if a program is installed (where.exe). Returns path or not found."),
    ("shell_env",    "Read environment variables. Pass key for specific var, empty for common vars."),
    ("shell_bg",     "Start a command in background (non-blocking). Returns PID immediately."),
]

SCHEMAS = {
    "shell_run": {
        "type": "object",
        "properties": {
            "command": {"type": "string",  "description": "Command to run"},
            "shell":   {"type": "string",  "description": "powershell (default) or cmd"},
            "timeout": {"type": "integer", "description": "Seconds before kill, max 120, default 60"},
            "cwd":     {"type": "string",  "description": "Working directory (optional)"}
        },
        "required": ["command"]
    },
    "shell_python": {
        "type": "object",
        "properties": {
            "code":    {"type": "string",  "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Seconds before kill, default 30"}
        },
        "required": ["code"]
    },
    "shell_which": {
        "type": "object",
        "properties": {
            "program": {"type": "string", "description": "Program name, e.g. python, git, node, ollama"}
        },
        "required": ["program"]
    },
    "shell_env": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Env var name (optional — empty returns common vars)"}
        }
    },
    "shell_bg": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to run in background"},
            "shell":   {"type": "string", "description": "powershell (default) or cmd"}
        },
        "required": ["command"]
    }
}

# ── handlers ───────────────────────────────────────────────────────────────
def _t_shell_run(a):
    cmd     = a.get("command", "").strip()
    shell   = a.get("shell", "powershell").lower()
    timeout = min(int(a.get("timeout", 60)), 120)
    cwd     = a.get("cwd") or None
    if not cmd:           return "Error: empty command"
    if _blocked(cmd):     return "Error: blocked — destructive command detected"
    try:
        args = (["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd]
                if shell == "powershell" else ["cmd", "/c", cmd])
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        parts = []
        if r.stdout.strip(): parts.append(f"STDOUT:\n{r.stdout.strip()}")
        if r.stderr.strip(): parts.append(f"STDERR:\n{r.stderr.strip()}")
        parts.append(f"Exit code: {r.returncode}")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

def _t_shell_python(a):
    code    = a.get("code", "").strip()
    timeout = min(int(a.get("timeout", 30)), 60)
    if not code: return "Error: empty code"
    try:
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, timeout=timeout)
        parts = []
        if r.stdout.strip(): parts.append(r.stdout.strip())
        if r.stderr.strip(): parts.append(f"STDERR:\n{r.stderr.strip()}")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

def _t_shell_which(a):
    prog = a.get("program", "").strip()
    if not prog: return "Error: no program specified"
    try:
        r = subprocess.run(["where", prog], capture_output=True, text=True, timeout=10)
        return f"✅ Found:\n{r.stdout.strip()}" if r.returncode == 0 else f"❌ '{prog}' not found in PATH"
    except Exception as e:
        return f"Error: {e}"

def _t_shell_env(a):
    key = a.get("key", "").strip()
    if key:
        v = os.environ.get(key)
        return f"{key} = {v}" if v else f"{key} is not set"
    show = ["PATH","PYTHONPATH","USERPROFILE","APPDATA","LOCALAPPDATA",
            "USERNAME","COMPUTERNAME","TEMP","NUMBER_OF_PROCESSORS","COMSPEC"]
    lines = []
    for k in show:
        v = os.environ.get(k, "(not set)")
        if k == "PATH" and len(v) > 300: v = v[:300] + "..."
        lines.append(f"{k} = {v}")
    return "\n".join(lines)

def _t_shell_bg(a):
    cmd   = a.get("command", "").strip()
    shell = a.get("shell", "powershell").lower()
    if not cmd:       return "Error: empty command"
    if _blocked(cmd): return "Error: blocked — destructive command detected"
    try:
        args = (["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd]
                if shell == "powershell" else ["cmd", "/c", cmd])
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"✅ Started background PID: {p.pid}\nCommand: {cmd}"
    except Exception as e:
        return f"Error: {e}"

_HANDLERS = {
    "shell_run":    _t_shell_run,
    "shell_python": _t_shell_python,
    "shell_which":  _t_shell_which,
    "shell_env":    _t_shell_env,
    "shell_bg":     _t_shell_bg,
}

# ── MCP loop ───────────────────────────────────────────────────────────────
def _handle(req):
    rid    = req.get("id")
    method = req.get("method", "")

    if method == "initialize":
        mcp_initialize(rid, "shell-mcp", "1.0.0")

    elif method == "tools/list":
        from _mcp_base import mcp_tools_list
        mcp_tools_list(rid, TOOLS, SCHEMAS)

    elif method == "tools/call":
        p    = req.get("params", {})
        name = p.get("name", "")
        args = p.get("arguments", {})
        fn   = _HANDLERS.get(name)
        if fn:
            try:
                mcp_respond(rid, fn(args))
            except Exception as e:
                mcp_error(rid, -32000, str(e))
        else:
            mcp_error(rid, -32601, f"Unknown tool: {name}")

    elif method == "notifications/initialized":
        pass

    elif rid is not None:
        mcp_send({"jsonrpc": "2.0", "id": rid, "result": {}})

if __name__ == "__main__":
    _log("Shell MCP v1.0 started — 5 tools ready")
    mcp_loop("shell-mcp", _handle)

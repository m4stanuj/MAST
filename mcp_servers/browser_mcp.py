"""
browser_mcp.py — OpenWork Browser MCP Server v2
================================================
Plain MCP stdio (JSON-RPC 2.0) via the hardened _mcp_base loop — client-agnostic.
Works in ANY MCP-compliant client (Claude Code, Cursor, Windsurf, Codex, Antigravity).

Tools: browse, browse_extract, browser_llm_status
Uses llm_fallback.py for automatic provider failover + browser_use for automation.

v2 change: rewritten from the low-level `mcp.server.Server` + `@app.tool()` mix
(which broke on the mcp 2.x SDK) to the same plain stdio JSON-RPC pattern used by
memory/shell/file/research servers. No dependency on the `mcp` package version.
"""
import sys, os, json, asyncio
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or os.path.expanduser("~/.config/opencode"))

# Import hardened base FIRST (sets up stdout UTF-8, signal handlers)
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_send, mcp_respond, mcp_error, mcp_initialize, mcp_tools_list, mcp_loop

BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "120"))  # seconds

def _log(m):
    try:
        print(f"[browser_mcp] {m}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _extract_browser_result(result) -> str:
    """
    browser_use API version-safe result extractor.
    v0.x: result.final_result() / result.extracted_content()
    v1.x: result is AgentHistoryList — iterate history
    v1.x alt: result.history[-1].result / result.all_results()
    """
    # v0.x methods
    for method in ("final_result", "extracted_content", "all_results"):
        try:
            fn = getattr(result, method, None)
            if fn:
                val = fn()
                if val:
                    return str(val) if not isinstance(val, list) else "\n".join(str(v) for v in val if v)
        except Exception:
            pass

    # v1.x: AgentHistoryList — last meaningful result
    try:
        if hasattr(result, "history") and result.history:
            for item in reversed(result.history):
                r = getattr(item, "result", None)
                if r and str(r).strip():
                    return str(r)
    except Exception:
        pass

    # v1.x: is_done + final answer attribute
    for attr in ("final_answer", "answer", "output", "content", "text"):
        try:
            val = getattr(result, attr, None)
            if val:
                return str(val)
        except Exception:
            pass

    # Absolute fallback — str() will at least give something
    raw = str(result)
    return raw if raw != "None" else "ERROR: Browser task completed but returned no output"


def _run_browser(task: str) -> str:
    """Run a browser_use agent task synchronously (wraps the async agent)."""
    try:
        from browser_use import Agent
        from llm_fallback import get_llm
        llm = get_llm(preferred="groq")
        agent = Agent(task=task, llm=llm)
        result = asyncio.run(asyncio.wait_for(agent.run(), timeout=BROWSER_TIMEOUT))
        return _extract_browser_result(result)
    except asyncio.TimeoutError:
        return f"ERROR: Browser task timed out ({BROWSER_TIMEOUT}s) — task may be too complex, try breaking it into steps"
    except ImportError:
        return "ERROR: browser_use not installed — run: pip install browser-use playwright && playwright install chromium"
    except Exception as e:
        return f"ERROR: Browser task failed — {type(e).__name__}: {e}"


# ── Tool handlers ────────────────────────────────────────────────────────────
def _t_browse(a):
    task = a.get("task", "")
    if not task or not task.strip():
        return "ERROR: Task cannot be empty — describe what you want the browser to do"
    return _run_browser(task)


def _t_browse_extract(a):
    url = a.get("url", "")
    what = a.get("what_to_extract", "")
    if not url.startswith(("http://", "https://")):
        return "ERROR: Invalid URL — must start with http:// or https://"
    task = f"Go to {url} and extract: {what}. Return only the extracted data."
    return _run_browser(task)


def _t_status(a):
    from llm_fallback import status_report
    return status_report()


TOOLS = [
    ("browse", "AI browser agent — navigate, click, fill forms, extract data from any website."),
    ("browse_extract", "Go to a specific URL and extract specific information. More reliable than browse() for simple data extraction tasks."),
    ("browser_llm_status", "Show current LLM provider status and key rotation state."),
]
SCHEMAS = {
    "browse": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]},
    "browse_extract": {"type": "object", "properties": {"url": {"type": "string"}, "what_to_extract": {"type": "string"}}, "required": ["url", "what_to_extract"]},
    "browser_llm_status": {"type": "object", "properties": {}},
}
HANDLERS = {
    "browse": _t_browse,
    "browse_extract": _t_browse_extract,
    "browser_llm_status": _t_status,
}


def _handle(msg):
    m = msg.get("method", "")
    rid = msg.get("id")
    if m == "initialize":
        mcp_initialize(rid, "browser-use")
    elif m == "tools/list":
        mcp_tools_list(rid, TOOLS, SCHEMAS)
    elif m == "tools/call":
        name = msg.get("params", {}).get("name", "")
        args = msg.get("params", {}).get("arguments", {})
        fn = HANDLERS.get(name)
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
    _log("started (plain MCP stdio)")
    mcp_loop("browser-use", _handle)


if __name__ == "__main__":
    main()
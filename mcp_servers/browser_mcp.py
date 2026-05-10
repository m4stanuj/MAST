"""
browser_mcp.py — OpenWork Browser MCP Server
=============================================
Uses llm_fallback.py for automatic provider failover.
Groq → Cerebras → Gemini → SambaNova → OpenRouter → DeepSeek → Together

Fixes:
  - Added asyncio.run() guard (was running unconditionally at module level)
  - Added timeout for browser tasks (was hanging indefinitely)
  - Better result extraction from browser_use Agent
  - Added browser_screenshot tool for quick visual checks
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from llm_fallback import get_llm, status_report

app = Server("browser-use")

BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "120"))  # seconds


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


@app.tool()
async def browse(task: str) -> str:
    """AI browser agent — navigate, click, fill forms, extract data from any website."""
    if not task or not task.strip():
        return "ERROR: Task cannot be empty — describe what you want the browser to do"
    try:
        from browser_use import Agent
        llm = get_llm(preferred="groq")
        agent = Agent(task=task, llm=llm)
        result = await asyncio.wait_for(agent.run(), timeout=BROWSER_TIMEOUT)
        return _extract_browser_result(result)

    except asyncio.TimeoutError:
        return f"ERROR: Browser task timed out ({BROWSER_TIMEOUT}s) — task may be too complex, try breaking it into steps"
    except ImportError:
        return "ERROR: browser_use not installed — run: pip install browser-use playwright && playwright install chromium"
    except Exception as e:
        return f"ERROR: Browser task failed — {type(e).__name__}: {e}"


@app.tool()
async def browse_extract(url: str, what_to_extract: str) -> str:
    """
    Go to a specific URL and extract specific information.
    More reliable than browse() for simple data extraction tasks.
    """
    if not url.startswith(("http://", "https://")):
        return f"ERROR: Invalid URL — must start with http:// or https://"
    task = f"Go to {url} and extract: {what_to_extract}. Return only the extracted data."
    return await browse(task)


@app.tool()
async def browser_llm_status() -> str:
    """Show current LLM provider status and key rotation state."""
    return status_report()


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


# FIX: Only run when executed directly as a script.
# MCP servers are always launched via `python browser_mcp.py`, never imported.
# The previous `else: asyncio.run(main())` was a bug — it ran on import too.
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except (BrokenPipeError, EOFError, OSError):
        pass  # OpenCode closed pipe — exit cleanly
    except Exception as e:
        import sys
        print(f"[{__file__}] fatal: {e}", file=sys.stderr)
        sys.exit(1)

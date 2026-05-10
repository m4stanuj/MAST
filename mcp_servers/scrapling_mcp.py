"""
scrapling_mcp.py — OpenWork Anti-Bot Scraper MCP
=================================================
Sync Fetcher runs in executor to avoid blocking async loop.

Fixes:
  - URL validation before scraping
  - asyncio.get_event_loop() deprecation fix (use get_running_loop)
  - Better error messages with failure reason
  - Timeout protection
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("scrapling")


def _validate_url(url: str) -> str | None:
    """Returns error string if invalid, None if OK."""
    if not url:
        return "URL cannot be empty"
    if not url.startswith(("http://", "https://")):
        return f"Invalid URL — must start with http:// or https:// (got: {url!r})"
    return None


@app.tool()
async def scrape(url: str) -> str:
    """Anti-bot web scraper — extract full text content from any URL without getting blocked."""
    err = _validate_url(url)
    if err:
        return f"ERROR: {err}"
    try:
        # FIX: Use get_running_loop() instead of deprecated get_event_loop()
        loop = asyncio.get_running_loop()

        def _fetch():
            from scrapling.defaults import Fetcher
            fetcher = Fetcher(auto_match=True)
            page = fetcher.get(url, timeout=30)
            text = page.get_all_text()
            if not text or not text.strip():
                return "WARNING: Page loaded but no text extracted (may be JS-heavy, try browser tool instead)"
            return text

        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        return f"ERROR: Scraping timed out (60s) — {url} is too slow or blocking"
    except Exception as e:
        return f"ERROR: Scraping failed — {type(e).__name__}: {e}"


@app.tool()
async def scrape_links(url: str) -> str:
    """Extract all links from a page. Useful for site mapping or finding specific pages."""
    err = _validate_url(url)
    if err:
        return f"ERROR: {err}"
    try:
        loop = asyncio.get_running_loop()

        def _fetch():
            from scrapling.defaults import Fetcher
            fetcher = Fetcher(auto_match=True)
            page = fetcher.get(url, timeout=30)
            links = page.find_all("a")
            results = []
            for link in links:
                href = link.attrib.get("href", "")
                text = link.text.strip() if link.text else ""
                if href and href.startswith("http"):
                    results.append(f"{text or '[no text]'}: {href}")
            return "\n".join(results[:100]) if results else "No links found"

        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        return f"ERROR: Timed out (60s)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


# FIX: Added __main__ guard — previous code ran asyncio.run(main()) at module
# level with no guard, causing crash when imported by other scripts.
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

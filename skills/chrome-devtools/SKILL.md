---
name: chrome-devtools
description: |
  Chrome DevTools MCP — full browser control: network inspection, console, performance, DOM.
  Better than basic browser MCP for debugging and scraping.

  Triggers when user says:
  - "browser debug", "inspect network", "chrome devtools"
  - "check console errors", "performance audit"
  - "DOM manipulation", "intercept requests"
---

# Chrome DevTools MCP

**Full Chrome DevTools access via MCP.**
Network inspection, console, performance profiling, DOM control.

**GitHub:** https://github.com/ChromeDevTools/chrome-devtools-mcp

---

## MCP Config

```jsonc
{
  "mcp": {
    "chrome-devtools": {
      "type": "local",
      "command": ["npx", "-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

No API key, no Chrome installation needed separately.

---

## Tools Available

### Network
- `get_network_requests` — Capture all HTTP requests/responses
- `intercept_request` — Modify requests on the fly
- `get_console_logs` — Read browser console output

### DOM & Page
- `evaluate_js` — Run JavaScript in page context
- `get_element` — Find elements by selector
- `screenshot` — Full page or element screenshot
- `get_page_source` — Full HTML source

### Performance
- `run_audit` — Lighthouse performance audit
- `get_paint_timing` — Core Web Vitals
- `profile_js` — CPU profiling

---

## OpenWork v6 Use Cases

```
# Debug your browser MCP server
chrome-devtools: get_console_logs(url="localhost:3000")

# Scraping alternative to scrapling (for JS-heavy sites)
chrome-devtools: evaluate_js(script="document.querySelectorAll('.price')")

# Audit your freelance portfolio site
chrome-devtools: run_audit(url="yoursite.com")

# Network monitoring for automation
chrome-devtools: get_network_requests(filter="api")
```

---

## vs. Your Existing Browser MCP

| Feature | Your Browser MCP | Chrome DevTools MCP |
|---------|-----------------|-------------------|
| Basic navigation | ✅ | ✅ |
| Network inspection | ❌ | ✅ |
| Console logs | ❌ | ✅ |
| JS execution | ❌ | ✅ |
| Performance audit | ❌ | ✅ |

**Verdict:** Add chrome-devtools as secondary, keep your browser MCP for navigation.

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Power | ✅ 10/10 |
| Official (Google) | ✅ 10/10 |
| Setup | ✅ Easy (npx) |

**Overall: 10/10** — Official Google tool. Production ready.

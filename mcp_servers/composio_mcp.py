"""
composio_mcp.py — OpenWork Composio API Integration MCP v1.0
Bridges OpenWork to 500+ apps: Gmail, Slack, GitHub, Notion, Calendar, etc.
Place in: C:/Users/<user>/.config/opencode/composio_mcp.py

Setup:
  1. Free account: https://composio.dev
  2. Get API key from dashboard
  3. Set COMPOSIO_API_KEY in opencode.json env OR as system env var
  4. Run: pip install composio-core
  5. Auth apps: python composio_mcp.py --auth gmail
"""
import sys, os, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import (
    mcp_send, mcp_respond, mcp_error,
    mcp_initialize, mcp_loop, mcp_tools_list
)

def _log(m): print(f"[composio_mcp] {m}", file=sys.stderr, flush=True)

# ── composio client (lazy init) ────────────────────────────────────────────
_composio = None

def _get_client():
    global _composio
    if _composio is not None:
        return _composio, None
    api_key = os.environ.get("COMPOSIO_API_KEY", "").strip()
    if not api_key or api_key.startswith("REPLACE"):
        return None, "COMPOSIO_API_KEY not set. Get free key from composio.dev"
    try:
        from composio import ComposioToolSet
        _composio = ComposioToolSet(api_key=api_key)
        return _composio, None
    except ImportError:
        return None, "composio-core not installed. Run: pip install composio-core"
    except Exception as e:
        return None, f"Composio init failed: {e}"

# ── tools ──────────────────────────────────────────────────────────────────
TOOLS = [
    ("composio_list_apps",    "List all connected/available apps (Gmail, Slack, GitHub, etc.)"),
    ("composio_run_action",   "Run any Composio action. E.g. GMAIL_SEND_EMAIL, SLACK_SEND_MESSAGE, GITHUB_CREATE_ISSUE"),
    ("composio_list_actions", "List all available actions for a specific app (e.g. GMAIL, SLACK, GITHUB)"),
    ("composio_auth_status",  "Check authentication status for a specific app"),
]

SCHEMAS = {
    "composio_list_apps": {
        "type": "object",
        "properties": {
            "filter": {"type": "string", "description": "Optional filter string e.g. 'google', 'slack'"}
        }
    },
    "composio_run_action": {
        "type": "object",
        "properties": {
            "action":  {"type": "string",  "description": "Action name e.g. GMAIL_SEND_EMAIL, SLACK_SEND_MESSAGE, GITHUB_CREATE_ISSUE, NOTION_CREATE_PAGE"},
            "params":  {"type": "object",  "description": "Action parameters as JSON object"},
            "user_id": {"type": "string",  "description": "User ID (optional, default: 'default')"}
        },
        "required": ["action", "params"]
    },
    "composio_list_actions": {
        "type": "object",
        "properties": {
            "app": {"type": "string", "description": "App name e.g. GMAIL, SLACK, GITHUB, NOTION, CALENDAR, DRIVE"}
        },
        "required": ["app"]
    },
    "composio_auth_status": {
        "type": "object",
        "properties": {
            "app": {"type": "string", "description": "App name to check e.g. GMAIL, SLACK, GITHUB"}
        },
        "required": ["app"]
    }
}

# ── handlers ───────────────────────────────────────────────────────────────
def _t_composio_list_apps(a):
    client, err = _get_client()
    if err: return f"❌ {err}"
    try:
        filter_str = a.get("filter", "").lower()
        apps = client.get_connected_accounts()
        lines = ["Connected apps:"]
        for app in apps:
            name = getattr(app, 'appName', str(app))
            if not filter_str or filter_str in name.lower():
                lines.append(f"  ✅ {name}")
        if len(lines) == 1:
            lines.append("  (none connected yet — run composio_auth_status to check)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing apps: {e}\nTip: Connect apps at composio.dev/dashboard"

def _t_composio_run_action(a):
    client, err = _get_client()
    if err: return f"❌ {err}"
    action  = a.get("action", "").strip().upper()
    params  = a.get("params", {})
    user_id = a.get("user_id", "default")
    if not action: return "Error: action name required"
    try:
        result = client.execute_action(
            action=action,
            params=params,
            entity_id=user_id
        )
        if hasattr(result, '__dict__'):
            return json.dumps(result.__dict__, indent=2, default=str)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error running {action}: {e}"

def _t_composio_list_actions(a):
    client, err = _get_client()
    if err: return f"❌ {err}"
    app = a.get("app", "").strip().upper()
    if not app: return "Error: app name required"
    try:
        from composio import App
        actions = client.get_tools(apps=[app])
        lines = [f"Actions for {app}:"]
        for act in actions[:30]:  # limit to 30
            name = getattr(act, 'name', str(act))
            desc = getattr(act, 'description', '')[:80]
            lines.append(f"  • {name}: {desc}")
        if len(actions) > 30:
            lines.append(f"  ... and {len(actions)-30} more")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing {app} actions: {e}"

def _t_composio_auth_status(a):
    client, err = _get_client()
    if err: return f"❌ {err}"
    app = a.get("app", "").strip().upper()
    if not app: return "Error: app name required"
    try:
        accounts = client.get_connected_accounts()
        for acc in accounts:
            if app.lower() in str(getattr(acc, 'appName', '')).lower():
                return f"✅ {app} is connected\nAccount: {getattr(acc, 'id', 'unknown')}"
        return (f"❌ {app} not connected\n"
                f"To connect, run in terminal:\n"
                f"  pip install composio-core\n"
                f"  composio login\n"
                f"  composio add {app.lower()}")
    except Exception as e:
        return f"Error checking {app}: {e}"

_HANDLERS = {
    "composio_list_apps":    _t_composio_list_apps,
    "composio_run_action":   _t_composio_run_action,
    "composio_list_actions": _t_composio_list_actions,
    "composio_auth_status":  _t_composio_auth_status,
}

# ── CLI auth helper ────────────────────────────────────────────────────────
def _cli_auth(app_name: str):
    """python composio_mcp.py --auth gmail"""
    try:
        import subprocess
        print(f"Authenticating {app_name}...")
        subprocess.run(["composio", "add", app_name], check=True)
        print(f"✅ {app_name} connected!")
    except FileNotFoundError:
        print("composio CLI not found. Run: pip install composio-core && composio login")
    except Exception as e:
        print(f"Error: {e}")

# ── MCP loop ───────────────────────────────────────────────────────────────
def _handle(req):
    rid    = req.get("id")
    method = req.get("method", "")

    if method == "initialize":
        mcp_initialize(rid, "composio-mcp", "1.0.0")

    elif method == "tools/list":
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
    # CLI auth helper
    if len(sys.argv) >= 3 and sys.argv[1] == "--auth":
        _cli_auth(sys.argv[2])
        sys.exit(0)

    _log("Composio MCP v1.0 started — 4 tools ready")
    _log(f"API key: {'SET ✅' if os.environ.get('COMPOSIO_API_KEY') else 'NOT SET ❌ — add to opencode.json env'}")
    mcp_loop("composio-mcp", _handle)

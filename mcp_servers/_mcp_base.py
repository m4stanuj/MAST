"""
_mcp_base.py — OpenWork MCP Shared Base v8
===========================================
HARDENED: BrokenPipe + EOF + SIGTERM + stdout encoding all handled.
Every MCP server imports this — one fix here = all servers fixed.
"""
import sys, os, json, signal, logging
from pathlib import Path

# ── stdout: force UTF-8, no buffering (Windows fix) ───────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── suppress broken pipe on Windows (SIGPIPE doesn't exist) ───────────
if sys.platform != "win32":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def get_config_dir() -> Path:
    env = os.environ.get("OPENWORK_CONFIG")
    if env: return Path(env)
    return Path(os.path.expanduser("~/.config/opencode"))

# ── Safe send: never crash on BrokenPipe ──────────────────────────────
def mcp_send(obj: dict):
    try:
        line = json.dumps(obj, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        # OpenCode closed the pipe — exit cleanly
        sys.exit(0)
    except Exception as e:
        try:
            sys.stderr.write(f"[mcp_base] send error: {e}\n")
            sys.stderr.flush()
        except Exception:
            pass

def mcp_respond(req_id, result_text: str):
    mcp_send({"jsonrpc": "2.0", "id": req_id,
              "result": {"content": [{"type": "text", "text": str(result_text)}]}})

def mcp_error(req_id, code: int, msg: str):
    mcp_send({"jsonrpc": "2.0", "id": req_id,
              "error": {"code": code, "message": str(msg)}})

def mcp_initialize(req_id, server_name: str, version: str = "1.0.0"):
    mcp_send({"jsonrpc": "2.0", "id": req_id, "result": {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": server_name, "version": version}
    }})

def mcp_tools_list(req_id, tools: list, schemas: dict):
    mcp_send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": [
        {"name": n, "description": d,
         "inputSchema": schemas.get(n, {"type": "object", "properties": {}})}
        for n, d in tools
    ]}})

def ensure_llm_fallback(config_dir: Path):
    p = str(config_dir)
    if p not in sys.path:
        sys.path.insert(0, p)

def brain(prompt: str, max_tokens: int = 800, config_dir: Path = None) -> str:
    if config_dir:
        ensure_llm_fallback(config_dir)
    try:
        from llm_fallback import chat_complete
        return chat_complete([{"role": "user", "content": prompt}],
                             max_tokens=max_tokens, use_cache=True)
    except Exception as e:
        return f"ERROR: {e}"

# ── THE HARDENED LOOP ─────────────────────────────────────────────────
def mcp_loop(server_name: str, handler_fn):
    """
    Crash-proof MCP stdin loop.
    Handles: BrokenPipeError, EOFError, KeyboardInterrupt, OSError, encoding errors.
    Any unhandled exception per-line is logged but loop CONTINUES (no crash).
    """
    _log = lambda m: _safe_stderr(f"[{server_name}] {m}")

    def _safe_stderr(msg):
        try:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except Exception:
            pass

    # SIGTERM: exit cleanly instead of traceback
    def _on_sigterm(sig, frame):
        _log("SIGTERM received — shutting down cleanly")
        sys.exit(0)
    try:
        signal.signal(signal.SIGTERM, _on_sigterm)
    except (OSError, ValueError):
        pass  # Can't set signal in some contexts

    _log("loop started")
    try:
        for raw_line in sys.stdin:
            # Decode issues
            if isinstance(raw_line, bytes):
                try:
                    raw_line = raw_line.decode("utf-8", errors="replace")
                except Exception:
                    continue

            line = raw_line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError as e:
                _log(f"JSON decode error: {e} | line={line[:80]}")
                continue

            try:
                handler_fn(msg)
            except (BrokenPipeError, OSError):
                _log("pipe broken — exiting cleanly")
                sys.exit(0)
            except SystemExit:
                raise
            except Exception as e:
                _log(f"handler error (continuing): {type(e).__name__}: {e}")
                # Try to send error back to client
                req_id = msg.get("id")
                if req_id is not None:
                    try:
                        mcp_error(req_id, -32000, f"Internal error: {type(e).__name__}: {e}")
                    except Exception:
                        pass

    except (EOFError, BrokenPipeError, OSError):
        _log("stdin closed — exiting cleanly")
        sys.exit(0)
    except KeyboardInterrupt:
        _log("KeyboardInterrupt — exiting cleanly")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        _log(f"FATAL loop error: {type(e).__name__}: {e}")
        sys.exit(1)

    _log("stdin EOF — loop ended normally")
